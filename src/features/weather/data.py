from datetime import datetime
from typing import Optional, List

import asyncpg
from pydantic import BaseModel, Field


class MetarConfigSchema(BaseModel):
    id: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    restrict_channel: bool = True
    delete_interval: int = 5
    guild_id: int

class WeatherRepository:

    def __init__(self, session: asyncpg.Connection):
        self.session = session


    async def metar_configurations(self, guild_id: int) -> List[MetarConfigSchema]:
        q = """select * from metarconfig;"""
        results = await self.session.fetch(q)
        return [MetarConfigSchema(**entity) for entity in results]



