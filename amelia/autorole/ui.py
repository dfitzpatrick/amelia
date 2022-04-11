import textwrap
from typing import TYPE_CHECKING

import discord
from discord import ui, Interaction


from amelia.bot import AmeliaBot
import logging
if TYPE_CHECKING:
    from amelia.autorole.config import AutoRoleConfig

log = logging.getLogger(__name__)


class ConfirmSyncModal(ui.Modal, title="Sync all auto-roles to all users"):

    def __init__(self, cog: 'AutoRoleConfig', **kwargs):
        super().__init__(**kwargs)
        self.cog = cog

    answer = ui.TextInput(label="type yes to confirm")

    async def on_submit(self, itx: Interaction) -> None:
        if self.answer.value.upper() != "YES":
            return
        guild = self.cog.bot.get_guild(itx.guild_id)
        auto_roles = self.cog.cache.item.get(itx.guild_id, [])
        if guild is None:
            await itx.response.send_message("Something went wrong. Could not locate guild from cache", ephemeral=True)
            return
        try:
            for member in guild.members:
                for role in auto_roles:
                    if role not in member.roles:
                        await member.add_roles(role)
        except discord.Forbidden:
            await itx.response.send_message("Autorole sync has failed. The bot does not have permissions to add roles", ephemeral=True)
        else:
            await itx.response.send_message('Autorole sync has completed', ephemeral=True)


