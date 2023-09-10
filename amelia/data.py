from __future__ import annotations

import asyncio
import collections
import json
import logging
import pathlib
from contextvars import ContextVar
from typing import Callable, List, Dict, Any, Type, TypeVar, Generic, Optional

import asyncpg
import asyncpg.transaction
import yoyo
from pydantic import BaseModel

log = logging.getLogger(__name__)
ctx_connection = ContextVar("ctx_connection")
ctx_transaction = ContextVar("ctx_transaction")

class UnknownEntity(Exception):
    pass

class PgNotify(BaseModel):
    table: str
    action: str
    id: int


class BaseUOW:
    def __init__(self, connection: asyncpg.Connection):
        self.session = connection

    async def commit(self):
        trans = ctx_transaction.get()
        await trans.commit()

T = TypeVar('T', bound=BaseUOW)

class Pg(Generic[T]):

    @classmethod
    async def from_dsn(cls, dsn: str, uow_cls: Type[T] = BaseUOW, entity_map: Dict[str, Any] = None):
        return cls[T](dsn, uow_cls, entity_map)



    def __init__(self, dsn: str, uow_cls: Type[T] = BaseUOW, entity_map: Dict[str, Any] = None, loop=None):
        self.pool = None
        self.dsn = dsn
        self._conn = None
        self._polling_conn = None
        self.table_listeners: Dict[str, List[Callable]] = {}
        self.global_listeners: List[Callable] = []
        self.entity_map = entity_map or {}
        self.uow_cls: Type[T] = uow_cls

    def migrate(self):
        migrations_folder = str(pathlib.Path(__file__).parents[1] / "migrations")
        print(f"Migrations path: {migrations_folder}")
        migrations = yoyo.read_migrations(migrations_folder)
        print(migrations)
        backend = yoyo.get_backend(self.dsn)
        with backend.lock():
            backend.apply_migrations(backend.to_apply(migrations))

    async def _init_connection(self):
        if self._polling_conn is None or self._polling_conn.is_closed():
            log.debug(f"Connecting to {self.dsn}")
            self._polling_conn = await asyncpg.connect(self.dsn)


    async def start_listening(self):
        await self._init_connection()
        await self._polling_conn.add_listener('events', self._notify)
        log.debug("Pg Service now listening for 'events'")

    async def stop_listening(self):
        if self._conn is not None and not self._conn.is_closed():
            await self._conn.remove_listener('events', self._notify)
            await self._conn.close()

    def register_listener(self, callback: Callable, tables: Optional[List[str]] = None):
        if tables is None:
            self.global_listeners.append(callback)
            return
        for t in tables:
            if t not in self.table_listeners.keys():
                self.table_listeners[t] = []
            self.table_listeners[t].append(callback)

    async def _notify(self, connection: asyncpg.Connection, pid: int, channel: str, payload: str):
        log.debug(f"PG Notify: {payload}")
        payload = json.loads(payload)
        args = (payload['table'], payload['action'], payload['id'])
        for callback in self.table_listeners.get(args[0], []):
            await callback(*args)
        for callback in self.global_listeners:
            await callback(*args)

    async def __aenter__(self) -> T:
        if self.pool is None:
            self.pool = await asyncpg.create_pool(self.dsn)
        self._conn = await self.pool.acquire()
        self._trans = self._conn.transaction()
        await self._trans.start()
        ctx_connection.set(self._conn)
        ctx_transaction.set(self._trans)
        return self.uow_cls(self._conn)

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        conn = ctx_connection.get()
        trans = ctx_transaction.get()
        if exc_type:
            await trans.rollback()
        try:
            await conn.close()
        except:
            pass

class LRUCache:

    def __init__(self, max_size: Optional[int] = 128):
        self.max_size = max_size
        self._cache = collections.OrderedDict()

    def put(self, key: str | int, value: Any):
        self._cache[key] = value
        self._cache.move_to_end(key)
        if self.max_size is not None and len(self._cache) > self.max_size:
            self._cache.popitem(last=False)

    def invalidate(self, key: str | int):
        if key in self._cache.keys():
            del self._cache[key]

    def get(self, key: str | int) -> Optional[Any]:
        if key not in self._cache:
            return
        self._cache.move_to_end(key)
        return self._cache[key]


class PgNotifyCacheStrategy:
    def __init__(self, cache: LRUCache):
        self.cache = cache

    async def notify(self, table: str, action: str, id: int):
        dispatch = {
            "INSERT": self.on_insert,
            "UPDATE": self.on_update,
            "DELETE": self.on_delete
        }
        await dispatch[table](table, action, id)
    async def on_insert(self, table: str, id: int):
        pass
    async def on_update(self, table: str, id: int):
        pass
    async def on_delete(self, table: str, id: int):
        pass

pg = Pg