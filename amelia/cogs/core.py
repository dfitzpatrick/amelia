import logging

import discord
from discord import app_commands, Interaction
from discord.app_commands import Group
from discord.ext.commands import Cog
from discord.ext import commands

from amelia import common
from amelia.bot import AmeliaBot

log = logging.getLogger(__name__)

weather_cmds = [
    '/metar',
    '/taf',
]
other_cmds = [
    '/sunset',
]
class Core(Cog):

    def __init__(self, bot: AmeliaBot):
        self.bot = bot

    @app_commands.command(name='reproduce')
    async def reproduce(self, interaction: discord.Interaction, channel: discord.ForumChannel):
        await interaction.response.send_message(channel.name)

    @app_commands.command(name='help', description="See the commands that Amelia has to offer")
    async def help_cmd(self, itx: Interaction):
        title = "Amelia Help Commands"

        description =  "For further help, use /cmd and see the hints that discord provides"
        embed = discord.Embed(title=title, description=description)
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.add_field(name="Weather Related", value='\n'.join(weather_cmds))
        embed.add_field(name="Other", value='\n'.join(other_cmds))
        embed.add_field(name="Configuration", value='/config', inline=False)
        await itx.response.send_message(embed=embed, ephemeral=True)


    @app_commands.command(name='sync', description='Sync application commands to guild')
    async def sync_cmd(self, itx: Interaction):
        if not await self.bot.is_owner(itx.user):
            return
        await self.bot.tree.sync()
        for o in common.APP_COMMANDS_GUILDS:
            log.debug(f"Copying Global App Commands to Guild id={o.id}")
            self.bot.tree.copy_global_to(guild=o)
            await self.bot.tree.sync(guild=o)
        await itx.response.send_message("Commands synced", ephemeral=True)

    @commands.command(name='sync')
    @commands.is_owner()
    async def sync_text(self, ctx: commands.Context):
        await self.bot.tree.sync()
        for o in common.APP_COMMANDS_GUILDS:
            log.debug(f"Copying Global App Commands to Guild id={o.id}")
            self.bot.tree.copy_global_to(guild=o)
            await self.bot.tree.sync(guild=o)
        await ctx.send("Commands synced", delete_after=5)

async def setup(bot):
    await bot.add_cog(Core(bot))
