import logging

import discord
from discord.ext import commands

from amelia import AmeliaBot

log = logging.getLogger(__name__)

class Core(commands.Cog):

    def __init__(self, bot: AmeliaBot):
        self.bot = bot


def setup(bot: AmeliaBot):
    bot.add_cog(Core(bot))