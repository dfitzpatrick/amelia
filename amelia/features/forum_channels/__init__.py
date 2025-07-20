from .pins import AutoPinsCog
from .qol import ForumQOL


async def setup(bot):
    await bot.add_cog(AutoPinsCog(bot))
    await bot.add_cog(ForumQOL(bot))