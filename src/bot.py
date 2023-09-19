from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from discord.app_commands import Group
from discord.ext import commands

from src.tfl import TFLService

from src.uow import UOW
if TYPE_CHECKING:
    from src.data import Pg


log = logging.getLogger(__name__)


class AmeliaBot(commands.Bot):

    def __init__(self, db_service: Pg, **kwargs):
        super(AmeliaBot, self).__init__(**kwargs)
        self.tfl = TFLService()
        db_service.uow_cls = UOW
        self.db: Pg[UOW] = db_service
        #Pg.migrate(os.environ['DSN'])

        self._first_run = True
        self.config_group = Group(name='config', description='Amelia Configuration settings')

    async def add_cog(self, *args, **kwargs) -> None:
        log.info(f"Cog Added: {args[0]}")
        await super(AmeliaBot, self).add_cog(*args, **kwargs)


    async def setup_hook(self) -> None:
        await self.load_extension('src.features.core')


    async def on_ready(self):
        if self._first_run:
            from src.uow import UOW
            self.db.uow_class = UOW
            self.tree.add_command(self.config_group)
        self._first_run = False


