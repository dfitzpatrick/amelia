from __future__ import annotations
from discord.ui.view import LayoutView
from discord.ui import Container, MediaGallery, TextDisplay, Separator, Button, Section,Thumbnail
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .services import Classified

class ClassifiedLayout(LayoutView):

    def __init__(self, ad: Classified):
        super().__init__()
        gallery = MediaGallery()
        ad_button = Button(label="See listing", url=ad.url)
        # max 10 for MediaGallery limitations
        for img in ad.image_filenames[:10]:
            gallery.add_item(media=f"attachment://{img}")
        container = Container(
            Section(
                TextDisplay("## " + ad.title),
                TextDisplay("### " + ad.price_string),
                accessory=ad_button
            ),
            Separator(),
            TextDisplay(ad.body),
        
        )
        if ad.images:
            container.add_item(gallery)

        container.add_item(Separator())
        if ad.location:
            container.add_item(TextDisplay(ad.location))
        container.add_item(TextDisplay("-# Ad and pictures sourced from barnstormers.com"))
        self.add_item(container)