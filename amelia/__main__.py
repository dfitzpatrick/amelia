import asyncio
import logging
import os

import asyncpg
import discord

from amelia.bot import AmeliaBot

log = logging.getLogger(__name__)


extensions = (
    'amelia.weather',
    'amelia.autorole',
    'amelia.cogs.core',
    'amelia.cogs.facility',
)


def bot_task_callback(future: asyncio.Future):
    if future.exception():
        raise future.exception()


def get_guild_prefix(bot: AmeliaBot, message: discord.Message):
    default = '!'
    server = bot.servers.get(message.guild.id)
    if server is None:
        return default

    return server.delimiter


async def run_bot():
    dsn = os.environ['DSN']
    token = os.environ['AMELIA_TOKEN']
    conn = await asyncpg.connect(dsn)
    pool = await asyncpg.create_pool(dsn)
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True

    activity = discord.Activity(
        type=discord.ActivityType.watching,
        status=discord.Status.idle,
        name=" the weather. /help for commands"
    )

    bot = AmeliaBot(
        pool,
        conn,
        intents=intents,
        command_prefix='!',
        extensions=extensions,
        slash_commands=True,
        activity=activity
    )
    try:
        await bot.start(token)
    finally:
        await bot.close()

loop = asyncio.new_event_loop()
try:
    future = asyncio.ensure_future(
        run_bot(),
        loop=loop
    )
    future.add_done_callback(bot_task_callback)
    loop.run_forever()
except KeyboardInterrupt:
    pass
finally:
    loop.close()





