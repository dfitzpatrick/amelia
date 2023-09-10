from __future__ import annotations

from asyncio import iscoroutinefunction
from functools import wraps
from typing import Optional, Dict, TYPE_CHECKING, List, Set, Any

import discord

from amelia.cache import DiscordEntityManyCache, LRUCache
from amelia.features.autorole.schema import AutoRoleSchema
import logging

if TYPE_CHECKING:
    from amelia.bot import AmeliaBot, log

log = logging.getLogger(__name__)
class AutoRoleCacheAdapter(LRUCache[AutoRoleSchema]):
    def __init__(self, item_identifier_field: str, max_size: int=128):
        super().__init__(max_size=max_size)
        self.object_map: Dict[int, set] = {}
        self._field_name = item_identifier_field
    def post_function_cache(self, key: int, item: AutoRoleSchema | list[AutoRoleSchema]):
        if item.id not in self.object_map.keys():
            self.object_map[item.id] = set()
        self.object_map[item.id] += {key}









class AutoRoleCache(DiscordEntityManyCache[discord.Role]):

    def __init__(self, bot:  AmeliaBot):
        self.bot = bot
        super().__init__(self._convert_to_role, self._fetch_auto_roles, event_type=AutoRoleSchema)

        self.bot.pg.register_listener('autorole', self.notify)
        self.bot.loop.create_task(self.populate_cache())


    async def _convert_to_role(self, entity: AutoRoleSchema) -> Optional[discord.Role]:
        await self.bot.wait_until_ready()
        guild = self.bot.get_guild(entity.guild_id)
        if guild is None:
            return
        return guild.get_role(entity.role_id)

    async def _fetch_auto_roles(self):
        async with self.bot.db as session:
            results = await session.auto_roles.all_auto_roles()
            return results





