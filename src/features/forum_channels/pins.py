from __future__ import annotations
from discord import app_commands
from discord.ext import commands
import discord
from typing import TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from src.bot import AmeliaBot

log = logging.getLogger(__name__)


class AutoPinsCog(commands.GroupCog, group_name='autopin'):

    def __init__(self, bot: AmeliaBot):
        self.bot = bot


    @app_commands.checks.has_permissions(manage_channels=True)
    @app_commands.command(name='add', description="Adds auto-pinning capabilities to a forum channel")
    async def add_channel(self, itx: discord.Interaction, channel: discord.ForumChannel):
        if itx.guild_id is None:
            return
        if not isinstance(channel, discord.ForumChannel):
            raise TypeError("Channel must be a Forum Channel")

        async with self.bot.db as session:
            await session.forum_channels.create_auto_pin(itx.guild_id, channel.id)
            await session.commit()

        await itx.response.send_message(f"Auto-pins enabled on {channel.name}", ephemeral=True)

    @app_commands.checks.has_permissions(manage_channels=True)
    @app_commands.command(name='remove', description="Removes auto-pinning capabilities to a forum channel")
    async def remove_channel(self, itx: discord.Interaction, channel: discord.ForumChannel):
        if not isinstance(channel, discord.ForumChannel):
            raise TypeError("Channel must be a Forum Channel")

        async with self.bot.db as session:
            await session.forum_channels.delete_auto_pin(channel.id)
        await itx.response.send_message(f"Auto-pins disabled on {channel.name}", ephemeral=True)

    async def auto_pin_enabled(self, channel_id: int):
        async with self.bot.db as session:
            enabled = await session.forum_channels.has_auto_pin(channel_id)
            return enabled

    @add_channel.error
    @remove_channel.error
    async def on_add_channel_error(self, itx: discord.Interaction, error: app_commands.AppCommandError):
        unwrapped_error = error.original if isinstance(error, app_commands.errors.CommandInvokeError) else error
        if isinstance(unwrapped_error, app_commands.MissingPermissions):
            await itx.response.send_message("You do not have permissions to use this command", ephemeral=True)
        else:
            raise

    @commands.Cog.listener()
    async def on_thread_create(self, thread: discord.Thread):
        parent = thread.parent

        if not isinstance(parent, discord.ForumChannel) or not await self.auto_pin_enabled(parent.id):
            return
        message = thread.get_partial_message(thread.id)
        try:
            await message.pin(reason="OP")
        except discord.Forbidden as e:
            log.warning(f"Auto-pin failed in {thread.guild.id}/'{thread.guild.name}' Missing Permissions - {e}")

        except (discord.HTTPException, discord.NotFound):
            pass



