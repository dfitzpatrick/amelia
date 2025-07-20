from typing import TYPE_CHECKING

import discord
from discord import ui, Interaction

import logging

from .services import convert_schemas_to_role_objects
if TYPE_CHECKING:
    from .config import AutoRoleConfig

log = logging.getLogger(__name__)


class ConfirmSyncModal(ui.Modal, title="Sync all auto-roles to all users"):

    def __init__(self, cog: 'AutoRoleConfig', **kwargs):
        super().__init__(**kwargs)
        self.cog: AutoRoleConfig = cog

    answer: ui.TextInput = ui.TextInput(label="type yes to confirm")

    async def on_submit(self, itx: Interaction) -> None:
        if self.answer.value.upper() != "YES":
            return
        guild = self.cog.bot.get_guild(itx.guild_id)  # type: ignore

        if guild is None:
            await itx.response.send_message("Something went wrong. Could not locate guild from cache", ephemeral=True)
            return
        async with self.cog.bot.db as session:
            log.debug(f"calling guild_auto_roles({itx.guild_id})")
            schemas = await session.auto_roles.guild_auto_roles(guild.id)
            auto_roles = convert_schemas_to_role_objects(guild, schemas)
        try:
            for member in guild.members:
                for role in auto_roles:
                    if role not in member.roles:
                        await member.add_roles(role)
        except discord.Forbidden:
            await itx.response.send_message(
                "Autorole sync has failed. The bot does not have permissions to add roles", 
                ephemeral=True
            )
        else:
            await itx.response.send_message('Autorole sync has completed', ephemeral=True)
