from __future__ import annotations

import logging
import typing as t

import discord
from ameliapg import AmeliaPgService, PgActions
from ameliapg.errors import DuplicateEntity
from ameliapg.models import PgNotify
from ameliapg.server.models import GuildDB
from discord.app_commands import Group, Command
from discord.ext import commands

log = logging.getLogger(__name__)


class ConfigGroup(Group):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def add_config_command(self, func, error_coro=None, name=None, desc=None, override: bool = False):
        desc = '...' if desc is None else desc
        cmd = Command(
            name=name if name is not None else func.__name__,
            description=desc,
            callback=func,
            parent=None,
        )
        handler = None
        if error_coro is not None:
            handler = lambda parent, itx, error: error_coro(itx, error)
        cmd.on_error = handler
        self.add_command(cmd, override=override)


class AmeliaBot(commands.Bot):

    def __init__(self, pool, connection, extensions: t.Tuple[str, ...] = (), **kwargs):
        super(AmeliaBot, self).__init__(**kwargs)
        self.servers: t.Dict[int, GuildDB] = {}
        self.pg: AmeliaPgService = AmeliaPgService(pool, connection, loop=self.loop)
        self._extensions = extensions
        self._first_run = True
        self.config_group = ConfigGroup(name='config', description='Amelia Configuration settings')

    async def add_cog(self, *args, **kwargs) -> None:
        log.info(f"Cog Added: {args[0]}")
        await super(AmeliaBot, self).add_cog(*args, **kwargs)

    async def setup_hook(self) -> None:
        for ext in self._extensions:
            await self._load_extension(ext)




    async def _load_extension(self, name):
        try:
            await self.load_extension(name)
            log.debug(f"Extension Loaded: {name}")
        except commands.ExtensionNotLoaded:
            pass
        except Exception as error:
            log.error(f"Extension {name} failed to load. {error}")
            raise

    async def delete_message_if_configured(self, message):
        guild = message.guild
        guild_id = guild.id
        cfg = self.servers.get(guild_id)

        if isinstance(cfg, GuildDB) and cfg.auto_delete_commands:
            try:
                await message.delete(delay=5)
            except (discord.errors.NotFound, discord.errors.Forbidden, discord.errors.HTTPException):
                log.error(f"Could not auto-delete command in guild: {guild.name} / {guild.id}")

    async def hook_command_completion(self, ctx:commands.Context):
        try:
            await ctx.message.add_reaction(u"\u2705")
        except (discord.errors.NotFound, discord.errors.Forbidden, discord.errors.HTTPException):
            pass
        finally:
            await self.delete_message_if_configured(ctx.message)

    async def hook_command_error(self, ctx: commands.Context, error: commands.CommandError):
        try:
            await ctx.message.add_reaction(u"\u274C")
        except (discord.errors.NotFound, discord.errors.Forbidden, discord.errors.HTTPException):
            pass
        finally:
            await self.delete_message_if_configured(ctx.message)
            raise error

    async def on_ready(self):
        if self._first_run:
            self.tree.add_command(self.config_group)
            await self.pg.start_listening()
            self.servers = await self._populate_server_config()
            await self.sync_servers()
            self._first_run = False

    async def on_guild_join(self, guild: discord.Guild):
        guild_db = None
        try:
            guild_db = await self.pg.new_guild_config(guild.id)
            self.servers[guild.id] = guild_db
        except DuplicateEntity:
            guild_db = await self.pg.get_guild_config(guild.id)
            log.debug(f"Rejoined Guild: {guild.name} with existing configuration in use.")
        finally:
            self.dispatch('new_guild_config', guild_db)

    async def on_guild_remove(self, guild: discord.Guild):
        # We are purposely not removing configs here in case of rejoining.
        pass


    async def _populate_server_config(self) -> t.Dict[int, GuildDB]:
        servers = await self.pg.get_servers()
        result = {s.guild_id:s for s in servers}
        log.debug(f"Server config shows {len(result)} Servers")
        return result

    async def map_guild_configs(self, fetch_method: t.Callable) -> t.Dict[int, t.Any]:
        objs = await fetch_method()
        container = {o.guild_id: o for o in objs}
        return container

    async def sync_configs(self, dict: t.Dict[int, t.Any], method: t.Callable):
        for guild in self.guilds:
            if guild.id not in dict.keys():
                try:
                    await method(guild.id)
                except DuplicateEntity:
                    pass

    async def sync_servers(self):
        for guild in self.guilds:
            if guild.id not in self.servers.keys():
                log.debug(f"Server not synced in Database. Syncing {guild.id}")
                await self.pg.new_guild_config(guild.id)


    async def \
            notify_t(self, t: t.Type, container: t.Dict[int, t.Any], payload: PgNotify):
        entity = payload.entity

        if isinstance(entity, t):
            if payload.action == PgActions.DELETE and entity.guild_id in self.servers.keys():
                del container[entity.id]
            else:
                container[entity.guild_id] = entity

    async def _notify(self, payload: PgNotify):
        entity = payload.entity
        if isinstance(entity, GuildDB):
            if payload.action == PgActions.DELETE and entity.guild_id in self.servers.keys():
                del self.servers[entity.id]
            else:
                self.servers[entity.guild_id] = entity