import logging
import math
import textwrap
import typing

import aiohttp
import dateutil.parser
import discord
from discord.ext import commands

from amelia import common
from amelia.mixins.avwx import AVWX, AvwxEmptyResponseError
from amelia.mixins.config import ConfigMixin

log = logging.getLogger(__name__)

class TAF(AVWX, ConfigMixin, commands.Cog):

    def __init__(self, bot: commands.Bot):
        super(TAF, self).__init__()
        self.bot = bot

    def get_taf_channel(self, guild: discord.Guild) -> typing.Optional[discord.TextChannel]:
        guild_id_str = str(guild.id)

        try:
            ch_id = self.config_settings[guild_id_str]['channel']
            ch = discord.utils.get(guild.text_channels, id=ch_id)
            return ch
        except KeyError:
            ch = discord.utils.get(guild.text_channels, name='metar')
            return ch

    def fetch_clouds(self, clouds: str) -> str:
        """
        Helper function that cleans up the cloud results.
        An example reply from the API is:
            'clouds': 'Overcast layer at 700ft - Reported AGL',

        The list is comma seperated. We truncate off the AGL reminder.

        Parameters
        ----------
        m: The AvwxResponse object from fetch_metar

        Returns
        -------
        :class: str
        """
        if clouds:
            result = clouds.split('-')[0]
            descriptions = result.split(',')
            result = '\n'.join(r.strip() for r in descriptions)
            if len(descriptions) > 1:
                result = '\n' + result

        else:
            result = 'Clear'
        return result

    @commands.group(name='taf', invoke_without_command=True)
    async def taf(self, ctx: commands.Context, icao: str):
        await ctx.trigger_typing()
        try:
            m = await self.fetch_taf(icao)
        except AvwxEmptyResponseError as e:
            title = 'Missing TAF'
            description = 'This ICAO has no TAF Information'
            embed = discord.Embed(title=title, description=description)
            await ctx.send(embed=embed, delete_after=10)
            return

        if 'error' in m.keys():
            raise commands.BadArgument(m['error'])
        icao = icao.upper()
        raw = '\n'.join(f['raw'] for f in m['forecast'])
        now = dateutil.parser.parse(m['meta']['timestamp'])
        valid_time = dateutil.parser.parse(m['time']['dt'])
        elapsed = "Reported {} minutes ago".format(math.ceil((now - valid_time).seconds / 60))
        valid_fmt = valid_time.strftime("%H:%M")
        description = textwrap.dedent(
            f"""
            **__Taf Valid {valid_fmt}Z__**  *({elapsed})*
    
            {raw}
            """
        )
        embed = discord.Embed(title=f"TAF {icao}", description=description)
        for idx, f in enumerate(m['forecast']):
            f_start = dateutil.parser.parse(f['start_time']['dt'])
            f_end = dateutil.parser.parse(f['end_time']['dt'])
            status = common.FlightRule.create(f['flight_rules'])

            title = "{} {} **__From__** {}Z **__thru__** {}Z".format(
                status.emoji,
                status.name,
                f_start.strftime("%H:%M"),
                f_end.strftime("%H:%M")
            )
            embed_description = ""
            translations = m['translate']['forecast'][idx]
            t = '\u0020\u0020\u0020\u0020\u0020\u0020\u0020\u0020'
            for k, v in translations.items():
                k: str
                if v == '':
                    continue
                key = k.capitalize().replace("_", " ")
                if k == 'clouds':
                    v = self.fetch_clouds(v)

                embed_description += f"**{key}:** {t} {v}\n"
            embed_description += '\u200b\n'
            embed.add_field(name=title, value=embed_description, inline=False)

        embed.timestamp = valid_time
        embed.set_footer(text=elapsed)

        taf_channel = self.get_taf_channel(ctx.guild)
        metar_channel_id = taf_channel.id if taf_channel is not None else None

        # Send to channel with auto delete if its not the metar channel
        if ctx.channel.id != metar_channel_id:
            await ctx.send(embed=embed, delete_after=120)

        # Send to metar channel if it exists with no delete
        if isinstance(taf_channel, discord.TextChannel):
            await taf_channel.send(embed=embed)

    @taf.error
    async def taf_error(self, ctx: commands.Context, error: typing.Any):
        """
        Simple function to cover syntax errors or bad API requests
        Parameters
        ----------
        ctx: The discord Context
        error: The CommandError that was encountered

        Returns
        -------
        :class: None
        """
        message = "Could not complete the request. Unknown error."
        pfx = self.bot.command_prefix
        if isinstance(error, commands.MissingRequiredArgument):
            message = textwrap.dedent(
                f"""
                        Syntax: *{pfx}taf **ICAO***

                        *ICAO*: The airport code (ex: KLGB)
                    """
            )
        elif isinstance(error, commands.BadArgument):
            message = textwrap.dedent(
                f"""
                    {error}

                    Syntax: *{pfx}taf **ICAO***

                    *ICAO*: The airport code (ex: KLGB)
                    """
            )

        elif isinstance(error, aiohttp.ClientResponseError):
            message = "The API service is currently down. Try again later"

        elif isinstance(error, AvwxEmptyResponseError):
            message = "This ICAO has no TAF information available."
        else:
            log.error(error)
            raise error


        embed = discord.Embed(title="TAF Unavailable", description=message)
        await ctx.send(embed=embed, delete_after=30)

    @taf.command(name='channel')
    async def taf_channel_cmd(self, ctx: commands.Context, ch: discord.TextChannel = None):
        guild_id_str = str(ctx.guild.id)

        if ch is None:
            try:
                del self.config_settings[guild_id_str]['channel']
            except KeyError:
                pass
            await ctx.send("Removed TAF Channel", delete_after=10)
            return

        if guild_id_str not in self.config_settings.keys():
            self.config_settings[guild_id_str] = {}
        self.config_settings[guild_id_str]['channel'] = ch.id
        self.save_settings()

        await ctx.send(f"TAF channel set to {ch.name}", delete_after=10)

    @taf_channel_cmd.error
    async def metar_channel_cmd_error(self, ctx: commands.Context, error: commands.CommandError):
        await ctx.send(f"Unable to Set TAF Channel. {error}", delete_after=10)

    @commands.Cog.listener()
    async def on_command_completion(self, ctx: commands.Context):
        """
        Simple Housekeeping function. Annotates the command with feedback that
        it completed correctly, and if permissioned for, will remove the command.

        Parameters
        ----------
        ctx: The discord Context

        Returns
        -------
        :class: None
        """
        if ctx.cog != self:
            return
        try:
            message: discord.Message = ctx.message
            await message.add_reaction(u"\u2705")  # Green Checkbox
            await message.delete(delay=5)
        except (discord.errors.NotFound, discord.errors.Forbidden, discord.errors.HTTPException):
            pass

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        """
            Simple Housekeeping function. Annotates the command with feedback that
            it failed, and if permissioned for, will remove the command.

            Parameters
            ----------
            ctx: The discord Context
            error: The CommandError that was raised.

            Returns
            -------
            :class: None
        """
        if ctx.cog != self:
            return
        try:
            message: discord.Message = ctx.message
            await message.add_reaction(u"\u274C")  # Red X
            await message.delete(delay=5)
            raise error
        except (discord.errors.NotFound, discord.errors.Forbidden, discord.errors.HTTPException):
            pass



def setup(bot: commands.Bot):
    bot.add_cog(TAF(bot))