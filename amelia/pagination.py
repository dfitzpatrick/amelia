from math import ceil

import discord
from discord import User, Interaction
from discord.ext.paginator import paginator
from typing import TYPE_CHECKING, Dict, Any

if TYPE_CHECKING:
    from amelia.bot import AmeliaBot

class LongDescriptionPaginator(paginator.Paginator):

    bot: 'AmeliaBot'

    def __init__(self, bot: 'AmeliaBot', user: User, title: str, description: str, num_characters: int, *args, **kwargs):
        super().__init__(bot, user, *args, **kwargs)
        assert num_characters < 4096, "Number of characters cannot be 4096 or higher."
        self.title = title
        self.num_characters = num_characters
        self.total_length = len(description)
        self.pages = ceil(self.total_length / num_characters)
        self.entries = []
        self.fill_entries(description)

    def fill_entries(self, description: str):
        lines = description.split('\n')
        page_content = ""
        for line in lines:
            if len(page_content) > self.num_characters:
                self.entries.append(page_content)
                page_content = ""
            page_content += line + '\n'



    async def get_page_count(self, interaction: Interaction) -> int:
        return len(self.entries)

    async def get_page_content(self, interaction: Interaction, page: int) -> Dict[str, Any]:
        return {

            "embed": (discord.Embed(title=self.title, description=self.entries[page]))
        }