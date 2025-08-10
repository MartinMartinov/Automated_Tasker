import discord
from discord.ext import commands
import asyncio


class DiscordBot(commands.Cog):
    def __init__(self, bot_token: str):
        intents = discord.Intents.all()
        intents.messages = True
        intents.guilds = True
        intents.message_content = True
        self.bot = commands.Bot(command_prefix="!", intents=intents)
        self.bot_token = bot_token
        self._ready_event = asyncio.Event()

        # Add event handlers
        @self.bot.event
        async def on_ready():
            self._ready_event.set()

    async def post_message(self, guild_name: str, channel_name: str, message: str):
        """
        Posts a message to a specific channel by name in a given guild.

        Args:
            guild_name (str): The name of the server (guild).
            channel_name (str): The name of the channel.
            message (str): The message to post.

        Returns:
            None
        """
        await self._ready_event.wait()
        for guild in self.bot.guilds:
            if guild.name == guild_name:
                for channel in guild.text_channels:
                    if channel.name == channel_name:
                        await channel.send(message)

    async def get_most_recent_message(self, guild_name: str, channel_name: str) -> str | None:
        """
        Retrieves the most recent message in a specific channel by name in a given guild.

        Args:
            guild_name: The name of the server (guild).
            channel_name: The name of the channel.

        Returns:
            discord.Message or None: The most recent message if found, otherwise None.
        """
        await self._ready_event.wait()
        for guild in self.bot.guilds:
            if guild.name == guild_name:
                for channel in guild.text_channels:
                    if channel.name == channel_name:
                        try:
                            return (await anext(channel.history(limit=1))).content
                        except discord.Forbidden:
                            return None
        return None

    async def start_bot(self):
        await self.bot.start(self.bot_token)

    async def close_bot(self):
        await self.bot.close()

    async def __aenter__(self):
        asyncio.create_task(self.start_bot())
        await self._ready_event.wait()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close_bot()
