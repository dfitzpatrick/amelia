from __future__ import annotations
import typing as t
from discord.ext import commands
from ameliapg.constants import PgActions
from ameliapg.autorole.models import AutoRoleDB
import discord
import logging
import asyncio
log = logging.getLogger(__name__)

if t.TYPE_CHECKING:
    from amelia.__main__ import AmeliaBot

    from ameliapg.models import PgNotify


class AutoRoleCog(commands.Cog):

    def __init__(self, bot: AmeliaBot):
        super(AutoRoleCog, self).__init__()
        self.bot = bot
        self.auto_roles: t.Dict[int, t.Dict[int, discord.Role]] = {}

    @commands.Cog.listener()
    async def on_safe_to_sync(self):
        auto_roles = await self.bot.pg.fetch_all_auto_roles()
        await self._load_to_cache(auto_roles)

        self.bot.pg.register_listener(self._notify)

    async def _load_to_cache(self, auto_roles: t.List[AutoRoleDB]):
        for auto_role in auto_roles:
            guild = self.bot.get_guild(auto_role.guild_id)
            if guild is None:
                # We don't clean up the role here in case the bot later rejoins.
                continue
            role = discord.utils.get(guild.roles, id=auto_role.role_id)
            if role is None:
                # Here we will delete since they deleted the role
                await self.bot.pg.remove_auto_role_from_guild(auto_role.role_id)
                continue
            self.add_to_cache(role)
        log.debug("AutoRoles loaded to cache.")


    async def on_command_completion(self):
        self.bot.dispatch()

    def add_to_cache(self, role: discord.Role):
        guild_id = role.guild.id
        guild_roles = self.auto_roles.get(guild_id)
        if guild_roles is None:
            self.auto_roles[guild_id] = {}
        self.auto_roles[guild_id][role.id] = role


    def remove_from_cache(self, role: discord.Role):
        if self.role_in_cache(role):
            del self.auto_roles[role.guild.id][role.id]

    async def _notify(self, payload: PgNotify):
        e = payload.entity
        if not isinstance(e, AutoRoleDB):
            return
        guild = self.bot.get_guild(e.guild_id)
        role = discord.utils.get(guild.roles, id=e.role_id)
        if role is None:
            return
        log.debug(f"{payload.action}={PgActions.DELETE}")
        if payload.action == PgActions.DELETE:

            self.remove_from_cache(role)
        else:
            self.add_to_cache(role)


    def role_in_cache(self, role: discord.Role):
        return role.id in self.auto_roles.get(role.guild.id, {}).keys()

    def cached_guild_roles(self, guild_id) -> t.List[discord.Role]:
        guild_roles = self.auto_roles.get(guild_id, {})
        return list(guild_roles.values())


    @commands.Cog.listener()
    async def on_testing_dispatch(self, message: str):
        log.debug(f'in listener cog: {message}')

    @commands.bot_has_permissions(manage_roles=True)
    @commands.has_permissions(manage_roles=True)
    @commands.group('autorole', invoke_without_command=True)
    async def auto_role_cmd(self, ctx: commands.Context, role: discord.Role = None):
        if role is None:
            description = "\n".join(r.name for r in self.cached_guild_roles(ctx.guild.id))
            embed = discord.Embed(title="Current AutoRoles", description=description)
            await ctx.send(embed=embed, delete_after=20)
            return

        name = role.name
        key = ctx.guild.id
        in_cache = self.role_in_cache(role)
        if not self.role_in_cache(role):
            log.debug('adding')
            await self.bot.pg.add_auto_role_to_guild(key, role.id)
            await ctx.send(f"Added {name} to AutoRole", delete_after=5)

        else:
            await self.bot.pg.remove_auto_role_from_guild(role.id)
            await ctx.send(f"Removed {name} from AutoRole", delete_after=5)

    @auto_role_cmd.command(name='sync')
    async def autorole_sync(self, ctx: commands.Context):
        """
        Syncs any added autoroles with members. This is explicit in case an
        autorole was added accidently.


        Parameters
        ----------
        ctx

        Returns
        -------

        """
        await ctx.trigger_typing()
        await ctx.send("Syncing Newly Added AutoRoles to members. This may take awhile... Note: Roles that are removed are not automatically removed from members", delete_after=10)
        roles = self.cached_guild_roles(ctx.guild.id)
        for m in ctx.guild.members:
            m: discord.Member
            for r in roles:
                if r not in m.roles:
                    await m.add_roles(r)


    @auto_role_cmd.error
    async def auto_role_cmd_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.BotMissingPermissions):
            s = "Bot is missing permissions to manage roles. Command ignored"
            await ctx.send(s, delete_after=5)

        if isinstance(error, commands.MissingPermissions):
            await ctx.author.send("You do not have the required permissions.")


    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        try:
            for role in self.cached_guild_roles(member.guild.id):
                await member.add_roles(role)
        except discord.Forbidden:
            log.warning(f"No AutoRole Manage Role Permissions or role in higher hierarchy: {member.guild.name}")


    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        await self.bot.pg.remove_auto_role_from_guild(role.id)

    @commands.Cog.listener()
    async def on_command_completion(self, ctx: commands.Context):
        """
        Simple Housekeeping function. Annotates the command with feedback that
        it completed correctly, and if permissioned for, will remove the command.

        Parameters
        ----------
        ctx: The discord Context

        Returns
        -------
        :class: None
        """
        if ctx.cog != self:
            return
        await self.bot.hook_command_completion(ctx)

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        """
            Simple Housekeeping function. Annotates the command with feedback that
            it failed, and if permissioned for, will remove the command.

            Parameters
            ----------
            ctx: The discord Context
            error: The CommandError that was raised.

            Returns
            -------
            :class: None
        """
        if ctx.cog != self:
            return
        await self.bot.hook_command_error(ctx, error)



def setup(bot: AmeliaBot):
    bot.add_cog(AutoRoleCog(bot))