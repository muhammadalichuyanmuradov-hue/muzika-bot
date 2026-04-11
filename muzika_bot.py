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

TOKEN = os.environ.get("BOT_TOKEN")
PROXY = os.environ.get("PROXY_URL")

bot = Bot(token=TOKEN, parse_mode="HTML")
dp = Dispatcher()

logging.basicConfig(level=logging.INFO)

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

class Engine:
    def __init__(self):
        self.path = "downloads"
        os.makedirs(self.path, exist_ok=True)

    async def search(self, query: str):
        results = []
        ydl_opts = {'quiet': True, 'extract_flat': True, 'noplaylist': True}
        if PROXY:
            ydl_opts['proxy'] = PROXY

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                data = await asyncio.to_thread(ydl.extract_info, f"ytsearch5:{query}", download=False)
                for e in data.get('entries', [])[:6]:
                    if e and e.get('id'):
                        results.append({
                            'id': e['id'],
                            'title': f"🎬 {e.get('title', 'Video')[:45]}",
                            'source': 'yt'
                        })
        except:
            pass

        return results[:8]

    async def download(self, vid, source, is_video):
        ts = int(time.time())
        final = f"{self.path}/{ts}.{'mp4' if is_video else 'mp3'}"
        
        opts = {
            'outtmpl': f"{self.path}/{ts}.%(ext)s",
            'quiet': True,
            'retries': 4,
            'fragment_retries': 4
        }
        if PROXY:
            opts['proxy'] = PROXY

        if is_video:
            opts['format'] = 'bestvideo[height<=360]+bestaudio/best'
            opts['merge_output_format'] = 'mp4'
        else:
            opts['format'] = 'bestaudio/best'
            opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}]

        urls = [f"https://www.youtube.com/watch?v={vid}"] if source == "yt" else [vid if vid.startswith("http") else f"https://soundcloud.com/{vid}"]

        for url in urls:
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    await asyncio.to_thread(ydl.download, [url])
                if os.path.exists(final) and os.path.getsize(final) > 5000:
                    return final
            except:
                continue
        raise Exception("Yuklab bo'lmadi")

engine = Engine()

@dp.message(Command("start"))
async def start(m: types.Message, state: FSMContext):
    await state.clear()
    await m.answer("👋 Salom! \nMusiqa yoki video yuklash uchun menyudan tanlang.", reply_markup=main_menu())

@dp.message(F.text == "🎵 Musiqa topish")
async def music_mode(m: types.Message, state: FSMContext):
    await state.set_state(SearchState.music)
    await m.answer("🎵 Qo‘shiq nomini yozing:")

@dp.message(F.text == "🎬 Video topish")
async def video_mode(m: types.Message, state: FSMContext):
    await state.set_state(SearchState.video)
    await m.answer("🎬 Video nomini yozing:")

@dp.message(SearchState.music | SearchState.video)
async def search_handler(m: types.Message, state: FSMContext):
    is_video = await state.get_state() == SearchState.video.state
    msg = await m.answer("🔍 Qidirilmoqda...")

    results = await engine.search(m.text)
    if not results:
        await msg.edit_text("❌ Hech narsa topilmadi.")
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=r['title'], callback_data=f"dl|{'v' if is_video else 'm'}|{r['source']}|{r['id']}")]
        for r in results
    ])
    await msg.edit_text("✨ Natijalar - tanlang:", reply_markup=kb)

@dp.callback_query(F.data.startswith("dl|"))
async def download_handler(call: types.CallbackQuery):
    _, mode, source, vid = call.data.split('|', 3)
    is_video = mode == 'v'
    await call.message.edit_text("🚀 Yuklanmoqda... Biroz kuting")

    try:
        path = await engine.download(vid, source, is_video)
        size_mb = os.path.getsize(path) / (1024*1024)
        if size_mb > 49:
            os.remove(path)
            await call.message.answer("❌ Fayl 50MB dan katta")
            return

        file = FSInputFile(path)
        if is_video:
            await call.message.answer_video(file, caption="🎬 Tayyor (360p)")
        else:
            await call.message.answer_audio(file, caption="🎧 Tayyor MP3!")
        os.remove(path)
    except Exception as e:
        await call.message.answer("⚠️ Yuklab bo'lmadi.\nKeyinroq urinib ko'ring yoki proxy qo'shing.")

# Keep-alive
app = Flask(__name__)
@app.route('/')
def home():
    return "Bot ishlayapti 🔥"

async def main():
    Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080))), daemon=True).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
