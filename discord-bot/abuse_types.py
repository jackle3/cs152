"""
Abuse type definitions for Discord moderation bot.
Focused on fraud and deception detection for public Discord channels.
"""

import discord
from enum import Enum
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class AbuseType:
    """Represents an abuse type with its metadata."""
    label: str
    description: str
    emoji: str
    color: discord.Color = discord.Color.blue()
    subtypes: Optional[Dict[str, 'AbuseType']] = None


class FraudType(Enum):
    """Specific types of fraud common in Discord channels."""
    PHISHING = "phishing"
    CRYPTO_SCAM = "crypto_scam" 
    FAKE_GIVEAWAY = "fake_giveaway"
    ACCOUNT_THEFT = "account_theft"
    IMPERSONATION = "impersonation"
    FAKE_LINKS = "fake_links"


class ModerationSeverity(Enum):
    """Severity levels for moderation actions."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# Simplified fraud subtypes focused on Discord context
FRAUD_SUBTYPES = {
    FraudType.PHISHING.value: AbuseType(
        label="Phishing",
        description="Attempts to steal login credentials or personal information",
        emoji="🎣",
        color=discord.Color.red()
    ),
    FraudType.CRYPTO_SCAM.value: AbuseType(
        label="Crypto Scam",
        description="Fake cryptocurrency investment schemes or wallet draining",
        emoji="💰",
        color=discord.Color.orange()
    ),
    FraudType.FAKE_GIVEAWAY.value: AbuseType(
        label="Fake Giveaway",
        description="Fraudulent giveaways or contests to steal information",
        emoji="🎁",
        color=discord.Color.gold()
    ),
    FraudType.ACCOUNT_THEFT.value: AbuseType(
        label="Account Theft",
        description="Compromised accounts posting malicious content",
        emoji="🔓",
        color=discord.Color.dark_red()
    ),
    FraudType.IMPERSONATION.value: AbuseType(
        label="Impersonation",
        description="Pretending to be someone else (admin, celebrity, etc.)",
        emoji="🎭",
        color=discord.Color.purple()
    ),
    FraudType.FAKE_LINKS.value: AbuseType(
        label="Malicious Links",
        description="Links to fake websites, malware, or scam pages",
        emoji="🔗",
        color=discord.Color.dark_orange()
    ),
}

# Main abuse categories - simplified and Discord-focused
ABUSE_TYPES = {
    "fraud": AbuseType(
        label="Fraud & Scams",
        description="Deceptive content attempting to steal money, information, or accounts",
        emoji="⚠️",
        color=discord.Color.red(),
        subtypes=FRAUD_SUBTYPES
    ),
    "spam": AbuseType(
        label="Spam",
        description="Unwanted promotional or repetitive content",
        emoji="📢",
        color=discord.Color.orange()
    ),
    "harassment": AbuseType(
        label="Harassment",
        description="Bullying, threats, or targeted abuse",
        emoji="🚫",
        color=discord.Color.dark_red()
    ),
    "inappropriate": AbuseType(
        label="Inappropriate Content",
        description="NSFW, hate speech, or other inappropriate content",
        emoji="🔞",
        color=discord.Color.purple()
    ),
    "other": AbuseType(
        label="Other",
        description="Other reportable content not covered above",
        emoji="❓",
        color=discord.Color.greyple()
    ),
}

# Message and user actions
MESSAGE_ACTIONS = {
    "remove": "Remove Message",
    "keep": "Keep Message",
}

USER_ACTIONS = {
    "warn": {
        "label": "Warn User",
        "message": "The user has been warned about their behavior.",
        "color": discord.Color.yellow(),
    },
    "timeout": {
        "label": "Timeout User (24h)",
        "message": "The user has been temporarily suspended from the server for 24 hours.",
        "color": discord.Color.orange(),
    },
    "kick": {
        "label": "Kick User",
        "message": "The user has been removed from the server and will need to rejoin if they wish to return.",
        "color": discord.Color.red(),
    },
    "ban": {
        "label": "Ban User",
        "message": "The user has been permanently banned from the server.",
        "color": discord.Color.red(),
    },
}

SEVERITY_LEVELS = {
    ModerationSeverity.LOW.value: {
        "label": "Low Severity",
        "description": "Minor violation that doesn't significantly impact the community",
        "color": discord.Color.green(),
    },
    ModerationSeverity.MEDIUM.value: {
        "label": "Medium Severity",
        "description": "Moderate violation that affects community members",
        "color": discord.Color.yellow(),
    },
    ModerationSeverity.HIGH.value: {
        "label": "High Severity",
        "description": "Serious violation that significantly impacts the community",
        "color": discord.Color.orange(),
    },
    ModerationSeverity.CRITICAL.value: {
        "label": "Critical Severity",
        "description": "Extreme violation that requires immediate attention",
        "color": discord.Color.red(),
    },
}

# Standard confirmation message for all reports
REPORT_CONFIRMATION_MESSAGE = """Thank you for helping keep our community safe. Our moderation team will review your report and take appropriate action.

To protect yourself from unwanted interactions, you can block the reported user.

If you believe your account security may be compromised, we strongly recommend:
- Changing your account password and email
- Enabling two-factor authentication

We will notify you once we have reviewed your report. Potential outcomes may include:
- No action if no violation is found
- Removal of the reported content
- Warning issued to the user
- Temporary or permanent ban from the server

If you have any questions or concerns, please contact a moderator directly."""

# Moderation summary template
MODERATION_SUMMARY_TEMPLATE = """
**Message Action:** {message_action}
**User Action:** {user_action}
**Severity Level:** {severity_level}

Report ID: {report_id}
Moderator: {moderator}
""" 