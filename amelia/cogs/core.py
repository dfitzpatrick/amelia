import asyncio
import inspect
import logging
import textwrap
import typing
from datetime import datetime, timedelta

import discord
from discord.ext import commands

from amelia.mixins.config import ConfigMixin
log = logging.getLogger(__name__)

class Core(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def assign_pax_role(self, member: discord.Member):
        guild: discord.Guild = member.guild
        # only r/flying
        if guild.id != 379051048129789953:
            return


        try:
            pax: discord.Role = discord.utils.get(guild.roles, id=759154599109328907)
            log.debug(pax)
            await member.add_roles(pax)
        except (discord.errors.Forbidden, discord.errors.HTTPException):

            return

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
       await self.assign_pax_role(member)

    @commands.Cog.listener()
    async def on_ready(self):
        guild: discord.Guild = self.bot.get_guild(379051048129789953)
        if not guild:
            return
        pax: discord.Role = discord.utils.get(guild.roles, id=759154599109328907)
        if not guild or not pax:
            log.debug('no guild or role')
            return
        for m in guild.members:
            if len(m.roles) == 1:
                try:
                    await m.add_roles(pax)
                    log.debug(f"Added PAX to {m.display_name}")
                except (discord.errors.Forbidden, discord.errors.HTTPException):
                    continue
        log.debug('done')

def setup(bot: commands.Bot):
    bot.add_cog(Core(bot))