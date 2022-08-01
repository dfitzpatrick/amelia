from typing import Optional, TYPE_CHECKING

import discord
from ameliapg.metar.models import MetarDB, MetarChannelDB
from ameliapg.taf.models import TafDB, TafChannelDB
from discord import TextChannel
if TYPE_CHECKING:
    from amelia.bot import AmeliaBot

from amelia.cache import DiscordEntityCache, DiscordEntityManyCache


class TafConfigCache(DiscordEntityCache[TafDB]):
    pass


class TafChannelCache(DiscordEntityManyCache[TextChannel]):
    pass


class MetarConfigCache(DiscordEntityCache[MetarDB]):
    pass


class MetarChannelCache(DiscordEntityManyCache[TextChannel]):
    pass


class MetarCache:

    def __init__(self, bot: 'AmeliaBot'):
        super(MetarCache, self).__init__()
        self.bot = bot
        self.config = MetarConfigCache(lambda e: e, self.bot.pg.fetch_metar_configs, MetarDB)
        self.channels = MetarChannelCache(self._convert_to_channel, self.bot.pg.fetch_all_metar_channels,
                                          MetarChannelDB)
        self.bot.pg.register_listener(self.config.notify)
        self.bot.pg.register_listener(self.channels.notify)
        self.bot.loop.create_task(self.config.populate_cache())
        self.bot.loop.create_task(self.channels.populate_cache())

    async def _convert_to_channel(self, entity: MetarChannelDB) -> Optional[discord.TextChannel]:
        await self.bot.wait_until_ready()
        guild = self.bot.get_guild(entity.guild_id)
        if guild is not None:
            return guild.get_channel(entity.channel_id)


class TafCache:

    def __init__(self, bot: 'AmeliaBot'):
        super().__init__()
        self.bot = bot
        self.config = TafConfigCache(lambda e: e, self.bot.pg.fetch_taf_configs, TafDB)
        self.channels = MetarChannelCache(self._convert_to_channel, self.bot.pg.fetch_all_taf_channels,
                                          TafChannelDB)
        self.bot.pg.register_listener(self.config.notify)
        self.bot.pg.register_listener(self.channels.notify)
        self.bot.loop.create_task(self.config.populate_cache())
        self.bot.loop.create_task(self.channels.populate_cache())

    async def _convert_to_channel(self, entity: MetarChannelDB) -> Optional[discord.TextChannel]:
        await self.bot.wait_until_ready()
        guild = self.bot.get_guild(entity.guild_id)
        if guild is not None:
            return guild.get_channel(entity.channel_id)