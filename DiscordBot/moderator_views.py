import discord
from discord.ui import View, Button, Modal, TextInput
from discord import ButtonStyle
import logging
from helpers import add_report_details_to_embed
from datetime import timedelta

logger = logging.getLogger("discord")


class ModeratorActionView(View):
    """View for moderator actions on reported content"""

    def __init__(self, report):
        super().__init__(timeout=None)  # No timeout for moderation actions
        self.report = report
        self._add_moderation_buttons()

    def _add_moderation_buttons(self):
        """Add buttons for moderator actions"""
        # Take Action button
        action_button = Button(
            label="Take Action",
            style=ButtonStyle.success,
            row=0,
            custom_id=f"mod_action_approve_{self.report.id}",
        )
        action_button.callback = self._action_callback
        self.add_item(action_button)

        # Dismiss button
        dismiss_button = Button(
            label="Dismiss", style=ButtonStyle.danger, row=0, custom_id=f"mod_action_reject_{self.report.id}"
        )
        dismiss_button.callback = self._dismiss_callback
        self.add_item(dismiss_button)

    async def _action_callback(self, interaction):
        """Handle action button click"""
        await interaction.response.defer()

        # Send confirmation that action is being taken
        await interaction.followup.send(f"🔄 {interaction.user.mention} is taking action on this report.")

        # Show action selection view
        view = ActionSelectView(self.report)
        await interaction.followup.send("Please select an action to take:", view=view)

    async def _dismiss_callback(self, interaction):
        """Handle dismiss button click"""
        modal = DismissalReasonModal(self.report)
        await interaction.response.send_modal(modal)


class ActionSelectView(View):
    """View for selecting moderation actions"""

    def __init__(self, report):
        super().__init__(timeout=300)
        self.report = report
        self._add_action_buttons()

    def _add_action_buttons(self):
        """Add buttons for each moderation action"""
        actions = [
            ("warn", "Warn User", ButtonStyle.danger),
            ("timeout", "Timeout User", ButtonStyle.danger),
            ("kick", "Kick User", ButtonStyle.danger),
            ("ban", "Ban User", ButtonStyle.danger),
        ]

        for action_id, label, style in actions:
            button = Button(label=label, style=style, custom_id=f"action_{action_id}")
            button.callback = self._create_action_callback(action_id)
            self.add_item(button)

    def _create_action_callback(self, action_id):
        """Create a callback for an action button"""

        async def callback(interaction):
            await interaction.response.defer()

            # Check if report is still active
            if not self.report.active:
                await interaction.followup.send(
                    "❌ This report has already been acted upon by another moderator.", ephemeral=True
                )
                return

            # Get the reported user
            reported_user = self.report.reported_message.author

            # Take the action
            if action_id == "warn":
                await self._warn_user(reported_user)
            elif action_id == "timeout":
                await self._timeout_user(reported_user)
            elif action_id == "kick":
                await self._kick_user(reported_user)
            elif action_id == "ban":
                await self._ban_user(reported_user)

            # Mark report as inactive
            self.report.active = False

            # Send confirmation in the mod thread
            await interaction.followup.send(
                f"✅ {interaction.user.mention} has taken action {action_id} against {reported_user.mention}"
            )

            # Send action notification to the report thread with action-specific messages
            report_thread = self.report.report_thread

            action_messages = {
                "warn": "The reported user has been warned about their behavior.",
                "timeout": "The reported user has been temporarily suspended from the server for 24 hours.",
                "kick": "The reported user has been removed from the server and will need to rejoin if they wish to return.",
                "ban": "The reported user has been permanently banned from the server.",
            }

            action_colors = {
                "warn": discord.Color.yellow(),
                "timeout": discord.Color.orange(),
                "kick": discord.Color.red(),
                "ban": discord.Color.red(),
            }

            await report_thread.send(
                embed=discord.Embed(
                    title=f"Action Taken: {action_id.title()}",
                    description=action_messages.get(action_id),
                    color=action_colors.get(action_id),
                )
            )

        return callback

    async def _warn_user(self, user):
        """Send a warning to the user"""
        try:
            embed = discord.Embed(
                title="Warning",
                description="You have received a warning for violating our community guidelines.",
                color=discord.Color.yellow(),
            )
            add_report_details_to_embed(embed, self.report, hide_reporter=True)
            await user.send(embed=embed)
        except discord.Forbidden:
            pass  # User has DMs disabled

    async def _timeout_user(self, user):
        """Timeout the user"""
        try:
            await user.timeout(discord.timedelta(hours=24), reason="Reported for violation")
            embed = discord.Embed(
                title="Timeout",
                description="You have been timed out for 24 hours for violating our community guidelines.",
                color=discord.Color.orange(),
            )
            add_report_details_to_embed(embed, self.report, hide_reporter=True)
            await user.send(embed=embed)
        except discord.Forbidden:
            pass  # User has DMs disabled

    async def _kick_user(self, user):
        """Kick the user"""
        try:
            await user.kick(reason="Reported for violation")
            embed = discord.Embed(
                title="Kick",
                description="You have been kicked from the server for violating our community guidelines.",
                color=discord.Color.red(),
            )
            add_report_details_to_embed(embed, self.report, hide_reporter=True)
            await user.send(embed=embed)
        except discord.Forbidden:
            pass  # Bot doesn't have kick permissions

    async def _ban_user(self, user):
        """Ban the user"""
        try:
            await user.ban(reason="Reported for violation")
            embed = discord.Embed(
                title="Ban",
                description="You have been banned from the server for violating our community guidelines.",
                color=discord.Color.red(),
            )
            add_report_details_to_embed(embed, self.report, hide_reporter=True)
            await user.send(embed=embed)
        except discord.Forbidden:
            pass  # Bot doesn't have ban permissions or user has DMs disabled


class DismissalReasonModal(Modal):
    """Modal for entering dismissal reason"""

    def __init__(self, report):
        super().__init__(title="Dismiss Report")
        self.report = report

        self.reason = TextInput(
            label="Reason for Dismissal",
            placeholder="Please provide a reason for dismissing this report...",
            style=discord.TextStyle.paragraph,
            required=True,
        )
        self.add_item(self.reason)

    async def on_submit(self, interaction):
        """Handle submission of dismissal reason"""
        await interaction.response.defer()

        # Check if report is still active
        if not self.report.active:
            await interaction.followup.send(
                "❌ This report has already been acted upon by another moderator.", ephemeral=True
            )
            return

        # Mark report as inactive
        self.report.active = False

        # Send dismissal confirmation in the mod thread
        await interaction.followup.send(
            f"❌ {interaction.user.mention} has dismissed this report.\nReason: {self.reason.value}"
        )

        # Send dismissal notification to the report thread
        report_thread = self.report.report_thread
        await report_thread.send(
            embed=discord.Embed(
                title="Report Dismissed",
                description=f"Your report has been dismissed.\nReason: {self.reason.value}",
                color=discord.Color.red(),
            )
        )
