import logging
import math
import textwrap
import typing
from datetime import datetime

import aiohttp
import discord
from discord.ext import commands

from amelia.avwx import AVWX, AvwxResponse
import dateutil.parser

log = logging.getLogger(__name__)

class TAF(AVWX, commands.Cog):

    def __init__(self, bot: commands.Bot):
        super(TAF, self).__init__()
        self.bot = bot

    @commands.command(name='taf')
    async def taf(self, ctx: commands.Context, icao: str):
        await ctx.trigger_typing()
        m = await self.fetch_taf(icao)



def setup(bot: commands.Bot):
    bot.add_cog(TAF(bot))