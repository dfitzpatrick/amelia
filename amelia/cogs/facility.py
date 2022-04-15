import textwrap
from math import ceil
from typing import Dict, Any

import discord
from discord.ext import commands
from discord import app_commands, Interaction, User
from discord.ext.paginator import paginator

from amelia.bot import AmeliaBot
from amelia.tfl import TFLService


class LongDescriptionPaginator(paginator.Paginator):

    bot: AmeliaBot

    def __init__(self, bot: AmeliaBot, user: User, title: str, description: str, num_characters: int, *args, **kwargs):
        super().__init__(bot, user, *args, **kwargs)
        assert num_characters < 4096, "Number of characters cannot be 4096 or higher."
        self.title = title
        self.num_characters = num_characters
        self.total_length = len(description)
        self.pages = ceil(self.total_length / num_characters)
        self.entries = []
        self.fill_entries(description)

    def fill_entries(self, description: str):
        lines = description.split('\n')
        page_content = ""
        for line in lines:
            if len(page_content) > self.num_characters:
                self.entries.append(page_content)
                page_content = ""
            page_content += line + '\n'



    async def get_page_count(self, interaction: Interaction) -> int:
        return len(self.entries)

    async def get_page_content(self, interaction: Interaction, page: int) -> Dict[str, Any]:
        return {

            "embed": (discord.Embed(title=self.title, description=self.entries[page]))
        }



class Airport(commands.Cog):

    def __init__(self, bot):
        self.bot = bot


    @app_commands.command(name='plates', description="Gets a listing of all STARs, Departures, and Instrument Approach Plans")
    @app_commands.describe(icao="The ICAO code of the airport to get plate information for")
    async def plate_app_cmd(self, itx: Interaction, icao: str):
        def _filter(seq, category):
            return [p for p in seq if p.code.upper() == category.upper()]

        def _make_markdown_links(seq):
            return "\n".join(f"[{p.name}]({p.plate_url})" for p in seq) or "None"

        icao = icao.upper()
        tfl = TFLService()
        airport = await tfl.fetch_airport(icao)
        if airport is None:
            await itx.response.send_message("Cannot find airport data", ephemeral=True)
            return

        plates = airport.plates
        stars = _filter(plates, "STAR")
        dp = _filter(plates, "DP")
        iap = _filter(plates, 'IAP')
        rest = [p for p in plates if p not in stars + dp + iap]
        description = textwrap.dedent(
            f"""
            **Standard Terminal Arrival Routes**
                {_make_markdown_links(stars)}
            
            **Departure Procedures**
            {_make_markdown_links(dp)}
            
            **Instrument Approach Procedures**
            {_make_markdown_links(iap)}
            
            **Other Plates**
            {_make_markdown_links(rest)}
            """
        )
        title = f"Plates for {icao}"
        if len(description) > 4000:
            content = "The result is too large to display in one embed. Please click the Start Button to allow pagination."
            await itx.response.send_message(content=content, view=await LongDescriptionPaginator(itx.client, itx.user, title, description, 2000).run())
        else:
            embed = discord.Embed(title=title, description=description)
            await itx.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Airport(bot))