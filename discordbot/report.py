import discord
import shortuuid
from abuse_types import ABUSE_TYPES, REPORT_CONFIRMATION_MESSAGE
from helpers import quote_message, add_report_details_to_embed
from moderation_flow import ModeratorView
from report_views import MainReportView


class Report:
    def __init__(self, client, interaction, message, automatic=False, agent_data=None):
        self.client = client
        self.id = shortuuid.uuid()[:8]

        # Core report data
        self.reported_message = message
        self.interaction = interaction
        self.is_automatic = automatic

        # Agent data for automatic reports
        if automatic and agent_data:
            self.agent_abuse_type = agent_data.get("abuse_type")
            self.agent_fraud_subtype = agent_data.get("fraud_subtype")
            self.agent_severity = agent_data.get("severity")
            self.agent_confidence = agent_data.get("confidence")
            if self.agent_confidence:
                self.agent_confidence = int(self.agent_confidence * 100)
            self.agent_reasoning = agent_data.get("reasoning")

            valid_categories = list(set(ABUSE_TYPES.keys()) - {"other"})
            if self.agent_abuse_type and self.agent_abuse_type.lower() in valid_categories:
                self.abuse_category = self.agent_abuse_type.lower()
            else:
                print(f"Agent returned unexpected abuse type: '{self.agent_abuse_type}'. Using 'other'.")
                self.abuse_category = "other"

            valid_subtypes = list(ABUSE_TYPES["fraud"].subtypes.keys())
            if self.agent_fraud_subtype and self.agent_fraud_subtype.lower() in valid_subtypes:
                self.subtypes = [self.agent_fraud_subtype.lower()]
            else:
                if self.agent_fraud_subtype:
                    print(
                        f"Agent returned unexpected fraud subtype: '{self.agent_fraud_subtype}'. Using empty list."
                    )
                self.subtypes = []

            self.additional_info = f"Agent Reasoning: {self.agent_reasoning}"
        else:
            # Initialize as None for manual reports (will be filled by user)
            self.agent_abuse_type = None
            self.agent_fraud_subtype = None
            self.agent_severity = None
            self.agent_confidence = None
            self.agent_reasoning = None

            # Report details
            self.abuse_category = None
            self.subtypes = []
            self.additional_info = None

        # Threads
        self.report_thread = None
        self.mod_thread = None
        self.mod_message = None

        # Whether the report is still active and can be acted upon
        self.active = True

        # Moderation flow data
        self.message_action = None  # What to do with the message
        self.user_action = None  # What to do with the user
        self.severity_level = None  # Severity level of the violation

        # Message tracking for cleanup
        self.bot_messages = (
            []
        )  # Track bot messages in order: [main_message, subtype_message, additional_info_message]
        self.main_message = None  # The initial message with abuse type buttons

    async def cleanup_messages_from_step(self, step_index):
        """Delete bot messages from a specific step onwards

        Args:
            step_index: 0=main message, 1=subtype message, 2=additional info message, etc.
        """
        try:
            # Delete messages from the specified step onwards
            messages_to_delete = self.bot_messages[step_index + 1 :]
            for msg in messages_to_delete:
                if msg:
                    try:
                        await msg.delete()
                    except (discord.NotFound, discord.Forbidden):
                        pass  # Message already deleted or no permissions

            # Remove deleted messages from tracking
            self.bot_messages = self.bot_messages[: step_index + 1]
        except IndexError:
            pass  # No messages to delete

    def add_bot_message(self, message):
        """Add a bot message to tracking"""
        self.bot_messages.append(message)

    async def show_report_view(self):
        """Show the message being reported and walk the user through the report flow"""
        reporter = self.interaction.user

        # Create a private thread in the channel where the message was reported
        thread = await self.reported_message.channel.create_thread(
            name=f"🚨 Report from {reporter.display_name}",
            auto_archive_duration=1440,  # 24 hours
            type=discord.ChannelType.private_thread,
        )
        self.report_thread = thread

        # Add the reporter to the thread
        await thread.add_user(reporter)

        # Send initial report view in the thread
        embed = self.create_main_embed()
        view = MainReportView(self)
        self.main_message = await thread.send(embed=embed, view=view)
        self.add_bot_message(self.main_message)

        # Notify the user that the report thread was created
        await self.interaction.response.send_message(
            f"📝 Report thread created: {thread.mention}. Please click to continue.",
            ephemeral=True,
            delete_after=60,
        )

    def create_main_embed(self):
        """Create the main report embed with improved formatting"""
        embed = discord.Embed(
            title="🚨 Report a Message",
            description="Please select the type of violation you want to report. Our team prioritizes fraud and scam detection.",
            color=discord.Color.red(),
        )

        # Show the profile picture of the reported user as thumbnail
        embed.set_thumbnail(
            url=(
                self.reported_message.author.display_avatar.url
                if self.reported_message.author.display_avatar
                else None
            )
        )

        # Add message details in a more organized way
        embed.add_field(name="📝 Reported Message", value=quote_message(self.reported_message), inline=False)
        embed.add_field(name="👤 Message Author", value=self.reported_message.author.mention, inline=True)
        embed.add_field(
            name="📍 Location", value=f"[Jump to message]({self.reported_message.jump_url})", inline=True
        )

        # Add helpful note about fraud reporting
        embed.add_field(
            name="💡 Quick Tip",
            value="If this looks like a scam or fraud, please select **⚠️ Fraud & Scams** and provide as much detail as possible.",
            inline=False,
        )

        embed.set_footer(text=f"Report ID: {self.id}")
        embed.timestamp = self.reported_message.created_at

        return embed

    async def submit_report_to_mods(self):
        """Submit the completed report to moderators"""
        # Get the mod channel for this server
        guild_id = self.reported_message.guild.id
        mod_channel = self.client.mod_channels.get(guild_id)
        if not mod_channel:
            # Handle the case where mod channel is not found more gracefully
            if self.is_automatic:
                # For automatic reports, log the error
                print(f"No mod channel configured for guild {guild_id}")
                return
            else:
                # For manual reports, show error in thread
                error_embed = discord.Embed(
                    title="❌ Configuration Error",
                    description="Moderator channel not configured for this server. Please contact an administrator.",
                    color=discord.Color.red(),
                )
                await self.report_thread.send(embed=error_embed)
                return

        # Create appropriate embed based on report type
        if self.is_automatic:
            embed = self._create_automatic_report_embed()
        else:
            embed = self._create_manual_report_embed()

        # Send report directly to mod channel (no thread yet)
        view = ModeratorView(self)
        mod_message = await mod_channel.send(embed=embed, view=view)

        # Store the mod channel message for reference
        self.mod_message = mod_message

        # Send confirmation to the report thread (only for manual reports)
        if not self.is_automatic:
            await self.send_confirmation()

    def _create_automatic_report_embed(self):
        """Create embed for automatic reports"""
        embed = discord.Embed(
            title="🤖 Automatic Report (AI Detected)",
            description=f"Our AI agent detected potential abuse with {self.agent_confidence}% confidence.",
            color=discord.Color.gold(),
        )

        # Add AI detection details
        embed.add_field(
            name="🧠 AI Analysis",
            value=f"**Detected Type:** {self.agent_abuse_type}\n"
            f"**Subtype:** {self.agent_fraud_subtype or 'N/A'}\n"
            f"**Severity:** {self.agent_severity}\n"
            f"**Confidence:** {self.agent_confidence}%",
            inline=False,
        )

        # Add reasoning
        if self.agent_reasoning:
            embed.add_field(
                name="💭 AI Reasoning",
                value=self.agent_reasoning,
                inline=False,
            )

        # Add message details
        embed.add_field(name="📝 Reported Message", value=quote_message(self.reported_message), inline=False)
        embed.add_field(name="👤 Message Author", value=self.reported_message.author.mention, inline=True)
        embed.add_field(
            name="📍 Location", value=f"[Jump to message]({self.reported_message.jump_url})", inline=True
        )

        embed.set_footer(text=f"Automatic Report ID: {self.id}")
        embed.timestamp = self.reported_message.created_at

        return embed

    def _create_manual_report_embed(self):
        """Create embed for manual reports"""
        # Create an embed for moderators with priority indication
        priority_color = discord.Color.red() if self.abuse_category == "fraud" else discord.Color.orange()
        embed = discord.Embed(
            title="🚨 New Report Received",
            description="A new report has been submitted and requires moderator attention.",
            color=priority_color,
        )

        # Add priority indicator for fraud reports
        if self.abuse_category == "fraud":
            embed.add_field(
                name="⚠️ HIGH PRIORITY",
                value="This is a fraud/scam report and requires immediate attention.",
                inline=False,
            )

        add_report_details_to_embed(embed, self)
        return embed

    async def submit_automatic_report(self):
        """Submit an automatic report directly to moderators without user interaction"""
        await self.submit_report_to_mods()

    async def send_confirmation(self):
        """Show confirmation message after report submission"""
        embed = discord.Embed(
            title="✅ Report Submitted Successfully",
            description=REPORT_CONFIRMATION_MESSAGE,
            color=discord.Color.green(),
        )

        # Add report summary
        if self.abuse_category in ABUSE_TYPES:
            abuse_type = ABUSE_TYPES[self.abuse_category]
            summary_text = f"{abuse_type.emoji} **{abuse_type.label}**"

            # Add subtype if selected
            if self.subtypes and abuse_type.subtypes:
                for subtype_key in self.subtypes:
                    if subtype_key in abuse_type.subtypes:
                        subtype = abuse_type.subtypes[subtype_key]
                        summary_text += f" → {subtype.emoji} {subtype.label}"

            embed.add_field(name="📋 Report Type", value=summary_text, inline=False)

        embed.set_footer(text=f"Report ID: {self.id} • Moderators have been notified")

        # Send confirmation to the report thread
        confirmation_msg = await self.report_thread.send(embed=embed)
        self.add_bot_message(confirmation_msg)
