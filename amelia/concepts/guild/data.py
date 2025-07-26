from datetime import datetime
from typing import Optional

import asyncpg
import discord
from pydantic import BaseModel, Field

class GuildSchema(BaseModel):
    id: Optional[int] = None
    created: Optional[datetime] = None
    updated: Optional[datetime] = None
    removed: Optional[datetime] = None
    joined: datetime = Field(default_factory=datetime.now)
    member_count: Optional[int] = None
    vanity_url: Optional[str] = None
    guild_id: int
    guild_name: str


class GuildDataContext:

    def __init__(self, session: asyncpg.Connection):
        self.session = session

    async def upsert(self, schema: GuildSchema):
        q = """
      insert into guilds (guild_id, guild_name, joined, member_count, vanity_url)
      values ($1, $2, $3, $4, $5)

      on conflict (guild_id)
      do update set guild_id = $1, guild_name = $2, joined = $3, member_count = $4, vanity_url = $5
      returning id, created, updated;
      """
        result = await self.session.fetchrow(q,
            schema.guild_id, schema.guild_name, schema.joined, schema.member_count, schema.vanity_url
        )
        values = schema.model_dump()
        values.update(**(result or {}))
        return GuildSchema(**values)

    async def fetch_guild(self, guild_id: int) -> Optional[GuildSchema]:
        q = "select * from guilds where guild_id = $1;"
        result = await self.session.fetchrow(q, guild_id)
        if result is None:
            return
        return GuildSchema(**result)

    async def create_guild(self, guild: discord.Guild, member_count: int):
        schema = GuildSchema(
            guild_id=guild.id,
            guild_name=guild.name,
            vanity_url=guild.vanity_url,
            member_count=member_count
        )
        await self.upsert(schema)

    async def update_member_count(self, guild_id: int, new_member_count: int):
        q = """update guilds set member_count = $2 where guild_id = $1 returning *; """
        o = await self.session.fetchrow(q, guild_id, new_member_count)
        return o if o is None else GuildSchema(**o)
    
    async def increment_member_count(self, guild_id: int) -> Optional[GuildSchema]:
        q = """
            update guilds set member_count = 
                case 
                    when member_count IS NULL THEN 1
                    else member_count + 1
                end
            where guild_id = $1 
            returning *; """
        o = await self.session.fetchrow(q, guild_id)
        return o if o is None else GuildSchema(**o)
