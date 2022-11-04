from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

import discord
from discord.ext import commands

if TYPE_CHECKING:
    from amelia.bot import AmeliaBot

log = logging.getLogger(__name__)


class EasterEggCog(commands.Cog):
    def __init__(self, bot: AmeliaBot):
        self.bot = bot

    def find_emoji(self, guild: discord.Guild, emoji_name: str, fallback_name: str) -> Optional[discord.Emoji]:
        fallback: Optional[discord.Emoji] = None
        for emoji in guild.emojis:
            if emoji.name == emoji_name:
                return emoji
            if emoji.name == fallback_name and fallback is None:
                fallback = emoji
        return fallback

    async def on_message_r_flying_easter_egg(self, message: discord.Message):
        predicates = [
            message.guild.id == 379051048129789953,     # r/flying
            message.channel.id == 383128744115830785,   # #metar-chat
            message.author.id == 491769129318088714     # NTSB_BOT
        ]
        if not all(predicates):
            return

        emoji = self.find_emoji(message.guild, 'ragerock', 'rage')
        try:
            if emoji is not None:
                await message.add_reaction(emoji)
        except discord.HTTPException as e:
            log.error(e)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.id == self.bot.user.id:
            return
        await self.on_message_r_flying_easter_egg(message)

async def setup(bot):
    await bot.add_cog(EasterEggCog(bot))
