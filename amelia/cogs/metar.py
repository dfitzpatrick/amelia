import logging
import textwrap
import typing

import aiohttp
import dateutil.parser
import discord
from discord.ext import commands

commands.has_permissions()
from amelia.mixins.avwx import AVWX, AvwxResponse, AvwxEmptyResponseError
from amelia.mixins.config import ConfigMixin
from amelia import common
from amelia import AmeliaBot
from ameliapg.metar.models import MetarDB, MetarChannelDB
from ameliapg.errors import DuplicateEntity
from ameliapg.models import PgNotify
from ameliapg import PgActions
import typing as t

log = logging.getLogger(__name__)

class FlightRule(typing.NamedTuple):
    emoji: str
    name: str

class Metar(AVWX, commands.Cog):
    def __init__(self, bot: AmeliaBot):
        super(Metar, self).__init__()
        self.bot = bot
        self.cfg: t.Dict[int, MetarDB] = {}
        self.metar_channels: t.Dict[int, t.List[discord.TextChannel]] = {}


    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        try:
            await self.bot.pg.new_metar_config(guild.id)
        except DuplicateEntity:
            log.debug(f"Rejoined Guild: {guild.name} with existing Metar Config")

    @commands.Cog.listener()
    async def on_safe_to_sync(self):
        self.bot.pg.register_listener(self._notify)
        self.cfg = await self.bot.map_guild_configs(self.bot.pg.fetch_metar_configs)
        await self.bot.sync_configs(self.cfg, self.bot.pg.new_metar_config)

        chs = await self.bot.pg.fetch_all_metar_channels()
        for c in chs:
            if c.guild_id not in self.metar_channels.keys():
                self.metar_channels[c.guild_id] = []
            guild = self.bot.get_guild(c.guild_id)
            if guild is None:
                continue
            tc = discord.utils.get(guild.text_channels, id=c.channel_id)
            if tc is not None:
                self.metar_channels[c.guild_id].append(tc)


    def _channel_ids(self, guild_id: int) -> t.List[int]:
        if not guild_id in self.metar_channels.keys():
            return []
        return [o.id for o in self.metar_channels[guild_id]]

    def _channel_objs(self, guild_id: int) -> t.List[discord.TextChannel]:
        if not guild_id in self.metar_channels.keys():
            return []
        return [o for o in self.metar_channels[guild_id]]

    async def _metar_channel_notification(self, entity: MetarChannelDB, action: str):
        guild_id = entity.guild_id
        if action == PgActions.DELETE or action == PgActions.UPDATE:
            if guild_id not in self.metar_channels.keys():
                return
            chs = self.metar_channels[guild_id]
            self.metar_channels[guild_id] = [o for o in chs if o.id != entity.channel_id]

        if action == PgActions.DELETE:
            return

        if guild_id not in self.metar_channels.keys():
            self.metar_channels[guild_id] = []

        guild = self.bot.get_guild(guild_id)
        if guild is None:
            return
        tc = discord.utils.get(guild.text_channels, id=entity.channel_id)
        if tc is not None:
            self.metar_channels[guild_id].append(tc)



    async def _notify(self, payload: PgNotify):
        await self.bot.notify_t(MetarDB, self.cfg, payload)
        if isinstance(payload.entity, MetarChannelDB):
            await self._metar_channel_notification(payload.entity, payload.action)



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


    @commands.command()
    async def metar(
            self, ctx: commands.Context,
            icao: str = commands.Option(description="The ICAO code for the airport")
    ):
        """
        Fetches the urrent METAR observation from the supplied icao.
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
            
            [Click here for more information](http://theflying.life/airports/{icao_code})
            
            {raw}
            """
        )
        remark_keys = m['translate']['remarks'].keys()
        if '_$' in remark_keys or '$' in remark_keys:
            description = "**Warning: This metar information is incomplete or requires servicing. This may cause the following station to report wrong such as Flight Rules**\n\n" + description
        status = common.FlightRule.create(m['flight_rules'])
        title = f"{status.emoji} {icao} ({status.name})"
        embed = discord.Embed(title=title, description=description, url=common.TFL_URL + f"/airports/{icao}")
        embed.add_field(name=":wind_chime: Wind", value=wind)
        embed.add_field(name=':eyes: Visibility', value=visibility)
        embed.add_field(name=':cloud: Clouds', value=clouds)
        embed.add_field(name=':thermometer: Temp', value=temp)
        embed.add_field(name=':regional_indicator_d: Dewpoint', value=dew)
        embed.add_field(name=':a: Altimeter', value=altimeter)
        embed.add_field(name=':cloud_rain: Weather', value=weather)
        embed.add_field(name=':pencil: Remarks', value=remarks, inline=False)

        embed.timestamp = valid_time
        embed.set_footer(
            text=f"{ctx.author.display_name} | Not an official source for flight planning",
            icon_url=ctx.author.display_avatar.url,
        )
        # Send to channel with auto delete if its not the metar channel
        if ctx.channel.id not in self._channel_ids(ctx.guild.id):
            delay = self.cfg[ctx.guild.id].delete_interval
            await ctx.send(embed=embed, delete_after=delay)
            if len(self.metar_channels.get(ctx.guild.id, [])) > 0:
                ch = self.metar_channels[ctx.guild.id][0]
                await ch.send(embed=embed)
                await ctx.send(f"Your Metar is auto-moving to {ch.mention}", delete_after=delay)
        else:
            await ctx.send(embed=embed)





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
            embed = discord.Embed(title="Metar Unavailable", description="Unknown Error")
            await ctx.send(embed=embed, delete_after=30)
            log.error(error)
            raise error

        embed = discord.Embed(title="Metar Unavailable", description=message)
        await ctx.send(embed=embed, delete_after=30)

    @commands.group()
    async def metar_config(self, ctx):
        pass

    @metar_config.command(name='channel')
    @commands.has_guild_permissions(manage_channels=True)
    async def metar_channel_cmd(self, ctx: commands.Context, ch: discord.TextChannel = None):

        if ch is None:
            description = "\n".join(ch.mention for ch in self._channel_objs(ctx.guild.id))
            embed = discord.Embed(title="Current Metar Channels", description=description)
            await ctx.send(embed=embed, delete_after=20)
            return

        channel_ids = self._channel_ids(ctx.guild.id)

        if ch.id in channel_ids:
            await self.bot.pg.remove_metar_channel(ch.id)
            action = "Removed"
        else:
            await self.bot.pg.add_metar_channel(ctx.guild.id, ch.id)
            action = "Added"
        await ctx.send(f"{action} Metar Channel {ch.mention}", delete_after=10)



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
    bot.add_cog(Metar(bot))