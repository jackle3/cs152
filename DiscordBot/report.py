import discord
from discord.ui import View, Button, Select, Modal, TextInput
from discord import SelectOption, ButtonStyle
import shortuuid
from utils import ABUSE_TYPES, quote_message, REPORT_CONFIRMATION_MESSAGE
from moderator import ModeratorActionView


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
            "history": [],  # List to store the history of views for back navigation
        }

    async def show_report_view(self):
        """Show the message being reported and walk the user through the report flow"""
        embed = self.create_main_embed(self.report_data["reported_message"])
        view = MainReportView(self)
        self.report_data["history"].append(("main", embed, view))
        await self.report_data["interaction"].response.send_message(embed=embed, view=view, ephemeral=True)

    def create_main_embed(self, message):
        """Create the main report embed"""
        embed = discord.Embed(
            title="Report a Message",
            description="Please select a reason for reporting this message by clicking one of the buttons below.",
            color=discord.Color.blue(),
        )

        # Show the profile picture of the reported user as thumbnail
        embed.set_thumbnail(url=message.author.display_avatar.url if message.author.display_avatar else None)
        embed.add_field(name="Message Author", inline=True, value=f"{message.author.mention}")
        embed.add_field(name="Message Content", value=quote_message(message), inline=False)
        embed.set_footer(text=f"Sent in #{message.channel.name}")
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
            embed.add_field(name="Additional Information", value=self.report_data["additional_info"], inline=False)
            
        embed.set_footer(text=f"Report ID: {self.id}")
        embed.timestamp = discord.utils.utcnow()

    async def submit_report_to_mods(self):
        """Submit the completed report to moderators and send a confirmation copy to the reporter"""

        # Get the mod channel for this server
        guild_id = self.report_data["reported_message"].guild.id
        mod_channel = self.client.mod_channels.get(guild_id)
        if not mod_channel:
            assert False, "Mod channel not found for this server"

        # Create an embed for moderators
        embed = discord.Embed(title="New Report", description="", color=discord.Color.red())
        self.add_report_details(embed)

        # Send to mod channel with appropriate action buttons
        view = ModeratorActionView(self)
        await mod_channel.send(embed=embed, view=view)
        await self.send_dm_confirmation()

    async def send_dm_confirmation(self):
        """Send a DM confirmation to the reporter with the report details"""
        reporter = self.report_data["interaction"].user

        # Create an embed for the reporter
        embed = discord.Embed(
            title="Report Confirmation",
            description="Your report has been submitted to our moderation team.",
            color=discord.Color.green(),
        )
        self.add_report_details(embed)

        await reporter.send(embed=embed)

    async def send_confirmation(self, interaction):
        """Show confirmation message after report submission"""
        embed = discord.Embed(title="Report Submitted", description=REPORT_CONFIRMATION_MESSAGE, color=discord.Color.green())
        await interaction.edit_original_response(embed=embed, view=None)

    async def go_back(self, interaction):
        """Go back to the previous view in the history"""
        if len(self.report_data["history"]) > 1:
            # Remove current view
            self.report_data["history"].pop()
            
            # Get previous view
            _, embed, view = self.report_data["history"][-1]
            
            # If going back from subtype selection, remove the last subtype
            if self.report_data["subtypes"]:
                self.report_data["subtypes"].pop()
            
            await interaction.response.edit_message(embed=embed, view=view)


class BaseView(View):
    """Base view class with back button functionality"""
    
    def __init__(self, report, timeout=300):
        super().__init__(timeout=timeout)
        self.report = report
        self._add_back_button()

    def _add_back_button(self):
        """Add a back button to the view"""
        back_button = Button(
            label="Back",
            style=ButtonStyle.secondary,
            row=4,  # Always on the last row
            custom_id="back"
        )
        back_button.callback = self._back_callback
        self.add_item(back_button)

    async def _back_callback(self, interaction):
        """Handle back button click"""
        await self.report.go_back(interaction)


class MainReportView(BaseView):
    def __init__(self, report):
        super().__init__(report)
        self._add_abuse_buttons()

    def _add_abuse_buttons(self):
        """Add buttons for each abuse type in the ABUSE_TYPES dictionary"""
        # Add a button for each abuse type, using a consistent blue style for all
        for i, (key, abuse_type) in enumerate(ABUSE_TYPES.items()):
            # Calculate row based on position
            row = i // 3

            # Create a button with blue style
            button = Button(
                label=abuse_type.label,
                style=ButtonStyle.primary,  # Blue for all options
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
            await interaction.response.defer(ephemeral=True)
            abuse_type = ABUSE_TYPES[abuse_type_key]

            # Set the report data
            self.report.report_data["abuse_category"] = abuse_type_key
            self.report.report_data["report_type"] = abuse_type.label

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
        message = self.report.report_data["reported_message"]
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

        # Add to history
        self.report.report_data["history"].append(("subtype", embed, view))
        await interaction.edit_original_response(embed=embed, view=view)

    async def subtype_selected(self, interaction, value, parent_type=None):
        """Handle subtype selection recursively"""
        # Add the selected subtype to the chain
        self.report.report_data["subtypes"].append(value)

        # Get the current type in the chain
        current_type = ABUSE_TYPES[parent_type]
        for subtype_key in self.report.report_data["subtypes"]:
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

            # Add to history
            self.report.report_data["history"].append(("subtype", embed, view))
            await interaction.edit_original_response(embed=embed, view=view)
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
        
        # Add to history
        self.report.report_data["history"].append(("info", embed, view))
        await interaction.edit_original_response(embed=embed, view=view)


class AdditionalInfoView(BaseView):
    """View for handling additional information input"""
    
    def __init__(self, report):
        super().__init__(report)
        
        # Add buttons
        add_info_button = Button(
            label="Add Information",
            style=ButtonStyle.primary,
            custom_id="add_info"
        )
        add_info_button.callback = self._add_info_callback
        self.add_item(add_info_button)
        
        skip_button = Button(
            label="Skip",
            style=ButtonStyle.secondary,
            custom_id="skip_info"
        )
        skip_button.callback = self._skip_callback
        self.add_item(skip_button)

    async def _add_info_callback(self, interaction):
        """Handle add info button click"""
        modal = AdditionalInfoModal(self.report)
        await interaction.response.send_modal(modal)

    async def _skip_callback(self, interaction):
        """Handle skip button click"""
        await interaction.response.defer(ephemeral=True)
        await self.report.submit_report_to_mods()
        await self.report.send_confirmation(interaction)


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
        await interaction.response.defer(ephemeral=True)
        
        # Store the additional information
        self.report.report_data["additional_info"] = self.info.value
        
        # Submit the report
        await self.report.submit_report_to_mods()
        await self.report.send_confirmation(interaction)


class SelectView(BaseView):
    """
    A generic selection view that can be used for any type of selection.
    """

    def __init__(self, report, placeholder, options, on_select, parent_type=None):
        super().__init__(report)
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
        await interaction.response.defer(ephemeral=True)

        value = interaction.data["values"][0]
        await self.on_select(interaction, value, self.parent_type)
