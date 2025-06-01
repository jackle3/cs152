import discord
from discord.ui import View, Button, Select, Modal, TextInput
from discord import SelectOption, ButtonStyle
from abuse_types import ABUSE_TYPES
from helpers import create_progress_embed


class MainReportView(View):
    def __init__(self, report):
        super().__init__(timeout=300)  # 5 minute timeout
        self.report = report
        self.selected_type = None
        self._add_abuse_buttons()

    def _add_abuse_buttons(self):
        """Add buttons for each abuse type with emojis"""
        # Add a button for each abuse type
        for i, (key, abuse_type) in enumerate(ABUSE_TYPES.items()):
            # Make fraud button more prominent since it's the primary focus
            button_style = ButtonStyle.primary
            if key == "other":
                button_style = ButtonStyle.secondary

            button = Button(
                label=f"{abuse_type.emoji} {abuse_type.label}",
                style=button_style,
                row=(i // 3),  # three buttons per row for better layout
                custom_id=f"abuse_type_{key}",
                disabled=False,
            )

            # Set the callback
            button.callback = self._create_abuse_button_callback(key)

            # Add the button to the view
            self.add_item(button)

    def _create_abuse_button_callback(self, abuse_type_key):
        """Create a callback for the abuse type button"""

        async def callback(interaction):
            await interaction.response.defer()

            # If user is changing their selection, clean up subsequent messages
            if self.selected_type and self.selected_type != abuse_type_key:
                await self.report.cleanup_messages_from_step(0)  # Clean up messages after main selection

            # Track selection
            abuse_type = ABUSE_TYPES[abuse_type_key]
            self.selected_type = abuse_type_key

            # Set the report data
            self.report.abuse_category = abuse_type_key
            self.report.report_type = abuse_type.label
            self.report.subtypes = []  # Reset subtypes when changing main category

            # Update buttons to show selection
            await self._update_buttons_after_selection(interaction, abuse_type_key)

            # Handle direct reports (no subtypes)
            if not abuse_type.subtypes:
                await self._show_additional_info_prompt(interaction)
                return

            # Handle subtypes
            await self._handle_subtype_selection(interaction, abuse_type_key, abuse_type)

        return callback

    async def _update_buttons_after_selection(self, interaction, selected_key):
        """Update buttons to show selection state while keeping them clickable"""
        for item in self.children:
            if isinstance(item, Button):
                abuse_key = item.custom_id.replace("abuse_type_", "")
                abuse_type = ABUSE_TYPES.get(abuse_key)

                if item.custom_id == f"abuse_type_{selected_key}":
                    # Highlight selected button with checkmark
                    item.style = ButtonStyle.success
                    base_label = f"{abuse_type.emoji} {abuse_type.label}"
                    item.label = f"✅ {base_label}"
                else:
                    # Reset other buttons to default appearance
                    if abuse_key == "other":
                        item.style = ButtonStyle.secondary
                    else:
                        item.style = ButtonStyle.primary

                    # Remove checkmark if it exists
                    base_label = f"{abuse_type.emoji} {abuse_type.label}"
                    item.label = base_label

        await self.report.main_message.edit(view=self)

    async def _handle_subtype_selection(self, interaction, abuse_type_key, abuse_type):
        """Handle subtype selection for any abuse type with subtypes"""
        embed = create_progress_embed(
            title=f"Select Specific {abuse_type.label} Type",
            description=f"What specific type of {abuse_type.label.lower()} is this?",
            color=abuse_type.color,
        )

        # Include a summary of the report so far
        message = self.report.reported_message
        embed.add_field(
            name="📝 Reporting Message",
            value=f"From {message.author.mention} in {message.channel.mention}",
            inline=False,
        )

        # Create subtype view
        view = SelectView(
            report=self.report,
            placeholder=f"Choose specific {abuse_type.label.lower()} type...",
            options=abuse_type.subtypes,
            on_select=self.subtype_selected,
            parent_type=abuse_type_key,
        )

        # Send subtype selection message and track it
        subtype_message = await interaction.followup.send(embed=embed, view=view)
        self.report.add_bot_message(subtype_message)

    async def subtype_selected(self, interaction, value, parent_type=None):
        """Handle subtype selection"""
        # Add the selected subtype to the chain
        self.report.subtypes = [value]  # Reset and set new subtype

        # Since we simplified the structure, we can go straight to additional info
        await self._show_additional_info_prompt(interaction)

    async def _show_additional_info_prompt(self, interaction):
        """Show prompt for additional information"""
        embed = create_progress_embed(
            title="Additional Information (Optional)",
            description="Would you like to provide any additional details that might help our moderators?",
            color=discord.Color.blue(),
        )

        embed.add_field(
            name="💡 Helpful Information",
            value="• Links to external content\n• Additional context\n• Previous related incidents\n• Any other relevant details",
            inline=False,
        )

        view = AdditionalInfoView(self.report)

        # Send additional info message and track it
        additional_info_message = await interaction.followup.send(embed=embed, view=view)
        self.report.add_bot_message(additional_info_message)


class AdditionalInfoView(View):
    """View for handling additional information input"""

    def __init__(self, report):
        super().__init__(timeout=300)
        self.report = report
        self.selected_action = None

        # Add buttons with better styling
        add_info_button = Button(label="📝 Add Information", style=ButtonStyle.primary, custom_id="add_info")
        add_info_button.callback = self._add_info_callback
        self.add_item(add_info_button)

        skip_button = Button(label="⏭️ Submit Report", style=ButtonStyle.primary, custom_id="skip_info")
        skip_button.callback = self._skip_callback
        self.add_item(skip_button)

    async def _add_info_callback(self, interaction):
        """Handle add info button click"""
        # If changing selection, clean up any messages after additional info step
        if self.selected_action and self.selected_action != "add_info":
            await self.report.cleanup_messages_from_step(2)  # Clean up messages after additional info

        self.selected_action = "add_info"

        modal = AdditionalInfoModal(self.report)
        await interaction.response.send_modal(modal)

        # Update buttons to show selection
        await self._update_buttons_after_selection(interaction, "add_info")

    async def _skip_callback(self, interaction):
        """Handle skip button click"""
        await interaction.response.defer()

        # If changing selection, clean up any messages after additional info step
        if self.selected_action and self.selected_action != "skip_info":
            await self.report.cleanup_messages_from_step(2)  # Clean up messages after additional info

        self.selected_action = "skip_info"

        # Update buttons to show selection
        await self._update_buttons_after_selection(interaction, "skip_info")

        # Submit without additional info
        await self.report.submit_report_to_mods()

    async def _update_buttons_after_selection(self, interaction, selected_action):
        """Update buttons to show what was selected while keeping them clickable"""
        for item in self.children:
            if isinstance(item, Button):
                if item.custom_id == selected_action:
                    item.style = ButtonStyle.success
                    item.label = f"✅ {item.label}"
                else:
                    # Reset other button
                    item.style = ButtonStyle.primary
                    if item.custom_id == "add_info":
                        item.label = "📝 Add Information"
                    else:
                        item.label = "⏭️ Submit Report"

        self.selected_action = selected_action
        await interaction.edit_original_response(view=self)


class AdditionalInfoModal(Modal):
    """Modal for submitting additional information"""

    def __init__(self, report):
        super().__init__(title="Additional Information")
        self.report = report

        self.info = TextInput(
            label="Additional Details",
            placeholder="Provide any additional context that might help moderators understand the situation...",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=1000,
        )
        self.add_item(self.info)

    async def on_submit(self, interaction):
        """Handle submission of additional information"""
        await interaction.response.defer()

        # Store the additional information
        self.report.additional_info = self.info.value

        await self.report.submit_report_to_mods()


class SelectView(View):
    """A generic selection view that can be used for any type of selection"""

    def __init__(self, report, placeholder, options, on_select, parent_type=None):
        super().__init__(timeout=300)
        self.report = report
        self.on_select = on_select
        self.parent_type = parent_type
        self.selected_value = None

        # Add the select menu
        select_options = []
        for key, value in options.items():
            # Include emoji in select options
            label = f"{value.emoji} {value.label}"
            select_options.append(
                SelectOption(label=label, value=key, description=value.description[:100])  # Discord limit
            )

        select = Select(placeholder=placeholder, options=select_options, row=0, custom_id="subtype_select")
        select.callback = self.select_callback
        self.add_item(select)

    async def select_callback(self, interaction):
        await interaction.response.defer()

        value = interaction.data["values"][0]

        # If user is changing subtype selection, clean up messages after subtype step
        if self.selected_value and self.selected_value != value:
            await self.report.cleanup_messages_from_step(1)  # Clean up messages after subtype selection

        self.selected_value = value

        # Update the select to show selection was made
        for item in self.children:
            if isinstance(item, Select):
                selected_subtype = ABUSE_TYPES[self.parent_type].subtypes[value]
                item.placeholder = f"✅ Selected: {selected_subtype.label}"

        await interaction.edit_original_response(view=self)

        await self.on_select(interaction, value, self.parent_type)
