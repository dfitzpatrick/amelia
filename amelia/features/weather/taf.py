from __future__ import annotations
import discord
from discord import app_commands, Interaction
from discord.ext import commands

from .config import TafConfigGroup
from .services import convert_allowed_channels_to_discord, make_taf_embed
from amelia import tfl
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from amelia.bot import AmeliaBot

class Taf(commands.Cog):

    def __init__(self, bot: AmeliaBot):
        self.bot = bot

    async def _get_taf_embed(self, icao: str, display_name: str, avatar_url: str):
        taf = await self.bot.tfl.fetch_taf(icao)
        embed = make_taf_embed(taf)
        text = f"{display_name} | Not an official source for flight planning"
        embed.set_footer(text=text, icon_url=avatar_url)
        return embed

    @app_commands.command(name='taf', description="Current TAF Forecast for an airport")
    @app_commands.describe(icao="The ICAO code of the airport that is reporting Terminal Area Forecasts")
    async def taf_app_cmd(self, itx: Interaction, icao: str):
        if itx.guild is None or itx.channel is None or not isinstance(itx.channel, discord.TextChannel):
            return
        async with self.bot.db as session:
            config = await session.weather.fetch_taf_configuration(itx.guild.id)
            restricted = config and config.restrict_channel
            allowed_channels = await session.weather.fetch_taf_channels(itx.guild.id)
            allowed_channels = convert_allowed_channels_to_discord(itx.guild, allowed_channels) 
        embed = await self._get_taf_embed(icao, itx.user.display_name, itx.user.display_avatar.url)
        message = ""
        ephemeral = False
        if restricted and itx.channel not in allowed_channels:
            ephemeral = True
            first_allowed_channel = allowed_channels[0]
            m = await first_allowed_channel.send(embed=embed)
            if isinstance(m.channel, discord.TextChannel):
                message = f"I am auto moving this to {m.channel.mention} so others may see as well."
        await itx.response.send_message(content=message, embed=embed, ephemeral=ephemeral)

    @taf_app_cmd.error
    async def taf_app_cmd_error(self, itx: Interaction, error: app_commands.AppCommandError):
        unwrapped_error = error.original if isinstance(error, app_commands.errors.CommandInvokeError) else error
        message = "Could not complete the request. Unknown error."
        if isinstance(unwrapped_error, tfl.StationHasNoDataError):
            icao = itx.data['options'][0]['value'].upper() #type: ignore
            message = f"**{icao}** is not currently reporting TAF"
        else:
            raise error
        embed = discord.Embed(title="TAF Unavailable", description=message)
        await itx.response.send_message(embed=embed, ephemeral=True)
       


    async def cog_load(self) -> None:
        self.bot.config_group.add_command(TafConfigGroup(self.bot))

    async def cog_unload(self) -> None:
        self.bot.config_group.remove_command(TafConfigGroup.COMMAND_NAME)