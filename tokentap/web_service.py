"""Docker entrypoint for the web dashboard service."""

import logging

import uvicorn

from tokentap.config import WEB_PORT

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def main():
    uvicorn.run(
        "tokentap.web.app:app",
        host="0.0.0.0",
        port=WEB_PORT,
        log_level="info",
    )


if __name__ == "__main__":
    main()
