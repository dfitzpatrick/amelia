from .plates import PlatesCog, ChartSupplementCOG


async def setup(bot):
    await bot.add_cog(PlatesCog(bot))
    await bot.add_cog(ChartSupplementCOG(bot))