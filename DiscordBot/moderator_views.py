import discord
from discord.ui import View, Button, Select, Modal, TextInput
from discord import SelectOption, ButtonStyle
from typing import Optional, Callable, Awaitable
from moderation_flow import start_moderation_flow


class ModeratorView(View):
    """View for moderators to handle reports"""

    def __init__(self, report):
        super().__init__(timeout=None)  # No timeout for moderator views
        self.report = report
        self._add_buttons()

    def _add_buttons(self):
        """Add buttons for moderator actions"""
        # Add button to start moderation flow
        action_button = Button(
            label="Take Action",
            style=ButtonStyle.primary,
            custom_id="take_action",
        )
        action_button.callback = self._on_action_button
        self.add_item(action_button)

        # Add button to dismiss report
        dismiss_button = Button(
            label="Dismiss Report",
            style=ButtonStyle.secondary,
            custom_id="dismiss_report",
        )
        dismiss_button.callback = self._on_dismiss_button
        self.add_item(dismiss_button)

    async def _on_action_button(self, interaction: discord.Interaction):
        """Handle action button click"""
        if not self.report.active:
            await interaction.response.send_message(
                "❌ This report has already been handled by another moderator.",
                ephemeral=True,
            )
            return

        await interaction.response.defer()
        await start_moderation_flow(self.report, interaction)

    async def _on_dismiss_button(self, interaction: discord.Interaction):
        """Handle dismiss button click"""
        if not self.report.active:
            await interaction.response.send_message(
                "❌ This report has already been handled by another moderator.",
                ephemeral=True,
            )
            return

        modal = DismissalReasonModal(self.report)
        await interaction.response.send_modal(modal)


class DismissalReasonModal(Modal):
    """Modal for entering dismissal reason"""

    def __init__(self, report):
        super().__init__(title="Dismiss Report")
        self.report = report

        self.reason = TextInput(
            label="Reason for Dismissal",
            placeholder="Enter the reason for dismissing this report...",
            style=discord.TextStyle.paragraph,
            required=True,
        )
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        """Handle modal submission"""
        await interaction.response.defer()

        # Create dismissal embed
        embed = discord.Embed(
            title="Report Dismissed",
            description=f"**Reason:** {self.reason.value}",
            color=discord.Color.greyple(),
        )
        embed.set_footer(text=f"Dismissed by {interaction.user}")

        # Send dismissal message
        await interaction.followup.send(embed=embed)

        # Mark report as inactive
        self.report.active = False
