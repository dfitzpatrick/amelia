
from __future__ import annotations
import logging
from typing import TYPE_CHECKING, Optional

import discord
from discord.ext import commands
from discord import app_commands
if TYPE_CHECKING:
    from src.bot import AmeliaBot

log = logging.getLogger(__name__)
NOTIFICATIONS_GUILD_SNOWFLAKE = discord.Object(379051048129789953)
NOTIFICATIONS_FORUM_ID = 1019661716763717702
NOTIFICATIONS_ROLE_ID = 1203538269183287378
NOTFICATION_CHANNEL_ID = 463039398330761237

class FlyingCog(commands.Cog):
    def __init__(self, bot: AmeliaBot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_thread_create(self, thread: discord.Thread):
        embed = discord.Embed(description="Want to enable/disable notifications for new topics? Type /classroom-notify")
        msg = "Hey {}, there's a new thread in classroom {}"
        role = thread.guild.get_role(NOTIFICATIONS_ROLE_ID)
        channel_notify = thread.guild.get_channel(NOTFICATION_CHANNEL_ID)
        if role is None or not isinstance(channel_notify, discord.TextChannel) or \
            thread.parent and thread.parent.id != NOTIFICATIONS_FORUM_ID:
            log.warning("Forum Notification Predicate Failed")
            return
        try:
            await thread.send(embed=embed)
            await channel_notify.send(msg.format(role.mention, thread.jump_url))
        except discord.Forbidden as e:
            log.warning(f"{channel_notify.guild.id}/{channel_notify.id}: Forum Notification No Permissions")

        except (discord.HTTPException, discord.NotFound):
            log.warning(f"{channel_notify.guild.id}/{channel_notify.id}: Forum Notification Error")

    @app_commands.command(name='classroom-notify', description="Adds or Removes you from Classroom Post Notifications")
    @app_commands.guilds(NOTIFICATIONS_GUILD_SNOWFLAKE)
    async def classroom_notify_cmd(self, interaction: discord.Interaction):
        role = interaction.guild and interaction.guild.get_role(NOTIFICATIONS_ROLE_ID)
        user = interaction.user
        if role is None:
           raise ValueError("Role not found.")
        if not isinstance(user, discord.Member):
            raise ValueError("Must be ran in a guild")
        
        action = "enabled" if role not in user.roles else "disabled"
        reason = f"User {action} classroom notifications"
        if action == 'enabled':
            await user.add_roles(role, reason=reason)
        else:
            await user.remove_roles(role, reason=reason)
        await interaction.response.send_message(f"Classroom notifications are {action}", ephemeral=True)

    @classroom_notify_cmd.error
    async def on_add_channel_error(self, interaction: discord.Interaction, wrapped_error: app_commands.AppCommandError):
        error = wrapped_error.original if isinstance(wrapped_error, app_commands.errors.CommandInvokeError) else wrapped_error
        if isinstance(error, ValueError):
            await interaction.response.send_message(f"Could not change notification settings: {str(error)}", ephemeral=True)
        if isinstance(error, discord.Forbidden):
            await interaction.response.send_message("No Permissions to alter member roles")
        else:
            raise

async def setup(bot):
    await bot.add_cog(FlyingCog(bot))