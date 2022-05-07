import logging
from typing import Dict, Any

import aiohttp
from dateutil import parser

from amelia.weather.objects import MetarDTO, TafDTO, AirportDTO

log = logging.getLogger(__name__)


class StationHasNoDataError(Exception):
    pass




class TFLService:

    def __init__(self, loop=None):
        self.api_url = 'http://theflying.life/api/v1'
        self.headers = {}

    async def _request(self, target, session=None, **kwargs) -> Dict[str, Any]:
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                url = "{0}{1}".format(self.api_url, target)
                async with session.get(url, **kwargs) as response:
                    status = response.status
                    result = await response.json()
                    log.debug(f"FETCH {status}: {url}")
                    log.debug(result)
                    return result
        except aiohttp.ClientResponseError as e:
            log.error(e)
            raise

    async def fetch_metar(self, icao: str) -> MetarDTO:
        target = f'/metar/{icao}'
        r = await self._request(target)
        if r is None:
            raise StationHasNoDataError
        return MetarDTO(
            icao=r['station_id'],
            valid=parser.parse(r['time']),
            flight_rule=r['flight_rule']['code'],
            wind=r['wind']['text'],
            visibility=r['visibility']['text'],
            clouds=[sc['text'] for sc in r['sky_condition']],
            temp=r['temperature']['text'],
            dewpoint=r['dewpoint']['text'],
            altimeter=r['altimeter']['text'],
            raw_text=r['raw_text'],
            weather=[wx['text'] for wx in r['wx_codes']],
            remarks=[f"{rmk['code']} - {rmk['text']}" for rmk in r['remarks']],
            last_polling_succeeded=r['last_polling_succeeded']
        )

    async def fetch_taf(self, icao: str) -> TafDTO:
        target = f'/taf/{icao}'
        r = await self._request(target)
        if r is None:
            raise StationHasNoDataError
        return TafDTO(
            valid_from=parser.parse(r['valid_from']),
            valid_to=parser.parse(r['valid_to']),
            raw_text=r['raw_text'],
            station_id=r['station_id'],
            issue_time=parser.parse(r['issue_time']),
            bulletin_time=parser.parse(r['bulletin_time']),
            location=r['location'],
            forecasts=r['forecasts'],
            last_polling_succeeded=r['last_polling_succeeded']
        )

    async def fetch_airport(self, icao: str) -> AirportDTO:
        target = f'/airport/{icao}'
        r = await self._request(target)
        if r is None:
            raise StationHasNoDataError
        return AirportDTO(**r)


