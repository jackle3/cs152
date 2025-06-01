# bot.py
import discord
from discord.ext import commands
from discord import app_commands
import os
import json
import logging
import re
from report import Report

# Set up logging to the console
logger = logging.getLogger("discord")
logger.setLevel(logging.DEBUG)
os.makedirs("logs", exist_ok=True)
handler = logging.FileHandler(filename="logs/discord.log", encoding="utf-8", mode="w")
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

    def _is_mod_channel(self, channel):
        """Check if the given channel is a mod channel for its guild"""
        if not hasattr(channel, "guild") or not channel.guild:
            return False
        return self.mod_channels.get(channel.guild.id) == channel

    def _get_abuse_types(self):
        """Get abuse types (importing here to avoid circular imports)"""
        from abuse_types import ABUSE_TYPES

        return ABUSE_TYPES

    async def on_ready(self):
        logger.info(f"{self.user.name} has connected to Discord! It is in these guilds:")
        for guild in self.guilds:
            logger.info(f" - {guild.name}")
        logger.info("Press Ctrl-C to quit.")

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
        logger.info(f"{interaction.user.name} reported {message.author} in {message.channel.name}")

        # Create a new Report object and add it to the reports dictionary
        report = Report(self, interaction, message)
        self.active_reports[report.id] = (interaction.user.id, report)
        await report.show_report_view()


########################################################
# Initialization
########################################################

# There should be a file called 'tokens.json' inside the same folder as this file
token_path = "tokens.json"
if not os.path.isfile(token_path):
    raise Exception(f"{token_path} not found!")
with open(token_path) as f:
    # If you get an error here, it means your token is formatted incorrectly. Did you put it in quotes?
    tokens = json.load(f)
    discord_token = tokens["discord"]

bot = ModBot()


########################################################
# Commands
########################################################
@bot.command(name="list_reports")
async def list_reports(ctx):
    """List all active reports in the mod channel (Moderators only)"""
    # Check if this is being used in a mod channel
    if not ctx.bot._is_mod_channel(ctx.channel):
        await ctx.send("❌ This command can only be used in moderator channels.")
        return

    # Get active reports for this guild
    guild_reports = []
    for report_id, (user_id, report) in ctx.bot.active_reports.items():
        if report.reported_message.guild.id == ctx.guild.id and report.active:
            guild_reports.append(report)

    if not guild_reports:
        embed = discord.Embed(
            title="📋 Active Reports",
            description="No active reports at this time.",
            color=discord.Color.green(),
        )
        await ctx.send(embed=embed)
        return

    # Create embed with report list
    embed = discord.Embed(
        title="📋 Active Reports",
        description=f"Found {len(guild_reports)} active report(s)",
        color=discord.Color.orange(),
    )

    for i, report in enumerate(guild_reports[:10]):  # Limit to 10 reports to avoid embed limits
        # Get report type with emoji
        if report.abuse_category and report.abuse_category in ctx.bot._get_abuse_types():
            abuse_type = ctx.bot._get_abuse_types()[report.abuse_category]
            type_text = f"{abuse_type.emoji} {abuse_type.label}"
        else:
            type_text = "❓ Other"

        # Get subtype if available
        if report.subtypes and report.abuse_category in ctx.bot._get_abuse_types():
            abuse_type = ctx.bot._get_abuse_types()[report.abuse_category]
            if abuse_type.subtypes and report.subtypes[0] in abuse_type.subtypes:
                subtype = abuse_type.subtypes[report.subtypes[0]]
                type_text += f" → {subtype.emoji} {subtype.label}"

        # Create field for this report
        embed.add_field(
            name=f"Report #{report.id}",
            value=f"**Type:** {type_text}\n"
            f"**Reporter:** <@{ctx.bot.active_reports[report.id][0]}>\n"
            f"**Target:** {report.reported_message.author.mention}\n"
            f"**Message:** [Jump to Moderator Action]({report.mod_message.jump_url})",
            inline=False,
        )

    if len(guild_reports) > 10:
        embed.set_footer(text=f"Showing first 10 of {len(guild_reports)} reports")

    await ctx.send(embed=embed)


########################################################
# Run the bot
########################################################
bot.run(discord_token)
