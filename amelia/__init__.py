from __future__ import annotations
import logging
import os
import sys
from logging import StreamHandler, FileHandler
from discord.ext import commands
from ameliapg import AmeliaPgService
from ameliapg.constants import PgActions
import discord
from ameliapg.server.models import GuildConfig
import asyncio

import typing as t
if t.TYPE_CHECKING:

    from ameliapg.models import PgNotify


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
        super(AmeliaBot, self).__init__(**kwargs)
        self.servers: t.Dict[int, GuildConfig] = {}
        self.pg: AmeliaPgService = AmeliaPgService(pool, connection, loop=self.loop)
        intents = discord.Intents.default()
        intents.members = True

        for ext in kwargs.get('extensions', ()):
            self._load_extension(ext)


    async def get_prefix(self, message: discord.Message):
        default = '!'
        server = self.servers.get(message.guild.id)
        if server is None:
            return default
        return server.delimiter

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
        if isinstance(cfg, GuildConfig) and cfg.auto_delete_commands:
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



    async def post_dispatch(self, event, *args, **kwargs):
        if event == "testing_dispatch" or event == "command_completion":
            log.debug(f"in post dispatch: {event}")

    async def on_ready(self):
        await self.pg.start_listening()
        self.servers = await self._populate_server_config()
        await self.sync_servers()

    async def on_guild_join(self, guild: discord.Guild):
        await self.pg.new_guild_config(guild.id)

    async def on_guild_remove(self, guild: discord.Guild):
        # We are purposely not removing configs here in case of rejoining.
        pass


    async def _populate_server_config(self) -> t.Dict[int, GuildConfig]:
        servers = await self.pg.get_servers()
        result = {s.guild_id:s for s in servers}
        log.debug(f"Server config shows {len(result)} Servers")
        return result

    async def sync_servers(self):
        for guild in self.guilds:
            if guild.id not in self.servers.keys():
                log.debug(f"Server not synced in Database. Syncing {guild.id}")
                await self.pg.new_guild_config(guild.id)

    async def _notify(self, payload: PgNotify):
        entity = payload.entity
        if isinstance(entity, GuildConfig):
            if payload.action == PgActions.DELETE and entity.guild_id in self.servers.keys():
                del self.servers[entity.id]
            else:
                self.servers[entity.guild_id] = entity
