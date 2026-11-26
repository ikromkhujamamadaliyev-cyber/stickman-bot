import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from config import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("stickman_bot")


class VideoJobForm(StatesGroup):
    master_prompt = State()
    topic = State()
    minutes = State()
    language = State()
    subtitles = State()


def subtitles_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Ha (Subtitr bilan)", callback_data="sub:yes"),
                InlineKeyboardButton(text="Yo‘q (Subtitrsiz)", callback_data="sub:no"),
            ]
        ]
    )


def cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Bekor qilish", callback_data="job:cancel")]
        ]
    )


async def start_new_job(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(VideoJobForm.master_prompt)
    await message.answer(
        "2D Stickman video yaratishni boshlaymiz.\n\n"
        "1/5 — **Master Prompt**ni kiriting (masalan: uslub, ranglar, qoidalar):",
        parse_mode="Markdown",
        reply_markup=cancel_keyboard(),
    )


async def cmd_start(message: Message, state: FSMContext) -> None:
    await start_new_job(message, state)


async def cmd_new(message: Message, state: FSMContext) -> None:
    await start_new_job(message, state)


async def cb_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer("Bekor qilindi")
    await callback.message.edit_text(
        "Jarayon bekor qilindi. Yangi video boshlash uchun /new yoki /start bosing."
    )


async def process_master_prompt(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if len(text) < 5:
        await message.answer("Master Prompt juda qisqa. Batafsilroq yozing:")
        return

    await state.update_data(master_prompt=text)
    await state.set_state(VideoJobForm.topic)
    await message.answer(
        "2/5 — Video **mavzusi**ni kiriting:",
        parse_mode="Markdown",
        reply_markup=cancel_keyboard(),
    )


async def process_topic(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if len(text) < 2:
        await message.answer("Mavzuni kiriting:")
        return

    await state.update_data(topic=text)
    await state.set_state(VideoJobForm.minutes)
    await message.answer(
        "3/5 — Video **davomiyligi (daqiqada)** ni kiriting (masalan: `1` yoki `2.5`):",
        parse_mode="Markdown",
        reply_markup=cancel_keyboard(),
    )


async def process_minutes(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip().replace(",", ".")
    try:
        minutes = float(raw)
        if minutes <= 0 or minutes > 15:
            raise ValueError("Out of range")
    except ValueError:
        await message.answer("0.5 dan 15 gacha bo‘lgan son kiriting (masalan: `1` yoki `3`):")
        return

    await state.update_data(minutes=minutes)
    await state.set_state(VideoJobForm.language)
    await message.answer(
        "4/5 — Matn va ovoz **tili**ni kiriting (masalan: `O‘zbekcha`, `English`, `Русский`):",
        parse_mode="Markdown",
        reply_markup=cancel_keyboard(),
    )


async def process_language(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if len(text) < 2:
        await message.answer("Til nomini kiriting:")
        return

    await state.update_data(language=text)
    await state.set_state(VideoJobForm.subtitles)
    await message.answer(
        "5/5 — Videoga **subtitr** qo‘shilsinmi?",
        reply_markup=subtitles_keyboard(),
    )


async def process_subtitles(callback: CallbackQuery, state: FSMContext) -> None:
    subtitles = callback.data.endswith(":yes")
    data = await state.get_data()
    await state.clear()
    await callback.answer()

    job_data = {
        "master_prompt": data["master_prompt"],
        "topic": data["topic"],
        "minutes": data["minutes"],
        "language": data["language"],
        "subtitles": subtitles,
    }

    await callback.message.edit_text(
        "Ma'lumotlar qabul qilindi:\n"
        f"• Mavzu: {job_data['topic']}\n"
        f"• Davomiylik: {job_data['minutes']} daqiqa\n"
        f"• Til: {job_data['language']}\n"
        f"• Subtitr: {'Ha' if job_data['subtitles'] else 'Yo‘q'}\n\n"
        "Keyingi bosqichlarda bu ma'lumotlar asosida ssenariy, ovoz, rasmlar va video yig‘iladi."
    )
    logger.info("Yangi vazifa tayyor: %s", job_data)


async def main() -> None:
    if not config.BOT_TOKEN:
        logger.error("BOT_TOKEN muhit o'zgaruvchisi topilmadi.")
        sys.exit(1)

    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher()

    dp.message.register(cmd_start, CommandStart())
    dp.message.register(cmd_new, Command("new"))
    dp.callback_query.register(cb_cancel, F.data == "job:cancel")
    dp.message.register(process_master_prompt, VideoJobForm.master_prompt)
    dp.message.register(process_topic, VideoJobForm.topic)
    dp.message.register(process_minutes, VideoJobForm.minutes)
    dp.message.register(process_language, VideoJobForm.language)
    dp.callback_query.register(process_subtitles, VideoJobForm.subtitles, F.data.startswith("sub:"))

    logger.info("Bot polling rejimida ishga tushmoqda...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
