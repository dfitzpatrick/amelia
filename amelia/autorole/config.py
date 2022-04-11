import discord
from discord import app_commands, Interaction, Role

from amelia.autorole.cache import AutoRoleCache
from amelia.autorole.ui import ConfirmSyncModal
from amelia.bot import AmeliaBot


class AutoRoleConfig(app_commands.Group):
    def __init__(self, bot: AmeliaBot, cache: AutoRoleCache):
        super().__init__(name='autorole', description='Configuration commands for AutoRole')
        self.cache = cache
        self.bot = bot

    @app_commands.command(name='add-role', description='Adds a role that will automatically be assigned on member join')
    @app_commands.describe(role="The role to auto-assign")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def add_auto_role(self, itx: Interaction, role: Role):
        roles = self.cache.item.get(itx.guild_id, [])
        if role not in roles:
            await self.bot.pg.add_auto_role_to_guild(itx.guild_id, role.id)
            response = f"{role.name} Added to auto roles. Note that this will not sync automatically. To sync," \
                       f"please run the sync command specifically"

        else:
            response = f"{role.name} is already an assigned auto-role"
        await itx.response.send_message(response, ephemeral=True)

    @app_commands.command(name='remove-role', description="Removes a role from automatically assigning to new members")
    @app_commands.describe(role="The role to unassign")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def remove_autorole(self, itx: Interaction, role: discord.Role):
        await self.bot.pg.remove_auto_role_from_guild(role.id)
        await itx.response.send_message(f"{role.name} is no longer an auto-role", ephemeral=True)

    @app_commands.command(name='list-roles', description="Lists the roles that are set to automatically assign")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def list_autorole(self, itx: Interaction):
        roles = self.cache.item.get(itx.guild_id, [])
        names = '\n'.join(r and r.mention for r in roles) or 'No Roles'
        embed = discord.Embed(title="Auto-Roles", description=names)
        await itx.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name='sync', description="Sync all auto-roles to members in the guild")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def sync(self, itx: Interaction):
        await itx.response.send_modal(ConfirmSyncModal(self))