from amelia.forum_channels.pins import AutoPinsCog


async def setup(bot):
    await bot.add_cog(AutoPinsCog(bot))