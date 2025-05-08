import discord
from discord.ui import View, Button, Select
from discord import SelectOption
import shortuuid

FRAUD_OPTIONS = [
    {
        "label": "Phishing",
        "value": "phishing",
        "description": "Attempts to steal personal information",
    },
    {
        "label": "Investment Scam",
        "value": "investment_scam",
        "description": "Fraudulent investment opportunities",
    },
    {
        "label": "E-Commerce Scam",
        "value": "ecommerce",
        "description": "Fake stores or counterfeit items",
    },
    {
        "label": "Account Takeover",
        "value": "account_takeover",
        "description": "Unauthorized account access",
    },
]

FRAUD_SUBTYPES = {
    "phishing": {
        "title": "Select Phishing Type",
        "description": "What type of information is being sought?",
        "options": [
            {
                "label": "identifying_info",
                "value": "identifying_info",
                "description": "Seeking birthday, name, or other identifying information",
            },
            {
                "label": "location",
                "value": "location",
                "description": "Seeking location information",
            },
            {
                "label": "payment_info",
                "value": "payment_info",
                "description": "Seeking credit card or payment details",
            },
            {
                "label": "SSN",
                "value": "ssn",
                "description": "Seeking Social Security Number",
            },
        ],
    },
    "investment_scam": {
        "title": "Select Investment Scam Type",
        "description": "What kind of investment scam is this?",
        "options": [
            {
                "label": "Crypto",
                "value": "crypto",
                "description": "Cryptocurrency investment scam",
            },
            {
                "label": "Counterfeit",
                "value": "counterfeit",
                "description": "Selling counterfeit items",
            },
            {
                "label": "Other",
                "value": "other",
                "description": "Other investment scam type",
            },
        ],
    },
    "ecommerce": {
        "title": "Select E-Commerce Scam Type",
        "description": "What kind of e-commerce fraud is this?",
        "options": [
            {
                "label": "Fake Online Store",
                "value": "fake_store",
                "description": "Fraudulent online store",
            },
            {
                "label": "Counterfeit Items",
                "value": "counterfeit",
                "description": "Selling counterfeit items",
            },
        ],
    },
    "account_takeover": {
        "title": "Select Account Takeover Type",
        "description": "What kind of account takeover is this?",
        "options": [
            {
                "label": "Unauthorized Login",
                "value": "unauthorized_login",
                "description": "Someone logged into my account without permission",
            },
            {
                "label": "Unauthorized Message",
                "value": "unauthorized_message",
                "description": "Someone posted/messaged from my account",
            },
        ],
    },
}


class Report:
    def __init__(self, client, interaction, message):
        self.client = client
        self.id = shortuuid.uuid()[:8]

        self.report_data = {
            "reported_message": message,
            "interaction": interaction,
            "message_link": (
                f"https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id}"
            ),
            "report_type": None,
            "fraud_type": None,
            "subtype": None,
        }

    async def show_report_view(self):
        """Show the message being reported and walk the user through the report flow"""
        embed = self.create_main_embed(self.report_data["reported_message"])
        view = MainReportView(self)
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

        # Add user information
        embed.add_field(
            name="Message Author",
            inline=True,
            value=f"{message.author.mention}",
        )

        # Add message content
        message_content = message.content if message.content else "[No text content]"
        if len(message_content) > 1024:
            message_content = message_content[:1021] + "..."
        message_content = f">>> {message_content}"
        embed.add_field(name="Message Content", value=message_content, inline=False)

        # Add footer with channel information
        embed.set_footer(text=f"Sent in #{message.channel.name}")

        # Add timestamp from the original message
        embed.timestamp = message.created_at

        return embed

    async def submit_report_to_mods(self):
        """Submit the completed report to moderators"""
        # Get the guild ID from the original message
        guild_id = self.report_data["reported_message"].guild.id

        # Get the mod channel for this guild
        mod_channel = self.client.mod_channels.get(guild_id)
        if not mod_channel:
            return  # Handle the case when mod channel is not set up

        message = self.report_data["reported_message"]
        reporter = self.report_data["interaction"].user

        # Create an embed for moderators
        embed = discord.Embed(
            title=f"New Report",
            description="",
            color=discord.Color.red(),
        )

        # Add report details
        if self.report_data.get("report_type") == "fraud":
            embed.add_field(
                name="Report Type",
                value=f"Fraud ({self.report_data.get('fraud_type', 'unspecified')})",
            )
            if self.report_data.get("subtype"):
                embed.add_field(name="Subtype", value=self.report_data.get("subtype"))
        else:
            embed.add_field(name="Report Type", value=self.report_data.get("report_type", "Other"))

        # Add user information
        embed.add_field(
            name="Message Author",
            value=f"{message.author.mention}",
            inline=True,
        )
        embed.add_field(name="Channel", value=self.report_data["message_link"], inline=True)

        # Add message content
        message_content = message.content if message.content else "[No text content]"
        if len(message_content) > 1024:
            message_content = message_content[:1021] + "..."
        message_content = f">>> {message_content}"
        embed.add_field(name=f"Message Content", value=message_content, inline=False)

        embed.add_field(name="Reported by", value=f"{reporter.mention}")
        embed.set_footer(text=f"Report ID: {self.id}")
        embed.timestamp = discord.utils.utcnow()

        await mod_channel.send(embed=embed)

    async def send_confirmation(self, interaction):
        """Show confirmation message after report submission"""
        embed = discord.Embed(
            title="Report Submitted",
            description="Thank you for your report. A moderator will review it shortly.",
            color=discord.Color.green(),
        )
        await interaction.edit_original_response(embed=embed, view=None)


class MainReportView(View):
    def __init__(self, report):
        super().__init__(timeout=300)  # 5 minute timeout
        self.report = report

    @discord.ui.button(label="Fraud", style=discord.ButtonStyle.primary)
    async def fraud_button(self, interaction, button):
        await interaction.response.defer(ephemeral=True)
        self.report.report_data["report_type"] = "fraud"

        # Create the fraud type selection embed
        embed = discord.Embed(
            title="Select Fraud Type",
            description="What kind of fraud is this message attempting?",
            color=discord.Color.orange(),
        )

        # Include a summary of the report so far
        message = self.report.report_data["reported_message"]
        embed.add_field(
            name="Reporting Message",
            value=f"From {message.author.mention} in {message.channel.mention}",
            inline=False,
        )

        # Create fraud type view
        view = SelectView(
            report=self.report,
            placeholder="Select fraud type...",
            options=FRAUD_OPTIONS,
            on_select=self.fraud_type_selected,
            back_view_factory=MainReportView,
        )

        await interaction.edit_original_response(embed=embed, view=view)

    @discord.ui.button(label="Other", style=discord.ButtonStyle.secondary)
    async def other_button(self, interaction, button):
        await interaction.response.defer(ephemeral=True)
        self.report.report_data["report_type"] = "other"

        # Submit the report and show confirmation
        await self.report.submit_report_to_mods()
        await self.report.send_confirmation(interaction)

    async def fraud_type_selected(self, interaction, value):
        """Handle fraud type selection"""
        self.report.report_data["fraud_type"] = value

        # If a valid fraud type was selected, show the corresponding subtype selection
        if value in FRAUD_SUBTYPES:
            subtype_config = FRAUD_SUBTYPES[value]

            embed = discord.Embed(
                title=subtype_config["title"],
                description=subtype_config["description"],
                color=discord.Color.orange(),
            )

            # Create the subtype selection view
            view = SelectView(
                report=self.report,
                placeholder=f"Select {value.replace('_', ' ')} type...",
                options=subtype_config["options"],
                on_select=self.subtype_selected,
                back_view_factory=lambda report: SelectView(
                    report=report,
                    placeholder="Select fraud type...",
                    options=FRAUD_OPTIONS,
                    on_select=self.fraud_type_selected,
                    back_view_factory=MainReportView,
                ),
                field_name="subtype",
            )

            await interaction.edit_original_response(embed=embed, view=view)
        else:
            # Submit the report directly if no subtypes are defined
            await self.report.submit_report_to_mods()
            await self.report.send_confirmation(interaction)

    async def subtype_selected(self, interaction, value):
        """Handle subtype selection"""
        # Submit the report and show confirmation
        await self.report.submit_report_to_mods()
        await self.report.send_confirmation(interaction)


class SelectView(View):
    """
    A generic selection view that can be used for any type of selection.
    This replaces the numerous specific selection views in the original code.
    """

    def __init__(
        self,
        report,
        placeholder,
        options,
        on_select,
        back_view_factory,
        field_name="fraud_type",
    ):
        super().__init__(timeout=300)  # 5 minute timeout
        self.report = report
        self.on_select = on_select
        self.back_view_factory = back_view_factory
        self.field_name = field_name

        # Add the select menu
        select_options = [
            SelectOption(label=option["label"], value=option["value"], description=option["description"])
            for option in options
        ]

        select = Select(placeholder=placeholder, options=select_options, row=0)
        select.callback = self.select_callback
        self.add_item(select)

        # Add back button
        back_button = Button(label="← Back", style=discord.ButtonStyle.secondary, row=1)
        back_button.callback = self.back_button_callback
        self.add_item(back_button)

    async def select_callback(self, interaction):
        await interaction.response.defer(ephemeral=True)

        # Get the selected value
        value = interaction.data["values"][0]

        # Call the provided callback with the selected value
        await self.on_select(interaction, value)

    async def back_button_callback(self, interaction):
        await interaction.response.defer(ephemeral=True)

        # Clear the current field selection
        if self.field_name in self.report.report_data:
            del self.report.report_data[self.field_name]

        # If going back from a subtype to fraud type selection
        if self.field_name == "subtype" and "fraud_type" in self.report.report_data:
            # Create the fraud type selection embed
            embed = discord.Embed(
                title="Select Fraud Type",
                description="What kind of fraud is this message attempting?",
                color=discord.Color.orange(),
            )

            # Include a summary of the report so far
            message = self.report.report_data["reported_message"]
            embed.add_field(
                name="Reporting Message",
                value=f"From {message.author.mention} in {message.channel.mention}",
                inline=False,
            )
        else:
            # Create the main report embed again
            message = self.report.report_data["reported_message"]
            embed = self.report.create_main_embed(message)

        # Create the appropriate back view using the provided factory
        view = self.back_view_factory(self.report)

        # Edit the original message to show the previous view
        await interaction.edit_original_response(embed=embed, view=view)
