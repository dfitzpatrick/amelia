import textwrap
from io import BytesIO
from typing import List

import aiohttp
import discord
from pdf2image import convert_from_bytes

from src.tfl import FAAPlate


async def pdf_to_memory(url: str) -> BytesIO:
    async with aiohttp.ClientSession() as session:
        async with session.get(url=url) as resp:
            data = BytesIO(await resp.read())
            data.seek(0)
            return data


async def plate_to_image_bytes(plate: FAAPlate) -> BytesIO:
    pdf = await pdf_to_memory(plate.plate_url)
    image = convert_from_bytes(
        pdf.read(),
        first_page=1,
        last_page=1
    )[0]
    image_bytes = BytesIO()
    image.save(image_bytes, format='PNG')
    image_bytes.seek(0)
    return image_bytes


def all_plates_embed(icao: str, plates: List[FAAPlate]) -> discord.Embed:
    def _filter(seq, category):
        return [p for p in seq if p.code.upper() == category.upper()]

    def _make_markdown_links(seq):
        return "\n".join(f"[{p.name}]({p.plate_url})" for p in seq) or "None"

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
    return discord.Embed(title=title, description=description)