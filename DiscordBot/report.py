import discord
import shortuuid
from helpers import ABUSE_TYPES, REPORT_CONFIRMATION_MESSAGE, quote_message
from moderator_views import ModeratorActionView
from report_views import MainReportView


class Report:
    def __init__(self, client, interaction, message):
        self.client = client
        self.id = shortuuid.uuid()[:8]

        message_link = f"https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id}"
        self.report_data = {
            "reported_message": message,
            "interaction": interaction,
            "message_link": message_link,
            "report_type": None,
            "abuse_category": None,
            "subtypes": [],  # List to store the chain of subtypes
            "additional_info": None,  # Optional additional information
            "report_thread": None,  # Store the report thread
            "mod_thread": None,  # Store the moderation thread
        }

    async def show_report_view(self):
        """Show the message being reported and walk the user through the report flow"""
        # Create a thread in the channel where the message was reported
        message = self.report_data["reported_message"]
        reporter = self.report_data["interaction"].user

        # Create a private thread in the channel
        thread = await message.channel.create_thread(
            name=f"Report from {reporter.name}",
            auto_archive_duration=1440,  # 24 hours
            type=discord.ChannelType.private_thread,
        )

        # Add the reporter to the thread
        await thread.add_user(reporter)

        # Send the reported message in the thread
        await thread.send(f"Reported message: {message.jump_url}")

        self.report_data["report_thread"] = thread

        # Send initial report view in the thread
        embed = self.create_main_embed(message)
        view = MainReportView(self)
        await thread.send(embed=embed, view=view)

        # Notify the user that the report thread was created
        await self.report_data["interaction"].response.send_message(
            f"Report thread created: {thread.mention}", ephemeral=True
        )

    def create_main_embed(self, message):
        """Create the main report embed"""
        embed = discord.Embed(
            title="Report a Message",
            description="Please select a reason for reporting this message by clicking one of the buttons below.",
            color=discord.Color.blue(),
        )

        # Show the profile picture of the reported user as thumbnail
        embed.set_thumbnail(url=message.author.display_avatar.url if message.author.display_avatar else None)
        embed.add_field(name="Reported Message", value=quote_message(message), inline=False)
        embed.add_field(name="Message Author", value=f"{message.author.mention}", inline=False)
        embed.add_field(name="Channel", value=f"{message.channel.mention}", inline=False)
        embed.timestamp = message.created_at

        return embed

    def add_report_details(self, embed):
        """Add the report details to the embed"""
        message = self.report_data["reported_message"]
        reporter = self.report_data["interaction"].user

        # Add report details based on abuse type
        abuse_category = self.report_data.get("abuse_category")
        if abuse_category and abuse_category in ABUSE_TYPES:
            abuse_type = ABUSE_TYPES[abuse_category]
            embed.add_field(name="Report Type", value=abuse_type.label)

            # Add all subtypes in the chain
            current_type = abuse_type
            for subtype_key in self.report_data["subtypes"]:
                if current_type.subtypes and subtype_key in current_type.subtypes:
                    subtype = current_type.subtypes[subtype_key]
                    embed.add_field(name="Subtype", value=subtype.label)
                    current_type = subtype

        else:
            # Fallback
            embed.add_field(name="Report Type", value=self.report_data.get("report_type", "Other"))

        embed.add_field(name="Message Author", value=f"{message.author.mention}", inline=True)
        embed.add_field(name="Channel", value=self.report_data["message_link"], inline=True)
        embed.add_field(name="Message Content", value=quote_message(message), inline=False)
        embed.add_field(name="Reported by", value=f"{reporter.mention}")

        # Add additional information if provided
        if self.report_data.get("additional_info"):
            embed.add_field(
                name="Additional Information", value=self.report_data["additional_info"], inline=False
            )

        embed.set_footer(text=f"Report ID: {self.id}")
        embed.timestamp = discord.utils.utcnow()

    async def submit_report_to_mods(self):
        """Submit the completed report to moderators"""
        # Get the mod channel for this server
        guild_id = self.report_data["reported_message"].guild.id
        mod_channel = self.client.mod_channels.get(guild_id)
        if not mod_channel:
            assert False, "Mod channel not found for this server"

        # Create a public thread in the mod channel for this report
        abuse_category_key = self.report_data.get("abuse_category")
        if abuse_category_key in ABUSE_TYPES:
            abuse_category_label = ABUSE_TYPES[abuse_category_key].label
        else:
            abuse_category_label = "Other"

        thread = await mod_channel.create_thread(
            name=f"New Report - {abuse_category_label}",
            auto_archive_duration=1440,  # 24 hours
            type=discord.ChannelType.public_thread,
        )
        self.report_data["mod_thread"] = thread

        # Create an embed for moderators
        embed = discord.Embed(title="New Report", description="", color=discord.Color.red())
        self.add_report_details(embed)

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
        await self.report_data["report_thread"].send(embed=embed)
