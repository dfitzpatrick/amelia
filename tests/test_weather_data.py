from typing import Tuple
import asyncpg
import pytest
import pytest_asyncio
from src.features.weather.data import AllowedChannel, WeatherConfigSchema, WeatherDataContext
from src.concepts.guild.data import GuildDataContext, GuildSchema
from polyfactory.factories.pydantic_factory import ModelFactory

class GuildFactory(ModelFactory[GuildSchema]):
    __model__ = GuildSchema

@pytest_asyncio.fixture()
async def ctx_with_guild_schema(session):
    o = GuildFactory.build(id=None)
    guild_ctx = GuildDataContext(session)
    o = await guild_ctx.upsert(o)
    ctx = WeatherDataContext(session)
    yield ctx, o

@pytest.mark.asyncio
async def test_create_metar_config(ctx_with_guild_schema: Tuple[WeatherDataContext, GuildSchema]) -> None:
    ctx, o = ctx_with_guild_schema
    schema = WeatherConfigSchema(guild_id=o.guild_id)
    await ctx.create_or_update_metar_configuration(schema)
    q = "select count(id) from metarconfig;"
    count = await ctx.session.fetchval(q)
    assert count == 1


@pytest.mark.asyncio
async def test_create_taf_config(ctx_with_guild_schema: Tuple[WeatherDataContext, GuildSchema]) -> None:
    ctx, o = ctx_with_guild_schema
    schema = WeatherConfigSchema(guild_id=o.guild_id)
    await ctx.create_or_update_taf_configuration(schema)
    q = "select count(id) from tafconfig;"
    count = await ctx.session.fetchval(q)
    assert count == 1

@pytest.mark.asyncio
async def test_create_station_config(ctx_with_guild_schema: Tuple[WeatherDataContext, GuildSchema]) -> None:
    ctx, o = ctx_with_guild_schema
    schema = WeatherConfigSchema(guild_id=o.guild_id)
    await ctx.create_or_update_station_configuration(schema)
    q = "select count(id) from stationconfig;"
    count = await ctx.session.fetchval(q)
    assert count == 1


@pytest.mark.asyncio
async def test_fetch_metar_configuration(ctx_with_guild_schema: Tuple[WeatherDataContext, GuildSchema]) -> None:
    ctx, o = ctx_with_guild_schema
    schema = WeatherConfigSchema(guild_id=o.guild_id)
    await ctx.create_or_update_metar_configuration(schema)
    config = await ctx.fetch_metar_configuration(o.guild_id)
    assert config is not None and config.guild_id == o.guild_id

@pytest.mark.asyncio
async def test_fetch_taf_configuration(ctx_with_guild_schema: Tuple[WeatherDataContext, GuildSchema]) -> None:
    ctx, o = ctx_with_guild_schema
    schema = WeatherConfigSchema(guild_id=o.guild_id)
    await ctx.create_or_update_taf_configuration(schema)
    config = await ctx.fetch_taf_configuration(o.guild_id)
    assert config is not None and config.guild_id == o.guild_id


@pytest.mark.asyncio
async def test_fetch_station_configuration(ctx_with_guild_schema: Tuple[WeatherDataContext, GuildSchema]) -> None:
    ctx, o = ctx_with_guild_schema
    schema = WeatherConfigSchema(guild_id=o.guild_id)
    await ctx.create_or_update_station_configuration(schema)
    config = await ctx.fetch_station_configuration(o.guild_id)
    assert config is not None and config.guild_id == o.guild_id


@pytest.mark.asyncio
async def test_create_metar_channel(ctx_with_guild_schema: Tuple[WeatherDataContext, GuildSchema]) -> None:
    ctx, o = ctx_with_guild_schema
    schema = AllowedChannel(guild_id=o.guild_id, channel_id=123456)
    await ctx.create_metar_channel(schema)
    q = "select count(id) from metarchannel;"
    count = await ctx.session.fetchval(q)
    assert count == 1
    with pytest.raises(asyncpg.UniqueViolationError):
        await ctx.create_metar_channel(schema)

@pytest.mark.asyncio
async def test_create_taf_channel(ctx_with_guild_schema: Tuple[WeatherDataContext, GuildSchema]) -> None:
    ctx, o = ctx_with_guild_schema
    schema = AllowedChannel(guild_id=o.guild_id, channel_id=123456)
    await ctx.create_taf_channel(schema)
    q = "select count(id) from tafchannel;"
    count = await ctx.session.fetchval(q)
    assert count == 1
    with pytest.raises(asyncpg.UniqueViolationError):
        await ctx.create_taf_channel(schema)

@pytest.mark.asyncio
async def test_create_station_channel(ctx_with_guild_schema: Tuple[WeatherDataContext, GuildSchema]) -> None:
    ctx, o = ctx_with_guild_schema
    schema = AllowedChannel(guild_id=o.guild_id, channel_id=123456)
    await ctx.create_station_channel(schema)
    q = "select count(id) from stationchannel;"
    count = await ctx.session.fetchval(q)
    assert count == 1
    with pytest.raises(asyncpg.UniqueViolationError):
        await ctx.create_station_channel(schema)


@pytest.mark.asyncio
async def test_remove_metar_channel(ctx_with_guild_schema: Tuple[WeatherDataContext, GuildSchema]) -> None:
    ctx, o = ctx_with_guild_schema
    schema = AllowedChannel(guild_id=o.guild_id, channel_id=123456)
    await ctx.create_metar_channel(schema)
    q = "select count(id) from metarchannel;"
    count = await ctx.session.fetchval(q)
    assert count == 1
    await ctx.remove_metar_channel(schema.channel_id)
    q = "select count(id) from metarchannel;"
    count = await ctx.session.fetchval(q)
    assert count == 0


@pytest.mark.asyncio
async def test_remove_taf_channel(ctx_with_guild_schema: Tuple[WeatherDataContext, GuildSchema]) -> None:
    ctx, o = ctx_with_guild_schema
    schema = AllowedChannel(guild_id=o.guild_id, channel_id=123456)
    await ctx.create_taf_channel(schema)
    q = "select count(id) from tafchannel;"
    count = await ctx.session.fetchval(q)
    assert count == 1
    await ctx.remove_taf_channel(schema.channel_id)
    q = "select count(id) from stationchannel;"
    count = await ctx.session.fetchval(q)
    assert count == 0

@pytest.mark.asyncio
async def test_remove_station_channel(ctx_with_guild_schema: Tuple[WeatherDataContext, GuildSchema]) -> None:
    ctx, o = ctx_with_guild_schema
    schema = AllowedChannel(guild_id=o.guild_id, channel_id=123456)
    await ctx.create_station_channel(schema)
    q = "select count(id) from stationchannel;"
    count = await ctx.session.fetchval(q)
    assert count == 1
    await ctx.remove_station_channel(schema.channel_id)
    q = "select count(id) from stationchannel;"
    count = await ctx.session.fetchval(q)
    assert count == 0