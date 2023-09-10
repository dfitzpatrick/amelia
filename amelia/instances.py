from __future__ import annotations

import asyncio
import logging
import os
from typing import TYPE_CHECKING, Optional

from amelia.data import Pg
if TYPE_CHECKING:
    from amelia.bot import AmeliaBot
    from amelia.uow import UOW



log = logging.getLogger(__name__)
_dsn = os.environ['DSN']
_token = os.environ['AMELIA_TOKEN']

db: Pg[UOW] = Pg['UOW'](_dsn)
bot: Optional[AmeliaBot] = None





