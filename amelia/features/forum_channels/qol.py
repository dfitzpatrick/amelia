from __future__ import annotations
from discord.ext import commands
from discord import app_commands
import discord

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from amelia.bot import AmeliaBot


class ForumQOL(commands.Cog):

    def __init__(self, bot: AmeliaBot):
        self.bot = bot

    @app_commands.command(name='op', description="Retrieves the Original Message from a thread/forum post")
    async def op_context(self, itx: discord.Interaction):
        if not isinstance(itx.channel, discord.Thread):
            raise TypeError("This command can only be done in a thread / forum post")
        if itx.channel_id is None:
            return
        message = await itx.channel.fetch_message(itx.channel_id)
        description = message.content
        name = message.author.display_name
        avatar = message.author.display_avatar.url
        embed = discord.Embed(title=f"{name} says...", description=description)
        embed.set_thumbnail(url=message.author.display_avatar.url)
        embed.set_footer(icon_url=avatar, text=name)
        embed.timestamp = message.created_at
        embed.url = message.jump_url
        await itx.response.send_message(embed=embed, ephemeral=True)

    @op_context.error
    async def op_context_error(self, itx, error: app_commands.AppCommandError):
        original = error.original if isinstance(error, app_commands.errors.CommandInvokeError) else error
        if isinstance(original, TypeError):
            await itx.response.send_message("You can only run this command in a thread/forum post", ephemeral=True)
        elif isinstance(original, discord.NotFound):
            await itx.response.send_message("Could not retrieve the original message", ephemeral=True)
        else:
            raise