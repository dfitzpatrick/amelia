from discord.ext import commands
import discord
from amelia.autorole.cache import AutoRoleCache
from amelia.autorole.config import AutoRoleConfig
from amelia.bot import AmeliaBot
import logging

log = logging.getLogger(__name__)


class AutoRole(commands.Cog):

    def __init__(self, bot: AmeliaBot):
        self.bot = bot
        self.cache = AutoRoleCache(bot)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        try:
            for role in self.cache.item.get(member.guild.id, []):
                await member.add_roles(role)
        except discord.Forbidden:
            log.warning(f"No AutoRole Manage Role Permissions or role in higher hierarchy: {member.guild.name}")

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        await self.bot.pg.remove_auto_role_from_guild(role.id)

    async def cog_load(self) -> None:
        self.bot.config_group.add_command(AutoRoleConfig(self.bot, self.cache))