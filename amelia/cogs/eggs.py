from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

import discord
from discord.ext import commands
from datetime import datetime, timezone, timedelta
if TYPE_CHECKING:
    from amelia.bot import AmeliaBot

log = logging.getLogger(__name__)


class EasterEggCog(commands.Cog):
    def __init__(self, bot: AmeliaBot):
        self.bot = bot
        self.hi_timestamp: datetime = datetime.now(timezone.utc)

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

    async def on_message_r_flying_beacon_hi(self, message: discord.Message):
        now = datetime.now(timezone.utc)
        predicates = [
            message.guild.id == 379051048129789953,  # r/flying
            message.author.id == 1071113753225068734,  # Beacon
            now >= self.hi_timestamp
        ]
        if not all(predicates):
            return
        content = message.content.lower()
        if content.startswith("hi") or "how are you" in content:
            try:
                await message.reply("Hi! How are you?")
            except (discord.Forbidden, discord.HTTPException):
                log.debug("could not send easter egg message due to permissions")
            finally:
                self.hi_timestamp = now + timedelta(hours=1)


    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.id == self.bot.user.id:
            return
        await self.on_message_r_flying_easter_egg(message)
        await self.on_message_r_flying_beacon_hi(message)

async def setup(bot):
    await bot.add_cog(EasterEggCog(bot))
