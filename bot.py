import asyncio
import logging
import uuid
import tempfile
import subprocess
from pathlib import Path
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import (
    BotCommand, ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
)
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO)

bot = Bot(
    token=os.getenv("BOT_TOKEN"),
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

user_temp_files = {}  # {user_id: {"aac": Path, "base": uid}}


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📤 Отправить видео")]],
        resize_keyboard=True
    )
    text = (
        "🎮 <b>Добро пожаловать в Video2Audio Bot!</b>\n\n"
        "Я помогу тебе превратить любое видео в качественное аудио.\n\n"
        "📅 Отправь видео и выбери формат:\n"
        "• 🎷 MP3\n"
        "• 🎶 M4A\n"
        "• 🥪 AAC (original)\n"
        "• 🎙 Voice (.ogg)\n\n"
        "💬 По всем вопросам: @yungnolife"
    )
    await message.answer(text, reply_markup=keyboard)


@dp.message(F.video | (F.document & F.document.mime_type.startswith("video/")))
async def handle_video(message: types.Message):
    user_id = message.from_user.id
    file = message.video or message.document
    file_id = file.file_id
    telegram_file = await bot.get_file(file_id)
    file_bytes = await bot.download_file(telegram_file.file_path)

    temp_dir = Path(tempfile.gettempdir())
    uid = uuid.uuid4().hex
    video_path = temp_dir / f"{uid}.mp4"
    aac_path = temp_dir / f"{uid}.aac"

    with open(video_path, "wb") as f:
        f.write(file_bytes.read())

    ffmpeg_path = r"C:\\ffmpeg\\bin\\ffmpeg.exe"
    subprocess.run([
        ffmpeg_path,
        "-y", "-i", str(video_path),
        "-map", "0:a",
        "-c:a", "copy",
        str(aac_path)
    ], check=True)

    user_temp_files[user_id] = {"aac": aac_path, "base": uid}

    buttons = [
        [InlineKeyboardButton(text="🎷 MP3", callback_data="to_mp3")],
        [InlineKeyboardButton(text="🎶 M4A", callback_data="to_m4a")],
        [InlineKeyboardButton(text="🥪 AAC (original)", callback_data="to_aac")],
        [InlineKeyboardButton(text="🎙 Voice (.ogg)", callback_data="to_voice")],
        [InlineKeyboardButton(text="💬 Связаться с поддержкой", url="https://t.me/yungnolife")]
    ]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    await message.answer(
        "🌐 Выбери нужный формат аудио:",
        reply_markup=kb
    )
    video_path.unlink(missing_ok=True)


@dp.callback_query(F.data.in_({"to_mp3", "to_m4a", "to_aac", "to_voice"}))
async def convert_audio(callback: CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    data = user_temp_files.get(user_id)

    if not data:
        await callback.message.answer("❌ Не найден временный файл. Попробуй заново.")
        return

    aac_path = data["aac"]
    uid = data["base"]
    temp_dir = Path(tempfile.gettempdir())
    ffmpeg_path = r"C:\\ffmpeg\\bin\\ffmpeg.exe"

    if callback.data == "to_aac":
        await callback.message.answer_document(
            types.FSInputFile(aac_path),
            caption="🧪 Оригинальный .aac без потерь\n"
        )

    elif callback.data == "to_mp3":
        mp3_path = temp_dir / f"{uid}.mp3"
        subprocess.run([
            ffmpeg_path, "-y", "-i", str(aac_path),
            "-acodec", "libmp3lame", "-b:a", "192k",
            str(mp3_path)
        ], check=True)
        await callback.message.answer_audio(
            types.FSInputFile(mp3_path),
            caption="🎧 MP3-файл готов.\n"
        )
        mp3_path.unlink(missing_ok=True)

    elif callback.data == "to_m4a":
        m4a_path = temp_dir / f"{uid}.m4a"
        subprocess.run([
            ffmpeg_path, "-y", "-i", str(aac_path),
            "-c:a", "aac", "-b:a", "192k",
            str(m4a_path)
        ], check=True)
        await callback.message.answer_document(
            types.FSInputFile(m4a_path),
            caption="🎶 M4A-файл готов.\n"
        )
        m4a_path.unlink(missing_ok=True)

    elif callback.data == "to_voice":
        ogg_path = temp_dir / f"{uid}.ogg"
        subprocess.run([
            ffmpeg_path, "-y", "-i", str(aac_path),
            "-ac", "1", "-ar", "48000",
            "-c:a", "libopus", "-b:a", "64k",
            "-application", "voip",
            str(ogg_path)
        ], check=True)
        await callback.message.answer_voice(
            types.FSInputFile(ogg_path),
            caption="🎙 Voice-сообщение готово."
        )
        ogg_path.unlink(missing_ok=True)

    aac_path.unlink(missing_ok=True)
    user_temp_files.pop(user_id, None)


async def main():
    await bot.set_my_commands([
        BotCommand(command="start", description="Запуск бота")
    ])
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())