import re
from io import BytesIO
from typing import Dict, Any, Optional, List

import aiohttp
import discord
from discord import app_commands, Interaction
from discord.app_commands import Choice
from discord.ext import commands
from pdf2image import convert_from_bytes


from amelia.auto_choices import DependentFuzzyChoicesCache, AutoCompleteItem, FuzzyChoicesCache
from amelia.bot import AmeliaBot
import logging

from amelia.facility.services import plate_to_image_bytes, all_plates_embed
from amelia.pagination import LongDescriptionPaginator
from amelia.tfl import TFLService, FAAPlate

log = logging.getLogger(__name__)
RE_COMMON_TERMS = re.compile(r"\s(runway|rwy|or)\s")

class PlatesCog(commands.Cog):

    def __init__(self, bot: AmeliaBot):
        self.bot = bot
        self.icao_cache = FuzzyChoicesCache(
            fetch_method=self._fetch_plate_icaos,
            threshold=7
        )
        self.plate_name_cache = DependentFuzzyChoicesCache(
            fetch_method=self._fetch_plates,
            sanitizer=sanitize_plate_name,
            threshold=7
        )


    @staticmethod
    def get_command_argument(options: List[Dict[str, Any]], name: str) -> Optional[Dict[str, Any]]:
        for o in options:
            if o['name'] == name:
                return o

    async def _plate_name_autocomplete(self, itx: Interaction, current: str):
        icao_arg = self.get_command_argument(itx.data['options'], name='icao')
        icao_value = (icao_arg and icao_arg.get('value')) or ''
        choices = await self.plate_name_cache.retrieve(itx.user.id, icao_value, current)
        log.debug(choices)
        return choices or []

    async def _icao_autocomplete(self, _: Interaction, current: str):
        choices = await self.icao_cache.retrieve(current)
        return choices or []

    async def _fetch_plates(self, icao: str) -> AutoCompleteItem:
        tfl = TFLService()
        airport = await tfl.fetch_airport(icao)
        plates = [FAAPlate(**p) for p in airport.plates]
        choices = [app_commands.Choice(**{'name': p.name, 'value': p.name}) for p in plates]
        return AutoCompleteItem(
            param_value=icao.lower(),
            choices_cache=choices
        )
    async def _fetch_plate_icaos(self):
        tfl = TFLService()
        icaos = await tfl.plates.all(icao_only=True)
        return icaos

    @app_commands.command(name='plates')
    @app_commands.autocomplete(plate_name=_plate_name_autocomplete)
    @app_commands.autocomplete(icao=_icao_autocomplete)
    async def plate_cmd(self, itx: Interaction, icao: str, plate_name: Optional[str]):
        if plate_name is  None:
            plates = await self.bot.tfl.plates.by_icao(icao)
            if not plates:
                await itx.response.send_message(f"No plates for {icao}", ephemeral=True)
                return
            embed = all_plates_embed(icao, plates)
            if len(embed.description) > 4000:
                content = "The result is too large to display in one embed. Please click the Start Button to allow pagination."
                await itx.response.send_message(
                    content=content,
                    view=await LongDescriptionPaginator(itx.client, itx.user, embed.title, embed.description, 2000).run()
                )
            else:
                await itx.response.send_message(embed=embed)
            return
        await itx.response.defer()
        plates = await self.bot.tfl.plates.by_icao(icao, name=plate_name)
        plate = plates[0]
        image_bytes = await plate_to_image_bytes(plate)
        fn = f"{icao.upper()}_{plate_name}.png"
        discord_file = discord.File(image_bytes, filename=fn.replace(' ', '_'))
        await itx.followup.send(f"Full Plate: {plate.plate_url}", file=discord_file)

    @plate_cmd.error
    async def plate_cmd_error(self, itx: Interaction, error: commands.CommandInvokeError):
        original_error = error.original
        if isinstance(original_error, IndexError):
            embed = discord.Embed(title="Plate not Found", description="Could not find that plate. This function only works with U.S. based plates")
            await itx.response.send(embed=embed, ephemeral=True)
        else:
            await itx.response.send_message("Unable to retrieve plate.", ephemeral=True)
            raise error




def sanitize_plate_name(value: str):
    value = str(re.sub(RE_COMMON_TERMS, ' ', value))
    return value

async def setup(bot):
    await bot.add_cog(PlatesCog(bot))