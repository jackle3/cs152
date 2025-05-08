# bot.py
import discord
from discord.ext import commands
import os
import json
import logging
import re
import requests
from report import Report
import pdb

# Set up logging to the console
logger = logging.getLogger("discord")
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")
handler.setFormatter(logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s"))
logger.addHandler(handler)

# There should be a file called 'tokens.json' inside the same folder as this file
token_path = "tokens.json"
if not os.path.isfile(token_path):
    raise Exception(f"{token_path} not found!")
with open(token_path) as f:
    # If you get an error here, it means your token is formatted incorrectly. Did you put it in quotes?
    tokens = json.load(f)
    discord_token = tokens["discord"]


class ModBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.reactions = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)

        self.group_num = None
        self.mod_channels = {}  # Map from guild to the mod channel id for that guild
        self.reports = {}  # Map from user IDs to the state of their report
        self.active_reports = []  # List of completed reports waiting for moderation

    async def on_ready(self):
        print(f"{self.user.name} has connected to Discord! It is these guilds:")
        for guild in self.guilds:
            print(f" - {guild.name}")
        print("Press Ctrl-C to quit.")

        # Parse the group number out of the bot's name
        match = re.search(r"[gG]roup (\d+) [bB]ot", self.user.name)
        if match:
            self.group_num = match.group(1)
        else:
            raise Exception('Group number not found in bot\'s name. Name format should be "Group # Bot".')

        # Find the mod channel in each guild that this bot should report to
        for guild in self.guilds:
            for channel in guild.text_channels:
                if channel.name == f"group-{self.group_num}-mod":
                    self.mod_channels[guild.id] = channel

    async def on_message(self, message):
        """
        This function is called whenever a message is sent in a channel that the bot can see (including DMs).
        Currently the bot is configured to only handle messages that are sent over DMs or in your group's "group-#" channel.
        """
        # Ignore messages from the bot
        if message.author.id == self.user.id:
            return

        # Check if this message was sent in a server ("guild") or if it's a DM
        if message.guild:
            await self.handle_channel_message(message)
        else:
            await self.handle_dm(message)

    async def on_reaction_add(self, reaction, user):
        """Handle reactions to bot messages"""
        print(
            f"on_reaction_add fired: reaction={reaction.emoji}, user={user}, channel={reaction.message.channel}"
        )
        # Ignore reactions from the bot
        if user.id == self.user.id:
            return

        # Find the report for this user
        if user.id not in self.reports:
            print("No report found for this user.")
            return

        # Convert reaction to message content format
        emoji = str(reaction.emoji)
        if emoji not in ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]:
            print(f"Emoji {emoji} not in allowed list.")
            return

        # Create a fake message with the reaction as content
        fake_message = type(
            "Message", (), {"content": emoji, "author": user, "channel": reaction.message.channel}
        )

        # Handle the reaction as if it were a message
        responses = await self.reports[user.id].handle_message(fake_message)
        for r in responses:
            await reaction.message.channel.send(r)

        # If the report is complete or cancelled, remove it from our map and add to active reports
        if self.reports[user.id].report_complete():
            completed_report = self.reports[user.id]
            self.active_reports.append(completed_report)
            # Notify moderators
            for guild_id, mod_channel in self.mod_channels.items():
                await mod_channel.send("New report received:\n" + completed_report.get_report_summary())
            self.reports.pop(user.id)

    async def handle_dm(self, message):
        # Handle a help message
        if message.content == Report.HELP_KEYWORD:
            reply = "Use the `report` command to begin the reporting process.\n"
            reply += "Use the `cancel` command to cancel the report process.\n"
            await message.channel.send(reply)
            return

        author_id = message.author.id
        responses = []

        # Only respond to messages if they're part of a reporting flow
        if author_id not in self.reports and not message.content.startswith(Report.START_KEYWORD):
            return

        # If we don't currently have an active report for this user, add one
        if author_id not in self.reports:
            self.reports[author_id] = Report(self)

        # Let the report class handle this message; forward all the messages it returns to us
        responses = await self.reports[author_id].handle_message(message)
        for r in responses:
            await message.channel.send(r)

        # If the report is complete or cancelled, remove it from our map and add to active reports
        if self.reports[author_id].report_complete():
            completed_report = self.reports[author_id]
            self.active_reports.append(completed_report)
            # Notify moderators
            for guild_id, mod_channel in self.mod_channels.items():
                await mod_channel.send("New report received:\n" + completed_report.get_report_summary())
            self.reports.pop(author_id)

    async def handle_channel_message(self, message):
        # Only handle messages sent in the "group-#" channel or mod channel
        if message.channel.name == f"group-{self.group_num}-mod":
            await self.handle_mod_channel_message(message)
        elif message.channel.name == f"group-{self.group_num}":
            # Forward the message to the mod channel
            mod_channel = self.mod_channels[message.guild.id]
            await mod_channel.send(f'Forwarded message:\n{message.author.name}: "{message.content}"')
            scores = self.eval_text(message.content)
            await mod_channel.send(self.code_format(scores))

    async def handle_mod_channel_message(self, message):
        """Handle messages in the moderation channel"""
        if not message.content.startswith("!mod"):
            return

        # Parse moderation command
        # Format: !mod <report_index> <action>
        # Actions: warn, delete, ban
        try:
            _, report_index, action = message.content.split()
            report_index = int(report_index)

            if report_index < 0 or report_index >= len(self.active_reports):
                await message.channel.send("Invalid report index")
                return

            report = self.active_reports[report_index]
            result = report.moderate(action)

            # Simulate the action
            if action == "warn":
                await message.channel.send(
                    f"Warning sent to user {report.report_data['reported_message'].author.name}"
                )
            elif action == "delete":
                await message.channel.send(
                    f"Message from {report.report_data['reported_message'].author.name} would be deleted"
                )
            elif action == "ban":
                await message.channel.send(
                    f"User {report.report_data['reported_message'].author.name} would be banned"
                )

            await message.channel.send(result)

            # Remove the report from active reports
            self.active_reports.pop(report_index)

        except ValueError:
            await message.channel.send("Invalid command format. Use: !mod <report_index> <action>")

    def eval_text(self, message):
        """'
        TODO: Once you know how you want to evaluate messages in your channel,
        insert your code here! This will primarily be used in Milestone 3.
        """
        return message

    def code_format(self, text):
        """'
        TODO: Once you know how you want to show that a message has been
        evaluated, insert your code here for formatting the string to be
        shown in the mod channel.
        """
        return "Evaluated: '" + text + "'"


client = ModBot()
client.run(discord_token)
