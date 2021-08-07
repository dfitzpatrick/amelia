from amelia.mixins.avwx import AVWX, AvwxResponse, AvwxEmptyResponseError
from amelia.mixins.sunriseset import SunRiseSet, SunRiseSetResponse, SunRiseSetInvalidException
from discord.ext import commands
import discord
import textwrap
import dateutil.parser
from datetime import datetime, timezone
import aiohttp
import logging
import typing
from amelia import AmeliaBot

log = logging.getLogger(__name__)

class Station(AVWX, SunRiseSet, commands.Cog):

    def __init__(self, bot: AmeliaBot):
        super(Station, self).__init__()
        self.bot = bot

    @commands.command(name='station')
    async def station(self, ctx: commands.Context, icao: str):
        """
        Displays an embed with station information.
        Parameters
        ----------
        ctx
        icao: the icao code of the airport

        Returns
        -------

        """
        _zulu_fmt = '%H:%MZ'
        try:
            icao_code = icao.upper()
            if icao_code == 'KMOO':
                # easter egg
                icao_code = 'KDVT'
            s = await self.fetch_station_info(icao_code)
        except AvwxEmptyResponseError:
            title = 'Missing Station'
            description = 'This ICAO has no Station Information'
            embed = discord.Embed(title=title, description=description)
            await ctx.send(embed=embed, delete_after=10)
            return

        if 'error' in s.keys():
            raise commands.BadArgument(s['error'])

        icao = icao.upper()
        city = s['city']
        country = s['country']
        elev_m = s['elevation_m']
        elev_ft = s['elevation_ft']
        website = s['website']
        wiki = s['wiki']
        lat = s['latitude']
        long = s['longitude']
        runways = s['runways']
        flag_emoji = f':flag_{country.lower()}:'
        rwys = '\n'.join(f"{o['ident1']}/{o['ident2']}: {o['length_ft']}x{o['width_ft']}"
                for o in runways
        ) or "N/A"
        now = datetime.now(timezone.utc)
        generated = now.strftime(f"%b %d at {_zulu_fmt}")

        # Get Sunset and Sunrise information
        try:
            ss = await self.fetch_sun_rise_set(lat, long)
            sunrise = dateutil.parser.parse(ss['sunrise']).strftime(_zulu_fmt)
            sunset = dateutil.parser.parse(ss['sunset']).strftime(_zulu_fmt)
            ctb = dateutil.parser.parse(ss['civil_twilight_begin']).strftime(_zulu_fmt)
            cte = dateutil.parser.parse(ss['civil_twilight_end']).strftime(_zulu_fmt)


        except SunRiseSetInvalidException as e:
            sunrise, sunset, ctb, cte = 'N/A', 'N/A', 'N/A', 'N/A'

        desc = textwrap.dedent(f"""
            Generated {generated}
            [Website]({website})
            [Wiki]({wiki})
            
            [Satellite View](https://www.google.com/maps/@?api=1&map_action=map&center={lat},{long}&zoom=14&basemap=satellite)
        """)

        embed = discord.Embed(title=f"{icao} Station Information", description=desc)
        embed.add_field(name=f'{flag_emoji} Location', value=f'{country}/{city}')
        embed.add_field(name=":regional_indicator_e: Elevation", value=f"{elev_ft}ft / {elev_m}m")
        embed.add_field(name=':left_right_arrow: Latitude', value=lat)
        embed.add_field(name=':arrow_up_down: Longitude', value=long)
        embed.add_field(name=':sunrise_over_mountains: Civil Twilight Begins', value=ctb)
        embed.add_field(name=':sunrise: Sunrise', value=sunrise)
        embed.add_field(name=':city_sunset: Sunset', value=sunset),
        embed.add_field(name=':crescent_moon: Civil Twilight Ends', value=cte)
        embed.add_field(name=':airplane_arriving: Runways', value=rwys, inline=False)

        embed.set_footer(
            text=f"{ctx.author.display_name} | Not an official source for flight planning",
            icon_url=ctx.author.avatar_url
        )
        await ctx.send(embed=embed)

    @station.error
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
                        Syntax: *{pfx}station **ICAO***

                        *ICAO*: The airport code (ex: KLGB)
                    """
            )
        elif isinstance(error, commands.BadArgument):
            message = textwrap.dedent(
                f"""
                    {error}

                    Syntax: *{pfx}station **ICAO***

                    *ICAO*: The airport code (ex: KLGB)
                    """
            )

        elif isinstance(error, aiohttp.ClientResponseError):
            message = "The API service is currently down. Try again later"
        else:
            log.error(error)
            raise error

        embed = discord.Embed(title="Station Unavailable", description=message)
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
        await self.bot.hook_command_completion(ctx)

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
        await self.bot.hook_command_error(ctx, error)

def setup(bot: AmeliaBot):
    bot.add_cog(Station(bot))