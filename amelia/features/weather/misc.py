from datetime import datetime

import discord

from amelia.sun import SunService
from amelia.tfl import TFLService
from discord import app_commands, Interaction
from dateutil.parser import parse


@app_commands.command(name='sunset', description='Find out when sunset occurs for logging practices')
@app_commands.describe(icao="The airport ICAO to lookup sunset information for. ex: KLGB")
async def sunset_cmd(itx: Interaction, icao: str):
    icao = icao.upper()
    tfl = TFLService()
    service = SunService()
    airport = await tfl.fetch_airport(icao)
    lat, lon = airport.latitude, airport.longitude
    s = await service.fetch_sun_rise_set(lat, lon)

    sunrise = parse(s['sunrise'])
    sunset = parse(s['sunset'])
    ctb = parse(s['civil_twilight_begin'])
    cte = parse(s['civil_twilight_end'])
    fmt = "%H:%MZ"
    description = f"You can log night time starting at {cte.strftime(fmt)}"

    embed = discord.Embed(title=f"Sunset Information for {icao}", description=description)
    embed.add_field(name=':sunrise_over_mountains: Civil Twilight Begins', value=cte.strftime(fmt))
    embed.add_field(name=':sunrise: Sunrise', value=sunrise.strftime(fmt))
    embed.add_field(name=':city_sunset: Sunset', value=sunset.strftime(fmt)),
    embed.add_field(name=':crescent_moon: Civil Twilight Ends', value=cte.strftime(fmt))
    embed.timestamp = datetime.now()
    await itx.response.send_message(embed=embed, ephemeral=True)
