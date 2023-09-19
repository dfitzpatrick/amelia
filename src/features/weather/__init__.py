
from src.features.weather.taf import Taf
from src.features.weather.metar import Metar
from src.features.weather.misc import sunset_cmd

async def setup(bot):
    await bot.add_cog(Metar(bot))
    await bot.add_cog(Taf(bot))
    bot.tree.add_command(sunset_cmd)
