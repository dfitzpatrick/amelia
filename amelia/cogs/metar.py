import logging
import math
import textwrap
import typing

import aiohttp
import dateutil.parser
import discord
from discord.ext import commands

from amelia.mixins.avwx import AVWX, AvwxResponse, AvwxEmptyResponseError
from amelia.mixins.config import ConfigMixin
from amelia import common

log = logging.getLogger(__name__)

class FlightRule(typing.NamedTuple):
    emoji: str
    name: str

class Metar(ConfigMixin, AVWX, commands.Cog):
    def __init__(self, bot: commands.Bot):
        super(Metar, self).__init__()
        self.bot = bot

        log.debug(hasattr(self, 'config_settings'))
        log.debug(self.config_settings)

    def get_metar_channel(self, guild: discord.Guild) -> typing.Optional[discord.TextChannel]:
        guild_id_str = str(guild.id)

        try:
            ch_id = self.config_settings[guild_id_str]['channel']
            ch = discord.utils.get(guild.text_channels, id=ch_id)
            return ch
        except KeyError:
            ch = discord.utils.get(guild.text_channels, name='metar-chat')
            return ch


    def flight_rules(self, rule: str) -> FlightRule:
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

    def fetch_clouds(self, m: AvwxResponse) -> str:
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
        clouds = m['translate']['clouds']
        if clouds:
            result = clouds.split('-')[0]
            result = '\n'.join(r.strip() for r in result.split(','))
        else:
            result = 'Clear'
        return result


    @commands.group(name='metar', invoke_without_command=True)
    async def metar(self, ctx: commands.Context, icao: str):
        """
        Sends a discord.Embed to the channel that shows METAR information.
        Invoked by the following syntax:
        !metar ICAO

        Parameters
        ----------
        ctx: Context object
        icao: The Airport ICAO code such as KLGB

        Returns
        -------
        :class: None
        """
        await ctx.trigger_typing()
        try:
            icao_code = icao.upper()
            if icao_code == 'KMOO':
                # easter egg
                icao_code = 'KDVT'
            m = await self.fetch_metar(icao_code)
        except AvwxEmptyResponseError:
            title = 'Missing Metar'
            description = 'This ICAO has no Metar Information'
            embed = discord.Embed(title=title, description=description)
            await ctx.send(embed=embed, delete_after=10)
            return

        if 'error' in m.keys():
            raise commands.BadArgument(m['error'])
        icao = icao.upper()


        now = dateutil.parser.parse(m['meta']['timestamp'])
        valid_time = dateutil.parser.parse(m['time']['dt'])
        elapsed = common.td_format(now - valid_time)
        valid_fmt = valid_time.strftime("%H:%M")
        altimeter = m['translate']['altimeter']
        wind = m['translate']['wind'] or 'Calm'
        clouds = self.fetch_clouds(m)
        visibility = m['translate']['visibility'] or "Not Reported"
        temp = m['translate']['temperature'] or "Not Reported"
        dew = m['translate']['dewpoint'] or "Not Reported"
        remarks = [f"{k} -  {v}" for k,v in m['translate']['remarks'].items()]
        remarks = '\n'.join(remarks) or 'No Remarks'
        raw = m['raw']
        weather = '\n'.join(w['value'] for w in m['wx_codes']) or "No Weather Reported"
        description = textwrap.dedent(
            f"""
            **__Metar Valid {valid_fmt}Z__**
            *Note: This report was generated {elapsed} afterwards.*
            
            {raw}
            """
        )
        remark_keys = m['translate']['remarks'].keys()
        if '_$' in remark_keys or '$' in remark_keys:
            description = "**Warning: This metar information is incomplete or requires servicing. This may cause the following station to report wrong such as Flight Rules**\n\n" + description
        status = common.FlightRule.create(m['flight_rules'])
        embed = discord.Embed(title=f"{status.emoji} {icao} ({status.name})", description=description)
        embed.add_field(name=":wind_chime: Wind", value=wind)
        embed.add_field(name=':eyes: Visibility', value=visibility)
        embed.add_field(name=':cloud: Clouds', value=clouds)
        embed.add_field(name=':thermometer: Temp', value=temp)
        embed.add_field(name=':regional_indicator_d: Dewpoint', value=dew)
        embed.add_field(name=':a: Altimeter', value=altimeter)
        embed.add_field(name=':cloud_rain: Weather', value=weather)
        embed.add_field(name=':pencil: Remarks', value=remarks, inline=False)

        embed.timestamp = valid_time
        embed.set_footer(text="Generated {} from valid time. Metar Valid local time is".format(elapsed))

        metar_channel = self.get_metar_channel(ctx.guild)
        metar_channel_id = metar_channel.id if metar_channel is not None else None

        # Send to channel with auto delete if its not the metar channel
        if ctx.channel.id != metar_channel_id:
            await ctx.send(embed=embed, delete_after=120)

        # Send to metar channel if it exists with no delete
        if isinstance(metar_channel, discord.TextChannel):
            await metar_channel.send(embed=embed)



    @metar.error
    async def metar_error(self, ctx: commands.Context, error: typing.Any):
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
                    Syntax: *{pfx}metar **ICAO***
                    
                    *ICAO*: The airport code (ex: KLGB)
                """
            )
        elif isinstance(error, commands.BadArgument):
            message = textwrap.dedent(
                f"""
                {error}
                
                Syntax: *{pfx}metar **ICAO***
                    
                *ICAO*: The airport code (ex: KLGB)
                """
            )

        elif isinstance(error, aiohttp.ClientResponseError):
            message = "The API service is currently down. Try again later"
        else:
            log.error(error)
            raise error

        embed = discord.Embed(title="Metar Unavailable", description=message)
        await ctx.send(embed=embed, delete_after=30)

    @metar.command(name='channel')
    @commands.has_guild_permissions(administrator=True)
    async def metar_channel_cmd(self, ctx: commands.Context, ch: discord.TextChannel = None):
        guild_id_str = str(ctx.guild.id)

        if ch is None:
            try:
                del self.config_settings[guild_id_str]['channel']
            except KeyError:
                pass
            await ctx.send("Removed Metar Channel", delete_after=10)
            return

        if guild_id_str not in self.config_settings.keys():
            self.config_settings[guild_id_str] = {}
        self.config_settings[guild_id_str]['channel'] = ch.id
        self.save_settings()

        await ctx.send(f"Metar channel set to {ch.name}", delete_after=10)

    @metar_channel_cmd.error
    async def metar_channel_cmd_error(self, ctx: commands.Context, error: commands.CommandError):
        await ctx.send(f"Unable to Set Metar Channel. {error}", delete_after=10)


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
            await message.add_reaction(u"\u2705") # Green Checkbox
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
    bot.add_cog(Metar(bot))