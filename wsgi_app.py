import os
import sys
import asyncio
import logging

sys.path.insert(0, os.path.dirname(__file__))

logging.basicConfig(level=logging.INFO)

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Update

from src.config import TOKEN, ADMIN_USERNAME
from src.database import init_db
from src.bot import router
from src.seed_data import seed_sections

init_db()

from src.bot import _load_sections
_load_sections()

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher(storage=MemoryStorage())
dp.include_router(router)

from flask import Flask, request

flask_app = Flask(__name__)

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)


@flask_app.route("/webhook", methods=["POST"])
def webhook():
    update = Update.model_validate(request.get_json())
    loop.run_until_complete(dp.feed_update(bot, update))
    return "OK"


@flask_app.route("/")
def index():
    return "OK"


@flask_app.route("/set")
def set_webhook():
    url = request.args.get("url", "")
    if url:
        loop.run_until_complete(bot.set_webhook(url))
        return f"Webhook set to {url}"
    return "Missing url parameter"


app = flask_app
