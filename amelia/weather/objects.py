from datetime import datetime
from decimal import Decimal
from typing import NamedTuple, List, Dict, Any, Optional
from pydantic.dataclasses import dataclass


class FlightRule(NamedTuple):
    emoji: str
    name: str

    @classmethod
    def create(self, rule: str):
        """
        Returns a Named Tuple based on the flight rules. Right now this
        tuple just contains an emoji and the name, but could be expanded later.

        Parameters
        ----------
        rule

        Returns
        -------
        FlightRule -> Tuple[str, str]
        """
        formats = {
            "VFR": FlightRule(":green_circle:", "VFR"),
            "IFR": FlightRule(":red_circle:", "IFR"),
            "MVFR": FlightRule(":blue_circle:", "MVFR"),
            "LIFR": FlightRule(":purple_circle:", "LIFR")

        }
        return formats.get(rule.upper(), FlightRule(":black_circle:", rule))


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
