import discord
from discord.ui import View, Button, Select, Modal, TextInput
from discord import SelectOption, ButtonStyle
from typing import Optional, Dict, Any
import logging

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
            label="Dismiss",
            style=ButtonStyle.danger,
            row=0,
            custom_id=f"mod_action_reject_{self.report.id}"
        )
        dismiss_button.callback = self._dismiss_callback
        self.add_item(dismiss_button)

    async def _action_callback(self, interaction):
        """Handle taking action on a report"""
        await interaction.response.defer(ephemeral=True)

        # Show action selection view
        embed = discord.Embed(
            title="Select Action",
            description="What action would you like to take on this report?",
            color=discord.Color.green(),
        )

        view = ActionSelectView(self.report)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

        # Update original message to show it's being handled
        await interaction.message.edit(content="✅ This report is being handled by a moderator.", view=None)

    async def _dismiss_callback(self, interaction):
        """Handle dismissal of report"""
        # Show dismissal reason modal
        modal = DismissalReasonModal(self.report)
        await interaction.response.send_modal(modal)

class ActionSelectView(View):
    """View for selecting specific moderation actions"""
    
    def __init__(self, report):
        super().__init__(timeout=300)
        self.report = report
        self._add_action_options()

    def _add_action_options(self):
        """Add action options to the view"""
        select = Select(
            placeholder="Select action to take...",
            options=[
                SelectOption(
                    label="Delete Message",
                    value="delete",
                    description="Remove the reported message"
                ),
                SelectOption(
                    label="Warn User",
                    value="warn",
                    description="Send a warning to the user"
                ),
                SelectOption(
                    label="Timeout User",
                    value="timeout",
                    description="Temporarily restrict the user"
                ),
                SelectOption(
                    label="Ban User",
                    value="ban",
                    description="Permanently ban the user"
                ),
            ],
            row=0,
        )
        select.callback = self._action_selected
        self.add_item(select)

    async def _action_selected(self, interaction):
        """Handle selection of a moderation action"""
        await interaction.response.defer(ephemeral=True)
        value = interaction.data["values"][0]

        # Get the message and user from the report
        message = self.report.report_data["reported_message"]
        user = message.author

        # Execute the selected action
        if value == "delete":
            await message.delete()
            await self._notify_user(user, "Your message has been removed for violating our community guidelines.")
        
        elif value == "warn":
            await self._notify_user(user, "You have received a warning for violating our community guidelines.")
        
        elif value == "timeout":
            # Timeout for 24 hours
            await user.timeout(discord.utils.utcnow() + discord.timedelta(hours=24))
            await self._notify_user(user, "You have been timed out for 24 hours for violating our community guidelines.")
        
        elif value == "ban":
            await user.ban(reason="Violation of community guidelines")
            await self._notify_user(user, "You have been banned from the server for violating our community guidelines.")

        # Log the action
        logger.info(f"Moderator {interaction.user} took action '{value}' on report {self.report.id}")

        # Confirm the action to the moderator
        await interaction.followup.send(f"✅ Action '{value}' has been taken.", ephemeral=True)

    async def _notify_user(self, user, message):
        """Send a notification to a user"""
        try:
            await user.send(message)
        except discord.Forbidden:
            logger.warning(f"Could not send DM to user {user.id}")

class DismissalReasonModal(Modal):
    """Modal for providing a dismissal reason"""
    
    def __init__(self, report):
        super().__init__(title="Dismiss Report")
        self.report = report
        
        self.reason = TextInput(
            label="Reason for dismissal",
            placeholder="Please provide a reason for dismissing this report...",
            style=discord.TextStyle.paragraph,
            required=True,
        )
        self.add_item(self.reason)

    async def on_submit(self, interaction):
        """Handle submission of dismissal reason"""
        await interaction.response.defer(ephemeral=True)
        
        # Update the message to show it was dismissed
        await interaction.message.edit(
            content=f"❌ This report has been dismissed by a moderator.\nReason: {self.reason.value}",
            view=None
        )

        # Notify the reporter
        reporter = self.report.report_data["interaction"].user
        try:
            await reporter.send(
                f"Your report has been dismissed.\nReason: {self.reason.value}"
            )
        except discord.Forbidden:
            logger.warning(f"Could not send DM to reporter {reporter.id}") 