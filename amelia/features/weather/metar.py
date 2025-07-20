import logging
from typing import TYPE_CHECKING

import discord
from discord import Interaction, app_commands
from discord.ext import commands

from .config import MetarConfigGroup
from .services import get_digital_atis, make_metar_embed, convert_allowed_channels_to_discord
from amelia.tfl import StationHasNoDataError

if TYPE_CHECKING:
    from amelia.bot import AmeliaBot
log = logging.getLogger(__name__)


class Metar(commands.Cog):


    def __init__(self, bot: 'AmeliaBot'):
        self.bot = bot
        self._config: MetarConfigGroup | None = None

    async def _get_metar_embed(self, icao: str, display_name: str, avatar_url: str):
        metar = await self.bot.tfl.fetch_metar(icao)
        datis = await get_digital_atis(icao)
        embed = make_metar_embed(metar)
        text = f"{display_name} | Not an official source for flight planning"
        embed.set_footer(text=text, icon_url=avatar_url)
        if datis is not None:
            name = ":desktop: Digital ATIS"
            embed.add_field(name=name, value=datis, inline=False)
        return embed


    


    @app_commands.command(name='metar', description="Current METAR Observation for an airport")
    @app_commands.describe(icao="The ICAO code of the airport that is reporting METAR observations")
    async def metar_app_cmd(self, itx: Interaction, icao: str):
        if itx.guild is None or itx.channel is None or not isinstance(itx.channel, discord.TextChannel):
            return
        async with self.bot.db as session:
            config = await session.weather.fetch_metar_configuration(itx.guild.id)
            restricted = config and config.restrict_channel
            allowed_channels = await session.weather.fetch_metar_channels(itx.guild.id)
            allowed_channels = convert_allowed_channels_to_discord(itx.guild, allowed_channels) 
        embed = await self._get_metar_embed(icao, itx.user.display_name, itx.user.display_avatar.url)
        message = ""
        ephemeral = False
        if restricted and itx.channel not in allowed_channels:
            ephemeral = True
            first_allowed_channel = allowed_channels[0]
            m = await first_allowed_channel.send(embed=embed)
            if isinstance(m.channel, discord.TextChannel):
                message = f"I am auto moving this to {m.channel.mention} so others may see as well."
        await itx.response.send_message(content=message, embed=embed, ephemeral=ephemeral)


    @metar_app_cmd.error
    async def metar_app_cmd_error(self, itx: Interaction, error: app_commands.AppCommandError):
        unwrapped_error = error.original if isinstance(error, app_commands.errors.CommandInvokeError) else error
        message = "Could not complete the request. Unknown error."
        if isinstance(unwrapped_error, StationHasNoDataError):
            icao = itx.data['options'][0]['value'].upper() #type: ignore
            message = f"**{icao}** is not currently reporting METAR observations"
        else:
            raise error
        embed = discord.Embed(title="Metar Unavailable", description=message)
        await itx.response.send_message(embed=embed, ephemeral=True)


    async def cog_load(self) -> None:
        self.bot.config_group.add_command(MetarConfigGroup(self.bot))

    async def cog_unload(self) -> None:
        self.bot.config_group.remove_command(MetarConfigGroup.COMMAND_NAME)


