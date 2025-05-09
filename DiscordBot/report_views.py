import discord
from discord.ui import View, Button, Select, Modal, TextInput
from discord import SelectOption, ButtonStyle
from helpers import ABUSE_TYPES


class MainReportView(View):
    def __init__(self, report, timeout=300):
        super().__init__(timeout=timeout)
        self.report = report
        self._add_abuse_buttons()

    def _add_abuse_buttons(self):
        """Add buttons for each abuse type in the ABUSE_TYPES dictionary"""
        # Add a button for each abuse type, using a consistent blue style for all
        for i, (key, abuse_type) in enumerate(ABUSE_TYPES.items()):
            # Four buttons per row (we have 8 buttons total right now)
            row = i // 4

            button_color = ButtonStyle.primary if key != "other" else ButtonStyle.secondary
            button = Button(
                label=abuse_type.label,
                style=button_color,
                row=row,
                custom_id=f"abuse_type_{key}",
            )

            # Set the callback
            button.callback = self._create_abuse_button_callback(key)

            # Add the button to the view
            self.add_item(button)

    def _create_abuse_button_callback(self, abuse_type_key):
        """Create a callback for the abuse type button"""

        async def callback(interaction):
            await interaction.response.defer()
            abuse_type = ABUSE_TYPES[abuse_type_key]

            # Set the report data
            self.report.abuse_category = abuse_type_key
            self.report.report_type = abuse_type.label

            # Handle direct reports (no subtypes)
            if not abuse_type.subtypes:
                await self._show_additional_info_prompt(interaction)
                return

            # Handle subtypes
            await self._handle_subtype_selection(interaction, abuse_type_key, abuse_type)
            return

        return callback

    async def _handle_subtype_selection(self, interaction, abuse_type_key, abuse_type):
        """Handle subtype selection for any abuse type with subtypes"""
        embed = discord.Embed(
            title=f"Select {abuse_type.label} Type",
            description=f"What kind of {abuse_type.label.lower()} is this?",
            color=discord.Color.blue(),
        )

        # Include a summary of the report so far
        message = self.report.reported_message
        embed.add_field(
            name="Reporting Message",
            value=f"From {message.author.mention} in {message.channel.mention}",
            inline=False,
        )

        # Create subtype view
        view = SelectView(
            report=self.report,
            placeholder=f"Select {abuse_type.label.lower()} type...",
            options=abuse_type.subtypes,
            on_select=self.subtype_selected,
            parent_type=abuse_type_key,
        )

        await interaction.followup.send(embed=embed, view=view)

    async def subtype_selected(self, interaction, value, parent_type=None):
        """Handle subtype selection recursively"""
        # Add the selected subtype to the chain
        self.report.subtypes.append(value)

        # Get the current type in the chain
        current_type = ABUSE_TYPES[parent_type]
        for subtype_key in self.report.subtypes:
            if current_type.subtypes and subtype_key in current_type.subtypes:
                current_type = current_type.subtypes[subtype_key]

        # If this type has further subtypes, show another selection
        if current_type.subtypes:
            embed = discord.Embed(
                title=f"Select {current_type.label} Details",
                description=f"Please provide more specific details about this {current_type.label.lower()}.",
                color=discord.Color.blue(),
            )

            view = SelectView(
                report=self.report,
                placeholder=f"Select specific details...",
                options=current_type.subtypes,
                on_select=self.subtype_selected,
                parent_type=parent_type,
            )

            await interaction.followup.send(embed=embed, view=view)
            return

        # If no further subtypes, show additional info prompt
        await self._show_additional_info_prompt(interaction)

    async def _show_additional_info_prompt(self, interaction):
        """Show prompt for additional information"""
        embed = discord.Embed(
            title="Additional Information",
            description="Would you like to provide any additional information about this report?",
            color=discord.Color.blue(),
        )

        view = AdditionalInfoView(self.report)
        await interaction.followup.send(embed=embed, view=view)


class AdditionalInfoView(View):
    """View for handling additional information input"""

    def __init__(self, report, timeout=300):
        super().__init__(timeout=timeout)
        self.report = report

        # Add buttons
        add_info_button = Button(label="Add Information", style=ButtonStyle.primary, custom_id="add_info")
        add_info_button.callback = self._add_info_callback
        self.add_item(add_info_button)

        skip_button = Button(label="Skip", style=ButtonStyle.secondary, custom_id="skip_info")
        skip_button.callback = self._skip_callback
        self.add_item(skip_button)

    async def _add_info_callback(self, interaction):
        """Handle add info button click"""
        modal = AdditionalInfoModal(self.report)
        await interaction.response.send_modal(modal)

    async def _skip_callback(self, interaction):
        """Handle skip button click"""
        await interaction.response.defer()
        await self.report.submit_report_to_mods()


class AdditionalInfoModal(Modal):
    """Modal for submitting additional information"""

    def __init__(self, report):
        super().__init__(title="Additional Information")
        self.report = report

        self.info = TextInput(
            label="Additional Information",
            placeholder="Please provide any additional context or information that might help moderators...",
            style=discord.TextStyle.paragraph,
            required=True,
        )
        self.add_item(self.info)

    async def on_submit(self, interaction):
        """Handle submission of additional information"""
        await interaction.response.defer()

        # Store the additional information
        self.report.additional_info = self.info.value

        # Submit the report
        await self.report.submit_report_to_mods()


class SelectView(View):
    """
    A generic selection view that can be used for any type of selection.
    """

    def __init__(self, report, placeholder, options, on_select, parent_type=None, timeout=300):
        super().__init__(timeout=timeout)
        self.report = report
        self.on_select = on_select
        self.parent_type = parent_type

        # Add the select menu
        select_options = []
        for key, value in options.items():
            select_options.append(SelectOption(label=value.label, value=key, description=value.description))

        select = Select(placeholder=placeholder, options=select_options, row=0)
        select.callback = self.select_callback
        self.add_item(select)

    async def select_callback(self, interaction):
        await interaction.response.defer()
        value = interaction.data["values"][0]
        await self.on_select(interaction, value, self.parent_type)
