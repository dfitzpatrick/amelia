import logging
from typing import Optional, List, TYPE_CHECKING
from amelia.instances import db
from .schema import AutoRoleSchema
from amelia.cache import FunctionOperationsCache
import asyncpg
if TYPE_CHECKING:
    from asyncpg import Record
log = logging.getLogger(__name__)

cache = FunctionOperationsCache[AutoRoleSchema]('id')


async def database_change_notify(_: str, action: str, _id: int):
    if action == "DELETE":
        cache.invalidate(_id)
        cache.invalidate_function_cache_object(_id)
        log.debug(f"auto role cache item invalidated for {_id}")
    if action == "UPDATE":
        async with db as session:
            o = await session.auto_roles.get_auto_role(_id)
        if o is  None:
            return
        cache.put(_id, o)
        cache.update_function_cache_object(o)
        log.debug(f"auto role cache item updated for {_id}")

db.register_listener(database_change_notify, tables=['autorole'])


class AutoRoleDataContext:

    def __init__(self, session: asyncpg.Connection):
        self.session = session

    async def add_auto_role(self, guild_id: int, role_id: int) -> AutoRoleSchema:
        q = "insert into autorole (guild_id, role_id) values ($1, $2) returning *"
        result: Record = await self.session.fetchrow(q, guild_id, role_id)  # type: ignore
        return AutoRoleSchema(**result)
        
    async def remove_auto_role(self, role_id: int):
        q = "delete from autorole where role_id = $1;"
        await self.session.execute(q, role_id)


    async def all_auto_roles(self) -> List[AutoRoleSchema]:
        q = "select * from autorole;"
        results = await self.session.fetch(q)
        return [AutoRoleSchema(**r) for r in results]


    async def guild_auto_roles(self, guild_id: int) -> List[AutoRoleSchema]:
        q = "select * from autorole where guild_id = $1;"
        results = await self.session.fetch(q, guild_id)
        return [AutoRoleSchema(**r) for r in results]


    async def get_auto_role(self, _id: int) -> Optional[AutoRoleSchema]:
        q = "select * from autorole where id = $1;"
        result = await self.session.fetchrow(q, _id)
        if result is None:
            return None    
        return AutoRoleSchema(**result)
    