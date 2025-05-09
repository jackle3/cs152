"""
Not actually part of the bot
A script to clean up the bot's messages and threads in the servers its in
"""
import discord
import asyncio
import json
import os
import logging
from discord.ext import commands

# Set up logging
logger = logging.getLogger("discord")
logger.setLevel(logging.INFO)
handler = logging.FileHandler(filename="delete_log.log", encoding="utf-8", mode="w")
handler.setFormatter(logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s"))
logger.addHandler(handler)


async def delete_bot_messages(bot, channel_id):
    """Delete all messages sent by the bot in the specified channel"""
    try:
        channel = bot.get_channel(channel_id)
        if not channel:
            logger.error(f"Channel with ID {channel_id} not found")
            return False

        logger.info(f"Starting to delete bot messages in channel: {channel.name}")

        # Keep track of deleted messages
        deleted_count = 0

        # Fetch message history in batches
        async for message in channel.history(limit=None):
            # Check if message was sent by the bot
            if message.author.id == bot.user.id:
                try:
                    await message.delete()
                    deleted_count += 1
                    logger.info(f"Deleted message with ID: {message.id}")
                    # Add a small delay to avoid rate limiting
                    await asyncio.sleep(0.5)
                except discord.errors.NotFound:
                    logger.warning(f"Message {message.id} already deleted")
                except discord.errors.Forbidden:
                    logger.error(f"No permission to delete message {message.id}")
                except Exception as e:
                    logger.error(f"Error deleting message {message.id}: {str(e)}")

        logger.info(f"Finished deleting bot messages. Total deleted: {deleted_count}")
        return True

    except Exception as e:
        logger.error(f"Error in delete_bot_messages: {str(e)}")
        return False


async def delete_bot_threads(bot, guild):
    """Delete all threads created by the bot in the guild"""
    try:
        deleted_count = 0

        # Check all text channels for threads
        for channel in guild.text_channels:
            # Get all threads in the channel
            try:
                threads = await channel.archived_threads().flatten()
                active_threads = channel.threads

                # Combine active and archived threads
                all_threads = threads + active_threads

                for thread in all_threads:
                    # Check if thread was created by the bot
                    if thread.owner_id == bot.user.id:
                        try:
                            await thread.delete()
                            deleted_count += 1
                            logger.info(f"Deleted thread: {thread.name} (ID: {thread.id})")
                            await asyncio.sleep(0.5)  # Avoid rate limiting
                        except discord.errors.NotFound:
                            logger.warning(f"Thread {thread.id} already deleted")
                        except discord.errors.Forbidden:
                            logger.error(f"No permission to delete thread {thread.id}")
                        except Exception as e:
                            logger.error(f"Error deleting thread {thread.id}: {str(e)}")
            except Exception as e:
                logger.error(f"Error accessing threads in channel {channel.name}: {str(e)}")

        logger.info(f"Finished deleting bot threads. Total deleted: {deleted_count}")
        return True

    except Exception as e:
        logger.error(f"Error in delete_bot_threads: {str(e)}")
        return False


async def main():
    # Load token from tokens.json
    token_path = "tokens.json"
    if not os.path.isfile(token_path):
        print(f"{token_path} not found!")
        return

    with open(token_path) as f:
        tokens = json.load(f)
        discord_token = tokens["discord"]

    # Set up bot with minimal permissions needed
    intents = discord.Intents.default()
    intents.message_content = True
    bot = commands.Bot(command_prefix="!", intents=intents)

    @bot.event
    async def on_ready():
        print(f"{bot.user.name} has connected to Discord!")

        # Get the group number from the bot's name
        import re

        match = re.search(r"[gG]roup (\d+) [bB]ot", bot.user.name)
        if not match:
            print("Group number not found in bot's name. Format should be 'Group # Bot'")
            await bot.close()
            return

        group_num = match.group(1)

        # Process each guild
        for guild in bot.guilds:
            print(f"Processing guild: {guild.name}")

            # Delete bot threads first
            print(f"Deleting bot threads in {guild.name}...")
            await delete_bot_threads(bot, guild)

            # Define the channels to clean
            channels_to_clean = [f"group-{group_num}", f"group-{group_num}-mod"]

            # Find and clean each specified channel
            for channel_name in channels_to_clean:
                channel = discord.utils.get(guild.text_channels, name=channel_name)

                if channel:
                    print(f"Found channel in {guild.name}: {channel.name}")
                    success = await delete_bot_messages(bot, channel.id)
                    if success:
                        print(f"Successfully deleted bot messages in {channel.name}")
                    else:
                        print(f"Failed to delete bot messages in {channel.name}")
                else:
                    print(f"Channel {channel_name} not found in {guild.name}")

        # Close the bot connection after completing the task
        await bot.close()

    try:
        await bot.start(discord_token)
    except Exception as e:
        print(f"Error starting bot: {e}")


if __name__ == "__main__":
    asyncio.run(main())
