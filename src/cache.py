from __future__ import annotations
import collections
import logging
from typing import TypeVar, Generic, Dict, Optional, Protocol, Any, OrderedDict, \
    TypeAlias
from functools import wraps
import gc
log = logging.getLogger(__name__)


class Indexable(Protocol):
    
    def __getitem__(self, item):
        ...


class Attritable(Protocol):
    def __getattribute__(self, __name: str) -> Any:
        ...
    
    
T = TypeVar("T", bound=Indexable | Attritable)
OneOrManyT: TypeAlias = T | list[T]


class LRUCache(Generic[T]):

    def __init__(self, max_size: Optional[int] = 128):
        self.max_size = max_size
        self._cache: OrderedDict[Any, OneOrManyT] = collections.OrderedDict()
        self.last_function_id: Optional[int] = None

    def put(self, key: str | int, value: OneOrManyT):
        self._cache[key] = value
        self._cache.move_to_end(key)
        if self.max_size is not None and len(self._cache) > self.max_size:
            self._cache.popitem(last=False)

    def invalidate(self, key: str | int):
        if key in self._cache.keys():
            del self._cache[key]

    def get(self, key: str | int) -> Optional[OneOrManyT]:
        if key not in self._cache:
            return None
        self._cache.move_to_end(key)
        return self._cache[key]

    def clear(self):
        self._cache = collections.OrderedDict()
        gc.collect()

    @property
    def cache_ids(self):
        return self._cache.keys()

    def function(self, class_level: bool = False):
        
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                arguments = args[1:] if class_level else args
                key = hash((arguments, frozenset(kwargs.items())))
                item = self._cache.get(key)
                if item is None:
                    log.debug(f'function cache miss detected {key}')
                    item = await func(*args, **kwargs)
                    if item is not None:
                        self.put(key, item)
                else:
                    log.debug(f"cache hit {item} / {key}")
                self.last_function_id = key
                self.post_function_cache(key, item)
                return item
            return wrapper
        return decorator

    def post_function_cache(self, key: int, item: T | list[T]):
        pass


class FunctionOperationsCache(LRUCache[T]):

    def __init__(self, item_identifier_field: str, max_size: int=128):
        super().__init__(max_size=max_size)
        self.object_map: Dict[int, set] = {}
        self._field_name = item_identifier_field

    def _get_identifier(self, obj: T) -> Any:
        value = None
        try:
            value = getattr(obj, self._field_name)
        except AttributeError:
            try:
                value = obj[self._field_name] #type: ignore
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

    def post_function_cache(self, key: int, result_set: OneOrManyT):
        if isinstance(result_set, list):
            self._map_sequence(result_set, key)
        else:
            self._map_scalar(result_set, key)

#TODO: Refactor two functions below as they are very similar.
    def invalidate_function_cache_object(self, field_id: int):
        function_ids = self.object_map.get(field_id, set())
        for fid in function_ids:
            value = self.get(fid)
            if value is None:
                return
            if isinstance(value, list):
                # Loop through and remove only that one object
                for obj in value: # list
                    obj_id = self._get_identifier(obj)
                    if obj_id == field_id:
                        value.remove(obj)
                        self.put(fid, value)
            else:
                self.invalidate(fid)
        if field_id in self.object_map.keys():
            del self.object_map[field_id]

    def update_function_cache_object(self, object: T):
        oid = self._get_identifier(object)
        function_ids = self.object_map.get(oid, set())
        for fid in function_ids:
            value = self.get(fid)
            if value is None:
                return None
            if isinstance(value, list):
                # Loop through and remove only that one object
                for obj in value: # list
                    obj_id = self._get_identifier(obj)
                    if obj_id == oid:
                        idx = value.index(obj)
                        value.remove(obj)
                        value.insert(idx, object)
                        self.put(fid, value)
            else:
                self.put(fid, object)
