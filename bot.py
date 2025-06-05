import os
import re
import logging
import asyncio
from dotenv import load_dotenv
from yt_dlp import YoutubeDL
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile
from aiogram.types import InlineKeyboardButton, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Load .env variables
load_dotenv()
TOKEN = os.getenv("TOKEN")

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Init bot
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Ensure downloads directory exists
os.makedirs("downloads", exist_ok=True)

# In-memory storage for user format data
user_video_data = {}

# Safe filename
def safe_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "_", name)

# /start command
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer("🎬 Send me a YouTube link, and I’ll show available download formats.")

# URL handler
@dp.message(F.text & ~F.text.startswith("/"))
async def handle_url(message: types.Message):
    url = message.text.strip()
    chat_id = message.chat.id

    if "youtube.com" not in url and "youtu.be" not in url:
        await message.answer("❌ Please send a valid YouTube URL.")
        return

    msg = await message.answer("🔍 Fetching formats...")

    try:
        with YoutubeDL({"quiet": True}) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = info.get("formats", [])
            title = safe_filename(info.get("title", "video"))

        # Store format info for this user
        user_video_data[chat_id] = {
            "url": url,
            "formats": {f["format_id"]: f for f in formats},
            "title": title
        }

        # Build inline buttons
        builder = InlineKeyboardBuilder()
        for f in formats:
            ext = f.get("ext")
            note = f.get("format_note", "unknown")
            fid = f.get("format_id")
            size = f.get("filesize", 0)
            size_text = f" ({size / 1024 / 1024:.1f} MB)" if size else ""
            label = f"{ext.upper()} {note}{size_text}"
            builder.add(InlineKeyboardButton(text=label, callback_data=f"dl_{fid}"))

        builder.adjust(2)

        await msg.edit_text(
            f"📥 <b>Formats for:</b> {title}",
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Error fetching formats: {e}")
        await msg.edit_text("❌ Failed to fetch formats. Try again later.")

# Download handler
@dp.callback_query(F.data.startswith("dl_"))
async def handle_download(callback: CallbackQuery):
    chat_id = callback.message.chat.id
    format_id = callback.data.split("_")[1]
    await callback.answer("⏳ Downloading...")

    try:
        user_data = user_video_data.get(chat_id)
        if not user_data:
            await callback.message.answer("❌ Session expired. Please send the link again.")
            return

        # Validate format ID
        selected_format = user_data["formats"].get(format_id)
        if not selected_format:
            await callback.message.answer("❌ Format is no longer valid. Please send the link again.")
            return

        url = user_data["url"]
        title = user_data["title"]
        outtmpl = f"downloads/{title}.%(ext)s"

        ydl_opts = {
            "format": format_id,
            "outtmpl": outtmpl,
            "quiet": True,
        }

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)

        # Check size
        if os.path.getsize(file_path) > 2 * 1024 * 1024 * 1024:
            await callback.message.answer("⚠️ File too large for Telegram (limit: 2GB).")
            os.remove(file_path)
            return

        # Send file
        if info["ext"] in ["mp3", "m4a", "webm"]:
            audio_file = FSInputFile(file_path)
            await callback.message.answer_audio(audio=audio_file, title=title[:64], performer="YouTube")
        else:
            video_file = FSInputFile(file_path)
            await callback.message.answer_video(video=video_file, caption=f"🎬 {title}")
        os.remove(file_path)
        user_video_data.pop(chat_id, None)

    except Exception as e:
        logger.error(f"Download failed: {e}")
        await callback.message.answer(f"❌ Download failed.\n<code>{str(e)}</code>", parse_mode="HTML")

# Bot entry point
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
