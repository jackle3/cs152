import discord
from discord.ui import View, Button, Modal, TextInput
from discord import ButtonStyle
from datetime import timedelta
from abuse_types import (
    MESSAGE_ACTIONS,
    USER_ACTIONS,
    SEVERITY_LEVELS,
    MODERATION_SUMMARY_TEMPLATE,
    ABUSE_TYPES,
)
from helpers import add_report_details_to_embed


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
            label="⚖️ Take Action",
            style=ButtonStyle.primary,
            custom_id="take_action",
        )
        action_button.callback = self._on_action_button
        self.add_item(action_button)

        # Add button to dismiss report
        dismiss_button = Button(
            label="❌ Dismiss Report",
            style=ButtonStyle.secondary,
            custom_id="dismiss_report",
        )
        dismiss_button.callback = self._on_dismiss_button
        self.add_item(dismiss_button)

    async def _on_action_button(self, interaction: discord.Interaction):
        """Handle action button click"""
        if not self.report.active:
            await interaction.response.send_message(
                "⚠️ This report has already been handled by another moderator.",
                ephemeral=True,
            )
            return

        await interaction.response.defer()

        # Create a thread for the moderation process
        await self._create_moderation_thread(interaction)

        # Start the moderation flow in the thread
        await start_moderation_flow(self.report, interaction)

    async def _create_moderation_thread(self, interaction):
        """Create a thread for the moderation process"""
        # Determine thread name based on report type
        if self.report.abuse_category in ABUSE_TYPES:
            abuse_type = ABUSE_TYPES[self.report.abuse_category]
            thread_name = f"{abuse_type.label} - {interaction.user.name}"
        else:
            thread_name = f"Other - {interaction.user.name}"

        # Create the thread from the original report message
        if hasattr(self.report, "mod_message"):
            thread = await self.report.mod_message.create_thread(
                name=thread_name,
                auto_archive_duration=1440,  # 24 hours
            )
            self.report.mod_thread = thread

            # Send initial message in thread
            embed = discord.Embed(
                title="⚖️ Moderation Process Started",
                description=f"Moderator {interaction.user.mention} is handling this report.",
                color=discord.Color.blue(),
            )
            await thread.send(embed=embed)

    async def _on_dismiss_button(self, interaction: discord.Interaction):
        """Handle dismiss button click"""
        if not self.report.active:
            await interaction.response.send_message(
                "⚠️ This report has already been handled by another moderator.",
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
            title="❌ Report Dismissed",
            description=f"**Reason:** {self.reason.value}",
            color=discord.Color.greyple(),
        )
        embed.set_footer(text=f"Dismissed by {interaction.user}")

        # Send dismissal message as a reply in the mod channel
        await interaction.followup.send(embed=embed)

        # Send a followup to the reporter in their report thread
        reporter_embed = discord.Embed(
            title="Report Dismissed",
            description="Your report has been dismissed by our moderators. If you disagree with the dismissal, please submit another report and provide more information in the additional information field.",
            color=discord.Color.greyple(),
        )
        reporter_embed.set_footer(text=f"Report ID: {self.report.id}")
        reporter_embed.timestamp = discord.utils.utcnow()

        if self.report.report_thread:
            await self.report.report_thread.send(embed=reporter_embed)

        # Mark report as inactive
        self.report.active = False


class MessageActionView(View):
    """View for selecting what to do with the reported message"""

    def __init__(self, report, on_complete):
        super().__init__(timeout=None)
        self.report = report
        self.on_complete = on_complete
        self.selected_action = None
        self._add_message_action_buttons()

    def _add_message_action_buttons(self):
        """Add buttons for each message action"""
        for action_id, action_label in MESSAGE_ACTIONS.items():
            # Add emojis to make buttons more clear
            emoji = "🗑️" if action_id == "remove" else "👍"
            button = Button(
                label=f"{emoji} {action_label}",
                style=ButtonStyle.primary,
                custom_id=f"message_action_{action_id}",
            )
            button.callback = self._create_action_callback(action_id)
            self.add_item(button)

    def _create_action_callback(self, action_id):
        async def callback(interaction):
            await interaction.response.defer()

            # If moderator is changing their selection, trigger cleanup
            if self.selected_action and self.selected_action != action_id:
                await self._cleanup_subsequent_messages()

            # Update selection tracking
            self.selected_action = action_id
            self.report.message_action = action_id

            # Update buttons to show selection
            await self._update_buttons_after_selection(interaction, action_id)

            await self.on_complete(action_id)

        return callback

    async def _cleanup_subsequent_messages(self):
        """Clean up messages after this step (step 1 - message action)"""
        if hasattr(self.report, "mod_messages") and len(self.report.mod_messages) > 2:
            try:
                messages_to_delete = self.report.mod_messages[2:]
                for msg in messages_to_delete:
                    if msg:
                        try:
                            await msg.delete()
                        except (discord.NotFound, discord.Forbidden):
                            pass
                self.report.mod_messages = self.report.mod_messages[:2]
            except (IndexError, AttributeError):
                pass

    async def _update_buttons_after_selection(self, interaction, selected_action):
        """Update buttons to show selection while keeping them clickable"""
        for item in self.children:
            if isinstance(item, Button):
                action_id = item.custom_id.replace("message_action_", "")
                if action_id == selected_action:
                    # Highlight selected button
                    item.style = ButtonStyle.success
                    item.label = f"✅ {MESSAGE_ACTIONS[action_id]}"
                else:
                    # Reset other buttons
                    emoji = "🗑️" if action_id == "remove" else "👍"
                    item.style = ButtonStyle.primary
                    item.label = f"{emoji} {MESSAGE_ACTIONS[action_id]}"

        await interaction.edit_original_response(view=self)


class UserActionView(View):
    """View for selecting what to do with the reported user"""

    def __init__(self, report, on_complete):
        super().__init__(timeout=None)
        self.report = report
        self.on_complete = on_complete
        self.selected_action = None
        self._add_user_action_buttons()

    def _add_user_action_buttons(self):
        """Add buttons for each user action"""
        emoji_map = {"warn": "⚠️", "timeout": "⏰", "kick": "👢", "ban": "🔨"}

        for action_id, action_data in USER_ACTIONS.items():
            emoji = emoji_map.get(action_id, "⚖️")
            button = Button(
                label=f"{emoji} {action_data['label']}",
                style=ButtonStyle.primary,
                custom_id=f"user_action_{action_id}",
            )
            button.callback = self._create_action_callback(action_id)
            self.add_item(button)

    def _create_action_callback(self, action_id):
        async def callback(interaction):
            await interaction.response.defer()

            # Update selection tracking (no cleanup needed as this is the final step)
            self.selected_action = action_id
            self.report.user_action = action_id

            # Update buttons to show selection
            await self._update_buttons_after_selection(interaction, action_id)

            await self.on_complete(action_id)

        return callback

    async def _update_buttons_after_selection(self, interaction, selected_action):
        """Update buttons to show selection while keeping them clickable"""
        emoji_map = {"warn": "⚠️", "timeout": "⏰", "kick": "👢", "ban": "🔨"}

        for item in self.children:
            if isinstance(item, Button):
                action_id = item.custom_id.replace("user_action_", "")
                emoji = emoji_map.get(action_id, "⚖️")

                if action_id == selected_action:
                    # Highlight selected button
                    item.style = ButtonStyle.success
                    item.label = f"✅ {emoji} {USER_ACTIONS[action_id]['label']}"
                else:
                    # Reset other buttons
                    item.style = ButtonStyle.primary
                    item.label = f"{emoji} {USER_ACTIONS[action_id]['label']}"

        await interaction.edit_original_response(view=self)


class SeverityLevelView(View):
    """View for selecting the severity level of the violation"""

    def __init__(self, report, on_complete):
        super().__init__(timeout=None)
        self.report = report
        self.on_complete = on_complete
        self.selected_level = None
        self._add_severity_buttons()

    def _add_severity_buttons(self):
        """Add buttons for each severity level"""
        emoji_map = {"low": "🟢", "medium": "🟡", "high": "🟠", "critical": "🔴"}

        for level_id, level_data in SEVERITY_LEVELS.items():
            emoji = emoji_map.get(level_id, "⚫")
            button = Button(
                label=f"{emoji} {level_data['label']}",
                style=ButtonStyle.primary,
                custom_id=f"severity_{level_id}",
            )
            button.callback = self._create_callback(level_id)
            self.add_item(button)

    def _create_callback(self, level_id):
        async def callback(interaction):
            await interaction.response.defer()

            # If moderator is changing their selection, trigger cleanup
            if self.selected_level and self.selected_level != level_id:
                await self._cleanup_subsequent_messages()

            # Update selection tracking
            self.selected_level = level_id
            self.report.severity_level = level_id

            # Update buttons to show selection
            await self._update_buttons_after_selection(interaction, level_id)

            await self.on_complete(level_id)

        return callback

    async def _cleanup_subsequent_messages(self):
        """Clean up messages after this step (step 0 - severity level)"""
        if hasattr(self.report, "mod_messages") and len(self.report.mod_messages) > 1:
            try:
                messages_to_delete = self.report.mod_messages[1:]
                for msg in messages_to_delete:
                    if msg:
                        try:
                            await msg.delete()
                        except (discord.NotFound, discord.Forbidden):
                            pass
                self.report.mod_messages = self.report.mod_messages[:1]
            except (IndexError, AttributeError):
                pass

    async def _update_buttons_after_selection(self, interaction, selected_level):
        """Update buttons to show selection while keeping them clickable"""
        emoji_map = {"low": "🟢", "medium": "🟡", "high": "🟠", "critical": "🔴"}

        for item in self.children:
            if isinstance(item, Button):
                level_id = item.custom_id.replace("severity_", "")
                emoji = emoji_map.get(level_id, "⚫")

                if level_id == selected_level:
                    # Highlight selected button
                    item.style = ButtonStyle.success
                    item.label = f"✅ {emoji} {SEVERITY_LEVELS[level_id]['label']}"
                else:
                    # Reset other buttons
                    item.style = ButtonStyle.primary
                    item.label = f"{emoji} {SEVERITY_LEVELS[level_id]['label']}"

        await interaction.edit_original_response(view=self)


async def start_moderation_flow(report, interaction):
    """Start the moderation flow for a report"""

    # Initialize moderator message tracking if not already done
    if not hasattr(report, "mod_messages"):
        report.mod_messages = []

    async def cleanup_mod_messages_from_step(step_index):
        """Clean up moderator messages from a specific step onwards"""
        try:
            messages_to_delete = report.mod_messages[step_index + 1 :]
            for msg in messages_to_delete:
                if msg:
                    try:
                        await msg.delete()
                    except (discord.NotFound, discord.Forbidden):
                        pass
            report.mod_messages = report.mod_messages[: step_index + 1]
        except (IndexError, AttributeError):
            pass

    async def on_severity_complete(level):
        # Clean up any subsequent messages if moderator changed their mind
        await cleanup_mod_messages_from_step(0)

        # Show message action view
        embed = discord.Embed(
            title="📝 Message Action",
            description="What should be done with the reported message?",
            color=discord.Color.blue(),
        )
        view = MessageActionView(report, on_message_action_complete)
        message_action_message = await report.mod_thread.send(embed=embed, view=view)
        report.mod_messages.append(message_action_message)

    async def on_message_action_complete(action):
        # Clean up any subsequent messages if moderator changed their mind
        await cleanup_mod_messages_from_step(1)

        # Show user action view
        embed = discord.Embed(
            title="👤 User Action",
            description="What action should be taken against the user?",
            color=discord.Color.blue(),
        )
        view = UserActionView(report, on_user_action_complete)
        user_action_message = await report.mod_thread.send(embed=embed, view=view)
        report.mod_messages.append(user_action_message)

    async def on_user_action_complete(action):
        # Generate and send summary
        await send_moderation_summary(report, interaction)

        # For high or critical severity reports, notify the specialized investigation team
        if report.severity_level in ["high", "critical"]:
            investigation_team_member = (
                "<@469007804523479050>"  # Temporarily tag William as the investigation team
            )
            investigation_message = f"🚨 {investigation_team_member} A {SEVERITY_LEVELS[report.severity_level]['label']} report requires your attention. Report ID: {report.id}"
            alert_message = await report.mod_thread.send(investigation_message)
            report.mod_messages.append(alert_message)

    # Start the flow with severity level
    embed = discord.Embed(
        title="📊 Severity Level",
        description="How severe is this violation?",
        color=discord.Color.blue(),
    )
    view = SeverityLevelView(report, on_severity_complete)
    severity_message = await report.mod_thread.send(embed=embed, view=view)

    # Initialize and track the first moderator message
    report.mod_messages = [severity_message]


async def send_moderation_summary(report, interaction):
    """Send a summary of the moderation actions taken and take the appropriate actions"""
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
    await report.mod_thread.send(embed=embed)

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
            await report.mod_thread.send(
                "⚠️ **Error:** Failed to delete the reported message. The bot may lack permissions."
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
        add_report_details_to_embed(embed, report)
        await user.send(embed=embed)
    except discord.Forbidden:
        pass  # User has DMs disabled


async def timeout_user(user, report):
    """Timeout the user"""
    try:
        # await user.timeout(timedelta(hours=24), reason="Reported for violation")
        embed = discord.Embed(
            title="Timeout",
            description="You have been timed out for 24 hours for violating our community guidelines.",
            color=discord.Color.orange(),
        )
        add_report_details_to_embed(embed, report)
        await user.send(embed=embed)
    except discord.Forbidden:
        pass  # User has DMs disabled


async def kick_user(user, report):
    """Kick the user"""
    try:
        # await user.kick(reason="Reported for violation")
        embed = discord.Embed(
            title="Kick",
            description="You have been kicked from the server for violating our community guidelines.",
            color=discord.Color.red(),
        )
        add_report_details_to_embed(embed, report)
        await user.send(embed=embed)
    except discord.Forbidden:
        pass  # Bot doesn't have kick permissions


async def ban_user(user, report):
    """Ban the user"""
    try:
        # await user.ban(reason="Reported for violation")
        embed = discord.Embed(
            title="Ban",
            description="You have been banned from the server for violating our community guidelines.",
            color=discord.Color.red(),
        )
        add_report_details_to_embed(embed, report)
        await user.send(embed=embed)
    except discord.Forbidden:
        pass  # Bot doesn't have ban permissions or user has DMs disabled
