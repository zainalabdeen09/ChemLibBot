import asyncio
import logging
from src.bot import start_bot

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    asyncio.run(start_bot())
