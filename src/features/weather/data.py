from datetime import datetime
from typing import Optional
from src.instances import db
import asyncpg
from pydantic import BaseModel, Field

from src.cache import FunctionOperationsCache

import logging
log = logging.getLogger(__name__)


class WeatherConfigSchema(BaseModel):
    id: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    restrict_channel: bool = True
    delete_interval: int = 5
    guild_id: int

class AllowedChannel(BaseModel):
    id: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    guild_id: int
    channel_id: int

config_cache = FunctionOperationsCache[WeatherConfigSchema]('id')

async def database_change_notify(_: str, action: str, _id: int):
    if action == "DELETE" or action == "UPDATE":
        # only invalidate strategy
        config_cache.invalidate_function_cache_object(_id)


db.register_listener(database_change_notify, tables=['metarconfig', 'tafconfig', 'stationconfig'])

class WeatherDataContext:

    def __init__(self, session: asyncpg.Connection):
        self.session = session


    async def _create_or_update_configuration(self, table: str, schema: WeatherConfigSchema) -> WeatherConfigSchema:
        q = f"""
      insert into {table} (guild_id, restrict_channel, delete_interval)
      values ($1, $2, $3)

      on conflict (guild_id)
      do update set guild_id = $1, restrict_channel = $2, delete_interval = $3
      returning id, created_at, updated_at;
      """
        result = await self.session.fetchrow(q,
            schema.guild_id, schema.restrict_channel, schema.delete_interval
        )
        values = schema.model_dump()
        values.update(**(result or {}))
        return WeatherConfigSchema(**values)
    
    async def _create_channel(self, table: str, schema: AllowedChannel) -> AllowedChannel:
        q = f"insert into {table} (guild_id, channel_id) values ($1, $2) returning *"
        result = await self.session.fetchrow(q, schema.guild_id, schema.channel_id)
        return AllowedChannel(**result) # type: ignore


    async def create_or_update_metar_configuration(self, schema: WeatherConfigSchema) -> WeatherConfigSchema:
         return await self._create_or_update_configuration("metarconfig", schema)
    
    async def create_or_update_taf_configuration(self, schema: WeatherConfigSchema) -> WeatherConfigSchema:
         return await self._create_or_update_configuration("tafconfig", schema)
    
    async def create_or_update_station_configuration(self, schema: WeatherConfigSchema) -> WeatherConfigSchema:
         return await self._create_or_update_configuration("stationconfig", schema)

    async def _fetch_config_table(self, table: str, guild_id: int) -> Optional[WeatherConfigSchema]:
        q = f"""select * from {table} where guild_id = $1;"""
        result = await self.session.fetchrow(q, guild_id)
        log.info(q)
        log.info(result)
        if result is None:
            return None
        return WeatherConfigSchema(**result)

    async def _get_allowed_channels(self, table: str, guild_id: int) -> list[AllowedChannel]:
         q = f"select * from {table} where guild_id = $1;"
         results = await self.session.fetch(q, guild_id)
         return [AllowedChannel(**r) for r in results]
         
    async def _remove_allowed_channel(self, table: str, channel_id: int) -> None:
         q = f"delete from {table} where channel_id = $1;"
         await self.session.execute(q, channel_id)

    @config_cache.function(class_level=True)
    async def fetch_metar_configuration(self, guild_id: int) -> Optional[WeatherConfigSchema]:
            return await self._fetch_config_table("metarconfig", guild_id)
    
    @config_cache.function(class_level=True)
    async def fetch_taf_configuration(self, guild_id: int) -> Optional[WeatherConfigSchema]:
            return await self._fetch_config_table("tafconfig", guild_id)

    @config_cache.function(class_level=True)
    async def fetch_station_configuration(self, guild_id: int) -> Optional[WeatherConfigSchema]:
            return await self._fetch_config_table("stationconfig", guild_id)
    
    @config_cache.function(class_level=True)
    async def fetch_metar_channels(self, guild_id: int):
         return await self._get_allowed_channels("metarchannel", guild_id)
    
    @config_cache.function(class_level=True)
    async def fetch_taf_channels(self, guild_id: int):
         return await self._get_allowed_channels("tafchannel", guild_id)

    @config_cache.function(class_level=True)
    async def fetch_station_channels(self, guild_id: int):
         return await self._get_allowed_channels("stationchannel", guild_id)
    
    async def create_metar_channel(self, schema: AllowedChannel) -> AllowedChannel:
         schema = await self._create_channel('metarchannel', schema)
         return schema
    
    async def create_taf_channel(self, schema: AllowedChannel) -> AllowedChannel:
         schema = await self._create_channel('tafchannel', schema)
         return schema
    
    async def create_station_channel(self, schema: AllowedChannel) -> AllowedChannel:
         schema = await self._create_channel('stationchannel', schema)
         return schema
    
    async def remove_metar_channel(self, channel_id: int) -> None:
         return await self._remove_allowed_channel("metarchannel", channel_id)
    
    async def remove_taf_channel(self, channel_id: int) -> None:
         return await self._remove_allowed_channel("tafchannel", channel_id)
    
    async def remove_station_channel(self, channel_id: int) -> None:
         return await self._remove_allowed_channel("stationchannel", channel_id)