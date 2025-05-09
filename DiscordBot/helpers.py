from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import discord


def quote_message(message):
    """Truncate a message and place it inside a block quote"""
    message_content = message.content if message.content else "[No text content]"
    if len(message_content) > 1024:
        message_content = message_content[:1021] + "..."
    message_content = f">>> {message_content}"
    return message_content


@dataclass
class AbuseType:
    label: str
    description: str
    subtypes: Optional[Dict[str, "AbuseType"]] = None


# Fraud subtypes
PHISHING_SUBTYPES = {
    "identifying_info": AbuseType(
        label="Identifying Information",
        description="Seeking birthday, name, or other identifying information",
    ),
    "location": AbuseType(
        label="Location",
        description="Seeking location information",
    ),
    "payment_info": AbuseType(
        label="Payment Information",
        description="Seeking credit card or payment details",
    ),
    "ssn": AbuseType(
        label="Social Security Number",
        description="Seeking Social Security Number",
    ),
}

INVESTMENT_SCAM_SUBTYPES = {
    "crypto": AbuseType(
        label="Crypto",
        description="Cryptocurrency investment scam",
    ),
    "counterfeit": AbuseType(
        label="Counterfeit",
        description="Selling counterfeit items",
    ),
    "other": AbuseType(
        label="Other",
        description="Other investment scam type",
    ),
}

ECOMMERCE_SUBTYPES = {
    "fake_store": AbuseType(
        label="Fake Online Store",
        description="Fraudulent online store",
    ),
    "counterfeit": AbuseType(
        label="Counterfeit Items",
        description="Selling counterfeit items",
    ),
}

ACCOUNT_TAKEOVER_SUBTYPES = {
    "unauthorized_login": AbuseType(
        label="Unauthorized Login",
        description="Someone logged into my account without permission",
    ),
    "unauthorized_message": AbuseType(
        label="Unauthorized Message",
        description="Someone posted/messaged from my account",
    ),
}

# Harassment subtypes
HARASSMENT_SUBTYPES = {
    "bullying": AbuseType(
        label="Bullying",
        description="Persistent harmful behavior targeting an individual",
    ),
    "sexual_harassment": AbuseType(
        label="Sexual Harassment",
        description="Unwanted sexual comments or advances",
    ),
    "threats": AbuseType(
        label="Threats",
        description="Threats of harm or intimidation",
    ),
    "doxxing": AbuseType(
        label="Doxxing",
        description="Sharing private or personal information without consent",
    ),
}

# Hate speech subtypes
HATE_SPEECH_SUBTYPES = {
    "racial": AbuseType(
        label="Racial/Ethnic",
        description="Hate based on race or ethnicity",
    ),
    "gender": AbuseType(
        label="Gender-Based",
        description="Hate based on gender or gender identity",
    ),
    "religion": AbuseType(
        label="Religious",
        description="Hate based on religious beliefs",
    ),
    "orientation": AbuseType(
        label="Sexual Orientation",
        description="Hate based on sexual orientation",
    ),
    "disability": AbuseType(
        label="Ability",
        description="Hate based on disability",
    ),
}

# Illegal content subtypes
ILLEGAL_CONTENT_SUBTYPES = {
    "piracy": AbuseType(
        label="Piracy",
        description="Unauthorized sharing of copyrighted material",
    ),
    "csam": AbuseType(
        label="CSAM",
        description="Child Sexual Abuse Material",
    ),
    "drugs": AbuseType(
        label="Illegal Substances",
        description="Content selling or promoting illegal substances",
    ),
    "weapons": AbuseType(
        label="Weapons/Violence",
        description="Content selling illegal weapons or promoting violence",
    ),
}

# Fraud types
FRAUD_SUBTYPES = {
    "phishing": AbuseType(
        label="Phishing",
        description="Attempts to steal personal information",
        subtypes=PHISHING_SUBTYPES,
    ),
    "investment_scam": AbuseType(
        label="Investment Scam",
        description="Fraudulent investment opportunities",
        subtypes=INVESTMENT_SCAM_SUBTYPES,
    ),
    "ecommerce": AbuseType(
        label="E-Commerce Scam",
        description="Fake stores or counterfeit items",
        subtypes=ECOMMERCE_SUBTYPES,
    ),
    "account_takeover": AbuseType(
        label="Account Takeover",
        description="Unauthorized account access",
        subtypes=ACCOUNT_TAKEOVER_SUBTYPES,
    ),
}

# All abuse types in a dictionary for easy lookup
ABUSE_TYPES = {
    "fraud": AbuseType(
        label="Fraud",
        description="Scams and deceptive content",
        subtypes=FRAUD_SUBTYPES,
    ),
    "harassment": AbuseType(
        label="Harassment",
        description="Bullying or targeted abuse",
        subtypes=HARASSMENT_SUBTYPES,
    ),
    "hate_speech": AbuseType(
        label="Hate Speech",
        description="Discriminatory or hateful content",
        subtypes=HATE_SPEECH_SUBTYPES,
    ),
    "spam": AbuseType(
        label="Spam",
        description="Unwanted promotional or repetitive content",
    ),
    "misinformation": AbuseType(
        label="Misinformation",
        description="Intentionally false or misleading information",
    ),
    "illegal_content": AbuseType(
        label="Illegal Content",
        description="Content that violates laws or platform terms",
        subtypes=ILLEGAL_CONTENT_SUBTYPES,
    ),
    "other": AbuseType(
        label="Other",
        description="Other reportable content",
    ),
}


# Standard confirmation message for all reports
REPORT_CONFIRMATION_MESSAGE = """Thank you for helping keep our community safe. Our moderation team will review your report and take appropriate action.

To protect yourself from unwanted interactions, you can block the reported user.

If you believe your account security may be compromised, we strongly recommend:
  - Changing your account password
  - Updating your account email
  - Enabling two-factor authentication

We will notify you via private message once we have reviewed your report."""


def add_report_details_to_embed(embed, report, hide_reporter=False, hide_additional_info=False):
    """Add report details to an embed

    Args:
        embed: The discord.Embed to add details to
        report: Report object containing report information
        hide_reporter: If True, don't show who reported the message
        hide_additional_info: If True, don't show additional information
    """
    message = report.reported_message
    reporter = report.interaction.user

    # Add the reported user's profile picture as thumbnail
    embed.set_thumbnail(url=message.author.display_avatar.url if message.author.display_avatar else None)

    # Add report details based on abuse type
    if report.abuse_category and report.abuse_category in ABUSE_TYPES:
        abuse_type = ABUSE_TYPES[report.abuse_category]
        embed.add_field(name="Report Type", value=abuse_type.label)

        # Add all subtypes in the chain
        current_type = abuse_type
        for subtype_key in report.subtypes:
            if current_type.subtypes and subtype_key in current_type.subtypes:
                subtype = current_type.subtypes[subtype_key]
                embed.add_field(name="Subtype", value=subtype.label)
                current_type = subtype
    else:
        # Fallback
        embed.add_field(name="Report Type", value=report.report_type or "Other")

    embed.add_field(name="Message Author", value=message.author.mention, inline=True)
    embed.add_field(name="Channel", value=message.jump_url, inline=True)
    embed.add_field(name="Message Content", value=quote_message(message), inline=False)

    if not hide_reporter:
        embed.add_field(name="Reported by", value=reporter.mention)

    # Add additional information if provided and not hidden
    if not hide_additional_info and report.additional_info:
        embed.add_field(name="Additional Information", value=report.additional_info, inline=False)

    embed.set_footer(text=f"Report ID: {report.id}")
    embed.timestamp = discord.utils.utcnow()

    return embed
