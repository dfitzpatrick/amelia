import logging

import discord
from discord import Interaction
from discord import app_commands
from typing import TYPE_CHECKING

from amelia.features.weather.cache import MetarCache, TafCache
if TYPE_CHECKING:
    from amelia.bot import AmeliaBot
log = logging.getLogger(__name__)


class MetarConfigGroup(app_commands.Group):
    def __init__(self, bot: 'AmeliaBot', cache: MetarCache):
        super().__init__(name='observation', description='Configuration commands for METAR functionality')
        self.cache = cache
        self.bot = bot

    @app_commands.command(name='add-channel', description='Adds a channel that will allow the output of observation')
    @app_commands.describe(channel="The channel to allow METAR reports to be posted")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def add_metar_channel(self, itx: Interaction, channel: discord.TextChannel):
        log.debug(self.cache.channels.item)
        if channel not in self.cache.channels.item.get(channel.guild.id, []):
            await self.bot.pg.add_metar_channel(channel.guild.id, channel.id)
            response = f"{channel.name} added to approved observation channels"
        else:
            response = f"{channel.name} is already added."
        await itx.response.send_message(response, ephemeral=True)

    @app_commands.command(name='remove-channel', description="Removes a channel from displaying observation output")
    @app_commands.describe(channel="The channel to disallow METAR reports being posted")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def remove_metar_channel(self, itx: Interaction, channel: discord.TextChannel):
        await self.bot.pg.remove_metar_channel(channel.id)
        await itx.response.send_message(f"{channel.name} is cleared from allowed observation channels", ephemeral=True)

    @app_commands.command(name='list-channels', description="Lists the current channels that allow observation output")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def list_metar_channels(self, itx: Interaction):
        channels = self.cache.channels.item.get(itx.guild_id, [])
        names = '\n'.join(ch and ch.mention for ch in channels) or 'No Channels'
        embed = discord.Embed(title="Approved Metar Channels", description=names)
        await itx.response.send_message(embed=embed, ephemeral=True)


class TafConfigGroup(app_commands.Group):
    def __init__(self, bot: 'AmeliaBot', cache: TafCache):
        super().__init__(name='taf', description='Configuration commands for TAF functionality')
        self.cache = cache
        self.bot = bot

    @app_commands.command(name='add-channel', description='Adds a channel that will allow the output of TAF')
    @app_commands.describe(channel="The channel to allow TAF reports to be posted")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def add_taf_channel(self, itx: Interaction, channel: discord.TextChannel):

        if channel not in self.cache.channels.item.get(channel.guild.id, []):
            await self.bot.pg.add_taf_channel(channel.guild.id, channel.id)
            response = f"{channel.name} added to approved TAF channels"
        else:
            response = f"{channel.name} is already added."
        await itx.response.send_message(response, ephemeral=True)

    @app_commands.command(name='remove-channel', description="Removes a channel from displaying TAF output")
    @app_commands.describe(channel="The channel to disallow TAF reports being posted")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def remove_taf_channel(self, itx: Interaction, channel: discord.TextChannel):
        await self.bot.pg.remove_taf_channel(channel.id)
        await itx.response.send_message(f"{channel.name} is cleared from allowed TAF channels", ephemeral=True)

    @app_commands.command(name='list-channels', description="Lists the current channels that allow TAF output")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def list_taf_channels(self, itx: Interaction):
        channels = self.cache.channels.item.get(itx.guild_id, [])
        names = '\n'.join(ch and ch.mention for ch in channels) or 'No Channels'
        embed = discord.Embed(title="Approved TAF Channels", description=names)
        await itx.response.send_message(embed=embed, ephemeral=True)