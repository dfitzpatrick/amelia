import discord
from .data import AutoRoleSchema

def convert_schemas_to_role_objects(guild: discord.Guild, schemas: list[AutoRoleSchema]) -> list[discord.Role]:
    container: list[discord.Role] = []
    for schema in schemas:
        role = discord.utils.get(guild.roles, id=schema.role_id)
        if role is not None:
            container.append(role)
    return container