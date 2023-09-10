from __future__ import annotations
import discord
from asyncpg import UniqueViolationError
from discord import app_commands, Interaction, Role

from amelia.features.autorole.cache import AutoRoleCache
from amelia.features.autorole.ui import ConfirmSyncModal

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from amelia.bot import AmeliaBot


class AutoRoleConfig(app_commands.Group):
    def __init__(self, bot: AmeliaBot, cache: AutoRoleCache):
        super().__init__(name='autorole', description='Configuration commands for AutoRole')
        self.bot = bot

    @app_commands.command(name='add-role', description='Adds a role that will automatically be assigned on member join')
    @app_commands.describe(role="The role to auto-assign")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def add_auto_role(self, itx: Interaction, role: Role):
        async with self.bot.db as session:
            await session.auto_roles.add_auto_role(itx.guild_id, role.id)
            await session.commit()
        response = f"{role.name} Added to auto roles. Note that this will not sync automatically. To sync," \
                   f"please run the sync command specifically"
        await itx.response.send_message(response, ephemeral=True)

    @add_auto_role.error
    async def on_add_error(self, itx: Interaction, error: app_commands.CommandInvokeError):
        original = error.original
        if isinstance(original, UniqueViolationError):
            await itx.response.send_message("This role is already added.", ephemeral=True)
        else:
            await itx.response.send_message("Role not added. Unknown error", ephemeral=True)
    @app_commands.command(name='remove-role', description="Removes a role from automatically assigning to new members")
    @app_commands.describe(role="The role to unassign")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def remove_autorole(self, itx: Interaction, role: discord.Role):
        async with self.bot.db as session:
            await session.auto_roles.remove_auto_role(role.id)
            await session.commit()
        await itx.response.send_message(f"{role.name} is no longer an auto-role", ephemeral=True)

    @app_commands.command(name='list-roles', description="Lists the roles that are set to automatically assign")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def list_autorole(self, itx: Interaction):
        #async with self.bot.db as session:
            #roles = await session.auto_roles.
        names = '\n'.join(r and r.mention for r in roles) or 'No Roles'
        embed = discord.Embed(title="Auto-Roles", description=names)
        await itx.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name='sync', description="Sync all auto-roles to members in the guild")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def sync(self, itx: Interaction):
        await itx.response.send_modal(ConfirmSyncModal(self))