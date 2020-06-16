import os
import aiohttp
import asyncio
import typing
import logging
from datetime import datetime, timezone
log = logging.getLogger(__name__)

SunRiseSetResponse = typing.Optional[typing.Dict[str, typing.Any]]

class SunRiseSetInvalidException(Exception):
    pass

class SunRiseSet:
    """
    Simple Mixin that will allow a Discord COG to take advantage of Sunrise/Set API

    """

    def __init__(self):
        super(SunRiseSet, self).__init__()
        _token = os.environ['AVWX_TOKEN']
        self.sunrise_api_url = 'https://api.sunrise-sunset.org/json'
        self.sunrise_headers = {
            'Content-Type': 'application/json',
        }
        self.sunrise_session = aiohttp.ClientSession(
            headers=self.sunrise_headers,
            loop=asyncio.get_event_loop()
        )

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
        try:
            session = self.sunrise_session if session is None else session
            url = "{0}{1}".format(self.sunrise_api_url, target)
            response = await session.get(url, **kwargs)
            status = response.status
            result = await response.json()
            log.debug(f"FETCH {status}: {url} - {result}")
            if result is None:
                raise SunRiseSetInvalidException
            return result
        except aiohttp.ClientResponseError as e:
            log.error(e)
            raise

    async def fetch_sun_rise_set(self, lat: int, long: int, valid_date: datetime = datetime.now(timezone.utc)):
        date_str = valid_date.strftime("%Y-%m-%d")
        target = f'?lat={lat}&lng={long}&date={date_str}&formatted=0'
        data = await self._sunriseset_fetch(target)
        if data['status'] != 'OK':
            raise SunRiseSetInvalidException(data['status'])
        return data['results']

