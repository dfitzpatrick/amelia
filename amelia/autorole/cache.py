from typing import Optional

import discord
from ameliapg.autorole.models import AutoRoleDB

from amelia.bot import AmeliaBot
from amelia.cache import DiscordEntityManyCache


class AutoRoleCache(DiscordEntityManyCache[discord.Role]):

    def __init__(self, bot:  AmeliaBot):
        self.bot = bot
        super().__init__(self._convert_to_role, bot.pg.fetch_all_auto_roles, event_type=AutoRoleDB)

        self.bot.pg.register_listener(self.notify)
        self.bot.loop.create_task(self.populate_cache())


    async def _convert_to_role(self, entity: AutoRoleDB) -> Optional[discord.Role]:
        await self.bot.wait_until_ready()
        guild = self.bot.get_guild(entity.guild_id)
        if guild is None:
            return
        return guild.get_role(entity.role_id)





