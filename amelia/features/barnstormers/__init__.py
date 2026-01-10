from .barnstormers import Barnstormers

async def setup(bot):
    await bot.add_cog(Barnstormers(bot))