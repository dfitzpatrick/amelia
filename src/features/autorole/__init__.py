from src.features.autorole.autorole import AutoRole


async def setup(bot):
    await bot.add_cog(AutoRole(bot))
