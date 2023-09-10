import asyncpg
import pytest
import pytest_asyncio
from polyfactory.factories.pydantic_factory import ModelFactory

from amelia.concepts.guild.data import GuildDataContext, GuildSchema

class GuildFactory(ModelFactory[GuildSchema]):
    __model__ = GuildSchema

@pytest_asyncio.fixture()
async def ctx(session):
    ctx = GuildDataContext(session)
    yield ctx

@pytest.mark.asyncio
async def test_guild_context_class(ctx: GuildDataContext):
    assert ctx.session is not None
    assert isinstance(ctx.session, asyncpg.Connection)

@pytest.mark.asyncio
async def test_guild_context_upsert(ctx: GuildDataContext):
    o = GuildFactory.build(id=None)
    assert o.id is None
    o = await ctx.upsert(o)
    assert o.id is not None

@pytest.mark.asyncio
async def test_member_count_increment(ctx: GuildDataContext):
    o = GuildFactory.build(id=None)
    assert o.id is None
    o = await ctx.upsert(o)
    assert o.id is not None
    count = o.member_count
    o = await ctx.increment_member_count(o.guild_id)
    assert o.member_count == count + 1

@pytest.mark.asyncio
async def test_member_count_increment_returns_none_if_no_guild(ctx: GuildDataContext):
    schema = await ctx.increment_member_count(guild_id=123) # Does not exist
    assert schema is None

@pytest.mark.asyncio
async def test_guild_context_fetch_guild(ctx: GuildDataContext):
    o = GuildFactory.build(id=None)
    o = await ctx.upsert(o)
    new = await ctx.fetch_guild(o.guild_id)
    assert new is not None
    missing_id = o.id + 1
    not_found = await ctx.fetch_guild(missing_id)
    assert not_found is None