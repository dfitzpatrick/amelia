import pytest
from ameliapg.metar.models import MetarChannelDB
from ameliapg.models import PgNotify
from pydantic import BaseModel

from src.cache import DiscordEntityManyCache, DiscordEntityCache


class ConvertedObject(BaseModel):
    guild_id: int
    channel_id: int

    def __str__(self):
        return "ConvertedObject(guild_id={0}, channel_id={1})".format(self.guild_id, self.channel_id)


class ManyConvertedObjectCache(DiscordEntityManyCache[ConvertedObject]):
    pass

class SingleConvertedObjectCache(DiscordEntityCache[ConvertedObject]):
    pass


async def fetcher():
    return [
        MetarChannelDB(id=1, guild_id=123, channel_id=123),
        MetarChannelDB(id=2, guild_id=456, channel_id=456)
    ]


async def converter(entity: MetarChannelDB) -> ConvertedObject:
    return ConvertedObject(guild_id=entity.guild_id, channel_id=entity.channel_id)


@pytest.mark.asyncio
async def test_many_cache_adds():
    cache = ManyConvertedObjectCache(converter, fetcher, MetarChannelDB)
    await cache.notify(PgNotify(table='test', action='INSERT', entity=MetarChannelDB(id=1, guild_id=1, channel_id=2)))
    assert len(cache.item) == 1


@pytest.mark.asyncio
async def test_many_cache_populates():
    cache = ManyConvertedObjectCache(converter, fetcher, MetarChannelDB)
    await cache.populate_cache()
    assert len(cache.item) == 2


@pytest.mark.asyncio
async def test_many_cache_updates():
    cache = ManyConvertedObjectCache(converter, fetcher, MetarChannelDB)
    await cache.populate_cache()
    await cache.notify(PgNotify(table='test', action='UPDATE', entity=MetarChannelDB(id=1, guild_id=123, channel_id=222)))
    assert any(item.channel_id == 222 for item in cache.item[123])


@pytest.mark.asyncio
async def test_many_cache_delete():
    cache = ManyConvertedObjectCache(converter, fetcher, MetarChannelDB)
    await cache.populate_cache()
    await cache.notify(PgNotify(table='test', action='DELETE', entity=MetarChannelDB(id=1, guild_id=123, channel_id=123)))
    assert len(cache.item[123]) == 0


@pytest.mark.asyncio
async def test_cache_adds():
    cache = SingleConvertedObjectCache(converter, fetcher, MetarChannelDB)
    await cache.notify(PgNotify(table='test', action='INSERT', entity=MetarChannelDB(id=1, guild_id=1, channel_id=2)))
    assert len(cache.item) == 1


@pytest.mark.asyncio
async def test_cache_populates():
    cache = SingleConvertedObjectCache(converter, fetcher, MetarChannelDB)
    await cache.populate_cache()
    assert len(cache.item) == 2


@pytest.mark.asyncio
async def test_cache_updates():
    cache = SingleConvertedObjectCache(converter, fetcher, MetarChannelDB)
    await cache.populate_cache()
    await cache.notify(PgNotify(table='test', action='UPDATE', entity=MetarChannelDB(id=1, guild_id=123, channel_id=222)))
    assert cache.item[123].channel_id == 222


@pytest.mark.asyncio
async def test_cache_delete():
    cache = SingleConvertedObjectCache(converter, fetcher, MetarChannelDB)
    await cache.populate_cache()
    assert cache.item.get(123) is not None
    await cache.notify(PgNotify(table='test', action='DELETE', entity=MetarChannelDB(id=1, guild_id=123, channel_id=123)))
    assert cache.item.get(123) is None



