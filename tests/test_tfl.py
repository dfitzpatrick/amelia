from amelia.tfl import FAAPlate, TFLService
import pytest

@pytest.mark.asyncio
async def test_fetch_airport_dto():
    tfl = TFLService()
    airport = await tfl.fetch_airport('klgb')
    assert airport.icao.upper() == 'KLGB'
    assert len(airport.plates) > 0
    assert isinstance(airport.plates[0], FAAPlate)
    