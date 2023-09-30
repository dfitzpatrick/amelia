from __future__ import annotations

import json
import logging
import pathlib
from contextvars import ContextVar
from typing import Callable, List, Dict, Any, Type, TypeVar, Generic, Optional, TypedDict
import asyncpg
import asyncpg.transaction
import yoyo

log = logging.getLogger(__name__)
ctx_connection = ContextVar("ctx_connection")
ctx_transaction = ContextVar("ctx_transaction") #gfgfdggdggdgfdfgdg

class UnknownEntity(Exception):
    pass

class PgNotify(TypedDict):
    table: str
    action: str
    id: int


class BaseUOW:
    def __init__(self, connection: asyncpg.Connection[Any] | asyncpg.pool.PoolConnectionProxy[Any]):
        self.session = connection

    async def commit(self):
        trans = ctx_transaction.get()
        await trans.commit()

T = TypeVar('T', bound=BaseUOW)

class Pg(Generic[T]):

    @classmethod
    async def from_dsn(cls, dsn: str, uow_cls: Type[T] = type(BaseUOW)):
        return cls(dsn, uow_cls)



    def __init__(self, dsn: str, uow_cls: Type[T] = type(BaseUOW)):
        self.pool: Optional[asyncpg.Pool] = None
        self.dsn = dsn
        self._conn = None
        self._polling_conn: Optional[asyncpg.Connection] = None
        self.table_listeners: Dict[str, List[Callable]] = {}
        self.global_listeners: List[Callable] = []
        self.uow_cls: Type[T] = uow_cls

    def migrate(self):
        migrations_folder = str(pathlib.Path(__file__).parents[1] / "migrations")
        print(f"Migrations path: {migrations_folder}")
        migrations = yoyo.read_migrations(migrations_folder)
        print(migrations)
        backend = yoyo.get_backend(self.dsn)
        with backend.lock():
            backend.apply_migrations(backend.to_apply(migrations))

    async def _init_connection(self) -> asyncpg.Connection[asyncpg.Record]:
        if self._polling_conn is None or self._polling_conn.is_closed():
            log.debug(f"Connecting to {self.dsn}")
            self._polling_conn = await asyncpg.connect(self.dsn)
        return self._polling_conn


    async def start_listening(self):
        self._polling_conn = await self._init_connection()
        if self._polling_conn is not None:
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

    async def _notify(
            self, 
            connection: asyncpg.Connection[Any] | asyncpg.pool.PoolConnectionProxy[Any], 
            pid: int, 
            channel: str, 
            payload: object):
        
        log.debug(f"PG Notify: {payload}")
        data: PgNotify = json.loads(str(payload))
        args = (data['table'], data['action'], data['id'])
        for callback in self.table_listeners.get(args[0], []):
            await callback(*args)
        for callback in self.global_listeners:
            await callback(*args)

    async def __aenter__(self) -> T:
        if self.pool is None:
            self.pool = await asyncpg.create_pool(self.dsn)
        if self.pool is not None:
            self._conn = await self.pool.acquire()
            if self._conn is None:
                raise asyncpg.ConnectionFailureError
            self._trans = self._conn.transaction()
            await self._trans.start()
            ctx_connection.set(self._conn)
            ctx_transaction.set(self._trans)
        return self.uow_cls(self._conn) #type: ignore

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        conn = ctx_connection.get()
        trans = ctx_transaction.get()
        if exc_type:
            await trans.rollback()
        try:
            await conn.close()
        except Exception:
            pass
