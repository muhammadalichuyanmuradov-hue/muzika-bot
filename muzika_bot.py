import os, asyncio, logging, time
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import (
    FSInputFile, ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import yt_dlp
from flask import Flask
from threading import Thread

# --- RENDER UYG'OQ TUTISH ---
app = Flask('')
@app.route('/')
def home():
    return "Bot is Online"

def run():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

# --- CONFIG ---
TOKEN = os.environ.get("BOT_TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

# --- STATE ---
class SearchState(StatesGroup):
    waiting_music = State()
    waiting_video = State()

# --- MENU ---
def get_menu():
    buttons = [
        [KeyboardButton(text="🎵 Musiqa topish")],
        [KeyboardButton(text="🎬 Video topish")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# --- ENGINE ---
class ImperatorEngine:
    def __init__(self):
        self.path = "downloads"
        if not os.path.exists(self.path):
            os.makedirs(self.path)

    async def search_media(self, query, is_video=False):
        search_engine = "ytsearch10"
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = await asyncio.to_thread(
                    ydl.extract_info,
                    f"{search_engine}:{query}",
                    download=False
                )
                return [
                    {
                        'id': e['id'],
                        'title': e.get('title', 'Noma\'lum')[:40]
                    }
                    for e in info.get('entries', [])
                ]
        except:
            return []

    async def download_file(self, url, is_video=False):
        filename = f"{self.path}/file_{int(time.time())}.{'mp4' if is_video else 'mp3'}"

        ydl_opts = {
            'format': 'bestvideo[height<=480]+bestaudio/best' if is_video else 'bestaudio/best',
            'outtmpl': filename,
            'geo_bypass': True,
            'nocheckcertificate': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            await asyncio.to_thread(ydl.download, [url])

        return filename

engine = ImperatorEngine()

# --- START ---
@dp.message(Command("start"))
async def start(m: types.Message, state: FSMContext):
    await state.clear()
    await m.answer(
        f"🌟 Salom, {m.from_user.first_name}!\nMedia botga xush kelibsiz!",
        reply_markup=get_menu()
    )

# --- MODES ---
@dp.message(F.text == "🎵 Musiqa topish")
async def music_mode(m: types.Message, state: FSMContext):
    await state.set_state(SearchState.waiting_music)
    await m.answer("🎵 Musiqa nomini yozing:")

@dp.message(F.text == "🎬 Video topish")
async def video_mode(m: types.Message, state: FSMContext):
    await state.set_state(SearchState.waiting_video)
    await m.answer("🎬 Video nomini yozing:")

# --- SEARCH ---
@dp.message(SearchState.waiting_music)
@dp.message(SearchState.waiting_video)
async def process_search(m: types.Message, state: FSMContext):
    is_video = (await state.get_state()) == SearchState.waiting_video

    wait = await m.answer("🔍 Qidirilmoqda...")
    results = await engine.search_media(m.text, is_video)

    if not results:
        return await wait.edit_text("❌ Hech narsa topilmadi.")

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=r['title'],
                callback_data=f"dl|{'v' if is_video else 'm'}|{r['id']}"
            )] for r in results
        ]
    )

    await wait.delete()
    await m.answer("✨ Topilgan natijalar:", reply_markup=kb)

# --- DOWNLOAD ---
@dp.callback_query(F.data.startswith("dl|"))
async def handle_download(call: types.CallbackQuery):
    _, f_type, f_id = call.data.split('|')
    is_video = f_type == 'v'

    url = f"https://www.youtube.com/watch?v={f_id}"

    await call.message.edit_text("🚀 Yuklanmoqda...")

    try:
        file_path = await engine.download_file(url, is_video)
        file = FSInputFile(file_path)

        if is_video:
            await call.message.answer_video(file, caption="✅ Tayyor!")
        else:
            await call.message.answer_audio(file, caption="🎵 Tayyor!")

        if os.path.exists(file_path):
            os.remove(file_path)

        await call.message.delete()

    except Exception as e:
        await call.message.answer("⚠️ Xatolik! Fayl katta yoki yuklab bo‘lmadi.")

# --- MAIN ---
async def main():
    Thread(target=run).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
