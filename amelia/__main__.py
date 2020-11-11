import logging
import os
import typing
import discord
from discord.ext import commands

log = logging.getLogger(__name__)

def load_cogs(cogs: typing.Tuple[str]):
    for cog in cogs:
        try:
            bot.load_extension(cog)
            log.info(f"Cog Loaded: {cog}")
        except commands.ExtensionNotLoaded:
            pass

        except Exception as error:
            log.error(f'Could not load COG: {cog}. {error}')
            raise


extensions = (
    'amelia.cogs.metar',
    'amelia.cogs.taf',
    'amelia.cogs.station',
    'amelia.cogs.core',
)

intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(
    command_prefix='!',
    intents=intents
)

load_cogs(extensions)
bot.run(os.environ['AMELIA_TOKEN'])



