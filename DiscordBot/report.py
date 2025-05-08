import discord
from discord.ui import View, Button, Select
from discord import SelectOption
import shortuuid
from utils import FRAUD_FLOW, quote_message


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
        embed.add_field(name="Message Author", inline=True, value=f"{message.author.mention}")
        embed.add_field(name="Message Content", value=quote_message(message), inline=False)
        embed.set_footer(text=f"Sent in #{message.channel.name}")
        embed.timestamp = message.created_at

        return embed

    def add_report_details(self, embed):
        """Add the report details to the embed"""
        message = self.report_data["reported_message"]
        reporter = self.report_data["interaction"].user

        # Add report details
        if self.report_data.get("report_type") == "fraud":
            fraud_type = self.report_data.get("fraud_type", "unspecified")
            fraud_type_str = FRAUD_FLOW[fraud_type]["label"]
            embed.add_field(name="Report Type", value=f"Fraud ({fraud_type_str})")
            if self.report_data.get("subtype"):
                subtype = self.report_data.get("subtype", "unspecified")
                subtype_options = FRAUD_FLOW[fraud_type]["subtypes"]["options"]
                subtype_str = subtype_options[subtype]["label"]
                embed.add_field(name="Subtype", value=subtype_str)
        else:
            embed.add_field(name="Report Type", value=self.report_data.get("report_type", "Other"))

        embed.add_field(name="Message Author", value=f"{message.author.mention}", inline=True)
        embed.add_field(name="Channel", value=self.report_data["message_link"], inline=True)
        embed.add_field(name="Message Content", value=quote_message(message), inline=False)
        embed.add_field(name="Reported by", value=f"{reporter.mention}")
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

        await mod_channel.send(embed=embed)
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
        message = """Thank you for your report. Our content moderation team will review it shortly and update you via a private message if necessary.
        
        In the meantime, you may wish to block the message author to stop future messages from appearing in your view."""

        if self.report_data.get("fraud_type") == "account_takeover":
            message = """Thank you for your report. Our moderation team will review it shortly and update you via a private message if necessary.
            
            We recommend you change your password and enable two-factor authentication if you have not already done so."""

        embed = discord.Embed(title="Report Submitted", description=message, color=discord.Color.green())
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
            options=FRAUD_FLOW,
            field_name="fraud_type",
            on_select=self.fraud_type_selected,
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
        fraud_config = FRAUD_FLOW[value]
        subtype_config = fraud_config["subtypes"]

        embed = discord.Embed(
            title=subtype_config["title"],
            description=subtype_config["description"],
            color=discord.Color.orange(),
        )

        # Create the subtype selection view
        view = SelectView(
            report=self.report,
            placeholder=f"Select {fraud_config['label'].lower()} type...",
            options=subtype_config["options"],
            field_name="subtype",
            on_select=self.subtype_selected,
        )

        await interaction.edit_original_response(embed=embed, view=view)

    async def subtype_selected(self, interaction, value):
        """Handle subtype selection"""
        await self.report.submit_report_to_mods()
        await self.report.send_confirmation(interaction)


class SelectView(View):
    """
    A generic selection view that can be used for any type of selection.
    """

    def __init__(self, report, placeholder, options, field_name, on_select):
        super().__init__(timeout=300)  # 5 minute timeout
        self.report = report
        self.on_select = on_select
        self.field_name = field_name

        # Add the select menu
        select_options = []
        for key, value in options.items():
            select_options.append(
                SelectOption(label=value["label"], value=key, description=value["description"])
            )

        select = Select(placeholder=placeholder, options=select_options, row=0)
        select.callback = self.select_callback
        self.add_item(select)

    async def select_callback(self, interaction):
        await interaction.response.defer(ephemeral=True)

        value = interaction.data["values"][0]
        self.report.report_data[self.field_name] = value
        await self.on_select(interaction, value)
