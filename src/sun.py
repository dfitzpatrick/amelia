from decimal import Decimal

import aiohttp
import typing
import logging
from datetime import datetime, timezone
log = logging.getLogger(__name__)

SunRiseSetResponse = typing.Optional[typing.Dict[str, typing.Any]]

class SunRiseSetInvalidException(Exception):
    pass


class SunService:
    """
    Simple Mixin that will allow a Discord COG to take advantage of Sunrise/Set API

    """

    def __init__(self):
        super(SunService, self).__init__()
        self.sunrise_api_url = 'https://api.sunrise-sunset.org/json'
        self.sunrise_headers = {
            'Content-Type': 'application/json',
        }


    async def _sunriseset_fetch(self, target, session=None, **kwargs) -> SunRiseSetResponse:
        """
        Get Sun Rise and Set Data
        Parameters
        ----------
        target: The api endpoint you wish to target
        session: The aiohttp.ClientSession
        kwargs

        Returns
        -------
        AvwxResponse JSON
        """
        async with aiohttp.ClientSession(headers=self.sunrise_headers) as session:
            try:
                url = "{0}{1}".format(self.sunrise_api_url, target)
                async with session.get(url, **kwargs) as response:
                    status = response.status
                    result = await response.json()
                    log.debug(f"FETCH {status}: {url} - {result}")
                    if result is None:
                        raise SunRiseSetInvalidException
                    return result
            except aiohttp.ClientResponseError as e:
                log.error(e)

    async def fetch_sun_rise_set(self, lat: Decimal, long: Decimal, valid_date: datetime = datetime.now(timezone.utc)):
        date_str = valid_date.strftime("%Y-%m-%d")
        target = f'?lat={lat}&lng={long}&date={date_str}&formatted=0'
        data = await self._sunriseset_fetch(target)
        if data is not None:
            if data['status'] != 'OK':
                raise SunRiseSetInvalidException(data['status'])
            return data['results']

