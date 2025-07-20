from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Optional

from .data import Pg
if TYPE_CHECKING:
    from .bot import AmeliaBot
    from .uow import UOW


log = logging.getLogger(__name__)
_dsn = os.environ['DSN']


db: Pg[UOW] = Pg['UOW'](_dsn)
bot: Optional[AmeliaBot] = None





