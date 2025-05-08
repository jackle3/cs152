from enum import Enum, auto
import discord
import re


class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    AWAITING_POST_TYPE = auto()
    AWAITING_OTHER_FRAUD_CHECK = auto()
    AWAITING_FRAUD_TYPE = auto()
    AWAITING_PHISHING_TYPE = auto()
    AWAITING_INVESTMENT_SCAM_TYPE = auto()
    AWAITING_ECOMMERCE_TYPE = auto()
    AWAITING_ACCOUNT_TAKEOVER_TYPE = auto()
    AWAITING_BLOCK_DECISION = auto()
    REPORT_COMPLETE = auto()


class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"

    def __init__(self, client):
        self.state = State.REPORT_START
        self.client = client
        self.message = None
        self.report_data = {
            "reporter": None,
            "reported_message": None,
            "post_type": None,
            "fraud_type": None,
            "phishing_type": None,
            "investment_scam_type": None,
            "ecommerce_type": None,
            "account_takeover_type": None,
            "blocked": False,
            "moderated": False,
            "moderation_action": None,
        }
        self.last_bot_message = None

    async def handle_message(self, message):
        """
        This function makes up the meat of the user-side reporting flow. It defines how we transition between states and what
        prompts to offer at each of those states. You're welcome to change anything you want; this skeleton is just here to
        get you started and give you a model for working with Discord.
        """

        if message.content == self.CANCEL_KEYWORD:
            self.state = State.REPORT_COMPLETE
            return ["Report cancelled."]

        if self.state == State.REPORT_START:
            reply = "Thank you for starting the reporting process. "
            reply += "Say `help` at any time for more information.\n\n"
            reply += "Please copy paste the link to the message you want to report.\n"
            reply += (
                "You can obtain this link by right-clicking the message and clicking `Copy Message Link`."
            )
            self.state = State.AWAITING_MESSAGE
            self.report_data["reporter"] = message.author
            return [reply]

        if self.state == State.AWAITING_MESSAGE:
            # Parse out the three ID strings from the message link
            m = re.search("/(\d+)/(\d+)/(\d+)", message.content)
            if not m:
                return ["I'm sorry, I couldn't read that link. Please try again or say `cancel` to cancel."]
            guild = self.client.get_guild(int(m.group(1)))
            if not guild:
                return [
                    "I cannot accept reports of messages from guilds that I'm not in. Please have the guild owner add me to the guild and try again."
                ]
            channel = guild.get_channel(int(m.group(2)))
            if not channel:
                return [
                    "It seems this channel was deleted or never existed. Please try again or say `cancel` to cancel."
                ]
            try:
                message = await channel.fetch_message(int(m.group(3)))
            except discord.errors.NotFound:
                return [
                    "It seems this message was deleted or never existed. Please try again or say `cancel` to cancel."
                ]

            # Here we've found the message - it's up to you to decide what to do next!
            self.message = message
            self.report_data["reported_message"] = message
            self.state = State.AWAITING_POST_TYPE

            bot_message = await message.channel.send(
                "Please select post type:\nReact with:\n1️⃣ for Fraud\n2️⃣ for Other"
            )
            self.last_bot_message = bot_message
            await bot_message.add_reaction("1️⃣")
            await bot_message.add_reaction("2️⃣")
            return []

        if self.state == State.AWAITING_POST_TYPE:
            if message.content == "1️⃣":  # Fraud
                self.report_data["post_type"] = "fraud"
                self.state = State.AWAITING_FRAUD_TYPE
                bot_message = await message.channel.send(
                    "Please select fraud type:\nReact with:\n1️⃣ for Phishing\n2️⃣ for Investment Scam\n3️⃣ for E-Commerce\n4️⃣ for Account Takeover"
                )
                self.last_bot_message = bot_message
                await bot_message.add_reaction("1️⃣")
                await bot_message.add_reaction("2️⃣")
                await bot_message.add_reaction("3️⃣")
                await bot_message.add_reaction("4️⃣")
                return []
            elif message.content == "2️⃣":  # Other
                self.report_data["post_type"] = "other"
                self.state = State.AWAITING_OTHER_FRAUD_CHECK
                bot_message = await message.channel.send(
                    "Thanks for reporting to fraud bot. Do you believe this message is an attempt at fraud?\nReact with:\n1️⃣ for Yes\n2️⃣ for No"
                )
                self.last_bot_message = bot_message
                await bot_message.add_reaction("1️⃣")
                await bot_message.add_reaction("2️⃣")
                return []

        if self.state == State.AWAITING_OTHER_FRAUD_CHECK:
            if message.content == "1️⃣":  # Yes
                self.state = State.AWAITING_FRAUD_TYPE
                bot_message = await message.channel.send(
                    "Please select fraud type:\nReact with:\n1️⃣ for Phishing\n2️⃣ for Investment Scam\n3️⃣ for E-Commerce\n4️⃣ for Account Takeover"
                )
                self.last_bot_message = bot_message
                await bot_message.add_reaction("1️⃣")
                await bot_message.add_reaction("2️⃣")
                await bot_message.add_reaction("3️⃣")
                await bot_message.add_reaction("4️⃣")
                return []
            elif message.content == "2️⃣":  # No
                self.state = State.REPORT_COMPLETE
                return ["Thank you for your report. This is a fraud bot, so we can't help with this case."]

        if self.state == State.AWAITING_FRAUD_TYPE:
            if message.content == "1️⃣":  # Phishing
                self.report_data["fraud_type"] = "phishing"
                self.state = State.AWAITING_PHISHING_TYPE
                bot_message = await message.channel.send(
                    "Please select Phishing type:\nReact with:\n1️⃣ for Seeking Birthday, Name, or other Identifying Information\n2️⃣ for Seeking Location\n3️⃣ for Seeking Payment Information\n4️⃣ for Seeking SSN\n5️⃣ for Seeking Account Information"
                )
                self.last_bot_message = bot_message
                await bot_message.add_reaction("1️⃣")
                await bot_message.add_reaction("2️⃣")
                await bot_message.add_reaction("3️⃣")
                await bot_message.add_reaction("4️⃣")
                await bot_message.add_reaction("5️⃣")
                return []

            elif message.content == "2️⃣":  # Investment Scam
                self.report_data["fraud_type"] = "investment_scam"
                self.state = State.AWAITING_INVESTMENT_SCAM_TYPE
                bot_message = await message.channel.send(
                    "Please select scam type:\nReact with:\n1️⃣ for Crypto\n2️⃣ for Selling Counterfeit Items\n3️⃣ for Other"
                )
                self.last_bot_message = bot_message
                await bot_message.add_reaction("1️⃣")
                await bot_message.add_reaction("2️⃣")
                await bot_message.add_reaction("3️⃣")
                return []

            elif message.content == "3️⃣":  # E-Commerce
                self.report_data["fraud_type"] = "ecommerce"
                self.state = State.AWAITING_ECOMMERCE_TYPE
                bot_message = await message.channel.send(
                    "Please select e-commerce type:\nReact with:\n1️⃣ for Fake Online Store\n2️⃣ for Selling Counterfeit Items"
                )
                self.last_bot_message = bot_message
                await bot_message.add_reaction("1️⃣")
                await bot_message.add_reaction("2️⃣")
                return []

            elif message.content == "4️⃣":  # Account Takeover
                self.report_data["fraud_type"] = "account_takeover"
                self.state = State.AWAITING_ACCOUNT_TAKEOVER_TYPE
                bot_message = await message.channel.send(
                    "Please select takeover type:\nReact with:\n1️⃣ for Unauthorized Login\n2️⃣ for Unauthorized Post/Message from my account"
                )
                self.last_bot_message = bot_message
                await bot_message.add_reaction("1️⃣")
                await bot_message.add_reaction("2️⃣")
                return []

        if self.state in [
            State.AWAITING_PHISHING_TYPE,
            State.AWAITING_INVESTMENT_SCAM_TYPE,
            State.AWAITING_ECOMMERCE_TYPE,
        ]:
            self.report_data["subcategory"] = message.content
            self.state = State.AWAITING_BLOCK_DECISION
            return await self.show_block_decision(message.channel)

        if self.state == State.AWAITING_ACCOUNT_TAKEOVER_TYPE:
            self.report_data["subcategory"] = message.content
            self.state = State.AWAITING_BLOCK_DECISION
            advisory = "We recommend changing your password and/or account email. Please follow these steps…"
            block_decision = await self.show_block_decision(message.channel)
            return [advisory] + block_decision

        if self.state == State.AWAITING_BLOCK_DECISION:
            if message.content == "1️⃣":  # Yes
                self.report_data["blocked"] = True
                self.state = State.REPORT_COMPLETE
                return ["User has been blocked. Report completed."]
            elif message.content == "2️⃣":  # No
                self.state = State.REPORT_COMPLETE
                return ["Report completed. Thank you for your report."]

        return []

    async def show_block_decision(self, channel):
        bot_message = await channel.send(
            "Thank you for reporting. Our content moderation team will review the account and/or post. Would you like to block the user?\nReact with:\n1️⃣ for Yes\n2️⃣ for No"
        )
        self.last_bot_message = bot_message
        await bot_message.add_reaction("1️⃣")
        await bot_message.add_reaction("2️⃣")
        return []

    def report_complete(self):
        return self.state == State.REPORT_COMPLETE

    def get_report_summary(self):
        """Returns a formatted summary of the report for moderators"""
        summary = f"Report from {self.report_data['reporter'].name}:\n"
        if self.report_data["reported_message"] is not None:
            summary += f"Reported Message: {self.report_data['reported_message'].content}\n"
        else:
            summary += "Reported Message: [No message provided]\n"
        summary += f"Post Type: {self.report_data['post_type']}\n"
        if self.report_data["fraud_type"]:
            summary += f"Fraud Type: {self.report_data['fraud_type']}\n"
        if self.report_data["phishing_type"]:
            summary += f"Phishing Type: {self.report_data['phishing_type']}\n"
        if self.report_data["investment_scam_type"]:
            summary += f"Investment Scam Type: {self.report_data['investment_scam_type']}\n"
        if self.report_data["ecommerce_type"]:
            summary += f"E-Commerce Type: {self.report_data['ecommerce_type']}\n"
        if self.report_data["account_takeover_type"]:
            summary += f"Account Takeover Type: {self.report_data['account_takeover_type']}\n"
        summary += f"User Blocked: {self.report_data['blocked']}\n"
        return summary

    def moderate(self, action):
        """Handle moderation actions"""
        self.report_data["moderated"] = True
        self.report_data["moderation_action"] = action
        return f"Moderation action taken: {action}"
