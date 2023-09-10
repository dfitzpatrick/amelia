from amelia.concepts.guild.cogs import GuildFeatures


async def setup(bot):
    await bot.add_cog(GuildFeatures(bot))
