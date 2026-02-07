"""Docker entrypoint for the proxy service."""

import asyncio
import logging

from tokentap.config import DEFAULT_PROXY_PORT
from tokentap.db import MongoEventStore
from tokentap.proxy import start_mitmproxy

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def main():
    db = MongoEventStore()
    asyncio.run(start_mitmproxy(DEFAULT_PROXY_PORT, db=db))


if __name__ == "__main__":
    main()
