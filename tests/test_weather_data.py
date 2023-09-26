from typing import Tuple
import pytest
import pytest_asyncio
from src.features.weather.data import WeatherConfigSchema, WeatherDataContext
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
async def test_create_metar(ctx_with_guild_schema: Tuple[WeatherDataContext, GuildSchema]) -> None:
    ctx, o = ctx_with_guild_schema
    schema = WeatherConfigSchema(guild_id=o.guild_id)
    await ctx.create_or_update_metar_configuration(schema)
    q = "select count(id) from metarconfig;"
    count = await ctx.session.fetchval(q)
    assert count == 1


