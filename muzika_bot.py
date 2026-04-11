import os
import asyncio
import logging
import time
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.client.default import DefaultBotProperties
import yt_dlp
from flask import Flask
from threading import Thread

TOKEN = os.environ.get("BOT_TOKEN")
PROXY = os.environ.get("PROXY_URL")

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
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

        # 1. Bandcamp (eng yaxshi yangi qo'shimcha)
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                data = await asyncio.to_thread(ydl.extract_info, f"bandcampsearch:{query}", download=False)
                for e in data.get('entries', [])[:4]:
                    if e:
                        results.append({
                            'id': e.get('webpage_url'),
                            'title': f"🎵 Bandcamp - {e.get('title', '')[:50]}",
                            'source': 'bc'
                        })
        except:
            pass

        # 2. Mixcloud
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                data = await asyncio.to_thread(ydl.extract_info, f"mixcloudsearch:{query}", download=False)
                for e in data.get('entries', [])[:3]:
                    if e:
                        results.append({
                            'id': e.get('webpage_url'),
                            'title': f"🎧 Mixcloud - {e.get('title', '')[:50]}",
                            'source': 'mc'
                        })
        except:
            pass

        # 3. SoundCloud
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                data = await asyncio.to_thread(ydl.extract_info, f"scsearch5:{query}", download=False)
                for e in data.get('entries', [])[:3]:
                    if e:
                        results.append({
                            'id': e.get('webpage_url'),
                            'title': f"🎧 SC - {e.get('title', '')[:50]}",
                            'source': 'sc'
                        })
        except:
            pass

        # 4. YouTube (oxirgi o'rinda)
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                data = await asyncio.to_thread(ydl.extract_info, f"ytsearch4:{query}", download=False)
                for e in data.get('entries', [])[:2]:
                    if e:
                        results.append({
                            'id': e['id'],
                            'title': f"🎬 YT - {e.get('title', '')[:50]}",
                            'source': 'yt'
                        })
        except:
            pass

        return results[:10]

    async def download(self, url_or_id, source, is_video):
        ts = int(time.time())
        final = f"{self.path}/{ts}.{'mp4' if is_video else 'mp3'}"
        
        opts = {
            'outtmpl': f"{self.path}/{ts}.%(ext)s",
            'quiet': True,
            'retries': 6,
            'fragment_retries': 6
        }
        if PROXY:
            opts['proxy'] = PROXY

        if is_video:
            opts['format'] = 'bestvideo[height<=360]+bestaudio/best'
            opts['merge_output_format'] = 'mp4'
        else:
            opts['format'] = 'bestaudio/best'
            opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}]

        # URL ni to'g'rilash
        if source == 'yt':
            urls = [f"https://www.youtube.com/watch?v={url_or_id}"]
        else:
            urls = [url_or_id]

        for url in urls:
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    await asyncio.to_thread(ydl.download, [url])
                if os.path.exists(final) and os.path.getsize(final) > 10000:
                    return final
            except:
                continue
        raise Exception("Yuklab bo'lmadi")

engine = Engine()

# ==================== HANDLERS ====================
@dp.message(Command("start"))
async def start(m: types.Message, state: FSMContext):
    await state.clear()
    await m.answer("👋 Salom!\nEndi YouTube kamroq, Bandcamp, Mixcloud va SoundCloud ko'proq ishlatiladi.", reply_markup=main_menu())

@dp.message(F.text.in_(["🎵 Musiqa topish", "🎬 Video topish"]))
async def mode_handler(m: types.Message, state: FSMContext):
    is_video = m.text == "🎬 Video topish"
    await state.set_state(SearchState.video if is_video else SearchState.music)
    await m.answer("🔍 Nom yozing:")

@dp.message(SearchState.music | SearchState.video)
async def search_handler(m: types.Message, state: FSMContext):
    is_video = await state.get_state() == SearchState.video.state
    msg = await m.answer("🔍 Qidirilmoqda... (Bandcamp, Mixcloud, SC, YT)")

    results = await engine.search(m.text)
    if not results:
        await msg.edit_text("❌ Hech narsa topilmadi. Boshqa nom bilan urinib ko'ring.")
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=r['title'], callback_data=f"dl|{'v' if is_video else 'm'}|{r['source']}|{r['id']}")]
        for r in results
    ])
    await msg.edit_text("✨ Natijalar (tanlang):", reply_markup=kb)

@dp.callback_query(F.data.startswith("dl|"))
async def download_handler(call: types.CallbackQuery):
    _, mode, source, vid = call.data.split('|', 3)
    is_video = mode == 'v'
    await call.message.edit_text("🚀 Yuklanmoqda... (20-60 soniya)")

    try:
        path = await engine.download(vid, source, is_video)
        size_mb = os.path.getsize(path) / (1024 * 1024)
        if size_mb > 49:
            os.remove(path)
            await call.message.answer("❌ Fayl juda katta (>50MB)")
            return

        file = FSInputFile(path)
        if is_video:
            await call.message.answer_video(file, caption="🎬 Tayyor!")
        else:
            await call.message.answer_audio(file, caption="🎧 Tayyor MP3!")
        os.remove(path)
    except:
        await call.message.answer("⚠️ Yuklab bo'lmadi.\nBoshqa platforma yoki nom bilan urinib ko'ring.")

# Keep Alive
app = Flask(__name__)
@app.route('/')
def home():
    return "Bot ishlayapti 🔥"

async def main():
    Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080))), daemon=True).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
