import asyncpg

class ForumChannelDataContext:

    def __init__(self, session: asyncpg.Connection):
        self.session = session

    async def create_auto_pin(self, guild_id: int, channel_id: int) -> None:
        q = "insert into autopins (guild_id, parent_id) values ($1, $2);"
        await self.session.execute(q, guild_id, channel_id)
    
    async def delete_auto_pin(self, channel_id: int) -> None:
        q = "delete from autopins where parent_id = $1;"
        await self.session.execute(q, channel_id)
    
    async def has_auto_pin(self, channel_id: int) -> bool:
        q = "select count(id) from autopins where parent_id = $1;"
        count = await self.session.fetchval(q, channel_id)
        return count > 0