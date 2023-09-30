import re
from typing import Dict, Any, Optional, List

import discord
from discord import app_commands, Interaction
from discord.ext import commands

from src.auto_choices import DependentFuzzyChoicesCache, AutoCompleteItem, FuzzyChoicesCache
from src.bot import AmeliaBot
import logging

from src.features.facility.services import plate_to_image_bytes, all_plates_embed
from src.tfl import TFLService
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

    async def _plate_name_autocomplete(self, itx: Interaction, current: str) -> list[app_commands.Choice]:
        options = itx.data and itx.data.get('options')
        if options is None:
            log.error("Could not retrieve interaction options for FAA Plate autocomplete")
            return []
        icao_arg = self.get_command_argument(options, name='icao') #type: ignore
        if icao_arg is None or not isinstance(icao_arg, dict):
            log.error("Could not retrieve current icao text for FAA Plate autocomplete")
            return []
        icao_value = icao_arg.get('value')
        icao_value = str(icao_value) if icao_value is not None else ''
        choices = await self.plate_name_cache.retrieve(itx.user.id, icao_value, current)
        log.debug(choices)
        return choices or []

    async def _icao_autocomplete(self, _: Interaction, current: str):
        choices = await self.icao_cache.retrieve(current)
        return choices or []

    async def _fetch_plates(self, icao: str) -> AutoCompleteItem:
        tfl = TFLService()
        airport = await tfl.fetch_airport(icao)
        choices = [app_commands.Choice(**{'name': p.name, 'value': p.name}) for p in airport.plates]
        return AutoCompleteItem(
            param_value=icao.lower(),
            choices_cache=choices
        )
    async def _fetch_plate_icaos(self) -> list[str]:
        tfl = TFLService()
        icaos = await tfl.plates.all(icao_only=True)
        return icaos #type: ignore  bad design from tfl

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
            if embed.description and len(embed.description) > 4000:
                return itx.followup.send("The result is too large to display at this time.")
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
    async def plate_cmd_error(self, itx: Interaction, error: app_commands.AppCommandError):
        original_error = error.original if isinstance(error, app_commands.errors.CommandInvokeError) else error
        if isinstance(original_error, IndexError):
            embed = discord.Embed(
                title="Plate not Found", 
                description="Could not find that plate. This function only works with U.S. based plates"
                )
            await itx.response.send_message(embed=embed, ephemeral=True)
        else:
            await itx.response.send_message("Unable to retrieve plate.", ephemeral=True)
            raise error




def sanitize_plate_name(value: str):
    value = str(re.sub(RE_COMMON_TERMS, ' ', value))
    return value

async def setup(bot):
    await bot.add_cog(PlatesCog(bot))