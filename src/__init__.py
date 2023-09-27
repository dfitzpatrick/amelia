from __future__ import annotations

import logging
import os
import pathlib
import sys
from logging import StreamHandler, FileHandler


import sentry_sdk
from dotenv import load_dotenv
load_dotenv()
sentry_sdk.init(
    dsn=os.environ['SENTRY_DSN'],

    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for performance monitoring.
    # We recommend adjusting this value in production.
    traces_sample_rate=1.0,
    environment=os.environ.get('SENTRY_ENVIRONMENT', 'unknown')
) # type: ignore

#t

BASE_DIR = os.path.normpath(os.path.dirname(os.path.realpath(__file__)))
LOG_PATH = pathlib.Path(__file__).parents[1] / 'logs'
LOG_PATH.mkdir(exist_ok=True)

handler_console = StreamHandler(stream=sys.stdout)
handler_filestream = FileHandler(filename=LOG_PATH / 'bot.log', encoding='utf-8')
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


