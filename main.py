import sys

import discord
from discord.ext import commands

from services import env
from services.save import Config

bot = commands.Bot([], intents=discord.Intents.default())

discord.utils.setup_logging()


@bot.event
async def setup_hook():
    Config.load()

    await bot.load_extension("cogs.set")
    await bot.load_extension("cogs.wolf")
    await bot.tree.sync()


async def main():
    await bot.start(env.get("discord"))


if __name__ == "__main__":
    if sys.platform in ("win32", "cygwin", "cli"):
        from winloop import run
    else:
        # if we're on apple or linux do this instead
        from uvloop import run

    run(main())
