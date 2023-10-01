import pytest

from src.cache import LRUCache, FunctionOperationsCache
import logging
log = logging.getLogger(__name__)

@pytest.mark.asyncio()
async def test_keys_generate_correctly():
    cache = FunctionOperationsCache[dict]('id')
    obj = {'id': 1, 'name': '1foo'}
    @cache.function()
    async def some_function(n: int):
        return {'id': n, 'name': f'{n}foo'}

    @cache.function()
    async def some_function_seq(n: int):
        return [
            {'id': n, 'name': f'{n}foo'},
            {'id': n+1, 'name': f'{n+1}foo'},
            {'id': n+2, 'name': f'{n + 2}foo'},
            ]

    await some_function(1)
    await some_function(1)
    await some_function(2)
    await some_function(1)
    await some_function(1)
    assert len(cache.cache_ids) == 2
    await some_function_seq(1)
    await some_function_seq(1)
    await some_function_seq(1)
    assert len(cache.cache_ids) == 3
    assert len(set(cache.cache_ids)) == len(cache.cache_ids)


@pytest.mark.asyncio()
async def test_invalidate_by_id_works():
    cache = FunctionOperationsCache[dict]('id')
    obj = {'id': 1, 'name': '1foo'}
    @cache.function()
    async def some_function(n: int):
        return {'id': n, 'name': f'{n}foo'}

    # Test that different args are not invalidated by another call
    await some_function(1)
    await some_function(2)
    await some_function(3)
    assert len(cache.cache_ids) == 3
    cache.invalidate_function_cache_object(1)
    assert len(cache.cache_ids) == 2

@pytest.mark.asyncio()
async def test_invalidate_for_many_will_invalidate_for_each_function_id():
    cache = FunctionOperationsCache[dict]('id')
    @cache.function()
    async def some_function_seq(n: int):
        return [
            {'id': n, 'name': f'{n}foo'},
            {'id': n+1, 'name': f'{n+1}foo'},
            {'id': n+2, 'name': f'{n + 2}foo'},
            ]

    await some_function_seq(1)
    await some_function_seq(3)
    # There is overlap in the two caches. test invalidate removes from each one)
    assert len(cache.cache_ids) == 2
    assert all(len(cache.preview(f_id)) == 3 for f_id in cache.cache_ids) #type: ignore
    assert len(set(cache.cache_ids)) == len(cache.cache_ids)
    # Invalidate the # 3
    cache.invalidate_function_cache_object(3)
    assert len(cache.cache_ids) == 2
    assert all(len(cache.preview(f_id)) == 2 for f_id in cache.cache_ids) #type: ignore



@pytest.mark.asyncio()
async def test_function_update_cache():
    class SampleObj(dict):

        def __eq__(self, other):
            return self['id'] == other['id']
        
    cache = FunctionOperationsCache[dict]('id')
    obj = SampleObj({'id': 1, 'name': '1foo'})
    @cache.function()
    async def some_function(n: int):
        return SampleObj({'id': n, 'name': f'{n}foo'})

    @cache.function()
    async def some_function_seq(n: int):
        return [
            SampleObj({'id': n, 'name': f'{n}foo'}),
            SampleObj({'id': n+1, 'name': f'{n+1}foo'}),
            SampleObj({'id': n+2, 'name': f'{n + 2}foo'}),
            ]


    # Test equality works
    id1 = await some_function(1)
    id1_id = cache.last_function_id
    seq1 = await some_function_seq(1)
    seq1_id = cache.last_function_id
    seq5 = await some_function_seq(5)
    seq5_id = cache.last_function_id
    assert id1 not in seq5
    assert id1 in seq1


    # Test updating
    id1['name'] = 'bar'
    cache.update_function_cache_object(id1)
    assert cache.preview(id1_id)['name'] == 'bar'
    assert cache.preview(seq1_id)[0]['name'] == 'bar'
