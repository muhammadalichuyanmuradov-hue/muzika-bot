import os, asyncio, logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import yt_dlp
from flask import Flask
from threading import Thread

# --- RENDER UCHUN PORT VA SERVER (WEB SERVICE UCHUN) ---
app = Flask('')
@app.route('/')
def home(): return "Bot is running!"

def run():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

# --- KONFIGURATSIYA ---
TOKEN = os.environ.get("BOT_TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

class SearchState(StatesGroup):
    waiting_music = State()
    waiting_video = State()

# --- KLAVIATURA ---
menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🎵 Musiqa"), KeyboardButton(text="🎬 Video")],
        [KeyboardButton(text="📊 Statistika"), KeyboardButton(text="ℹ️ Ma'lumot")]
    ],
    resize_keyboard=True
)

# --- MEDIA ENGINE ---
class ImperatorEngine:
    def __init__(self):
        self.path = "downloads"
        if not os.path.exists(self.path): os.makedirs(self.path)

    async def search_media(self, query, is_video=False):
        search_type = "ytsearch5" if is_video else "scsearch5"
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = await asyncio.to_thread(ydl.extract_info, f"{search_type}:{query}", download=False)
            return [{'id': e['id'], 'title': e.get('title', 'Nomsiz')[:45], 'url': e.get('url') or f"https://youtube.com{e['id']}"} for e in info.get('entries', [])]

    async def download_file(self, url, is_video=False):
        file_id = "".join(x for x in url if x.isalnum())[-10:]
        ext = 'mp4' if is_video else 'mp3'
        out_path = f"{self.path}/{file_id}.{ext}"
        
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]' if is_video else 'bestaudio/best',
            'outtmpl': out_path,
            'geo_bypass': True,
            'nocheckcertificate': True,
            'quiet': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Fayl hajmini tekshirish (Render limiti uchun)
            meta = await asyncio.to_thread(ydl.extract_info, url, download=False)
            if meta.get('filesize', 0) > 50 * 1024 * 1024: # 50MB
                return "limit"
            
            await asyncio.to_thread(ydl.download, [url])
            return out_path

engine = ImperatorEngine()

# --- HANDLERS ---
@dp.message(Command("start"))
async def start(m: types.Message, state: FSMContext):
    await state.clear()
    await m.answer(f"🌟 Imperator AI'ga xush kelibsiz, {m.from_user.first_name}!", reply_markup=menu)

@dp.message(F.text == "🎵 Musiqa")
async def music_mode(m: types.Message, state: FSMContext):
    await state.set_state(SearchState.waiting_music)
    await m.answer("🔍 Musiqa nomini yozing:")

@dp.message(F.text == "🎬 Video")
async def video_mode(m: types.Message, state: FSMContext):
    await state.set_state(SearchState.waiting_video)
    await m.answer("🔍 Video nomini yoki YouTube linkini yozing:")

@dp.message(SearchState.waiting_music)
@dp.message(SearchState.waiting_video)
async def process_search(m: types.Message, state: FSMContext):
    is_video = (await state.get_state()) == SearchState.waiting_video
    wait = await m.answer("🔎 Qidiryapman...")
    
    results = await engine.search_media(m.text, is_video)
    if not results:
        return await wait.edit_text("❌ Hech narsa topilmadi.")

    keyboard = [[InlineKeyboardButton(text=f"⬇️ {r['title']}", callback_data=f"dl|{'v' if is_video else 'm'}|{r['id']}")] for r in results]
    await wait.delete()
    await m.answer("Topilgan natijalar:", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@dp.callback_query(F.data.startswith("dl|"))
async def handle_download(call: types.CallbackQuery):
    _, f_type, f_id = call.data.split('|')
    is_video = f_type == 'v'
    url = f"https://youtube.com{f_id}"
    
    await call.message.edit_text("🚀 Yuklab olyapman, ozroq kuting...")
    
    res = await engine.download_file(url, is_video)
    if res == "limit":
        return await call.message.edit_text("⚠️ Fayl juda katta (50MB dan ortiq). Kichikroq video tanlang.")
    
    try:
        file = FSInputFile(res)
        if is_video: await call.message.answer_video(file, caption="✅ Video tayyor!")
        else: await call.message.answer_audio(file, caption="✅ Musiqa tayyor!")
        os.remove(res)
        await call.message.delete()
    except Exception as e:
        await call.message.answer("❌ Xatolik yuz berdi. YouTube bloklagan bo'lishi mumkin.")

# --- ISHGA TUSHIRISH ---
async def main():
    # Flaskni alohida oqimda ishga tushirish (Render uyg'oq turishi uchun)
    Thread(target=run).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
