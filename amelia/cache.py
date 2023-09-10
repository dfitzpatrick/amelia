from __future__ import annotations

import collections
import logging
from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Type, Dict, List, Callable, Optional, Awaitable, Protocol, Any
from inspect import iscoroutinefunction
from ameliapg import PgActions
from ameliapg.models import PgNotify
from functools import wraps
from inspect import iscoroutinefunction
import gc

log = logging.getLogger(__name__)


Container_T = TypeVar("Container_T")
Entity_T = TypeVar("Entity_T")
Item_T = TypeVar("Item_T")
T = TypeVar("T")

class LRUCache(Generic[T]):

    def __init__(self, max_size: Optional[int] = 128):
        self.max_size = max_size
        self._cache: Dict[Any, T | list[T]] = collections.OrderedDict()
        self.last_function_id: Optional[int] = None

    def put(self, key: str | int, value: T):
        self._cache[key] = value
        self._cache.move_to_end(key)
        if self.max_size is not None and len(self._cache) > self.max_size:
            self._cache.popitem(last=False)

    def invalidate(self, key: str | int):
        if key in self._cache.keys():
            del self._cache[key]

    def get(self, key: str | int) -> Optional[T]:
        if key not in self._cache:
            return
        self._cache.move_to_end(key)
        return self._cache[key]

    def clear(self):
        self._cache = collections.OrderedDict()
        collect = gc.collect()
        log.debug(f"Clear cache and GC collected {collect} items")
    @property
    def cache_ids(self):
        return self._cache.keys()

    def function(self) -> Optional[T] | list[T]:
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                key = hash((args, frozenset(kwargs.items())))
                item = self._cache.get(key)
                if item is None:
                    log.debug('cache miss detected')
                    item = await func(*args, **kwargs)
                    if item is not None:
                        self.put(key, item)
                else:
                    log.debug(f"cache hit {item}")
                self.last_function_id = key
                self.post_function_cache(key, item)
                return item
            return wrapper
        return decorator

    def post_function_cache(self, key: int, item: T | list[T]):
        pass


class FunctionOperationsCache(Generic[T], LRUCache[T]):

    def __init__(self, item_identifier_field: str, max_size: int=128):
        super().__init__(max_size=max_size)
        self.object_map: Dict[int, set] = {}
        self._field_name = item_identifier_field

    def _get_identifier(self, object: T):
        try:
            value = getattr(object, self._field_name)
        except AttributeError:
            try:
                value = object[self._field_name]
            except (TypeError, KeyError):
                raise AttributeError
        finally:
            return value

    def _map_scalar(self, object: T, function_cache_id: int):
        id_value = self._get_identifier(object)
        if id_value not in self.object_map.keys():
            self.object_map[id_value] = set()
        self.object_map[id_value].add(function_cache_id)

    def _map_sequence(self, objects: list[T], function_cache_id: int):
        for obj in objects:
            self._map_scalar(obj, function_cache_id)

    def post_function_cache(self, key: int, result_set: T | list[T]):
        if type(result_set) is list:
            self._map_sequence(result_set, key)
        else:
            self._map_scalar(result_set, key)

    def invalidate_function_cache_object(self, field_id: int):
        function_ids = self.object_map.get(field_id, set())
        for fid in function_ids:
            value = self.get(fid)
            if value is None:
                return
            if type(value) is list:
                # Loop through and remove only that one object
                for obj in value: # list
                    value: list
                    obj_id = self._get_identifier(obj)
                    if obj_id == field_id:
                        value.remove(obj)
                        self.put(fid, value)
            else:
                self.invalidate(fid)
        if field_id in self.object_map.keys():
            del[field_id]

    def update_function_cache_object(self, object: T):
        oid = self._get_identifier(object)
        function_ids = self.object_map.get(oid, set())
        for fid in function_ids:
            value = self.get(fid)
            if value is None:
                return
            if type(value) is list:
                # Loop through and remove only that one object
                for obj in value: # list
                    value: list
                    obj_id = self._get_identifier(obj)
                    if obj_id == oid:
                        idx = value.index(obj)
                        value.remove(obj)
                        value.insert(idx, object)
                        self.put(fid, value)
            else:
                self.put(fid, object)

class PgListenerCache(Generic[Container_T, Entity_T, Item_T], ABC):
    item: Container_T

    def __init__(self,
                 converter: Callable[[Entity_T], Awaitable[Optional[Item_T]]],
                 fetcher: Callable,
                 event_type: Type):
        self.converter = converter
        self.fetcher = fetcher
        self.event_type = event_type

    async def notify(self, payload: PgNotify):
        entity = payload.entity
        if isinstance(entity, self.event_type):
            dispatch = {
                PgActions.INSERT: self.on_insert,
                PgActions.UPDATE: self.on_update,
                PgActions.DELETE: self.on_delete,
            }
            item = await self.converter(entity)
            func = dispatch.get(payload.action)
            if func is None:
                log.error(f"Unmapped entity {payload.entity} action {payload.action}")
                return
            await func(entity, item)


    @abstractmethod
    async def on_insert(self, entity: Entity_T, item: Optional[Item_T]) -> None:
        ...

    @abstractmethod
    async def on_update(self, entity: Entity_T, item: Optional[Item_T]) -> None:
        ...

    @abstractmethod
    async def on_delete(self, entity: Entity_T, item: Optional[Item_T]) -> None:
        ...

    @abstractmethod
    async def populate_cache(self) -> None:
        ...


class ManyToOneCache(PgListenerCache[Dict[int, List[Item_T]], Entity_T, Item_T], Generic[Entity_T, Item_T], ABC):

    def __init__(self,
                 converter: Callable[[Entity_T], Awaitable[Optional[Item_T]]],
                 fetcher: Callable,
                 event_type: Type):
        super(ManyToOneCache, self).__init__(converter, fetcher, event_type)
        self.item = {}

    def remove_item_from_cache(self, id: int, item: Item_T) -> None:
        if id not in self.item.keys():
            return
        seq = self.item[id]
        self.item[id] = [o for o in seq if o != item]

    def add_item_to_cache(self, id: int, item: Item_T) -> None:
        if id not in self.item.keys():
            self.item[id] = []
        self.item[id].append(item)


class DiscordGuildRelation(Protocol):
    guild_id: int


class DiscordEntityManyCache(ManyToOneCache[DiscordGuildRelation, Item_T], Generic[Item_T]):

    async def on_insert(self, entity: DiscordGuildRelation, item: Optional[Item_T]) -> None:
        if item is not None:
            self.add_item_to_cache(entity.guild_id, item)

    async def on_update(self, entity: DiscordGuildRelation, item: Optional[Item_T]) -> None:
        if item is not None:
            self.remove_item_from_cache(entity.guild_id, item)
            self.add_item_to_cache(entity.guild_id, item)

    async def on_delete(self, entity: DiscordGuildRelation, item: Optional[Item_T]) -> None:
        if item is not None:
            self.remove_item_from_cache(entity.guild_id, item)

    async def populate_cache(self):
        items = await self.fetcher()
        for item in items:
            if iscoroutinefunction(self.converter):
                converted_item = await self.converter(item)
            else:
                converted_item = self.converter(item)
            if converted_item:
                self.add_item_to_cache(item.guild_id, converted_item)


class SingleEntityCache(PgListenerCache[Dict[int, Entity_T], Entity_T, Item_T], Generic[Entity_T, Item_T], ABC):

    def __init__(self,
                 converter: Callable[[Entity_T], Awaitable[Optional[Item_T]]],
                 fetcher: Callable,
                 event_type: Type):
        super(SingleEntityCache, self).__init__(converter, fetcher, event_type)
        self.item = {}

    def add_item_to_cache(self, id: int, item: Item_T) -> None:
        self.item[id] = item

    def remove_item_from_cache(self, id: int) -> None:
        if id in self.item.keys():
            del self.item[id]


class DiscordEntityCache(SingleEntityCache[DiscordGuildRelation, Item_T], Generic[Item_T]):

    async def on_insert(self, entity: DiscordGuildRelation, item: Optional[Item_T]) -> None:
        if item is not None:
            self.add_item_to_cache(entity.guild_id, item)

    async def on_update(self, entity: DiscordGuildRelation, item: Optional[Item_T]) -> None:
        if item is not None:
            self.remove_item_from_cache(entity.guild_id)
            self.add_item_to_cache(entity.guild_id, item)

    async def on_delete(self, entity: DiscordGuildRelation, item: Optional[Item_T]) -> None:
        if item is not None:
            self.remove_item_from_cache(entity.guild_id)

    async def populate_cache(self):
        items = await self.fetcher()
        for item in items:
            if iscoroutinefunction(self.converter):
                converted_item = await self.converter(item)
            else:
                converted_item = self.converter(item)
            if item:
                self.add_item_to_cache(item.guild_id, converted_item)