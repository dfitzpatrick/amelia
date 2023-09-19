from src.features.facility.plates import PlatesCog


async def setup(bot):
    await bot.add_cog(PlatesCog(bot))