from __future__ import annotations
from discord.ext import commands
from typing import TYPE_CHECKING
from discord.ext import tasks
from .services import get_classifieds, download_images
import aiohttp
from asyncio import Queue
import discord.utils
from .ui import ClassifiedLayout
import os
import aiofiles
import logging

if TYPE_CHECKING:
    from bot import AmeliaBot
    from discord.app_commands.commands import Group
    from .services import Classified

log = logging.getLogger(__name__)

PARENT_PATH = os.path.dirname(os.path.abspath(__file__))
class Barnstormers(commands.Cog):
    polling_minutes = 15
    polling_url = "https://www.barnstormers.com/listing.php"
    channel_id = os.environ.get('FOR_SALE_CHANNEL', 1020393930342268961)
    marker = PARENT_PATH + "/.marker.txt"
    def __init__(self, bot: AmeliaBot):
        self.bot = bot
        self.config_command: Group | None = None
        self.last_id: int | None = None
        self.queue: Queue[Classified] = Queue()


    async def cog_load(self):
        await self.load_marker()

        self.polling_task.start()
        self.publisher_task.start()

    async def save_marker(self, ad: Classified):
        # This is extremely lazy, but even if corrupted its not a huge deal.
        async with aiofiles.open(self.marker, mode='w') as f:
            await f.write(str(ad.data_id))
    
    async def load_marker(self):
        try:
            async with aiofiles.open(self.marker, mode='r') as f:
                try:
                    data = await f.readline()
                    data = int(data.strip())
                    self.last_id = data
                except ValueError:
                    self.last_id = None
        except FileNotFoundError:
            self.last_id = None
    
    @tasks.loop(seconds=polling_minutes*60, reconnect=True)
    async def polling_task(self):
        async with aiohttp.ClientSession() as session:
            async with session.get(self.polling_url) as response:
                html = await response.text()
                await self.collect_classifieds(html)
    
    async def collect_classifieds(self, html: str):
        classifieds = get_classifieds(html)
        collected: list[Classified] = []
        # collect up to any marker that is found
        for ad in classifieds:
            if ad.data_id == self.last_id:
                break
            collected.append(ad)
        
        # no new ads
        if len(collected) == 0:
            return
        
        # set the first ad as the new marker, reverse to make old to new, and enter into queue
        for ad in reversed(collected):
            await self.queue.put(ad)
        await self.save_marker(collected[0])

    @tasks.loop(seconds=5)
    async def publisher_task(self):
        await self.bot.wait_until_ready()
        ad = await self.queue.get()
        channel = self.bot.get_channel(self.channel_id)
        layout = ClassifiedLayout(ad)
        files = []
        if len(ad.images) > 0:
            # Copy in files and not hotlink, but also protect if barnstormers removes the ad. Keep to max of 10 for MediaGallery
            images = ad.images[:10]
            files = [discord.File(bd, filename=fn) for fn, bd in await download_images(images)]
            log.debug(files)
        await channel.send(view=layout, files=files)
        

