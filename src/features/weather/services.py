import textwrap
from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING

import aiohttp
import discord

from src import common
from src.features.weather.data import AllowedChannel
from src.instances import db
from src.features.weather.objects import FlightRule
if TYPE_CHECKING:
    from src.tfl import MetarDTO, TafDTO

def flight_rules(rule: str) -> FlightRule:
    """
    Returns a Named Tuple based on the flight rules. Right now this
    tuple just contains an emoji and the name, but could be expanded later.

    Parameters
    ----------
    rule

    Returns
    -------
    FlightRule -> Tuple[str, str]
    """
    formats = {
        "VFR": FlightRule(":green_circle:", "VFR"),
        "IFR": FlightRule(":red_circle:", "IFR"),
        "MVFR": FlightRule(":blue_circle:", "MVFR"),
        "LIFR": FlightRule(":purple_circle:", "LIFR")

    }
    return formats.get(rule.upper(), FlightRule(":black_circle:", rule))


def make_metar_embed(metar_dto: 'MetarDTO') -> discord.Embed:
    icao = metar_dto.icao
    now = datetime.now(timezone.utc)
    elapsed = common.td_format(now - metar_dto.valid)
    warning = "\n\n**Warning: Last attempt to fetch new data __FAILED__. This data may be out of date.**"
    warning = warning if not metar_dto.last_polling_succeeded else ''
    description = textwrap.dedent(
        f"""
         **__Metar Valid {metar_dto.valid.strftime('%m/%d %H:%M')}Z__**
            {elapsed} ago
            [Click here for more information](http://theflying.life/airports/{icao}) {warning}
            
            {metar_dto.raw_text}
            """
    )
    status = FlightRule.create(metar_dto.flight_rule)
    title = f"{status.emoji} {icao} ({status.name})"
    embed = discord.Embed(title=title, description=description, url=common.TFL_URL + f"/airports/{icao}")
    embed.add_field(name=":wind_chime: Wind", value=metar_dto.wind)
    embed.add_field(name=':eyes: Visibility', value=metar_dto.visibility)
    embed.add_field(name=':cloud: Clouds', value='\n'.join(metar_dto.clouds) or 'Not Reported')
    embed.add_field(name=':thermometer: Temp', value=metar_dto.temp)
    embed.add_field(name=':regional_indicator_d: Dewpoint', value=metar_dto.dewpoint)
    embed.add_field(name=':a: Altimeter', value=metar_dto.altimeter)
    embed.add_field(name=':cloud_rain: Weather', value='\n'.join(metar_dto.weather) or 'No Weather', inline=False)
    embed.add_field(name=':pencil: Remarks', value='\n'.join(metar_dto.remarks) or 'No Remarks', inline=False)
    embed.timestamp = datetime.now()
    return embed

def make_taf_embed(taf_dto: 'TafDTO') -> discord.Embed:
    icao = taf_dto.station_id.upper()
    now = datetime.now(timezone.utc)
    elapsed = common.td_format(now - taf_dto.issue_time)
    warning = "\n\n**Warning: Last attempt to fetch new data __FAILED__. This data may be out of date.**"
    warning = warning if not taf_dto.last_polling_succeeded else ''
    description = textwrap.dedent(
        f"""
             **Taf Issued __{taf_dto.issue_time.strftime('%m/%d %H:%M')}Z__**
                {elapsed} ago
                [Click here for more information](http://theflying.life/airports/{icao}) {warning}
                
                {taf_dto.raw_text}
                """
    )
    t = ":regional_indicator_t:"
    embed = discord.Embed(title=f"{t} TAF {icao}", description=description)
    for f in taf_dto.forecasts:
        status = common.FlightRule.create(f.flight_rules)
        if f.time_becoming is None:
            title = f"{status.emoji} **{status.name} {f.text}**"
        else:
            a = ":arrow_heading_up:"
            status = f" {status.emoji} {status.name} "
            title = f.text.split()
            # Insert after first word. Just to make it read more like english
            title = title[0] + status + ' '.join(title[1:])
            title = f"**{a} {title}**"

        wx_codes = ', '.join(wx['text'] for wx in f.wx_codes) or 'None Reported'
        sky_conditions = ', '.join(sc['text'] for sc in f.sky_condition) or 'Not Reported'
        ceilings = ', '.join(f"{c} ft" for c in f.ceilings) or 'Not Reported'
        descriptions = [
            f"**Sky Condition:** {sky_conditions}",
            f"**Wind:** {f.wind['text']}",
            f"**Visibility:** {f.visibility['text']}",
            f"**Ceilings:** {ceilings}",
            f"**Weather:** {wx_codes}",
            "\u200b\n",
        ]
        embed.add_field(name=title, value='\n'.join(descriptions), inline=False)
    embed.timestamp = datetime.now()
    return embed


def depr(command: str):
    return f"This command will no longer work with a future update. Please use {command} going forward"

async def get_digital_atis(icao: str) -> Optional[str]:
    target = f"http://datis.clowd.io/api/{icao}"
    async with aiohttp.ClientSession() as session:
        async with session.get(target) as resp:
            data = await resp.json()
            if isinstance(data, list):
                data = data[0]
            if 'error' in data.keys():
                return
            return data['datis']


async def get_allowed_channels(guild: discord.Guild) -> list[discord.TextChannel]:
        container = []
        async with db as session:
            schemas = await session.weather.fetch_metar_channels(guild.id)
            for sch in schemas:
                o = discord.utils.get(guild.text_channels, id=sch.channel_id)
                if o is not None:
                    container.append(o)
        return container

def convert_allowed_channels_to_discord(
        guild: discord.Guild, 
        channels: list[AllowedChannel]
    ) -> list[discord.TextChannel]:
    container = []
    for schema in channels:
        o = discord.utils.get(guild.text_channels, id=schema.channel_id)
        if o is not None:
            container.append(o)
    return container
