"""
GWT - Galactic War Terminal Discord Bot
Entry point: python bot.py
"""
import asyncio
import discord
from discord.ext import commands

from config import TOKEN, ensure_data_dirs
from cogs import ALL_COGS

ensure_data_dirs()

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix="$", intents=intents)


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')


async def load_cogs():
    for cog in ALL_COGS:
        await bot.add_cog(cog(bot))


async def main():
    await load_cogs()
    await bot.start(TOKEN)


if __name__ == '__main__':
    asyncio.run(main())
