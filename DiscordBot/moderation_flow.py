import discord
from discord.ui import View, Button, Modal, TextInput
from discord import ButtonStyle
from datetime import timedelta
from helpers import (
    MESSAGE_ACTIONS,
    USER_ACTIONS,
    SEVERITY_LEVELS,
    MODERATION_SUMMARY_TEMPLATE,
    add_report_details_to_embed,
)


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
                "Error: This report has already been handled by another moderator.",
                ephemeral=True,
            )
            return

        await interaction.response.defer()
        await start_moderation_flow(self.report, interaction)

    async def _on_dismiss_button(self, interaction: discord.Interaction):
        """Handle dismiss button click"""
        if not self.report.active:
            await interaction.response.send_message(
                "Error: This report has already been handled by another moderator.",
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

        # Send a followup to the reporter
        await self.report.report_thread.send(
            f"Your report has been dismissed by our moderators. If you disagree with the dismissal, please submit another report and provide more information in the additional information field."
        )

        # Mark report as inactive
        self.report.active = False


class MessageActionView(View):
    """View for selecting what to do with the reported message"""

    def __init__(self, report, on_complete):
        super().__init__(timeout=None)  # No timeout for moderator views
        self.report = report
        self.on_complete = on_complete
        self._add_message_action_buttons()

    def _add_message_action_buttons(self):
        """Add buttons for each message action"""
        for action_id, action_label in MESSAGE_ACTIONS.items():
            button = Button(
                label=action_label,
                style=ButtonStyle.primary,
                custom_id=f"message_action_{action_id}",
            )
            button.callback = self._create_action_callback(action_id)
            self.add_item(button)

    def _create_action_callback(self, action_id):
        async def callback(interaction):
            await interaction.response.defer()
            self.report.message_action = action_id
            await self.on_complete(action_id)

        return callback


class UserActionView(View):
    """View for selecting what to do with the reported user"""

    def __init__(self, report, on_complete):
        super().__init__(timeout=None)
        self.report = report
        self.on_complete = on_complete
        self._add_user_action_buttons()

    def _add_user_action_buttons(self):
        """Add buttons for each user action"""
        for action_id, action_data in USER_ACTIONS.items():
            button = Button(
                label=action_data["label"],
                style=ButtonStyle.primary,
                custom_id=f"user_action_{action_id}",
            )
            button.callback = self._create_action_callback(action_id)
            self.add_item(button)

    def _create_action_callback(self, action_id):
        async def callback(interaction):
            await interaction.response.defer()
            self.report.user_action = action_id
            await self.on_complete(action_id)

        return callback


class SeverityLevelView(View):
    """View for selecting the severity level of the violation"""

    def __init__(self, report, on_complete):
        super().__init__(timeout=None)
        self.report = report
        self.on_complete = on_complete
        self._add_severity_buttons()

    def _add_severity_buttons(self):
        """Add buttons for each severity level"""
        for level_id, level_data in SEVERITY_LEVELS.items():
            button = Button(
                label=level_data["label"],
                style=ButtonStyle.primary,
                custom_id=f"severity_{level_id}",
            )
            button.callback = self._create_callback(level_id)
            self.add_item(button)

    def _create_callback(self, level_id):
        async def callback(interaction):
            await interaction.response.defer()
            self.report.severity_level = level_id
            await self.on_complete(level_id)

        return callback


async def start_moderation_flow(report, interaction):
    """Start the moderation flow for a report"""

    async def on_message_action_complete(action):
        # Show user action view
        embed = discord.Embed(
            title="User Action",
            description="What action should be taken against the user?",
            color=discord.Color.blue(),
        )
        view = UserActionView(report, on_user_action_complete)
        await interaction.followup.send(embed=embed, view=view)

    async def on_user_action_complete(action):
        # Show severity level view
        embed = discord.Embed(
            title="Severity Level",
            description="How severe is this violation?",
            color=discord.Color.blue(),
        )
        view = SeverityLevelView(report, on_severity_complete)
        await interaction.followup.send(embed=embed, view=view)

    async def on_severity_complete(level):
        # Generate and send summary
        await send_moderation_summary(report, interaction)

    # Start the flow with message action
    embed = discord.Embed(
        title="Message Action",
        description="What should be done with the reported message?",
        color=discord.Color.blue(),
    )
    view = MessageActionView(report, on_message_action_complete)
    await interaction.followup.send(embed=embed, view=view)


async def send_moderation_summary(report, interaction):
    """Send a summary of the moderation actions taken"""
    # Format the summary
    summary = MODERATION_SUMMARY_TEMPLATE.format(
        message_action=MESSAGE_ACTIONS[report.message_action],
        user_action=USER_ACTIONS[report.user_action]["message"],
        severity_level=SEVERITY_LEVELS[report.severity_level]["label"],
        report_id=report.id,
        moderator=interaction.user.mention,
    )

    # Create and send the summary embed
    embed = discord.Embed(
        title="Moderation Summary",
        description=summary,
        color=SEVERITY_LEVELS[report.severity_level]["color"],
    )
    await interaction.followup.send(embed=embed)

    # Send summary to the reporter in the report thread
    if report.report_thread:
        reporter_embed = discord.Embed(
            title="Report Outcome",
            description=f"Your report has been reviewed by our moderators.\n{summary}",
            color=discord.Color.blue(),
        )
        await report.report_thread.send(embed=reporter_embed)

    # Take the message action
    if report.message_action == "remove":
        try:
            await report.reported_message.delete()
        except:
            await interaction.followup.send(
                "Error: Failed to delete the reported message. The bot may lack permissions.",
                ephemeral=True,
            )

    # Take the user action
    user = report.reported_message.author
    if report.user_action == "warn":
        await warn_user(user, report)
    elif report.user_action == "timeout":
        await timeout_user(user, report)
    elif report.user_action == "kick":
        await kick_user(user, report)
    elif report.user_action == "ban":
        await ban_user(user, report)

    # Mark report as inactive
    report.active = False


async def warn_user(user, report):
    """Send a warning to the user"""
    try:
        embed = discord.Embed(
            title="Warning",
            description="You have received a warning for violating our community guidelines.",
            color=discord.Color.yellow(),
        )
        add_report_details_to_embed(embed, report, hide_reporter=True, hide_additional_info=True)
        await user.send(embed=embed)
    except discord.Forbidden:
        pass  # User has DMs disabled


async def timeout_user(user, report):
    """Timeout the user"""
    try:
        await user.timeout(timedelta(hours=24), reason="Reported for violation")
        embed = discord.Embed(
            title="Timeout",
            description="You have been timed out for 24 hours for violating our community guidelines.",
            color=discord.Color.orange(),
        )
        add_report_details_to_embed(embed, report, hide_reporter=True, hide_additional_info=True)
        await user.send(embed=embed)
    except discord.Forbidden:
        pass  # User has DMs disabled


async def kick_user(user, report):
    """Kick the user"""
    try:
        await user.kick(reason="Reported for violation")
        embed = discord.Embed(
            title="Kick",
            description="You have been kicked from the server for violating our community guidelines.",
            color=discord.Color.red(),
        )
        add_report_details_to_embed(embed, report, hide_reporter=True, hide_additional_info=True)
        await user.send(embed=embed)
    except discord.Forbidden:
        pass  # Bot doesn't have kick permissions


async def ban_user(user, report):
    """Ban the user"""
    try:
        await user.ban(reason="Reported for violation")
        embed = discord.Embed(
            title="Ban",
            description="You have been banned from the server for violating our community guidelines.",
            color=discord.Color.red(),
        )
        add_report_details_to_embed(embed, report, hide_reporter=True, hide_additional_info=True)
        await user.send(embed=embed)
    except discord.Forbidden:
        pass  # Bot doesn't have ban permissions or user has DMs disabled
