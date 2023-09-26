from typing import Tuple
from src.features.forum_channels.data import ForumChannelDataContext
import pytest
import pytest_asyncio
from src.concepts.guild.data import GuildDataContext, GuildSchema
from polyfactory.factories.pydantic_factory import ModelFactory

class GuildFactory(ModelFactory[GuildSchema]):
    __model__ = GuildSchema

@pytest_asyncio.fixture()
async def ctx_with_guild_schema(session):
    o = GuildFactory.build(id=None)
    guild_ctx = GuildDataContext(session)
    o = await guild_ctx.upsert(o)
    ctx = ForumChannelDataContext(session)
    yield ctx, o


@pytest.mark.asyncio
async def test_create_auto_pin(ctx_with_guild_schema: Tuple[ForumChannelDataContext, GuildSchema]):
    ctx, o = ctx_with_guild_schema
    await ctx.create_auto_pin(o.guild_id,43634634)
    count = await ctx.session.fetchval("select count(id) from autopins;")
    assert count == 1


@pytest.mark.asyncio
async def test_delete_auto_pin(ctx_with_guild_schema: Tuple[ForumChannelDataContext, GuildSchema]):
    ctx, o = ctx_with_guild_schema
    await ctx.create_auto_pin(o.guild_id,43634634)
    count = await ctx.session.fetchval("select count(id) from autopins;")
    assert count == 1

    await ctx.delete_auto_pin(123455667)
    count = await ctx.session.fetchval("select count(id) from autopins;")
    assert count == 1

    await ctx.delete_auto_pin(43634634)
    count = await ctx.session.fetchval("select count(id) from autopins;")
    assert count == 0


@pytest.mark.asyncio
async def test_has_auto_pin(ctx_with_guild_schema: Tuple[ForumChannelDataContext, GuildSchema]):
    ctx, o = ctx_with_guild_schema
    await ctx.create_auto_pin(o.guild_id,43634634)
    count = await ctx.session.fetchval("select count(id) from autopins;")
    assert count == 1
    has_pin = await ctx.has_auto_pin(43634634)
    assert has_pin is True

    has_pin = await ctx.has_auto_pin(123455)
    assert has_pin is False