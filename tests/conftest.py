import pathlib
import os

import pytest
import pytest_asyncio
import asyncpg
import asyncio

from polyfactory.factories.pydantic_factory import ModelFactory

from src.data import Pg, BaseUOW
from src.concepts.guild.data import GuildDataContext, GuildSchema



DSN = os.environ['TEST_DSN']
TEST_DB = "amelia_tests_db"
TEST_DB_TEMPLATE = f"{TEST_DB}_template"
MIGRATIONS = pathlib.Path(__file__).parents[1] / 'migrations'
OWNER = os.environ['POSTGRES_USER']

DROP_QUERY = """DO $$ DECLARE
    r RECORD;
BEGIN
    -- if the schema you operate on is not "current", you will want to
    -- replace current_schema() in query with 'schematodeletetablesfrom'
    -- *and* update the generate 'DROP...' accordingly.
    FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = current_schema()) LOOP
        EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
    END LOOP;
END $$;"""


class GuildFactory(ModelFactory[GuildSchema]):
    __model__ = GuildSchema
@pytest.fixture(scope="session")
def event_loop():
    loop = None
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    finally:
        return loop


@pytest_asyncio.fixture(scope="session")
async def test_db_setup():
    conn: asyncpg.Connection
    conn = await asyncpg.connect(f"{DSN}/template1")
    await conn.execute(f"DROP DATABASE IF EXISTS {TEST_DB_TEMPLATE} WITH (FORCE);")
    await conn.execute(f"CREATE DATABASE {TEST_DB_TEMPLATE} OWNER {OWNER};")
    await conn.close()
    conn = await asyncpg.connect(f"{DSN}/{TEST_DB_TEMPLATE}")
    await conn.execute(DROP_QUERY)
    async with conn.transaction():
        for f in sorted(list(MIGRATIONS.iterdir())):
            if not 'rollback' in f.name.split('.'):
                await conn.execute(f.read_text())
    await conn.close()
    yield


@pytest_asyncio.fixture()
async def empty_db(test_db_setup):
    conn = await asyncpg.connect(f"{DSN}/template1")
    await conn.execute(f"DROP DATABASE IF EXISTS {TEST_DB} WITH (FORCE);")
    await conn.execute(f"CREATE DATABASE {TEST_DB} WITH TEMPLATE {TEST_DB_TEMPLATE} OWNER {OWNER};")
    await conn.close()
    yield


@pytest_asyncio.fixture()
async def pg(empty_db):
    conn = await asyncpg.connect(f"{DSN}/{TEST_DB}")
    pool = await asyncpg.create_pool(f"{DSN}/{TEST_DB}")
    yield Pg(pool, conn, uow_cls=BaseUOW, entity_map={})

@pytest_asyncio.fixture()
async def session(empty_db):
    conn = await asyncpg.connect(f"{DSN}/{TEST_DB}")
    yield conn

@pytest_asyncio.fixture()
async def db_pool(db_reset):
    pool = await asyncpg.create_pool(dsn_base + "/" + test_db)
    yield pool
    await pool.close()

@pytest.fixture()
def guild_factory():
    yield GuildFactory

@pytest_asyncio.fixture()
async def one_guild(session, guild_factory: ModelFactory):
    guild_ctx = GuildDataContext(session)
    guild_schema = guild_factory.build(id=None)
    guild_schema = await guild_ctx.upsert(guild_schema)
    yield session, guild_schema