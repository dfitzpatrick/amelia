import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, List, Optional

import aiohttp
from dateutil import parser
from urllib.parse import urlencode
log = logging.getLogger(__name__)
from io import BytesIO

import os

class StationHasNoDataError(Exception):
    pass

class NoChartSupplementError(Exception):
    pass

@dataclass
class MetarDTO:
    icao: str
    valid: datetime
    flight_rule: str
    wind: str
    visibility: str
    clouds: List[str]
    temp: str
    dewpoint: str
    altimeter: str
    raw_text: str
    weather: List[str]
    remarks: List[str]
    last_polling_succeeded: bool


@dataclass
class Forecast:
    valid_from: datetime
    valid_to: datetime
    sky_condition: List[Dict[str, Any]]
    wind: Dict[str, Any]
    visibility: Dict[str, Any]
    ceilings: List[int]
    flight_rules: str
    wx_codes: List[Dict[str, Any]]
    text: str
    time_becoming: Optional[str] = None

@dataclass
class TafDTO:
    valid_from: datetime
    valid_to: datetime
    raw_text: str
    station_id: str
    issue_time: datetime
    bulletin_time: datetime
    location: Dict[str, Decimal]
    forecasts: List[Forecast]
    last_polling_succeeded: bool

@dataclass
class Runway:
    bearing1: Optional[Decimal]
    bearing2: Optional[Decimal]
    ident1: str
    ident2: str
    length_ft: int
    lights: bool
    surface: Optional[str]
    width_ft: int
    text: str

@dataclass
class FAAPlate:
    tpp_cycle: int
    icao: str
    code: str
    name: str
    pdf_name: str
    plate_url: str

@dataclass
class AirportDTO:
    city: Optional[str]
    country: str
    elevation_ft: Optional[int]
    elevation_m: Optional[int]
    iata: Optional[str]
    icao: str
    latitude: Decimal
    longitude: Decimal
    name: str
    note: Optional[str]
    reporting: bool
    runways: Optional[List[Runway]]
    state: Optional[str]
    type: str
    website: Optional[str]
    wiki: Optional[str]
    plates: List[FAAPlate]


class TFLService:

    def __init__(self, loop=None):
        self.api_url = os.environ.get('TFL_API', 'http://api.theflying.life/api/v1')
        self.headers = {}
        self.plates = Plates(self._request)

    async def _request(self, target, session=None, **kwargs) -> Dict[str, Any]:
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                url = "{0}{1}".format(self.api_url, target)
                async with session.get(url, **kwargs) as response:
                    status = response.status
                    result = await response.json()
                    log.debug(f"FETCH {status}: {url}")
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
            forecasts=[Forecast(**f) for f in r['forecasts']],
            last_polling_succeeded=r['last_polling_succeeded']
        )

    async def fetch_airport(self, icao: str) -> AirportDTO:
        target = f'/airport/{icao}'
        r = await self._request(target)
        if r is None:
            raise StationHasNoDataError
        plates = [FAAPlate(**p) for p in r['plates']]
        del r['plates']
        return AirportDTO(**r, plates=plates)
    
    async def fetch_chart_supplement(self, icao: str) -> BytesIO | None:
        log.info("In chart supplement")
        target = f'/dcs/{icao}'
        async with aiohttp.ClientSession(headers=self.headers) as session:
            url = "{0}{1}".format(self.api_url, target)
            log.info(f"Calling: {url}")
            async with session.get(url) as response:
                if response.content_type != "application/x-zip-compressed":
                    return
                data = await response.read()
                data = BytesIO(data)
                return data


class Plates:
    def __init__(self, req):
        self.req = req

    async def all(self, **kwargs) -> list[FAAPlate] | list[str]:
        qs = urlencode(kwargs)
        target = f'/plates/?{qs}'
        resp = await self.req(target)
        log.debug(resp)
        if resp is None:
            raise StationHasNoDataError
        try:
            return [FAAPlate(**r) for r in resp]
        except TypeError:
            return resp

    async def by_icao(self, icao: str, **kwargs) -> list[FAAPlate]:
        qs = urlencode(kwargs)
        target = f'/plates/{icao}?{qs}'
        resp = await self.req(target)
        if resp is None:
            raise StationHasNoDataError
        return [FAAPlate(**r) for r in resp]

