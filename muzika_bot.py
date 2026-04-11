import os
import asyncio
import logging
import time
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import yt_dlp
from flask import Flask
from threading import Thread

# ====================== CONFIG ======================
TOKEN = os.environ.get("BOT_TOKEN")
PROXY = os.environ.get("PROXY_URL")

bot = Bot(token=TOKEN, parse_mode="HTML")
dp = Dispatcher()

logging.basicConfig(level=logging.INFO)

# ====================== STATES & MENU ======================
class SearchState(StatesGroup):
    music = State()
    video = State()

def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎵 Musiqa topish")],
            [KeyboardButton(text="🎬 Video topish")],
            [KeyboardButton(text="ℹ️ Yordam")]
        ],
        resize_keyboard=True
    )

# ====================== ENGINE (Yaxshilangan) ======================
class Engine:
    def __init__(self):
        self.path = "downloads"
        os.makedirs(self.path, exist_ok=True)

    def get_ydl_opts(self, proxy=None):
        opts = {
            'quiet': True,
            'noplaylist': True,
            'retries': 5,
            'fragment_retries': 5,
            'ignoreerrors': True,
            'http_headers': {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        }
        if proxy:
            opts['proxy'] = proxy
        return opts

    async def search(self, query: str):
        results = []
        ydl_opts = self.get_ydl_opts(PROXY)

        # YouTube
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                data = await asyncio.to_thread(ydl.extract_info, f"ytsearch5:{query}", download=False)
                for entry in data.get('entries', [])[:5]:
                    if entry and entry.get('id'):
                        results.append({
                            'id': entry['id'],
                            'title': f"🎬 {entry.get('title', 'No title')[:50]}",
                            'source': 'yt'
                        })
        except Exception as e:
            logging.error(f"YT Search error: {e}")

        # SoundCloud (yaxshilangan)
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                data = await asyncio.to_thread(ydl.extract_info, f"scsearch5:{query}", download=False)
                for entry in data.get('entries', [])[:5]:
                    if entry:
                        results.append({
                            'id': entry.get('webpage_url') or entry.get('id'),
                            'title': f"🎧 {entry.get('title', 'No title')[:50]}",
                            'source': 'sc'
                        })
        except Exception as e:
            logging.error(f"SC Search error: {e}")

        return results[:8]

    async def download(self, vid: str, source: str, is_video: bool):
        timestamp = int(time.time())
        ext = "mp4" if is_video else "mp3"
        final_path = f"{self.path}/{timestamp}.{ext}"

        ydl_opts = self.get_ydl_opts(PROXY)
        ydl_opts.update({
            'outtmpl': f"{self.path}/{timestamp}.%(ext)s",
            'progress_hooks': [],
        })

        if is_video:
            ydl_opts.update({
                'format': 'bestvideo[height<=360]+bestaudio/best[height<=360]/best',
                'merge_output_format': 'mp4',
            })
        else:
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }]
            })

        urls = []
        if source == "yt":
            urls = [
                f"https://www.youtube.com/watch?v={vid}",
                f"https://piped.video/watch?v={vid}",
            ]
        else:
            urls = [vid if vid.startswith("http") else f"https://soundcloud.com/{vid}"]

        for url in urls:
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    await asyncio.to_thread(ydl.download, [url])
                
                if os.path.exists(final_path) and os.path.getsize(final_path) > 10000:
                    return final_path
            except Exception as e:
                logging.warning(f"Failed {url}: {e}")
                continue

        raise Exception("Barcha usullar bilan yuklab bo'lmadi")

engine = Engine()

# ====================== HANDLERS ======================
@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        f"👋 Salom <b>{message.from_user.first_name}</b>!\n\n"
        "🤖 <b>Universal Media Bot</b>\n"
        "✅ YouTube + SoundCloud\n"
        "✅ MP3 192kbps\n"
        "✅ Video 360p\n"
        "✅ Anti-block",
        reply_markup=main_menu()
    )

@dp.message(F.text == "🎵 Musiqa topish")
async def music_mode(message: types.Message, state: FSMContext):
    await state.set_state(SearchState.music)
    await message.answer("🎵 Qo‘shiq yoki ijrochi nomini yozing:")

@dp.message(F.text == "🎬 Video topish")
async def video_mode(message: types.Message, state: FSMContext):
    await state.set_state(SearchState.video)
    await message.answer("🎬 Video nomini yozing:")

@dp.message(SearchState.music | SearchState.video)
async def handle_search(message: types.Message, state: FSMContext):
    is_video = (await state.get_state()) == SearchState.video.state
    msg = await message.answer("🔍 Qidirilmoqda...")

    results = await engine.search(message.text.strip())

    if not results:
        await msg.edit_text("❌ Hech narsa topilmadi. Boshqa nom bilan urinib ko‘ring.")
        await state.clear()
        return

    buttons = [
        [InlineKeyboardButton(text=r['title'], callback_data=f"dl|{'v' if is_video else 'm'}|{r['source']}|{r['id']}")]
        for r in results
    ]

    await msg.edit_text("✨ Natijalar:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@dp.callback_query(F.data.startswith("dl|"))
async def handle_download(callback: types.CallbackQuery):
    _, mode, source, vid = callback.data.split('|', 3)
    is_video = mode == 'v'

    await callback.message.edit_text("🚀 Yuklanmoqda... (20-70 soniya kuting)")

    try:
        file_path = await engine.download(vid, source, is_video)

        size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if size_mb > 49:
            os.remove(file_path)
            return await callback.message.answer("❌ Fayl 50MB dan katta.")

        file = FSInputFile(file_path)
        if is_video:
            await callback.message.answer_video(file, caption="🎬 Tayyor! 360p")
        else:
            await callback.message.answer_audio(file, caption="🎧 Tayyor MP3!")

        os.remove(file_path)

    except Exception as e:
        logging.error(f"Download error: {e}")
        await callback.message.answer("⚠️ Yuklab bo‘lmadi.\n\nProxy qo‘shing yoki keyinroq urinib ko‘ring.")

# ====================== MAIN ======================
app = Flask(__name__)
@app.route('/')
def home():
    return "Bot ishlayapti!"

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

async def main():
    Thread(target=run_flask, daemon=True).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
