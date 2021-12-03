from amelia.mixins.avwx import AVWX, AvwxResponse, AvwxEmptyResponseError
from amelia.mixins.sunriseset import SunRiseSet, SunRiseSetResponse, SunRiseSetInvalidException
from discord.ext import commands
import discord
import textwrap
import dateutil.parser
from datetime import datetime, timezone
import aiohttp
import logging
import typing as t
from amelia import AmeliaBot
from ameliapg.station.models import StationDB, StationChannelDB
from ameliapg.server.models import GuildDB
from ameliapg.errors import DuplicateEntity
from ameliapg.models import PgNotify
from ameliapg import PgActions

log = logging.getLogger(__name__)

class Station(AVWX, SunRiseSet, commands.Cog):

    def __init__(self, bot: AmeliaBot):
        super(Station, self).__init__()
        self.bot = bot
        self.cfg: t.Dict[int, StationDB] = {}
        self.station_channels: t.Dict[int, t.List[discord.TextChannel]] = {}

    @commands.Cog.listener()
    async def on_new_guild_config(self, guild_db: GuildDB):
        id = guild_db.guild_id
        station_db = None
        try:
            station_db = await self.bot.pg.new_station_config(id)
        except DuplicateEntity:
            station_db = await self.bot.pg.fetch_station_config(id)
            log.debug(f"Rejoined Guild: {id} with existing Station Config")
        finally:
            self.station_channels[id] = await self.fetch_station_channels(id)
            self.cfg[id] = station_db

    async def fetch_station_channels(self, guild_id) -> t.List[discord.TextChannel]:
        guild = self.bot.get_guild(guild_id)
        if guild is None:
            return []
        channels = await self.bot.pg.fetch_taf_channels(guild_id)
        channels = map(lambda c: discord.utils.get(guild.text_channels, id=c.channel_id), channels)
        return [c for c in channels if c is not None]

    @commands.Cog.listener()
    async def on_safe_to_sync(self):
        self.bot.pg.register_listener(self._notify)
        self.cfg = await self.bot.map_guild_configs(self.bot.pg.fetch_station_configs)
        await self.bot.sync_configs(self.cfg, self.bot.pg.new_station_config)

        chs = await self.bot.pg.fetch_all_station_channels()
        for c in chs:
            if c.guild_id not in self.station_channels.keys():
                self.station_channels[c.guild_id] = []
            guild = self.bot.get_guild(c.guild_id)
            if guild is None:
                continue
            tc = discord.utils.get(guild.text_channels, id=c.channel_id)
            if tc is not None:
                self.station_channels[c.guild_id].append(tc)

    def _channel_ids(self, guild_id: int) -> t.List[int]:
        if not guild_id in self.station_channels.keys():
            return []
        return [o.id for o in self.station_channels[guild_id]]

    def _channel_objs(self, guild_id: int) -> t.List[discord.TextChannel]:
        if not guild_id in self.station_channels.keys():
            return []
        return [o for o in self.station_channels[guild_id]]

    async def _station_channel_notification(self, entity: StationChannelDB, action: str):
        guild_id = entity.guild_id
        if action == PgActions.DELETE or action == PgActions.UPDATE:
            if guild_id not in self.station_channels.keys():
                return
            chs = self.station_channels[guild_id]
            self.station_channels[guild_id] = [o for o in chs if o.id != entity.channel_id]

        if action == PgActions.DELETE:
            return

        if guild_id not in self.station_channels.keys():
            self.station_channels[guild_id] = []

        guild = self.bot.get_guild(guild_id)
        if guild is None:
            return
        tc = discord.utils.get(guild.text_channels, id=entity.channel_id)
        if tc is not None:
            self.station_channels[guild_id].append(tc)

    async def _notify(self, payload: PgNotify):
        await self.bot.notify_t(StationDB, self.cfg, payload)
        if isinstance(payload.entity, StationChannelDB):
            await self._station_channel_notification(payload.entity, payload.action)



    @commands.command(name='station')
    async def station(
            self, ctx: commands.Context,
            icao: str = commands.Option(description="The ICAO code for the airport. Ex: KLGB")
    ):
        """
        Displays helpful information about an airport including sunset times.
        Parameters
        ----------
        ctx
        icao: the icao code of the airport

        Returns
        -------

        """
        await ctx.trigger_typing()
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
            icon_url=ctx.author.display_avatar.url
        )
        restricted = self.cfg[ctx.guild.id].restrict_channel
        channel_ids = self._channel_ids(ctx.guild.id)
        if len(channel_ids) > 0 and ctx.channel.id not in channel_ids and restricted:
            delay = self.cfg[ctx.guild.id].delete_interval
            await ctx.send(embed=embed, delete_after=delay)
            if len(self.station_channels.get(ctx.guild.id, [])) > 0:
                ch = self.station_channels[ctx.guild.id][0]
                await ch.send(embed=embed)
                await ctx.send(f"Your Station Report is auto-moving to {ch.mention}", delete_after=delay)
        else:
            await ctx.send(embed=embed)

    @station.error
    async def station_error(self, ctx: commands.Context, error: t.Any):
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
            embed = discord.Embed(title="Station Unavailable", description="Unknown Error")
            await ctx.send(embed=embed, delete_after=30)
            log.error(error)
            raise error

        embed = discord.Embed(title="Station Unavailable", description=message)
        await ctx.send(embed=embed, delete_after=30)

    @commands.group()
    async def station_config(self, ctx):
        pass

    @station_config.command(name='channel')
    @commands.has_guild_permissions(manage_channels=True)
    async def station_channel_cmd(self,
        ctx: commands.Context,
        channel = commands.Option(
            default=None,
            description="The text channel to add/remove")
    ):
        """Adds/Removes a channel where Station Information will be used. No Argument shows a list of channels"""
        if channel is None:
            description = "\n".join(ch.mention for ch in self._channel_objs(ctx.guild.id))
            embed = discord.Embed(title="Current Station Channels", description=description)
            await ctx.send(embed=embed, delete_after=20)
            return

        channel_ids = self._channel_ids(ctx.guild.id)

        if channel.id in channel_ids:
            await self.bot.pg.remove_station_channel(channel.id)
            action = "Removed"
        else:
            await self.bot.pg.add_station_channel(ctx.guild.id, channel.id)
            action = "Added"
        await ctx.send(f"{action} Station Channel {channel.mention}", delete_after=10)

    @station_channel_cmd.error
    async def station_channel_cmd_error(self, ctx: commands.Context, error: commands.CommandError):
        await ctx.send(f"Unable to Set Station Channel. {error}", delete_after=10)

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