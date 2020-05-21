import asyncio
import logging
import os
import typing

import aiohttp

log = logging.getLogger(__name__)

AvwxResponse = typing.Optional[typing.Dict[str, typing.Any]]

class AVWX:
    """
    Simple Mixin that will allow a Discord COG to take advantage of AVWX API
    Calls for METAR/TAF
    """

    def __init__(self):
        super(AVWX, self).__init__()
        _token = os.environ['AVWX_TOKEN']
        self.api_url = 'https://avwx.rest/api'
        self.avx_headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {_token}'
        }
        self.avwx_session = aiohttp.ClientSession(
            headers=self.avx_headers,
            loop=asyncio.get_event_loop()
        )

    async def _avwx_fetch(self, target, session=None, **kwargs) -> AvwxResponse:
        """
        Base GET request for the AVWX endpoints and just some flexibility if we
        need to change sessions at a later date.
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
            session = self.avwx_session if session is None else session
            url = "{0}{1}".format(self.api_url, target)
            response = await session.get(url, **kwargs)
            status = response.status
            result = await response.json()
            log.debug(f"FETCH {status}: {url} - {result}")
            return result
        except aiohttp.ClientResponseError as e:
            log.error(e)


    async def fetch_metar(self, icao: str) -> AvwxResponse:
        """
        Fetches a METAR from the AVWX api
        Parameters
        ----------
        icao: the icao code of the airport to fetch

        Returns
        -------
        AvwxResponse JSON
        """
        target = f'/metar/{icao}?options=translate'
        return await self._avwx_fetch(target)
