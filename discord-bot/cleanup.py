import re
import discord
from discord.ext import commands
import os
import json
import asyncio

class CleanupBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.reactions = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)
        
        self.group_num = None

    async def setup_hook(self):
        # Parse the group number out of the bot's name
        match = re.search(r"[gG]roup (\d+) [bB]ot", self.user.name)
        if match:
            self.group_num = match.group(1)
        else:
            raise Exception('Group number not found in bot\'s name. Name format should be "Group # Bot".')

    async def cleanup_messages(self):
        """Delete all bot messages in group channels"""
        for guild in self.guilds:
            # Find all channels that start with 'group-'
            for channel in guild.text_channels:
                if channel.name.startswith('group-18'):
                    try:
                        # Get all messages in the channel
                        async for message in channel.history(limit=None):
                            # Delete if message is from this bot
                            if message.author == self.user:
                                await message.delete()
                                print(f"Deleted message in {channel.name}")
                                # Add a small delay to avoid rate limits
                                await asyncio.sleep(0.5)
                    except Exception as e:
                        print(f"Error cleaning up {channel.name}: {str(e)}")

async def main():
    # Load token from tokens.json
    token_path = "tokens.json"
    if not os.path.isfile(token_path):
        raise Exception(f"{token_path} not found!")
    with open(token_path) as f:
        tokens = json.load(f)
        discord_token = tokens["discord"]

    # Create and run the bot
    bot = CleanupBot()
    
    @bot.event
    async def on_ready():
        print(f"{bot.user.name} has connected to Discord!")
        # Run cleanup
        await bot.cleanup_messages()
        # Disconnect after cleanup
        await bot.close()

    await bot.start(discord_token)

if __name__ == "__main__":
    asyncio.run(main())
