import logging

import discord
from discord import Interaction
from discord import app_commands
from typing import TYPE_CHECKING

from src.features.weather.data import AllowedChannel
from src.features.weather.services import convert_allowed_channels_to_discord
if TYPE_CHECKING:
    from src.bot import AmeliaBot
log = logging.getLogger(__name__)


class MetarConfigGroup(app_commands.Group):
    def __init__(self, bot: 'AmeliaBot'):
        super().__init__(name='observation', description='Configuration commands for METAR functionality')
        self.bot = bot

    @app_commands.command(name='add-channel', description='Adds a channel that will allow the output of observation')
    @app_commands.describe(channel="The channel to allow METAR reports to be posted")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def add_metar_channel(self, itx: Interaction, channel: discord.TextChannel):
        if itx.guild is None:
            return
        async with self.bot.db as session:
            await session.weather.create_metar_channel(AllowedChannel(guild_id=itx.guild.id, channel_id=channel.id))
            response = f"{channel.name} added to approved observation channels"
            await itx.response.send_message(response, ephemeral=True)
            await session.commit()

    @app_commands.command(name='remove-channel', description="Removes a channel from displaying observation output")
    @app_commands.describe(channel="The channel to disallow METAR reports being posted")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def remove_metar_channel(self, itx: Interaction, channel: discord.TextChannel):
        async with self.bot.db as session:
            await session.weather.remove_metar_channel(channel.id)
            await itx.response.send_message(f"{channel.name} is cleared from allowed observation channels", ephemeral=True)  # noqa: E501
            await session.commit()

    @app_commands.command(name='list-channels', description="Lists the current channels that allow observation output")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def list_metar_channels(self, itx: Interaction):
        if itx.guild is None:
            return
        async with self.bot.db as session:
            channels = await session.weather.fetch_metar_channels(itx.guild.id)
        channels = convert_allowed_channels_to_discord(itx.guild, channels)
        names = '\n'.join(ch and ch.mention for ch in channels) or 'No Channels'
        embed = discord.Embed(title="Approved Metar Channels", description=names)
        await itx.response.send_message(embed=embed, ephemeral=True)


class TafConfigGroup(app_commands.Group):
    def __init__(self, bot: 'AmeliaBot'):
        super().__init__(name='taf', description='Configuration commands for TAF functionality')
        self.bot = bot

    @app_commands.command(name='add-channel', description='Adds a channel that will allow the output of TAF')
    @app_commands.describe(channel="The channel to allow TAF reports to be posted")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def add_taf_channel(self, itx: Interaction, channel: discord.TextChannel):
        if itx.guild is None:
            return
        async with self.bot.db as session:
            await session.weather.create_taf_channel(AllowedChannel(guild_id=itx.guild.id, channel_id=channel.id))
            response = f"{channel.name} added to approved observation channels"
            await itx.response.send_message(response, ephemeral=True)
            await session.commit()

    @app_commands.command(name='remove-channel', description="Removes a channel from displaying TAF output")
    @app_commands.describe(channel="The channel to disallow TAF reports being posted")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def remove_taf_channel(self, itx: Interaction, channel: discord.TextChannel):
        async with self.bot.db as session:
            await session.weather.remove_taf_channel(channel.id)
            await itx.response.send_message(f"{channel.name} is cleared from allowed observation channels", ephemeral=True)  # noqa: E501
            await session.commit()

    @app_commands.command(name='list-channels', description="Lists the current channels that allow TAF output")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def list_taf_channels(self, itx: Interaction):
        if itx.guild is None:
            return
        async with self.bot.db as session:
            channels = await session.weather.fetch_taf_channels(itx.guild.id)
        channels = convert_allowed_channels_to_discord(itx.guild, channels)
        names = '\n'.join(ch and ch.mention for ch in channels) or 'No Channels'
        embed = discord.Embed(title="Approved TAF Channels", description=names)
        await itx.response.send_message(embed=embed, ephemeral=True)