from src.features.forum_channels.pins import AutoPinsCog
from src.features.forum_channels.qol import ForumQOL


async def setup(bot):
    await bot.add_cog(AutoPinsCog(bot))
    await bot.add_cog(ForumQOL(bot))