import asyncio
import logging
import os
import typing
import asyncpg
import discord
from ameliapg import AmeliaPgService

from discord.ext import commands

from amelia import AmeliaBot

log = logging.getLogger(__name__)


extensions = (
   'amelia.cogs.metar',
    'amelia.cogs.taf',
    'amelia.cogs.station',
    'amelia.cogs.core',
    'amelia.cogs.autorole',
)


def bot_task_callback(future: asyncio.Future):
    raise future.exception()


async def run_bot():
    dsn = os.environ['DSN']
    token = os.environ['AMELIA_TOKEN']
    conn = await asyncpg.connect(dsn)
    pool = await asyncpg.create_pool(dsn)
    intents = discord.Intents.default()
    intents.members = True
    bot = AmeliaBot(pool, conn, intents=intents, command_prefix='!', extensions=extensions)

    try:
        await bot.start(token)
    finally:
        await bot.close()



loop =asyncio.get_event_loop()
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





