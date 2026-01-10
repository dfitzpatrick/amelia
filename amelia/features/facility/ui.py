from discord.ui import LayoutView, MediaGallery
import discord
class ChartSupplementView(LayoutView):
    gallery = MediaGallery()

    def __init__(self, files: list[discord.File], *, timeout = 180):
        super().__init__(timeout=timeout)
        for f in files:
            self.gallery.add_item(media=f)
        
    