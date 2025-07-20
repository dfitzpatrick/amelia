from .plates import PlatesCog


async def setup(bot):
    await bot.add_cog(PlatesCog(bot))