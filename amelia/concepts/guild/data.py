from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Optional

import asyncpg
import discord
from pydantic import BaseModel, Field


ctx_connection = ContextVar("ctx_connection1")
ctx_transaction = ContextVar("ctx_transaction1")

class GuildSchema(BaseModel):
    id: Optional[int] = None
    created: Optional[datetime] = None
    updated: Optional[datetime] = None
    removed: Optional[datetime] = None
    joined: datetime = Field(default_factory=datetime.now)
    guild_id: int
    guild_name: str

    member_count: int

class GuildDataContext:

    def __init__(self, session: asyncpg.Connection):
        self.session = session

    async def upsert(self, schema: GuildSchema):
        q = """
      insert into guilds (guild_id, guild_name, joined, member_count)
      values ($1, $2, $3, $4)

      on conflict (guild_id)
      do update set guild_id = $1, guild_name = $2, joined = $3, member_count = $4
      returning id, created, updated;
      """
        result = await self.session.fetchrow(q,
            schema.guild_id, schema.guild_name, schema.joined, schema.member_count
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
            member_count=member_count
        )
        await self.session.upsert(schema)

    async def update_member_count(self, guild_id: int, new_member_count: int):
        q = """update guilds set member_count = $2 where guild_id = $1 returning *; """
        o = await self.session.fetchrow(q, guild_id, new_member_count)
        return o if o is None else GuildSchema(**o)
    async def increment_member_count(self, guild_id: int) -> Optional[GuildSchema]:
        q = """update guilds set member_count = member_count + 1 where guild_id = $1 returning *; """
        o = await self.session.fetchrow(q, guild_id)
        return o if o is None else GuildSchema(**o)







class GuildRepository:
    def __init__(self, session: asyncpg.Connection):
        self.session = session
        self.table = "guilds"

    async def all(self):
        q = f"select {GuildSchema.fields_csv()} from {self.table};"
        results = await self.session.fetch(q)
        return [GuildSchema(**entity) for entity in results]

    async def create(self, schema: GuildSchema) -> GuildSchema:
        q = f"insert into guilds (guild_id, guild_name) values ($1, $2) returning id, created, updated;"
        result = await self.session.fetchrow(q, schema.guild_id, schema.guild_name)
        return GuildSchema(
            id=result['id'],
            created=result['created'],
            updated=result['updated'],
            joined=datetime.now(timezone.utc),
            guild_id=schema.guild_id,
            guild_name=schema.guild_name,
            member_count=schema.member_count
        )
    async def upsert(self, schema: GuildSchema):
        q = """
        insert into guilds (guild_id, guild_name, joined, member_count)
        values ($1, $2, $3, $4)
       
        on conflict (guild_id)
        do update set guild_id = $1, guild_name = $2, joined = $3, member_count = $4
        returning id, created, updated;
        """
        result = await self.session.fetchrow(q,
            schema.guild_id, schema.guild_name, schema.joined, schema.member_count
        )
        values = schema.dict()
        values.update(**(result or {}))
        return GuildSchema(**values)

    async def update_member_count(self, guild_id: int, new_member_count: int):
        q = """update guilds set member_count = $2 where guild_id = $1 returning *; """
        o = await self.session.fetchrow(q, guild_id, new_member_count)
        return o if o is None else GuildSchema(**o)
    async def increment_member_count(self, guild_id: int) -> Optional[GuildSchema]:
        q = """update guilds set member_count = member_count + 1 where guild_id = $1 returning *; """
        o = await self.session.fetchrow(q, guild_id)
        return o if o is None else GuildSchema(**o)


