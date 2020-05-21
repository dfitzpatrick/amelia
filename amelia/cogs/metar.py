import logging
import math
import textwrap
import typing
from datetime import datetime

import aiohttp
import discord
from discord.ext import commands

from amelia.avwx import AVWX, AvwxResponse
import dateutil.parser

log = logging.getLogger(__name__)

class FlightRule(typing.NamedTuple):
    emoji: str
    name: str

class Metar(AVWX, commands.Cog):
    def __init__(self, bot: commands.Bot):
        super(Metar, self).__init__()

        self.bot = bot

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
            result = '\n'.join(r for r in result.split(','))
        else:
            result = 'Clear'
        return result

    @commands.command(name='metar')
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
        m = await self.fetch_metar(icao)
        if 'error' in m.keys():
            raise commands.BadArgument(m['error'])
        icao = icao.upper()
        now = dateutil.parser.parse(m['meta']['timestamp'])
        valid_time = dateutil.parser.parse(m['time']['dt'])
        elapsed = "Reported {} minutes ago".format(math.ceil((now - valid_time).seconds / 60))
        valid_fmt = valid_time.strftime("%H:%M")
        altimeter = m['translate']['altimeter']
        wind = m['translate']['wind'] or 'Calm'
        clouds = self.fetch_clouds(m)
        visibility = m['translate']['visibility']
        temp = m['translate']['temperature']
        dew = m['translate']['dewpoint']
        remarks = [f"{k} -  {v}" for k,v in m['translate']['remarks'].items()]
        remarks = '\n'.join(remarks) or 'No Remarks'
        raw = m['raw']
        weather = '\n'.join(w['value'] for w in m['wx_codes']) or "No Weather Reported"
        description = textwrap.dedent(
            f"""
            **__Metar Valid {valid_fmt}Z__**  *({elapsed})*
            
            {raw}
            """
        )
        status = self.flight_rules(m['flight_rules'])
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
        embed.set_footer(text=elapsed)
        await ctx.send(embed=embed, delete_after=120)


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
        except (discord.errors.NotFound, discord.errors.Forbidden, discord.errors.HTTPException):
            pass


def setup(bot: commands.Bot):
    bot.add_cog(Metar(bot))