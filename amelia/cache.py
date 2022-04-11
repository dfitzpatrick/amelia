from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Type, Dict, List, Callable, Optional, Awaitable, Protocol
from inspect import iscoroutinefunction
from ameliapg import PgActions
from ameliapg.models import PgNotify

log = logging.getLogger(__name__)


Container_T = TypeVar("Container_T")
Entity_T = TypeVar("Entity_T")
Item_T = TypeVar("Item_T")


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