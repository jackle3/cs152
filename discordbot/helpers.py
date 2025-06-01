"""
Utility functions for the Discord moderation bot.
"""

import discord


def quote_message(message):
    """Truncate a message and place it inside a block quote."""
    message_content = message.content if message.content else "[No text content]"
    if len(message_content) > 1024:
        message_content = message_content[:1021] + "..."
    message_content = f">>> {message_content}"
    return message_content


def add_report_details_to_embed(embed, report):
    """Add report details to an embed.

    Args:
        embed: The discord.Embed to add details to
        report: Report object containing report information
    """
    from abuse_types import ABUSE_TYPES

    message = report.reported_message

    # Add the reported user's profile picture as thumbnail
    embed.set_thumbnail(url=message.author.display_avatar.url if message.author.display_avatar else None)

    # Add report details based on abuse type
    if report.abuse_category and report.abuse_category in ABUSE_TYPES:
        abuse_type = ABUSE_TYPES[report.abuse_category]

        # Add emoji to make it more visually appealing
        report_type_text = f"{abuse_type.emoji} {abuse_type.label}"
        embed.add_field(name="Report Type", value=report_type_text)

        # Add subtypes if they exist
        if abuse_type.subtypes and report.subtypes:
            current_type = abuse_type
            for subtype_key in report.subtypes:
                if current_type.subtypes and subtype_key in current_type.subtypes:
                    subtype = current_type.subtypes[subtype_key]
                    subtype_text = f"{subtype.emoji} {subtype.label}"
                    embed.add_field(name="Specific Type", value=subtype_text)
                    current_type = subtype
    else:
        # Fallback
        embed.add_field(name="Report Type", value=report.report_type or "Other")

    embed.add_field(name="Message Author", value=message.author.mention, inline=True)
    embed.add_field(name="Channel", value=message.jump_url, inline=True)
    embed.add_field(name="Message Content", value=quote_message(message), inline=False)

    embed.set_footer(text=f"Report ID: {report.id}")
    embed.timestamp = discord.utils.utcnow()

    return embed


def create_progress_embed(title, description, color=discord.Color.blue()):
    """Create a standardized embed for showing progress through the report flow.

    Args:
        title: Embed title
        description: Embed description
        color: Embed color

    Returns:
        discord.Embed with progress information
    """
    embed = discord.Embed(title=title, description=description, color=color)

    return embed
