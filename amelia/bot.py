from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from discord.app_commands import Group, Command
from discord.ext import commands

from amelia.tfl import TFLService

from amelia.uow import UOW
if TYPE_CHECKING:
    from amelia.data import Pg


log = logging.getLogger(__name__)


class ConfigGroup(Group):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def add_config_command(self, func, error_coro=None, name=None, desc=None, override: bool = False):
        desc = '...' if desc is None else desc
        cmd = Command(
            name=name if name is not None else func.__name__,
            description=desc,
            callback=func,
            parent=None,
        )
        handler = None
        if error_coro is not None:
            handler = lambda parent, itx, error: error_coro(itx, error)
        cmd.on_error = handler
        self.add_command(cmd, override=override)




class AmeliaBot(commands.Bot):

    def __init__(self, db_service: Pg, **kwargs):
        super(AmeliaBot, self).__init__(**kwargs)
        self.tfl = TFLService()
        db_service.uow_cls = UOW
        self.db: Pg[UOW] = db_service
        #Pg.migrate(os.environ['DSN'])

        self._first_run = True
        self.config_group = ConfigGroup(name='config', description='Amelia Configuration settings')

    async def add_cog(self, *args, **kwargs) -> None:
        log.info(f"Cog Added: {args[0]}")
        await super(AmeliaBot, self).add_cog(*args, **kwargs)


    async def setup_hook(self) -> None:
        await self.load_extension('amelia.features.core')



    async def on_ready(self):
        if self._first_run:
            from amelia.uow import UOW
            self.db.uow_class = UOW
            self.tree.add_command(self.config_group)
        self._first_run = False


