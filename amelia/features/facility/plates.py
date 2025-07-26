import re
from typing import Dict, Any, Optional, List

import discord
from discord import app_commands, Interaction
from discord.ext import commands

from amelia.auto_choices import DependentFuzzyChoicesCache, AutoCompleteItem, FuzzyChoicesCache
from amelia.bot import AmeliaBot
import logging

from .services import plate_to_image_bytes, all_plates_embed
from io import BytesIO
from amelia.tfl import TFLService, NoChartSupplementError
log = logging.getLogger(__name__)
RE_COMMON_TERMS = re.compile(r"\s(runway|rwy|or)\s")
from zipfile import ZipFile
from pdf2image import convert_from_bytes

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
        try:
            icao_value = itx.namespace.icao
            icao_value = str(icao_value) if icao_value is not None else ''
            choices = await self.plate_name_cache.retrieve(itx.user.id, icao_value, current)
            return choices or []

        except AttributeError:
            log.error("Could not retrieve current icao text for FAA Plate autocomplete")
            return []
        
        
    async def _icao_autocomplete(self, _: Interaction, current: str):
        log.debug("in icao auto")
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
        if plate_name is None:
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


class ChartSupplementCOG(commands.Cog):
    def __init__(self, bot: AmeliaBot):
        self.bot = bot

    @app_commands.command(name='chart-supplement')
    @app_commands.describe(icao="Airport ICAO")
    async def chart_supplment(self, itx: Interaction, icao: str):

        tfl = TFLService()
        icao = icao.lower()

        response = await tfl.fetch_chart_supplement(icao)
        if not response:
            response = await tfl.fetch_chart_supplement(icao[1::])
        if not response:
            raise NoChartSupplementError
        await itx.response.defer()
        image_objs = zip_pdfs_to_image(response)
        discord_files = [discord.File(img, filename=f"{icao}_{idx}.png") for idx, img in enumerate(image_objs)]
        await itx.followup.send(f"Chart Supplement for {icao.upper()}", files=discord_files)


    @chart_supplment.error
    async def chart_cmd_error(self, itx: Interaction, error: app_commands.AppCommandError):
        original_error = error.original if isinstance(error, app_commands.errors.CommandInvokeError) else error
        if isinstance(original_error, NoChartSupplementError):
            embed = discord.Embed(
                title="No Chart Supplement Found", 
                description="We could not find the chart supplement for this airport"
                )
            await itx.response.send_message(embed=embed, ephemeral=True)
        else:
            await itx.response.send_message("Unable to retrieve chart supplement.", ephemeral=True)
            raise error

def zip_pdfs_to_image(zip_obj: BytesIO) -> BytesIO:
    image_objs = []
    log.info("Getting Zip File")
    with ZipFile(zip_obj) as zf:
        for member in zf.namelist():
            log.info("Processing image")
            with zf.open(member) as page:
                image = convert_from_bytes(page.read(), first_page=1, last_page=1)[0]
                image_bytes = BytesIO()
                image.save(image_bytes, format='PNG')
                image_bytes.seek(0)
                image_objs.append(image_bytes)
    
    return image_objs
    
async def setup(bot):
    await bot.add_cog(PlatesCog(bot))
    await bot.add_cog(ChartSupplementCOG(bot))