
import pytest
import pytest_asyncio
from polyfactory.factories.pydantic_factory import ModelFactory

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




