import asyncio
import inspect
import logging
import textwrap
import typing
from datetime import datetime, timedelta

import discord
from discord.ext import commands

from amelia.mixins.config import ConfigMixin

log = logging.getLogger(__name__)

class Classroom(ConfigMixin, commands.Cog):
    """
    This COG is responsible for facilitating a classroom-like setting in
    discord.

    An administrator can designate "classroom" channels
    An administrator can designate which role(s) can use this

    When invoked, a free channel will lock between the user and any guests that they specify
        If all channels are in use. The command will issue an error.

    The user can add additional guests by mentioning them.
    The user can end the session by typing the command again at any time.
    Sessions will auto-end if no activity is present for 5 minutes.


    !cr add-channel CHANNEL_ID
    !cr del-channel CHANNEL_ID
    !cr ls-channel CHANNEL_ID

    !cr add-role CHANNEL_ID
    !cr del-role CHANNEL_ID
    !cr ls-role CHANNEL_ID

    !cr @Names - Create
    !cr - End


    """

    def __init__(self, bot: commands.Bot):
        super(Classroom, self).__init__()
        self.bot = bot
        self.channels_key = 'classroom_channels'
        self.allows_key = 'classroom_auto_allow'
        self.timeout = 5*60


    def get_allows(self, guild: discord.Guild) -> typing.List[typing.Union[discord.Member, discord.Role]]:
        """
        Gets all the roles or users that are auto-allowed to post in the classroom when locked
        Parameters
        ----------
        guild: The guild for the auto-allows

        Returns
        -------
        List[Union[discord.Member, discord.Role]]
        """
        guild_id_str = str(guild.id)
        result = []
        try:
            allows: typing.List[int] = self.config_settings[guild_id_str][self.allows_key]
            initial_count = len(allows)
            for id in allows:
                o = discord.utils.get(guild.roles, id=id) or discord.utils.get(guild.members, id=id)
                if o is None:
                    allows.remove(id)
                else:
                    result.append(o)
                if len(allows) < initial_count:
                    self.config_settings[guild_id_str][self.allows_key] = allows
                    self.save_settings()
            return result
        except KeyError:
            return []

    def get_classroom_channels(self, guild: discord.Guild) -> typing.List[discord.TextChannel]:
        """
        Retrieves the "classroom" channels from the configuration.
        Parameters
        ----------
        guild: The guild to retrieve channel configuration for

        Returns
        -------
        List[discord.TextChannel]
        """
        guild_id_str = str(guild.id)
        result = []
        try:
            channels: typing.List[int] = self.config_settings[guild_id_str][self.channels_key]
            inital_channel_count = len(channels)
            for ch in channels:
                obj = discord.utils.get(guild.text_channels, id=ch)
                if obj is None:
                    # This channel was deleted. Clean it from the config object
                    channels.remove(ch)
                else:
                    result.append(obj)
            if len(channels) < inital_channel_count:
                self.config_settings[guild_id_str][self.channels_key] = channels
                self.save_settings()

            return result
        except KeyError:
            return []

    def is_member(self, channel: discord.TextChannel, obj: typing.Union[discord.Member, discord.Role]):
        """
        Checks if a discord member is a 'member' in the classroom. This means
        that they either have a role that is allowed or a user permission to
        chat in the channel.
        Parameters
        ----------
        channel: the discord.TextChannel to validate
        obj: The obj to validate

        Returns
        -------
        bool
        """
        try:
            overwrites = channel.overwrites[obj]
            return not overwrites.is_empty()
        except KeyError:
            return False

    def is_allowed(self, guild: discord.Guild, member: discord.Member):
        """
        Is this user on the server 'allow' list. Ergo, they can always
        chat in a classroom.
        Parameters
        ----------
        guild: The guild to check
        member: The member to check

        Returns
        -------
        bool
        """
        allows = self.get_allows(guild)
        manage_channels = member.guild_permissions.manage_channels
        return manage_channels or any([obj in allows for obj in member.roles + [member]])

    def is_classroom(self, channel: discord.TextChannel):
        """
        Returns a bool if the TextChannel is listed in the 'channel' configuration.
        Parameters
        ----------
        channel: The TextChannel to check

        Returns
        -------
        bool
        """
        channel_ids = [ch.id for ch in self.get_classroom_channels(channel.guild)]
        return channel.id in channel_ids

    def is_open(self, channel: discord.TextChannel):
        """
        Returns a bool if the channel does not have the @everyone permissions
        modified to deny send_messages
        Parameters
        ----------
        channel: the TextChannel to validate

        Returns
        -------
        bool
        """
        everyone = discord.utils.get(channel.guild.roles, name='@everyone')
        overwrites = channel.overwrites_for(everyone)
        send_messages = overwrites._values.get('send_messages', True)
        return send_messages

    def is_locked(self, channel: discord.TextChannel):
        """
        See is_open. This is a negation for semantics.
        Parameters
        ----------
        channel: the TextChannel to validate

        Returns
        -------
        bool
        """
        return not self.is_open(channel)

    def get_classrooms_by_member(self, member: discord.Member) -> typing.List[discord.TextChannel]:
        """
        Returns a list of TextChannels that a Member is associated with.
        Parameters
        ----------
        member: The member to validate

        Returns
        -------
        List[discord.TextChannel]
        """
        channels = self.get_classroom_channels(member.guild)
        return [ch for ch in channels if self.is_member(ch, member)]

    def embed_list(self, seq: typing.List[typing.Any], attr: str, title="Listing") -> discord.Embed:
        """
        Simple function to make a list of all entries of a List
        Parameters
        ----------
        seq: The sequence to evaluate
        attr: The attribute to apply on the object for the string result
        title: The discord embed title

        Returns
        -------
        discord.Embed
        """
        lst = '\n'.join(getattr(obj, attr) for obj in seq)
        embed = discord.Embed(title=title, description=lst)
        return embed

    def get_first_free_channel(self, guild) -> typing.Optional[discord.TextChannel]:
        """
        Retrieves the first channel that can be used by the command
        Parameters
        ----------
        guild

        Returns
        -------
        Optional[discord.TextChannel]
        """
        channels = self.get_classroom_channels(guild)
        for ch in channels:
            if self.is_open(ch):
                return ch

    async def activity_monitor(self, channel: discord.TextChannel):
        """
        Used to evaluate if a channel was abandoned and will auto-unlock after
        a specific timeout.
        Parameters
        ----------
        channel: the channel to Validate

        Returns
        -------

        """
        await asyncio.sleep(self.timeout)
        if self.is_classroom(channel) and self.is_locked(channel):
            now = datetime.utcnow()
            message:discord.Message = channel.last_message
            message_time = message.created_at
            delta = now - message_time

            if delta >= timedelta(seconds=self.timeout - 2):
                await self.end_class(channel, self.bot.user)

    async def start_class(self, channel: discord.TextChannel, teacher: discord.Member, members_or_roles: typing.List[discord.Member]):
        """
        Locks a channel into classroom mode that prohibits everyone from sending messages
        except for those invited.
        Parameters
        ----------
        channel: the channel to lock
        teacher: the person initiating the class
        members: The initial list of members to invite

        Returns
        -------
        None
        """
        pfx = self.bot.command_prefix
        everyone = discord.utils.get(channel.guild.roles, name='@everyone')
        allows = self.get_allows(channel.guild)
        await channel.set_permissions(everyone, send_messages=False)
        await channel.set_permissions(teacher, send_messages=True)
        for member in members_or_roles:
            await channel.set_permissions(member, send_messages=True)
        for obj in allows:
            if isinstance(obj, discord.Member) and not self.is_member(channel, obj):
                await channel.set_permissions(obj, send_messages=True)
            else:
                await channel.set_permissions(obj, send_messages=True)

        description = textwrap.dedent(f"""
            {teacher.mention} has temporarily locked this channel for classroom purposes.
            Only those that are invited can currently send messages in this channel.
            
            This is done to keep the learning on topic and controlled. If you require assistance,
            please wait until the channel is open again, or ask in another relevant channel.
            
            For {teacher.mention}:
            Invite others by mentioning their name
            You can end this at anytime by typing **{pfx}classroom**
            
            *This channel will auto unlock if there is no activity for 5 minutes.*
        """)
        mentions = ' '.join(member.mention if isinstance(member, discord.Member) else member.name for member in members_or_roles)
        embed = discord.Embed(title="Class In Progress", description=description, color=discord.Color.red())
        await channel.send(embed=embed)
        await channel.send(f"{teacher.mention} {mentions}")
        asyncio.ensure_future(self.activity_monitor(channel))
        log.info(f"{channel.guild.name}: {teacher.display_name} Started Classroom in {channel.name}")

    async def end_class(self, channel: discord.TextChannel, member: discord.Member):
        """
        Ends a channel from being in classroom mode and reopens all permissions to defaults.
        Parameters
        ----------
        channel: the channel to unlock
        member: the member initiating the command. Used for display purposes only.

        Returns
        -------
        None
        """
        overwrites = channel.overwrites
        if isinstance(overwrites, dict):
            for obj, overwrite in overwrites.items():
                await channel.set_permissions(obj, overwrite=None)

        description = textwrap.dedent(f"""
            {member.mention} has opened this room back into the public.
            You are now free to use this channel, but keep all discussions relevant.
        """)
        embed = discord.Embed(title="Channel Now Available", description=description, color=discord.Color.green())
        await channel.send(embed=embed)
        log.info(f"{channel.guild.name}: {member.display_name} Ended Classroom in {channel.name}")

    @commands.group(name='classroom', aliases=('cr',), invoke_without_command=True)
    async def classroom(self, ctx: commands.Context, members: commands.Greedy[discord.Member], roles: commands.Greedy[discord.Role]):
        """
        The main classroom command.
        When called with a list of members, it will lock the channel into classroom mode
        For brevity, this command can be used by itself to end the class.
        If no classroom exists, a syntax error will be displayed.
        Parameters
        ----------
        ctx
        members: the members to invite

        Returns
        -------
        None
        """
        channel = ctx.channel
        pfx = self.bot.command_prefix
        allowed = self.is_allowed(ctx.guild, ctx.author)

        if not self.is_allowed(ctx.guild, ctx.author):
            raise PermissionError("You are not authorized to use this function")
        if not members and not roles:
            # See if this person is closing out a session.
            classrooms = self.get_classrooms_by_member(ctx.author)
            if len(classrooms) == 0:
                missing_param = inspect.Parameter('members', inspect.Parameter.POSITIONAL_ONLY)
                raise commands.MissingRequiredArgument(missing_param)
            if self.is_classroom(channel) and self.is_locked(channel):
                # Technically we don't need to check if they are a member because
                # they wouldn't be able to type in this channel. This could be
                # an admin or someone with a permission override closing, and
                # that is acceptable.
                await self.end_class(channel, ctx.author)
        else:
            if self.is_classroom(channel) and self.is_open(channel):
                await self.start_class(channel, ctx.author, members + roles)
            else:
                open_channel = self.get_first_free_channel(ctx.guild)
                if open_channel is None:
                    raise Exception(f"No channels available. Create a classroom with {pfx}classroom channel channel_id")
                await self.start_class(open_channel, ctx.author, members + roles)

    @classroom.error
    async def classroom_error(self, ctx: commands.Context, error: commands.CommandError):
        """
        Generic Error Messages to display to the user
        Parameters
        ----------
        ctx
        error: the error class

        Returns
        -------
        None
        """
        if isinstance(error, commands.CommandInvokeError):
            error = error.original

        pfx = self.bot.command_prefix
        description = ""
        if isinstance(error, commands.MissingRequiredArgument):
            description = textwrap.dedent(f"""
            Syntax: *{pfx}classroom **Members***

            *Members*: Members (@Name) of who you want to have access to type. You can list more than one separated by a space.
            """)
        if isinstance(error, PermissionError) or isinstance(error, commands.MissingPermissions):
            description = "You are not authorized to use this feature. Contact an admin for more information."
        if isinstance(error, Exception):
            description = f"Error: {error}"
        if description != "":
            embed = discord.Embed(description=description, color=discord.Color.red())
            await ctx.send(embed=embed, delete_after=10)

    @commands.has_permissions(manage_channels=True)
    @classroom.command(name='channel', aliases=('ch', 'channels'))
    async def classroom_channel(self, ctx: commands.Context, channel: discord.TextChannel = None):
        """
        Allows a person with guild manage_channels to define which TextChannels are designated classrooms.
        Parameters
        ----------
        ctx
        channel: the channel to designate

        Returns
        -------
        None
        """
        guild_str_id = str(ctx.guild.id)
        channels = self.get_classroom_channels(ctx.guild)
        if channel is None:
            await ctx.send(embed=self.embed_list(channels, 'mention', 'Classroom Channels'), delete_after=10)
            return

        channel_ids = [ch.id for ch in self.get_classroom_channels(ctx.guild)]
        if channel.id in channel_ids:
            channel_ids.remove(channel.id)
        else:
            channel_ids.insert(0, channel.id)

        self.config_settings[guild_str_id][self.channels_key] = channel_ids
        self.save_settings()

    @commands.has_permissions(manage_channels=True)
    @classroom.command(name='allow')
    async def classroom_allow(self, ctx: commands.Context, obj: typing.Union[discord.Member, discord.Role] = None):
        """
        Allows a perosn with guild manage_channels to define which roles or members are Auto-Allowed into any Classroom setting.
        Parameters
        ----------
        ctx
        obj: either the role or member.

        Returns
        -------
        None
        """
        guild_str_id = str(ctx.guild.id)
        allows = self.get_allows(ctx.guild)
        if obj is None:
            await ctx.send(embed=self.embed_list(allows, 'mention', 'Classroom Permissions'), delete_after=10)
            return

        allow_ids = [allow.id for allow in self.get_allows(ctx.guild)]
        if obj.id in allow_ids:
            allow_ids.remove(obj.id)
        else:
            allow_ids.insert(0, obj.id)

        self.config_settings[guild_str_id][self.allows_key] = allow_ids
        self.save_settings()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """
        Default message listener to help manage classroom timeouts
        Parameters
        ----------
        message: the message object that was sent

        Returns
        -------
        None
        """
        if message.author == self.bot.user:
            return
        channel = message.channel
        if self.is_classroom(channel) and self.is_locked(channel):
            asyncio.ensure_future(self.activity_monitor(channel))

            for obj in message.mentions + message.role_mentions:
                if not self.is_member(channel, obj):
                    await channel.set_permissions(obj, send_messages=True)
                    await message.add_reaction(u"\u2705")  # Green Checkbox

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
            log.error(error)
            raise error.with_traceback(error.__traceback__)
        except (discord.errors.NotFound, discord.errors.Forbidden, discord.errors.HTTPException):
            log.debug('error discord exception')
            pass

def setup(bot: commands.Bot):
    bot.add_cog(Classroom(bot))