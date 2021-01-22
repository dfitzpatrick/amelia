import discord
from discord.ext import commands
from . import AmeliaBot
import logging
log = logging.getLogger(__name__)

class Core(commands.Cog):
    """
    Required instance of all bot functions that cannot be disabled.
    This is a COG but not in the cog directory to differentiate.
    """

    def __init__(self, bot: AmeliaBot):
        self.bot = bot


    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        id = str(guild.id)
        log.debug("Created guild entry")
        await self.bot.pg.register_guild(id)

    @commands.has_permissions(administrator=True)
    @commands.command(name='prefix')
    async def prefix(self, ctx: commands.Context, pfx: str):
        """
        Changes the prefix for the server
        Parameters
        ----------
        ctx
        pfx: Prefix to set to

        Returns
        -------
        None
        """

        gid = str(ctx.guild.id)
        self.bot.config[gid]['prefix'] = pfx
        q = f"UPDATE guilds SET prefix = {pfx} WHERE id = {gid}"
        await self.bot.pg.pool.execute(q)

    @commands.Cog.listener()
    async def on_command_completion(self, ctx: commands.Context):
        """
        Simple Housekeeping function. Annotates the command with feedback that
        it completed correctly, and if permissioned for, will remove the command.

        Parameters
        ----------
        ctx: The discord Context

        Returns
        -------
        :class: None
        """
        gid = str(ctx.guild.id)
        auto_delete = self.bot.config.get(gid, {}).get('auto_delete_commands', True)
        try:
            message: discord.Message = ctx.message
            await message.add_reaction(u"\u2705")  # Green Checkbox
            if auto_delete:
                await message.delete(delay=5)
        except (discord.errors.NotFound, discord.errors.Forbidden, discord.errors.HTTPException) as e:
            log.error(e)


def setup(bot: AmeliaBot):
    bot.add_cog(Core(bot))
