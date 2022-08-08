import discord
from discord import app_commands, Interaction
from discord.ext import commands

from amelia.tfl import StationHasNoDataError
from amelia.weather.cache import TafCache
from amelia.weather.config import TafConfigGroup
from amelia.weather.services import make_taf_embed, depr
from amelia import tfl

class Taf(commands.Cog):

    def __init__(self, bot: 'AmeliaBot'):
        self.bot = bot
        self.cache = TafCache(bot)

    async def _get_taf_embed(self, icao: str, display_name: str, avatar_url: str):
        taf = await self.bot.tfl.fetch_taf(icao)
        embed = make_taf_embed(taf)
        text = f"{display_name} | Not an official source for flight planning"
        embed.set_footer(text=text, icon_url=avatar_url)
        return embed

    def is_taf_channel(self, channel: discord.TextChannel):
        allowed_channels = self.cache.channels.item.get(channel.guild.id, [])
        return len(allowed_channels) == 0 or channel in allowed_channels

    async def send_to_first_allowed_channel(self, guild_id: int, **kwargs) -> discord.Message:
        channel = self.cache.channels.item[guild_id][0]
        msg = await channel.send(**kwargs)
        return msg

    @commands.command(name='taf')
    async def taf_txt_cmd(self, ctx: commands.Context, icao: str):
        _depr = depr('/taf')
        embed = await self._get_taf_embed(icao, ctx.author.display_name, ctx.author.display_avatar.url)
        if ctx.author.id == 675262431190319104:
            embed.set_thumbnail(url='http://clipart-library.com/image_gallery/n1592036.jpg')
        if self.is_taf_channel(ctx.channel):
            await ctx.reply(content=_depr, embed=embed)
        else:
            msg = await self.send_to_first_allowed_channel(ctx.guild.id, embed=embed)
            try:
                await ctx.author.send(f"I have moved your TAF report to {msg.channel.mention}")
            except (discord.Forbidden, discord.HTTPException):
                pass

    @app_commands.command(name='taf', description="Current TAF Forecast for an airport")
    @app_commands.describe(icao="The ICAO code of the airport that is reporting Terminal Area Forecasts")
    async def taf_app_cmd(self, itx: Interaction, icao: str):
        embed = await self._get_taf_embed(icao, itx.user.display_name, itx.user.display_avatar.url)
        message = ""
        ephemeral = False
        if not self.is_taf_channel(itx.channel):  # duck typing is ok here
            ephemeral = True
            m = await self.send_to_first_allowed_channel(itx.guild_id, embed=embed)
            message = f"I am auto moving this to {m.channel.mention} so others may see as well."
        await itx.response.send_message(content=message, embed=embed, ephemeral=ephemeral)

    @taf_app_cmd.error
    async def taf_app_cmd_error(self, itx: Interaction, error):
        unknown_error = False
        message = "Could not complete the request. Unknown error."
        if isinstance(error.original, tfl.StationHasNoDataError):
            icao = itx.data['options'][0]['value'].upper()
            message = f"**{icao}** is not currently reporting TAF"
        else:
            unknown_error = True

        embed = discord.Embed(title="TAF Unavailable", description=message)
        await itx.response.send_message(embed=embed, ephemeral=True)
        if unknown_error:
            raise error

    @taf_txt_cmd.error
    async def taf_txt_cmd_error(self, ctx: commands.Context, error):
        message = "Could not complete the request. Unknown error."
        if isinstance(error.original, StationHasNoDataError):
            icao = ctx.args[2].upper()
            message = f"**{icao}** is not currently reporting TAF"
        else:
            raise error
        embed = discord.Embed(title="TAF Unavailable", description=message)
        await ctx.send(embed=embed)


    async def cog_load(self) -> None:
        self.bot.config_group.add_command(TafConfigGroup(self.bot, self.cache))