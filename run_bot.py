import logging
from amelia.bot import AmeliaBot
import discord
import os
import asyncio
import dotenv
from discord.ext import commands

import discord.ext
dotenv.load_dotenv()

log = logging.getLogger(__name__)

_token = os.environ['BOT_TOKEN']


def bot_task_callback(future: asyncio.Future):
    exc = future.exception()
    if exc is not None:
        raise exc

async def bootstrap():
    from amelia.instances import db
    log.info(f"Discord Version: {discord.__version__}")
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
        command_prefix=commands.when_mentioned,
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
    future = loop.create_task(
        bootstrap(),
    )
    future.add_done_callback(bot_task_callback)
    loop.run_forever()
except KeyboardInterrupt:
    pass
finally:
    loop.close()