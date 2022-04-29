import logging

import discord
from discord import Interaction
from discord import app_commands
from discord.ext import commands

from amelia.bot import AmeliaBot
from amelia.tfl import TFLService, StationHasNoDataError
from amelia.weather.cache import MetarCache
from amelia.weather.config import MetarConfigGroup
from amelia.weather.services import make_metar_embed, depr

log = logging.getLogger(__name__)


class Metar(commands.Cog):


    def __init__(self, bot: AmeliaBot):
        self.bot = bot
        self.service = TFLService()
        self.cache = MetarCache(bot)

    async def _get_metar_embed(self, icao: str, display_name: str, avatar_url: str):
        metar = await self.service.fetch_metar(icao)
        embed = make_metar_embed(metar)
        text = f"{display_name} | Not an official source for flight planning"
        embed.set_footer(text=text, icon_url=avatar_url)
        return embed

    def is_metar_channel(self, channel: discord.TextChannel):
        allowed_channels = self.cache.channels.item.get(channel.guild.id, [])
        return len(allowed_channels) == 0 or channel in allowed_channels

    async def send_to_first_allowed_channel(self, guild_id: int, **kwargs) -> discord.Message:
        channel = self.cache.channels.item[guild_id][0]
        msg = await channel.send(**kwargs)
        return msg

    @commands.command(name='metar')
    async def metar_txt_cmd(self, ctx: commands.Context, icao: str):
        _depr = depr('/metar')
        embed = await self._get_metar_embed(icao, ctx.author.display_name, ctx.author.display_avatar.url)
        # easter egg
        if ctx.author.id == 675262431190319104:
            embed.set_thumbnail(url='http://clipart-library.com/image_gallery/n1592036.jpg')
        if self.is_metar_channel(ctx.channel):
            await ctx.reply(content=_depr, embed=embed)
        else:
            msg = await self.send_to_first_allowed_channel(ctx.guild.id, embed=embed)
            try:
                await ctx.author.send(f"I have moved your metar report to {msg.channel.mention}")
            except (discord.Forbidden, discord.HTTPException):
                pass


    @app_commands.command(name='metar', description="Current METAR Observation for an airport")
    @app_commands.describe(icao="The ICAO code of the airport that is reporting METAR observations")
    async def metar_app_cmd(self, itx: Interaction, icao: str):
        embed = await self._get_metar_embed(icao, itx.user.display_name, itx.user.display_avatar.url)
        message = ""
        ephemeral = False
        if not self.is_metar_channel(itx.channel):
            ephemeral = True
            m = await self.send_to_first_allowed_channel(itx.guild_id, embed=embed)
            message = f"I am auto moving this to {m.channel.mention} so others may see as well."
        await itx.response.send_message(content=message, embed=embed, ephemeral=ephemeral)


    @metar_app_cmd.error
    async def metar_app_cmd_error(self, itx: Interaction, error):
        message = "Could not complete the request. Unknown error."
        if isinstance(error.original, StationHasNoDataError):
            icao = itx.data['options'][0]['value'].upper()
            message = f"**{icao}** is not currently reporting METAR observations"
        else:
            raise error
        embed = discord.Embed(title="Metar Unavailable", description=message)
        await itx.response.send_message(embed=embed, ephemeral=True)


    @metar_txt_cmd.error
    async def metar_txt_cmd_error(self, ctx: commands.Context, error):
        message = "Could not complete the request. Unknown error."
        if isinstance(error.original, StationHasNoDataError):
            icao = ctx.args[2].upper()
            message = f"**{icao}** is not currently reporting METAR observations"
        else:
            raise error
        embed = discord.Embed(title="Metar Unavailable", description=message)
        await ctx.send(embed=embed)

    async def cog_load(self) -> None:
        self.bot.config_group.add_command(MetarConfigGroup(self.bot, self.cache))




