from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import discord
from discord.ext import commands
from typing import TYPE_CHECKING, Dict, Optional
from discord.ext import tasks

from amelia.concepts.guild.data import GuildSchema, GuildDataContext
import logging

if TYPE_CHECKING:
    from amelia.bot import AmeliaBot

log = logging.getLogger(__name__)
class GuildFeatures(commands.Cog):

    def __init__(self, bot: AmeliaBot):
        self.bot = bot

    async def cog_load(self) -> None:
        log.info("Starting task to update guild member counts")
        self.update_member_counts_task.start()

    async def cog_unload(self) -> None:
        self.update_member_counts_task.cancel()

    async def member_count(self, guild: discord.Guild, fetch: bool = False) -> int:
        count = guild.approximate_member_count
        if count is None or fetch:
            fetched_guild = await self.bot.fetch_guild(guild.id, with_counts=True)
            count = fetched_guild.approximate_member_count
        return count

    async def collect_guild_member_counts(self, delay: int = 1) -> Dict[int, int]:
        container = {}
        for cached_guild in self.bot.guilds:
            count = await self.member_count(cached_guild, fetch=True)
            container[cached_guild.id] = count
            await asyncio.sleep(delay)
        return container

    @tasks.loop(hours=2, reconnect=True)
    async def update_member_counts_task(self):
        await self.bot.wait_until_ready()
        guild_counts = await self.collect_guild_member_counts()
        async with self.bot.db as session:
            for guild_id, member_count in guild_counts.items():
                schema = await session.guilds.update_member_count(guild_id, member_count)
                if schema is None:
                    schema = await self.create_guild_schema(guild_id, member_count)
                    await session.guilds.upsert(schema)
            await session.commit()
            log.debug("guild member count update complete")

    async def create_guild_schema(self, guild_id: int, member_count: Optional[int] = None):
        guild = self.bot.get_guild(guild_id)
        member_count = member_count or await self.member_count(guild)
        return GuildSchema(guild_id=guild_id, guild_name=guild.name, member_count=member_count)


    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        schema = self.create_guild_schema(guild.id)
        async with self.bot.db as session:
            await session.guilds.upsert(schema)
            await session.commit()


    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        async with self.bot.db as session:
            schema = await session.guilds.fetch_guild(guild.id)
            if schema is not None:
                schema.removed = datetime.now(timezone.utc)
                await session.guilds.upsert(schema)
                await session.commit()

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        async with self.bot.db as session:
            schema = session.guilds.increment_member_count(member.guild.id)
            if schema is None:
                schema = await self.create_guild_schema(member.guild.id)
                await session.guilds.upsert(schema)
            await session.commit()

