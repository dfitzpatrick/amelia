
from .metar import Metar
from .misc import sunset_cmd
from .taf import Taf


async def setup(bot):
    await bot.add_cog(Metar(bot))
    await bot.add_cog(Taf(bot))
    bot.tree.add_command(sunset_cmd)
