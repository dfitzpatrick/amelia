from __future__ import annotations

import logging
import os
import sys
import typing as t
from logging import StreamHandler, FileHandler

from amelia import common

if t.TYPE_CHECKING:
    pass

import sentry_sdk
sentry_sdk.init(
    dsn=os.environ['SENTRY_DSN'],

    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for performance monitoring.
    # We recommend adjusting this value in production.
    traces_sample_rate=1.0,
    environment=os.environ.get('SENTRY_ENVIRONMENT', 'unknown')
)

#t

BASE_DIR = os.path.normpath(os.path.dirname(os.path.realpath(__file__)))

handler_console = StreamHandler(stream=sys.stdout)
handler_filestream = FileHandler(filename=f"{BASE_DIR}/bot.log", encoding='utf-8')
handler_filestream.setLevel(logging.INFO)
handler_console.setLevel(logging.DEBUG)


logging_handlers = [
        handler_console,
        handler_filestream
    ]

logging.basicConfig(
    format="%(asctime)s | %(name)25s | %(funcName)25s | %(levelname)6s | %(message)s",
    datefmt="%b %d %H:%M:%S",
    level=logging.DEBUG,
    handlers=logging_handlers
)
logging.getLogger('asyncio').setLevel(logging.ERROR)
logging.getLogger('discord').setLevel(logging.ERROR)
logging.getLogger('websockets').setLevel(logging.ERROR)
logging.getLogger('asyncpg').setLevel(logging.DEBUG)
log = logging.getLogger(__name__)


