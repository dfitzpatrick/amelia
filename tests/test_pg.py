
import pytest

@pytest.mark.asyncio
async def test_pg_context_commit(pg):
    async with pg as db:
        await db.session.execute("create table foo (id serial primary key, name text);")
        await db.session.execute("insert into foo (name) values ('bar');")
        await db.commit()

    async with pg as db:
        count = await db.session.fetchval("select count(id) from foo;")
        assert count == 1

@pytest.mark.asyncio
async def test_pg_context_no_implicit_commit(pg):
    async with pg as db:
        await db.session.execute("create table foo (id serial primary key, name text);")
        await db.commit()

    async with pg as db:
        await db.session.execute("insert into foo (name) values ('bar');")

    async with pg as db:
        count = await db.session.fetchval("select count(id) from foo;")
        assert count == 0

@pytest.mark.asyncio
async def test_pg_context_rollback_on_error(pg):
    async with pg as db:
        await db.session.execute("create table foo (id serial primary key, name text);")
        await db.commit()

    async with pg as db:
        await db.session.execute("insert into foo (name) values ('bar');")
        with pytest.raises(ZeroDivisionError):
            f = 5 / 0
            await db.commit()
    async with pg as db:
        count = await db.session.fetchval("select count(id) from foo;")
        assert count == 0


