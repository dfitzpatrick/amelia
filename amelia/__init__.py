from __future__ import annotations

import logging
import os
import sys
import typing as t
from logging import StreamHandler, FileHandler

import discord
from ameliapg import AmeliaPgService
from ameliapg.constants import PgActions
from ameliapg.errors import DuplicateEntity
from discord.ext import commands
from ameliapg.server.models import GuildDB
if t.TYPE_CHECKING:

    from ameliapg.models import PgNotify

import sentry_sdk
sentry_sdk.init(
    os.environ['SENTRY_INGEST'],

    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for performance monitoring.
    # We recommend adjusting this value in production.
    traces_sample_rate=1.0
)

BASE_DIR = os.path.normpath(os.path.dirname(os.path.realpath(__file__)))

handler_console = StreamHandler(stream=sys.stdout)
handler_filestream = FileHandler(filename=f"{BASE_DIR}/bot.log", encoding='utf-8')
handler_filestream.setLevel(logging.INFO)
handler_console.setLevel(logging.DEBUG)


logging_handlers = [
        handler_console,
        handler_filestream
    ]

logging.basicConfig(
    format="%(asctime)s | %(name)25s | %(funcName)25s | %(levelname)6s | %(message)s",
    datefmt="%b %d %H:%M:%S",
    level=logging.DEBUG,
    handlers=logging_handlers
)
logging.getLogger('asyncio').setLevel(logging.ERROR)
logging.getLogger('discord').setLevel(logging.ERROR)
logging.getLogger('websockets').setLevel(logging.ERROR)
log = logging.getLogger(__name__)


class AmeliaBot(commands.Bot):

    def __init__(self, pool, connection, **kwargs):
        super(AmeliaBot, self).__init__(slash_command_guilds=[734183623707721874], **kwargs)
        self.servers: t.Dict[int, GuildDB] = {}
        self.pg: AmeliaPgService = AmeliaPgService(pool, connection, loop=self.loop)
        for ext in kwargs.get('extensions', ()):
            self._load_extension(ext)


    def _load_extension(self, name):
        try:
            self.load_extension(name)
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
        await self.pg.start_listening()
        self.servers = await self._populate_server_config()
        await self.sync_servers()
        self.dispatch("safe_to_sync")

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


    async def notify_t(self, t: t.Type, container: t.Dict[int, t.Any], payload: PgNotify):
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
