# bot.py
import discord
from discord.ext import commands
from discord import app_commands
import os
import json
import logging
import re
from report import Report
from collections import defaultdict

# Set up logging to the console
logger = logging.getLogger("discord")
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")
handler.setFormatter(logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s"))
logger.addHandler(handler)


class ModBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.reactions = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)

        self.group_num = None
        self.mod_channels = {}  # Map from guild to the mod channel id for that guild
        self.active_reports = {}  # Maps from (report_id) to (user_id, report_object)

    async def setup_hook(self):
        """This executes when the bot is starting up"""

        # Register the context menu command
        # - This allows the user to right click a message, go to Apps, and select "Report Message"
        # - When the user clicks this, it will trigger the report_message function
        self.tree.add_command(
            app_commands.ContextMenu(
                name="Report Message", callback=self.report_message, type=discord.AppCommandType.message
            )
        )

        # Sync commands with Discord
        await self.tree.sync()
        logger.info("Context menu commands synced with Discord")

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

    async def report_message(self, interaction: discord.Interaction, message: discord.Message):
        """
        When a user right clicks a message and selects 'Report Message', this function is called
        """
        logger.info(
            f"Report message triggered by {interaction.user} against {message.author} in {message.channel.name}"
        )

        # Create a new Report object and add it to the reports dictionary
        report = Report(self, interaction, message)
        self.active_reports[report.id] = (interaction.user.id, report)
        await report.show_report_view()


if __name__ == "__main__":
    # There should be a file called 'tokens.json' inside the same folder as this file
    token_path = "tokens.json"
    if not os.path.isfile(token_path):
        raise Exception(f"{token_path} not found!")
    with open(token_path) as f:
        # If you get an error here, it means your token is formatted incorrectly. Did you put it in quotes?
        tokens = json.load(f)
        discord_token = tokens["discord"]

    bot = ModBot()
    bot.run(discord_token)
