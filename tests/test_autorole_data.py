import asyncpg
import pytest
import pytest_asyncio
from polyfactory.factories.pydantic_factory import ModelFactory

from amelia.concepts.guild.data import GuildDataContext
from amelia.features.autorole.cache import AutoRoleCache, AutoRoleCacheAdapter
from amelia.features.autorole.data import AutoRoleDataContext
from amelia.features.autorole.schema import AutoRoleSchema


class AutoRoleFactory(ModelFactory[AutoRoleSchema]):
    __model__ = AutoRoleSchema

@pytest_asyncio.fixture()
async def ctx(session):
    ctx = AutoRoleDataContext(session)
    yield ctx

@pytest_asyncio.fixture()
async def ctx_with_guild(one_guild):
    session, guild_schema = one_guild
    ctx = AutoRoleDataContext(session)
    yield ctx, guild_schema

@pytest.mark.asyncio
async def test_autorole_add(ctx_with_guild):
    ctx, guild_schema = ctx_with_guild
    role_id = 123
    result = await ctx.add_auto_role(guild_schema.guild_id, role_id)
    assert result.id is not None
    assert result.created_at is not None
    assert result.updated_at is not None
    assert result.guild_id == guild_schema.guild_id
    assert result.role_id == role_id

@pytest.mark.asyncio
async def test_autorole_remove(ctx_with_guild):
    ctx, guild_schema = ctx_with_guild
    role_id = 123
    result = await ctx.add_auto_role(guild_schema.guild_id, role_id)
    assert result.id is not None

    await ctx.remove_auto_role(result.role_id)
    count = await ctx.session.fetchval('select count(id) from autorole')
    assert count == 0

@pytest.mark.asyncio
async def test_autorole_all_roles(ctx_with_guild):
    ctx, guild_schema = ctx_with_guild
    await ctx.add_auto_role(guild_schema.guild_id, 1234)
    await ctx.add_auto_role(guild_schema.guild_id, 5678)
    results = await ctx.all_auto_roles()
    assert len(results) == 2
    assert results[0].role_id == 1234
    assert results[1].role_id == 5678


@pytest.mark.asyncio
async def test_autorole_cache_working():
    cache = AutoRoleCacheAdapter()
    @cache.use(lambda o: o)
    async def return_one(role_id: int):
        return role_id

    @cache.use(lambda o: o)
    async def return_another(another_id: int):
        return another_id + 1

    @cache.use(lambda o: o)
    async def return_many(guild_id):
        return [x for x in guild_id] + [guild_id]

    async def return_two(role_id: int):
        return role_id

    item = await return_one(5)
    assert cache.has_value(5)
    another_item = await return_another(5)
    def function_contents(func):
        closure = tuple(cell.cell_contents for cell in func.__closure__) if func.__closure__ else ()
        return (
        func.__name__, func.__defaults__, func.__kwdefaults__, closure, func.__code__.co_code, func.__code__.co_consts)

    first = hash(function_contents(return_one))
    same = hash(function_contents(return_one))
    second = hash(function_contents(return_another))
    third = hash(function_contents(return_two))

    assert first != second
    assert first != third
    assert second != third
    assert first == same
    assert False

