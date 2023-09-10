import logging
from typing import Optional, List
from amelia.instances import db
from amelia.features.autorole.cache import AutoRoleCacheAdapter
from amelia.features.autorole.schema import AutoRoleSchema
from amelia.cache import FunctionOperationsCache
import asyncpg
log = logging.getLogger(__name__)

cache = FunctionOperationsCache[AutoRoleSchema]('id')
async def database_change_notify(table: str, action: str, id: int):

    if action == "DELETE":
        cache.invalidate(id)
        cache.invalidate_function_cache_object(id)
        log.debug(f"autorole cache item invalidated for {id}")
    if action == "UPDATE":
        async with db as session:
            o = await session.auto_roles.get_auto_role(id)
            cache.put(id)
            cache.update_function_cache_object(o)
        log.debug(f"autorole cache item updated for {id}")

db.register_listener(database_change_notify, tables=['autorole'])
class AutoRoleDataContext:

    def __init__(self, session: asyncpg.Connection):
        self.session = session

    async def add_auto_role(self, guild_id: int, role_id: int) -> AutoRoleSchema:
        q = "insert into autorole (guild_id, role_id) values ($1, $2) returning *"
        result = await self.session.fetchrow(q, guild_id, role_id)
        return AutoRoleSchema(**result)


    async def remove_auto_role(self, role_id: int):
        q = "delete from autorole where role_id = $1;"
        await self.session.execute(q, role_id)

    @cache.function()
    async def all_auto_roles(self) -> List[AutoRoleSchema]:
        q = "select * from autorole;"
        results = await self.session.fetch(q)
        return [AutoRoleSchema(**r) for r in results]

    @cache.function()
    async def get_auto_role(self, id: int) -> Optional[AutoRoleSchema]:
        q = "select * from autorole where id = $1;"
        result = await self.session.fetchrow(q, id)
        if result is None:
            return
        return AutoRoleSchema(**result)

