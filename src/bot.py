import logging
import os
from functools import partial
from aiogram import Bot, Dispatcher, Router, F
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

from .config import TOKEN, ADMIN_USERNAME
from .i18n import LANGUAGES
from .database import (init_db, get_user_lang, set_user_lang, get_sections, get_section,
                        get_papers_by_section, add_paper, paper_exists_by_doi, count_papers_in_section)
from .keyboards import lang_keyboard, main_menu, sections_keyboard, back_keyboard, paper_keyboard
from .search import search_papers, fetch_paper_by_doi
from .seed_data import seed_sections, SECTION_KEYWORDS

router = Router()

_MAIN_SECTIONS = []
_PARENT_SECTIONS = {}


def _load_sections():
    global _MAIN_SECTIONS, _PARENT_SECTIONS
    sections = get_sections(parent_id=None)
    if not sections:
        seed_sections()
        sections = get_sections(parent_id=None)
    _MAIN_SECTIONS = [dict(s) for s in sections]
    _PARENT_SECTIONS = {}
    for sec in sections:
        _PARENT_SECTIONS[sec["id"]] = [dict(s) for s in get_sections(parent_id=sec["id"])]


def _get_cached_sections(parent_id=None):
    if not _MAIN_SECTIONS:
        _load_sections()
    if parent_id is None:
        return _MAIN_SECTIONS
    if isinstance(parent_id, int) and parent_id in _PARENT_SECTIONS:
        return _PARENT_SECTIONS[parent_id]
    subs = [dict(s) for s in get_sections(parent_id=parent_id)]
    _PARENT_SECTIONS[parent_id] = subs
    return subs


def _get_cached_section(section_id):
    for s in _MAIN_SECTIONS:
        if s["id"] == section_id:
            return s
    for subs in _PARENT_SECTIONS.values():
        for s in subs:
            if s["id"] == section_id:
                return s
    sec = get_section(section_id)
    if sec:
        return dict(sec)
    return None



class SearchState(StatesGroup):
    waiting_for_query = State()


class AddPaperState(StatesGroup):
    waiting_for_doi = State()


def is_admin(user: Message | CallbackQuery) -> bool:
    username = user.from_user.username
    if not username:
        return False
    return f"@{username}".lower() == ADMIN_USERNAME.lower()


def t(user_id: int, key: str):
    lang = get_user_lang(user_id)
    return LANGUAGES[lang][key]


def lang_t(lang: str, key: str):
    return LANGUAGES[lang][key]


@router.message(F.text == "/start")
async def cmd_start(message: Message):
    user_id = message.from_user.id
    lang = get_user_lang(user_id)
    if lang == "ar":
        await message.answer(
            "👋 مرحباً بك في <b>ChemLibBot</b>!\n"
            "مكتبتك العلمية المتخصصة في الكيمياء.\n\n"
            "🌐 اختر لغتك المفضلة:",
            reply_markup=lang_keyboard(),
        )
    else:
        await message.answer(
            "👋 Welcome to <b>ChemLibBot</b>!\n"
            "Your scientific library specialized in Chemistry.\n\n"
            "🌐 Choose your preferred language:",
            reply_markup=lang_keyboard(),
        )


@router.callback_query(F.data.startswith("lang_"))
async def set_language(callback: CallbackQuery):
    lang = callback.data.split("_")[1]
    user_id = callback.from_user.id
    set_user_lang(user_id, lang)
    await callback.message.delete()
    await callback.message.answer(
        lang_t(lang, "main_menu"),
        reply_markup=main_menu(lang),
    )
    await callback.answer()


@router.callback_query(F.data == "main_menu")
async def go_main_menu(callback: CallbackQuery):
    lang = get_user_lang(callback.from_user.id)
    await callback.message.delete()
    await callback.message.answer(
        lang_t(lang, "main_menu"),
        reply_markup=main_menu(lang),
    )
    await callback.answer()


@router.callback_query(F.data == "about")
async def show_about(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = get_user_lang(user_id)
    text = lang_t(lang, "about_text").format(admin=ADMIN_USERNAME)
    await callback.message.delete()
    await callback.message.answer(
        text, reply_markup=back_keyboard(lang, "main_menu")
    )
    await callback.answer()


@router.callback_query(F.data == "help")
async def show_help(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = get_user_lang(user_id)
    text = lang_t(lang, "help_text").format(admin=ADMIN_USERNAME)
    await callback.message.delete()
    await callback.message.answer(
        text, reply_markup=back_keyboard(lang, "main_menu")
    )
    await callback.answer()


@router.callback_query(F.data == "sections")
async def show_sections(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = get_user_lang(user_id)
    sections = _get_cached_sections(parent_id=None)
    await callback.message.delete()
    await callback.message.answer(
        lang_t(lang, "select_main_section"),
        reply_markup=sections_keyboard(sections, lang, "main_menu"),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("section_"))
async def show_sub_sections(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = get_user_lang(user_id)
    section_id = int(callback.data.split("_")[1])
    section = _get_cached_section(section_id)
    if not section:
        await callback.answer(t(user_id, "error_occurred"))
        return
    sub_sections = _get_cached_sections(parent_id=section_id)
    await callback.message.delete()
    if sub_sections:
        title = lang_t(lang, "select_sub_section")
        kb = sections_keyboard(sub_sections, lang, "sections")
        await callback.message.answer(title, reply_markup=kb)
    else:
        papers = get_papers_by_section(section_id)
        name = section["name_ar"] if lang == "ar" else section["name_en"]
        if papers:
            title = f"{lang_t(lang, 'papers_in')} {name}:"
            await callback.message.answer(
                title,
                reply_markup=back_keyboard(lang, "sections"),
            )
            for paper in papers:
                msg = (
                    f"📄 <b>{paper['title']}</b>\n"
                    f"👤 {lang_t(lang, 'authors')}: {paper['authors'] or 'N/A'}\n"
                )
                if paper["year"]:
                    msg += f"📅 {lang_t(lang, 'year')}: {paper['year']}\n"
                if paper["abstract"]:
                    msg += f"📝 {paper['abstract'][:200]}...\n"
                await callback.message.answer(
                    msg,
                    reply_markup=paper_keyboard(
                        paper["doi"], paper["pdf_url"], lang
                    ),
                )
        else:
            await callback.message.answer(
                f"{lang_t(lang, 'no_papers')} ({name})",
                reply_markup=back_keyboard(lang, "sections"),
            )
    await callback.answer()


@router.callback_query(F.data == "search")
async def search_prompt(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    lang = get_user_lang(user_id)
    await callback.message.delete()
    await callback.message.answer(lang_t(lang, "send_search_query"))
    await state.set_state(SearchState.waiting_for_query)
    await callback.answer()


@router.message(SearchState.waiting_for_query)
async def handle_search(message: Message, state: FSMContext):
    user_id = message.from_user.id
    lang = get_user_lang(user_id)
    query = message.text.strip()
    if query.lower() == "/cancel":
        await message.answer(lang_t(lang, "search_cancelled"))
        await state.clear()
        return
    if not query:
        await message.answer(lang_t(lang, "send_search_query"))
        return
    status_msg = await message.answer(f"🔍 {lang_t(lang, 'search_results')} \"{query}\"...")
    results = await search_papers(query)
    await state.clear()
    if not results:
        await status_msg.delete()
        await message.answer(
            lang_t(lang, "no_results"),
            reply_markup=back_keyboard(lang, "main_menu"),
        )
        return
    await status_msg.delete()
    await message.answer(
        f"{lang_t(lang, 'search_results')} \"{query}\": ({len(results)})",
        reply_markup=back_keyboard(lang, "main_menu"),
    )
    for paper in results:
        msg = (
            f"📄 <b>{paper['title']}</b>\n"
            f"👤 {lang_t(lang, 'authors')}: {paper['authors']}\n"
        )
        if paper["year"]:
            msg += f"📅 {lang_t(lang, 'year')}: {paper['year']}\n"
        if paper["source"]:
            msg += f"📰 {lang_t(lang, 'source')}: {paper['source']}\n"
        if paper["abstract"]:
            msg += f"📝 {paper['abstract']}\n"
        if not paper["is_open_access"]:
            msg += "\n⚠️ هذا البحث قد لا يكون متاحاً مجاناً - قد تحتاج اشتراك للوصول الكامل"
        await message.answer(
            msg,
            reply_markup=paper_keyboard(paper["doi"], paper["pdf_url"], lang),
        )


@router.message(F.text == "/seed")
async def cmd_seed(message: Message):
    if not is_admin(message):
        return
    msg = await message.answer("🌱 جاري جلب البحوث للأقسام... قد يستغرق دقيقة")
    leaf_sections = []
    all_main = _get_cached_sections(parent_id=None)
    for main_sec in all_main:
        subs = _get_cached_sections(parent_id=main_sec["id"])
        for sub in subs:
            deeper = _get_cached_sections(parent_id=sub["id"])
            if not deeper:
                leaf_sections.append(sub)

    added = 0
    skipped = 0
    for sec in leaf_sections:
        name_en = sec["name_en"]
        keyword = SECTION_KEYWORDS.get(name_en, name_en)
        results = await search_papers(keyword, limit=5)
        for paper in results:
            doi = paper.get("doi", "")
            if doi and paper_exists_by_doi(doi):
                skipped += 1
                continue
            add_paper(
                section_id=sec["id"],
                title=paper["title"],
                authors=paper["authors"],
                year=paper["year"],
                doi=doi,
                url=paper.get("url", ""),
                abstract=paper["abstract"],
                source=paper.get("source", ""),
                pdf_url=paper.get("pdf_url", ""),
                is_open_access=1 if paper.get("is_open_access") else 0,
            )
            added += 1

    await msg.delete()
    await message.answer(
        f"🌱 تمت عملية البذر!\n"
        f"✅ {added} بحث مضاف\n"
        f"⏭️ {skipped} مكرر"
    )


@router.message(F.text == "/addpaper")
async def cmd_add_paper(message: Message, state: FSMContext):
    if not is_admin(message):
        return
    await message.answer(
        "📎 أرسل رابط DOI للبحث الذي تريد إضافته\n"
        "مثال: 10.1021/acs.joc.0c01234\n"
        "أو أرسل /cancel للإلغاء"
    )
    await state.set_state(AddPaperState.waiting_for_doi)


@router.message(AddPaperState.waiting_for_doi)
async def handle_add_paper_doi(message: Message, state: FSMContext):
    if not is_admin(message):
        await state.clear()
        return
    doi = message.text.strip()
    if doi.lower() == "/cancel":
        await message.answer("تم الإلغاء")
        await state.clear()
        return
    if "/" in doi and "doi" in doi.lower():
        doi = doi.split("doi.org/")[-1].split("?")[0]
    status_msg = await message.answer(f"🔍 جلب معلومات البحث...")
    paper = await fetch_paper_by_doi(doi)
    if not paper:
        await status_msg.delete()
        await message.answer("⚠️ لم أجد البحث بهذا DOI. تأكد من الرابط.")
        await state.clear()
        return
    if paper_exists_by_doi(doi):
        await status_msg.delete()
        await message.answer("⚠️ هذا البحث موجود مسبقاً في قاعدة البيانات.")
        await state.clear()
        return
    await state.update_data(paper=paper)
    await status_msg.delete()
    msg = (
        f"📄 <b>{paper['title']}</b>\n"
        f"👤 {paper['authors']}\n"
        f"📅 {paper['year']}\n"
        f"🔗 DOI: {doi}\n\n"
        f"اختر القسم الذي تريد إضافة البحث إليه:"
    )
    all_main = _get_cached_sections(parent_id=None)
    builder = InlineKeyboardBuilder()
    for sec in all_main:
        name = sec["name_ar"]
        builder.button(text=name, callback_data=f"addsec_{sec['id']}")
    builder.adjust(1)
    builder.row(InlineKeyboardButton(text="🔙 إلغاء", callback_data="cancel_add"))
    await message.answer(msg, reply_markup=builder.as_markup())
    await state.set_state(AddPaperState.waiting_for_doi)


@router.callback_query(F.data.startswith("addsec_"))
async def handle_add_to_section(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback):
        await callback.answer()
        return
    section_id = int(callback.data.split("_")[1])
    data = await state.get_data()
    paper = data.get("paper")
    if not paper:
        await callback.message.delete()
        await callback.message.answer("⚠️ انتهت الجلسة. حاول مرة أخرى.")
        await state.clear()
        await callback.answer()
        return
    add_paper(
        section_id=section_id,
        title=paper["title"],
        authors=paper["authors"],
        year=paper["year"],
        doi=paper["doi"],
        url=paper.get("url", ""),
        abstract=paper["abstract"],
        source=paper.get("source", ""),
        pdf_url=paper.get("pdf_url", ""),
        is_open_access=1 if paper.get("is_open_access") else 0,
    )
    sec = _get_cached_section(section_id)
    name = sec["name_ar"] if sec else "Unknown"
    await callback.message.delete()
    await callback.message.answer(f"✅ تم إضافة البحث إلى قسم <b>{name}</b>")
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "cancel_add")
async def cancel_add_paper(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await callback.message.answer("تم الإلغاء")
    await callback.answer()


async def on_startup(bot: Bot, base_url: str):
    await bot.set_webhook(f"{base_url}/webhook")


async def on_shutdown(bot: Bot):
    await bot.delete_webhook()


async def async_health_server():
    app = web.Application()
    app.router.add_get("/", lambda r: web.Response(text="OK"))
    port = int(os.environ.get("PORT", 8080))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info(f"Health server on port {port}")


def create_bot_and_dp():
    init_db()
    _load_sections()
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    return bot, dp


async def start_bot_webhook():
    webhook_url = os.environ.get("WEBHOOK_URL")
    if not webhook_url:
        return None
    bot, dp = create_bot_and_dp()
    dp.startup.register(partial(on_startup, base_url=webhook_url))
    dp.shutdown.register(on_shutdown)
    app = web.Application()
    webhook_requests_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    webhook_requests_handler.register(app, path="/webhook")
    setup_application(app, dp, bot=bot)
    app.router.add_get("/", lambda r: web.Response(text="OK"))
    return app


async def start_bot():
    webhook_app = await start_bot_webhook()
    if webhook_app:
        port = int(os.environ.get("PORT", 8080))
        await web.run_app(webhook_app, host="0.0.0.0", port=port)
        return
    await async_health_server()
    bot, dp = create_bot_and_dp()
    logging.info("ChemLibBot started (polling)!")
    await dp.start_polling(bot)
