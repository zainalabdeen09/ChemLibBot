from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from .i18n import LANGUAGES


def lang_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🇸🇦 العربية", callback_data="lang_ar")
    builder.button(text="🇬🇧 English", callback_data="lang_en")
    builder.adjust(2)
    return builder.as_markup()


def main_menu(lang: str):
    t = LANGUAGES[lang]
    builder = InlineKeyboardBuilder()
    builder.button(text=t["about"], callback_data="about")
    builder.button(text=t["sections"], callback_data="sections")
    builder.button(text=t["search"], callback_data="search")
    builder.button(text=t["help"], callback_data="help")
    builder.adjust(1)
    return builder.as_markup()


def sections_keyboard(sections, lang: str, back_callback="main_menu"):
    builder = InlineKeyboardBuilder()
    for sec in sections:
        name = sec["name_ar"] if lang == "ar" else sec["name_en"]
        builder.button(text=name, callback_data=f"section_{sec['id']}")
    builder.adjust(1)
    builder.row(
        InlineKeyboardButton(
            text=LANGUAGES[lang]["back"], callback_data=back_callback
        )
    )
    return builder.as_markup()


def back_keyboard(lang: str, callback_data: str):
    builder = InlineKeyboardBuilder()
    builder.button(text=LANGUAGES[lang]["back"], callback_data=callback_data)
    return builder.as_markup()


def paper_keyboard(doi: str, pdf_url: str, lang: str):
    builder = InlineKeyboardBuilder()
    if pdf_url:
        builder.button(text=LANGUAGES[lang]["open_pdf"], url=pdf_url)
    if doi and doi != "unknown":
        builder.button(
            text=LANGUAGES[lang]["view_doi"],
            url=f"https://doi.org/{doi}",
        )
    builder.adjust(1)
    return builder.as_markup()
