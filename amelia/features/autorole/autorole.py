from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from amelia.features.autorole.cache import AutoRoleCacheAdapter
from amelia.features.autorole.config import AutoRoleConfig
from amelia.features.autorole.data import cache
if TYPE_CHECKING:
    from amelia.bot import AmeliaBot

log = logging.getLogger(__name__)


class AutoRole(commands.Cog):

    def __init__(self, bot: AmeliaBot):
        self.bot = bot
        self.cache = cache

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        try:
            for role in self.cache.item.get(member.guild.id, []):
                await member.add_roles(role)
        except discord.Forbidden:
            log.warning(f"No AutoRole Manage Role Permissions or role in higher hierarchy: {member.guild.name}")

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        async with self.bot.db as session:
            await session.auto_roles.remove_auto_role(role.id)
            await session.commit()


    async def cog_load(self) -> None:
        self.bot.config_group.add_command(AutoRoleConfig(self.bot, self.cache))