import discord
import shortuuid
from helpers import ABUSE_TYPES, REPORT_CONFIRMATION_MESSAGE, quote_message, add_report_details_to_embed
from moderator_views import ModeratorActionView
from report_views import MainReportView


class Report:
    def __init__(self, client, interaction, message):
        self.client = client
        self.id = shortuuid.uuid()[:8]

        # Core report data
        self.reported_message = message
        self.interaction = interaction

        # Report details
        self.report_type = None
        self.abuse_category = None
        self.subtypes = []  # List to store the chain of subtypes
        self.additional_info = None

        # Threads
        self.report_thread = None
        self.mod_thread = None

        # Whether the report is still active and can be acted upon
        self.active = True

    async def show_report_view(self):
        """Show the message being reported and walk the user through the report flow"""
        reporter = self.interaction.user

        # Create a private thread in the channel where the message was reported
        thread = await self.reported_message.channel.create_thread(
            name=f"Report from {reporter.name}",
            auto_archive_duration=1440,  # 24 hours
            type=discord.ChannelType.private_thread,
        )
        self.report_thread = thread

        # Add the reporter to the thread
        await thread.add_user(reporter)

        # Send initial report view in the thread
        embed = self.create_main_embed()
        view = MainReportView(self)
        await thread.send(embed=embed, view=view)

        # Notify the user that the report thread was created
        await self.interaction.response.send_message(
            f"Report thread created: {thread.mention}", ephemeral=True
        )

    def create_main_embed(self):
        """Create the main report embed"""
        embed = discord.Embed(
            title="Report a Message",
            description="Please select a reason for reporting this message by clicking one of the buttons below.",
            color=discord.Color.blue(),
        )

        # Show the profile picture of the reported user as thumbnail
        embed.set_thumbnail(
            url=(
                self.reported_message.author.display_avatar.url
                if self.reported_message.author.display_avatar
                else None
            )
        )
        embed.add_field(name="Reported Message", value=quote_message(self.reported_message), inline=False)
        embed.add_field(name="Message Author", value=self.reported_message.author.mention, inline=False)
        embed.add_field(name="Channel", value=self.reported_message.jump_url, inline=False)
        embed.timestamp = self.reported_message.created_at

        return embed

    async def submit_report_to_mods(self):
        """Submit the completed report to moderators"""
        # Get the mod channel for this server
        guild_id = self.reported_message.guild.id
        mod_channel = self.client.mod_channels.get(guild_id)
        if not mod_channel:
            assert False, "Mod channel not found for this server"

        # Create a public thread in the mod channel for this report
        if self.abuse_category in ABUSE_TYPES:
            abuse_category_label = ABUSE_TYPES[self.abuse_category].label
        else:
            abuse_category_label = "Other"

        thread = await mod_channel.create_thread(
            name=f"New Report - {abuse_category_label}",
            auto_archive_duration=1440,  # 24 hours
            type=discord.ChannelType.public_thread,
        )
        self.mod_thread = thread

        # Create an embed for moderators
        embed = discord.Embed(title="New Report", description="", color=discord.Color.red())
        add_report_details_to_embed(embed, self)

        # Send to mod thread with appropriate action buttons
        view = ModeratorActionView(self)
        await thread.send(embed=embed, view=view)

        # Send confirmation to the report thread
        await self.send_confirmation()

    async def send_confirmation(self):
        """Show confirmation message after report submission"""
        embed = discord.Embed(
            title="Report Submitted",
            description=REPORT_CONFIRMATION_MESSAGE,
            color=discord.Color.green(),
        )
        # Send confirmation to the report thread
        await self.report_thread.send(embed=embed)
