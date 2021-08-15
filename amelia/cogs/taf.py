import logging
import math
import textwrap
import typing

import aiohttp
import dateutil.parser
import discord
from discord.ext import commands
from datetime import datetime, timedelta

from amelia import common
from amelia.mixins.avwx import AVWX, AvwxEmptyResponseError, AvwxResponse
from amelia.mixins.config import ConfigMixin
from ameliapg.taf.models import TafDB, TafChannelDB
from ameliapg.errors import DuplicateEntity
from ameliapg.models import PgNotify
from ameliapg import PgActions
import re
from amelia import AmeliaBot
import typing as t

log = logging.getLogger(__name__)

class TAF(AVWX, ConfigMixin, commands.Cog):

    def __init__(self, bot: AmeliaBot):
        super(TAF, self).__init__()
        self.bot = bot
        self.time_format = '%b %d, %H:%M'
        self.cfg: t.Dict[int, TafDB] = {}
        self.taf_channels: t.Dict[int, t.List[discord.TextChannel]] = {}

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        try:
            await self.bot.pg.new_taf_config(guild.id)
        except DuplicateEntity:
            log.debug(f"Rejoined Guild: {guild.name} with existing Metar Config")

    @commands.Cog.listener()
    async def on_safe_to_sync(self):
        self.bot.pg.register_listener(self._notify)
        self.cfg = await self.bot.map_guild_configs(self.bot.pg.fetch_taf_configs)
        await self.bot.sync_configs(self.cfg, self.bot.pg.new_taf_config)

        chs = await self.bot.pg.fetch_all_taf_channels()
        for c in chs:
            if c.guild_id not in self.taf_channels.keys():
                self.taf_channels[c.guild_id] = []
            guild = self.bot.get_guild(c.guild_id)
            if guild is None:
                continue
            tc = discord.utils.get(guild.text_channels, id=c.channel_id)
            if tc is not None:
                self.taf_channels[c.guild_id].append(tc)

    def _channel_ids(self, guild_id: int) -> t.List[int]:
        if not guild_id in self.taf_channels.keys():
            return []
        return [o.id for o in self.taf_channels[guild_id]]

    def _channel_objs(self, guild_id: int) -> t.List[discord.TextChannel]:
        if not guild_id in self.taf_channels.keys():
            return []
        return [o for o in self.taf_channels[guild_id]]

    async def _taf_channel_notification(self, entity: TafChannelDB, action: str):
        guild_id = entity.guild_id
        if action == PgActions.DELETE or action == PgActions.UPDATE:
            if guild_id not in self.taf_channels.keys():
                return
            chs = self.taf_channels[guild_id]
            self.taf_channels[guild_id] = [o for o in chs if o.id != entity.channel_id]

        if action == PgActions.DELETE:
            return

        if guild_id not in self.taf_channels.keys():
            self.taf_channels[guild_id] = []

        guild = self.bot.get_guild(guild_id)
        if guild is None:
            return
        tc = discord.utils.get(guild.text_channels, id=entity.channel_id)
        if tc is not None:
            self.taf_channels[guild_id].append(tc)

    async def _notify(self, payload: PgNotify):
        await self.bot.notify_t(TafDB, self.cfg, payload)
        if isinstance(payload.entity, TafChannelDB):
            await self._taf_channel_notification(payload.entity, payload.action)

    def get_clouds(self, clouds: str) -> str:
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

    def get_type(self, taf_type: str):
        """
        Text formatting for common TAF types (FROM, BECMG, TEMPO).
        Resolves to the full english name.
        Parameters
        ----------
        taf_type: The parsed TAF type from the AVWX api

        Returns
        -------
        :class: str
        """
        taf_types = {
            'BECMG': 'BECOMING',
            'TEMPO': 'TEMPORARILY'
        }
        return taf_types.get(taf_type, taf_type)

    def map_times(self, m: AvwxResponse) -> typing.Dict[str, typing.Dict[str, typing.Any]]:
        """
        The AVWX Response for times does not handle transitions so well.
        We will manually parse the date and times from the API
        Parameters
        ----------
        forecast

        Returns
        -------

        """
        result = {}
        search_keys = ['start_time', 'end_time', 'transition_time']
        for f in m['forecast']:
            keys = f.keys()
            for sk in search_keys:
                if sk in keys:
                    repr = f[sk]['repr']
                    obj = f[sk]
                    if repr not in result.keys():
                        result[repr] = obj
        return result


    def parse_times(self, forecast: typing.Dict[str, typing.Any], mapping: typing.Dict[str, typing.Any])\
            -> typing.Tuple[common.AvwxTime, common.AvwxTime]:
        """
        The AVWX Response for times does not handle transitions so well.
        We will manually parse the date and times from the API if the format
        is there. Otherwise we will resort to the normal start/end
        Parameters
        ----------
        forecast

        Returns
        -------

        """
        pattern = r'[0-9]+\/[0-9]+'
        match = re.search(pattern, forecast['sanitized'])
        if match is not None:
            match = match[0]
            start, end = match.split('/')
            start_obj = mapping[start]
            end_obj = mapping[end]
            return common.AvwxTime.create(start_obj), common.AvwxTime.create(end_obj)
        return common.AvwxTime.create(forecast['start_time']), common.AvwxTime.create(forecast['end_time'])




    @commands.group(name='taf', invoke_without_command=True)
    async def taf(self, ctx: commands.Context, icao: str):
        """
        Retrieves a TAF from the ICAO provided.
        Parameters
        ----------
        ctx: Discord Context Class
        icao: the station identifier

        Returns
        -------
        None
        """
        await ctx.trigger_typing()
        try:
            icao_code = icao.upper()
            if icao_code == 'KMOO':
                # easter egg
                icao_code = 'KDVT'
            m = await self.fetch_taf(icao_code)
        except AvwxEmptyResponseError as e:
            title = 'Missing TAF'
            description = 'This ICAO has no TAF Information'
            embed = discord.Embed(title=title, description=description)
            await ctx.send(embed=embed, delete_after=10)
            return

        if 'error' in m.keys():
            raise commands.BadArgument(m['error'])
        time_maps = self.map_times(m)
        icao = icao.upper()
        station = m['station']
        original_time = m['time']['repr']
        raw = [f['raw'] for f in m['forecast']]

        raw.insert(0, f"{station} {original_time}")
        raw = '\n'.join(raw)
        t = ":regional_indicator_t:"
        now = dateutil.parser.parse(m['meta']['timestamp'])
        valid_time = dateutil.parser.parse(m['time']['dt'])
        valid_time_fmt = common.td_format(now - valid_time)
        elapsed = valid_time_fmt
        valid_fmt = valid_time.strftime(self.time_format)
        description = textwrap.dedent(
            f"""
            **__Taf Valid {valid_fmt}Z__**  
            *Note: This report was generated {elapsed} afterwards.*
            
            [Click here for more information](http://theflying.life/airports/{icao_code})
    
            {raw}
            """
        )
        title = f"{t} TAF {icao}"
        embed = discord.Embed(title=title, url=common.TFL_URL + f"/airports/{icao}", description=description)
        for idx, f in enumerate(m['forecast']):
            f_start, f_end = self.parse_times(f, time_maps)

            status = common.FlightRule.create(f['flight_rules'])
            taf_type = self.get_type(f['type'])
            if taf_type == 'FROM':
                title = "{} {} **__{}__** {}Z **__thru__** {}Z".format(
                    status.emoji,
                    status.name,
                    taf_type,
                    f_start.text,
                    f_end.text
                )
            else:
                title = "{} **__{}__** {} {} {}Z **__thru__** {}Z".format(
                    ":arrow_heading_up:",
                    taf_type,
                    status.emoji,
                    status.name,
                    f_start.text,
                    f_end.text,
                )

            embed_description = ""
            translations = m['translate']['forecast'][idx]
            for k, v in translations.items():
                k: str
                if v == '':
                    continue
                key = k.capitalize().replace("_", " ")
                if k == 'clouds':
                    v = self.get_clouds(v)

                embed_description += f"**{key}:** {v}\n"
            embed_description += '\u200b\n'
            embed.add_field(name=title, value=embed_description, inline=False)

        embed.timestamp = valid_time
        embed.set_footer(
            text=f"{ctx.author.display_name} | Not an official source for flight planning",
            icon_url=ctx.author.avatar_url
        )
        # Send to channel with auto delete if its not the metar channel
        restricted = self.cfg[ctx.guild.id].restrict_channel
        if ctx.channel.id not in self._channel_ids(ctx.guild.id) and restricted:
            delay = self.cfg[ctx.guild.id].delete_interval
            await ctx.send(embed=embed, delete_after=delay)
            if len(self.taf_channels.get(ctx.guild.id, [])) > 0:
                ch = self.taf_channels[ctx.guild.id][0]
                await ch.send(embed=embed)
                await ctx.send(f"Your TAF is auto-moving to {ch.mention}", delete_after=delay)
        else:
            await ctx.send(embed=embed)

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
            embed = discord.Embed(title="TAF Unavailable", description="Unknown Error")
            await ctx.send(embed=embed, delete_after=30)
            raise error


        embed = discord.Embed(title="TAF Unavailable", description=message)
        await ctx.send(embed=embed, delete_after=30)

    @taf.command(name='channel')
    @commands.has_guild_permissions(administrator=True)
    async def taf_channel_cmd(self, ctx: commands.Context, ch: discord.TextChannel = None):
        """
        Command that will set the given TAF channel to another channel and echo
        all responses back there
        Parameters
        ----------
        ctx: Discord Context Class
        ch: a discord.TextChannel of the channel to set to

        Returns
        -------
        None
        """
        if ch is None:
            description = "\n".join(ch.mention for ch in self._channel_objs(ctx.guild.id))
            embed = discord.Embed(title="Current TAF Channels", description=description)
            await ctx.send(embed=embed, delete_after=20)
            return

        channel_ids = self._channel_ids(ctx.guild.id)

        if ch.id in channel_ids:
            await self.bot.pg.remove_taf_channel(ch.id)
            action = "Removed"
        else:
            await self.bot.pg.add_taf_channel(ctx.guild.id, ch.id)
            action = "Added"
        await ctx.send(f"{action} TAF Channel {ch.mention}", delete_after=10)

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
    bot.add_cog(TAF(bot))