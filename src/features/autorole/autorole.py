from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

import discord
from discord.ext import commands
from src.features.autorole.config import AutoRoleConfig
from .services import convert_schemas_to_role_objects

if TYPE_CHECKING:
    from src.bot import AmeliaBot
    from discord.app_commands.commands import Group
log = logging.getLogger(__name__)


class AutoRole(commands.Cog):

    def __init__(self, bot: AmeliaBot):
        self.bot = bot
        self.config_command: Optional[Group] = None



    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        async with self.bot.db as session:
            schemas = await session.auto_roles.guild_auto_roles(member.guild.id)
            roles = convert_schemas_to_role_objects(member.guild, schemas)
        for role in roles:
            try:
                await member.add_roles(role)
            except discord.Forbidden:
                log.warning(
                    f"No AutoRole Manage Role Permissions or role in higher hierarchy: "
                    f"{member.guild.name}"
                )

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        async with self.bot.db as session:
            await session.auto_roles.remove_auto_role(role.id)
            await session.commit()

    async def cog_load(self) -> None:
        self.config_command = AutoRoleConfig(self.bot)
        self.bot.config_group.add_command(self.config_command)
        
    async def cog_unload(self) -> None:
        if self.config_command is not None:
            self.bot.config_group.remove_command(self.config_command.name)
