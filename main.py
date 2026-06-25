import asyncio
import logging
import os
from aiohttp import web
from src.bot import start_bot

logging.basicConfig(level=logging.INFO)


if __name__ == "__main__":
    app = asyncio.run(start_bot())
    if app:
        port = int(os.environ.get("PORT", 8080))
        web.run_app(app, host="0.0.0.0", port=port)
