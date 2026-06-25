import asyncio
import logging
import os
from aiohttp import web
from src.bot import start_bot

logging.basicConfig(level=logging.INFO)


async def healthcheck(request):
    return web.Response(text="OK")


async def start_health_server():
    app = web.Application()
    app.router.add_get("/", healthcheck)
    port = int(os.environ.get("PORT", 8080))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info(f"Health server running on port {port}")


async def main():
    await asyncio.gather(start_health_server(), start_bot())


if __name__ == "__main__":
    asyncio.run(main())
