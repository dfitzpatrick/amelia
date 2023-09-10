import pytest

from amelia.cache import LRUCache, FunctionOperationsCache

@pytest.mark.asyncio()
async def test_function_invalidate_cache():
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
    await some_function(2)
    await some_function(3)
    assert len(cache.cache_ids) == 3
    cache.invalidate_function_cache_object(1)
    assert len(cache.cache_ids) == 2
    cache.clear()

    await some_function_seq(1)
    func_id = cache.last_function_id
    await some_function_seq(3)
    f2 = cache.last_function_id
    assert len(cache.cache_ids) == 2
    cache.invalidate_function_cache_object(1)
    cache.invalidate_function_cache_object(3)
    assert len(cache.get(func_id)) == 1
    assert len(cache.get(f2)) == 2




@pytest.mark.asyncio()
async def test_function_update_cache():
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
    x = cache.last_function_id
    await some_function(2)
    y = cache.last_function_id
    await some_function(3)
    z = cache.last_function_id
    assert len(cache.cache_ids) == 3
    cache.update_function_cache_object({'id': 1, 'name':'bar'})
    item = cache.get(x)
    assert item['name'] == 'bar'
    assert cache.get(y)['name'] == '2foo'

    cache.clear()

    await some_function_seq(1)
    func_id = cache.last_function_id
    await some_function_seq(3)
    f2 = cache.last_function_id
    assert len(cache.cache_ids) == 2
    o = {'id': 3, 'name': 'bar'}
    cache.update_function_cache_object(o)
    cache.update_function_cache_object(o)
    assert len(cache.get(func_id)) == 3
    assert len(cache.get(f2)) == 3
    items = cache.get(func_id)
    assert o in items
    assert items[2]['name'] == 'bar'

    items = cache.get(f2)
    assert o in items
    assert items[0]['name'] == 'bar'




