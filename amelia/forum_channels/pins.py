from __future__ import annotations
from discord import app_commands
from discord.ext import commands
import discord
from typing import TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from amelia.bot import AmeliaBot

log = logging.getLogger(__name__)

class AutoPinsCog(commands.GroupCog, group_name='autopin'):

    def __init__(self, bot: AmeliaBot):
        self.bot = bot

    @app_commands.command(name='op')
    async def op_context(self, itx: discord.Interaction):
        if not isinstance(itx.channel, discord.Thread):
            raise TypeError("This command can only be done in a thread / forum post")
        message = await itx.channel.fetch_message(itx.channel_id)

        description = message.content
        embed = discord.Embed(title="Originating Post", description=description)
        await itx.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name='add')
    async def add_channel(self, itx: discord.Interaction, channel: discord.ForumChannel):
        if not isinstance(channel, discord.ForumChannel):
            raise TypeError("Channel must be a Forum Channel")

        async with self.bot.pg as db:
            await db.forum_channels.create_auto_pin(itx.guild_id, channel.id)

        await itx.response.send_message(f"Auto-pins enabled on {channel.name}")

    @app_commands.command(name='remove')
    async def remove_channel(self, itx: discord.Interaction, channel: discord.ForumChannel):
        if not isinstance(channel, discord.ForumChannel):
            raise TypeError("Channel must be a Forum Channel")

        async with self.bot.pg as db:
            await db.forum_channels.delete_auto_pin(channel.id)
        await itx.response.send_message(f"Auto-pins disabled on {channel.name}")

    async def auto_pin_enabled(self, channel_id: int):
        async with self.bot.pg as db:
            query = "select count(id) from autopins where parent_id = $1;"
            count = await db.connection.fetchval(query, channel_id)
            return count > 0

    @commands.Cog.listener()
    async def on_thread_create(self, thread: discord.Thread):
        parent = thread.parent

        if not isinstance(parent, discord.ForumChannel) or not await self.auto_pin_enabled(parent.id):
            return
        message = thread.get_partial_message(thread.id)
        try:
            await message.pin(reason="OP")
        except discord.Forbidden:
            log.warning(f"Auto-pin failed in {thread.guild.id}/'{thread.guild.name}' Missing Permissions")

        except (discord.HTTPException, discord.NotFound):
            pass



