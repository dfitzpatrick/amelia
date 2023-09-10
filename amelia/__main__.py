import asyncio
import logging
import os

import discord

from amelia.bot import AmeliaBot
from amelia.instances import db
from amelia.uow import UOW

log = logging.getLogger(__name__)
_dsn = os.environ['DSN']
_token = os.environ['AMELIA_TOKEN']

def bot_task_callback(future: asyncio.Future):
    if future.exception():
        raise future.exception()

async def bootstrap():
    log.info(f"Discord Version: {discord.__version__}")
    #db.uow_cls = UOW
    db.migrate()
    await db.start_listening()
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True

    activity = discord.Activity(
        type=discord.ActivityType.watching,
        status=discord.Status.idle,
        name=" the weather. /help for commands"
    )
    bot = AmeliaBot(
        db_service=db,
        intents=intents,
        command_prefix='!',
        slash_commands=True,
        activity=activity
    )
    try:
        await bot.start(_token)
    except RuntimeError:
        pass
    finally:
        await bot.close()

loop = asyncio.new_event_loop()

try:
    future = asyncio.ensure_future(
        bootstrap(),
        loop=loop
    )
    future.add_done_callback(bot_task_callback)
    loop.run_forever()
except KeyboardInterrupt:
    pass
finally:
    loop.close()


