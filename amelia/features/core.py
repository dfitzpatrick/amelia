import logging

import discord
from discord import app_commands, Interaction
from discord.ext.commands import Cog
from discord.ext import commands

from amelia import common
from amelia.bot import AmeliaBot
from typing import Optional, Literal

log = logging.getLogger(__name__)

custom_extensions = (
    'amelia.concepts.guild',
    'amelia.features.forum_channels',
    'amelia.features.facility',
    'amelia.features.eggs',
    'amelia.features.autorole',
    'amelia.features.weather',
    'amelia.features.r_flying'
)

weather_cmds = [
    '/metar',
    '/taf',
]
other_cmds = [
    '/plates',
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
        if self.bot.user is None:
            return
        title = "Amelia Help Commands"

        description =  "For further help, use /cmd and see the hints that discord provides"
        embed = discord.Embed(title=title, description=description)
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.add_field(name="Weather Related", value='\n'.join(weather_cmds))
        embed.add_field(name="Facility", value='\n'.join(other_cmds))
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
    async def sync(self, ctx: commands.Context, guilds: commands.Greedy[discord.Object], spec: Optional[Literal["~", "*", "^"]] = None) -> None:
        if not guilds:
            if spec == "~":
                synced = await ctx.bot.tree.sync(guild=ctx.guild)
            elif spec == "*":
                ctx.bot.tree.copy_global_to(guild=ctx.guild)
                synced = await ctx.bot.tree.sync(guild=ctx.guild)
            elif spec == "^":
                ctx.bot.tree.clear_commands(guild=ctx.guild)
                await ctx.bot.tree.sync(guild=ctx.guild)
                synced = []
            else:
                synced = await ctx.bot.tree.sync()
            await ctx.send(
                f"Synced {len(synced)} commands {'globally' if spec is None else 'to the current guild.'}",
                delete_after=5
            )
            return

        ret = 0
        for guild in guilds:
            try:
                await ctx.bot.tree.sync(guild=guild)
            except discord.HTTPException:
                pass
            else:
                ret += 1

        await ctx.send(f"Synced the tree to {ret}/{len(guilds)}.")

    async def setup_extensions(self, callable):
        for ext in custom_extensions:
            await callable(ext)

    @commands.command(name='r')
    @commands.is_owner()
    async def reload_extensions_cmd(self, ctx: commands.Context):
        await self.setup_extensions(self.bot.reload_extension)
        await ctx.send("Reload done")

    @app_commands.command(name='guilds')
    async def guilds_app_cmd(self, itx: discord.Interaction):
        if not (await self.bot.is_owner(itx.user)):
            await itx.response.send_message("You do not have access to this command",ephemeral=True)
            return
        description = '\n'.join(g.name for g in self.bot.guilds)
        embed = discord.Embed(title="Guiids", description=description)
        await itx.response.send_message(embed=embed, ephemeral=True)

async def setup(bot: AmeliaBot):
    log.debug("in setup")
    core = Core(bot)
    await bot.add_cog(core)
    log.debug("calling extension load with load_extension")
    await core.setup_extensions(bot.load_extension)

