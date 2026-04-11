import os, asyncio, logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import yt_dlp
from flask import Flask
from threading import Thread

# --- RENDER UCHUN SERVER (UYG'OQ TUTISH UCHUN) ---
app = Flask('')
@app.route('/')
def home(): return "Bot uyg'oq va xizmatingizga tayyor!"

def run():
    # Render avtomatik beradigan PORT orqali ishga tushadi
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

# --- KONFIGURATSIYA ---
TOKEN = os.environ.get("BOT_TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

class SearchState(StatesGroup):
    waiting_music = State()
    waiting_video = State()

# --- KLAVIATURA (XATOSIZ) ---
menu = ReplyKeyboardMarkup(
    keyboard=
    resize_keyboard=True
)

# --- MEDIA ENGINE ---
class ImperatorEngine:
    def __init__(self):
        self.path = "downloads"
        if not os.path.exists(self.path):
            os.makedirs(self.path)

    async def search_media(self, query, is_video=False):
        # Qidiruv turi: Video bo'lsa YouTube, musiqa bo'lsa Soundcloud/YouTube
        search_engine = "ytsearch5" if is_video else "scsearch5"
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'source_address': '0.0.0.0',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = await asyncio.to_thread(ydl.extract_info, f"{search_engine}:{query}", download=False)
                return [{'id': e['id'], 'title': e.get('title', 'Nomsiz')[:45], 'url': e.get('url') or f"https://youtube.com{e['id']}"} for e in info.get('entries', [])]
        except Exception as e:
            logging.error(f"Qidiruvda xato: {e}")
            return []

    async def download_file(self, url, is_video=False):
        file_id = "".join(x for x in url if x.isalnum())[-10:]
        ext = 'mp4' if is_video else 'mp3'
        out_path = f"{self.path}/{file_id}.{ext}"
        
        ydl_opts = {
            'format': 'bestvideo[ext=mp4][height<=720]+bestaudio[ext=m4a]/best[ext=mp4]/best' if is_video else 'bestaudio/best',
            'outtmpl': out_path,
            'geo_bypass': True,
            'nocheckcertificate': True,
            'socket_timeout': 30,
            'source_address': '0.0.0.0',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            await asyncio.to_thread(ydl.download, [url])
            return out_path

engine = ImperatorEngine()

# --- HANDLERLAR ---
@dp.message(Command("start"))
async def start(m: types.Message, state: FSMContext):
    await state.clear()
    await m.answer(
        f"🌟 **Assalomu alaykum, {m.from_user.first_name}!**\n\n"
        "Men sizning professional media yordamchingizman. 🤖\n\n"
        "🎬 **Video** — YouTube va boshqa manbalardan.\n"
        "🎵 **Musiqa** — Soundcloud va YouTube tizimidan.\n\n"
        "Qidiruvni boshlash uchun quyidagi tugmalardan birini tanlang:", 
        reply_markup=menu
    )

@dp.message(F.text == "🎵 Musiqa topish")
async def music_mode(m: types.Message, state: FSMContext):
    await state.set_state(SearchState.waiting_music)
    await m.answer("🎵 Musiqa nomini yoki xonanda ismini yuboring:")

@dp.message(F.text == "🎬 Video topish")
async def video_mode(m: types.Message, state: FSMContext):
    await state.set_state(SearchState.waiting_video)
    await m.answer("🎬 Video nomini yoki YouTube linkini yuboring:")

@dp.message(SearchState.waiting_music)
@dp.message(SearchState.waiting_video)
async def process_search(m: types.Message, state: FSMContext):
    is_video = (await state.get_state()) == SearchState.waiting_video
    wait = await m.answer("🔍 **Galaktik qidiruv ketmoqda...**\nIltimos, ozgina kuting.")
    
    results = await engine.search_media(m.text, is_video)
    if not results:
        return await wait.edit_text("❌ Kechirasiz, hech narsa topilmadi. Iltimos, boshqa so'zlar bilan qidirib ko'ring.")

    keyboard = []
    for r in results:
        # Callback data uzunligi 64 belgidan oshmasligi kerak
        cb_data = f"dl|{'v' if is_video else 'm'}|{r['id']}"
        keyboard.append(}", callback_data=cb_data)])
    
    await wait.delete()
    await m.answer("✨ Siz uchun bir nechta ajoyib variantlarni topdim:", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@dp.callback_query(F.data.startswith("dl|"))
async def handle_download(call: types.CallbackQuery):
    _, f_type, f_id = call.data.split('|')
    is_video = f_type == 'v'
    url = f"https://youtube.com{f_id}"
    
    await call.message.edit_text("🚀 **Yuklash boshlandi...**\nHozir yuboraman, iltimos sahifadan chiqib ketmang.")
    
    try:
        res = await engine.download_file(url, is_video)
        file = FSInputFile(res)
        
        if is_video:
            await call.message.answer_video(file, caption="✅ **Video tayyor!**\nMaroqli hordiq tilayman! ✨")
        else:
            await call.message.answer_audio(file, caption="✅ **Musiqa tayyor!**\nYoqimli tinglov tilayman! 🎵")
        
        if os.path.exists(res):
            os.remove(res)
        await call.message.delete()
    except Exception as e:
        logging.error(f"Yuklashda xato: {e}")
        await call.message.answer("⚠️ Kechirasiz, ushbu faylni yuklashda muammo bo'ldi. Fayl hajmi 50MB dan katta bo'lishi mumkin.")

@dp.message(F.text == "📊 Statistika")
async def stats(m: types.Message):
    await m.answer(f"📈 **Bot holati:** Online ✅\n🕒 **Tizim:** 24/7 Uyg'oq\n🛰 **Server:** Render Cloud")

@dp.message(F.text == "ℹ️ Ma'lumot")
async def info(m: types.Message):
    await m.answer("🤖 **Imperator Media Bot v10.0**\n\nUshbu bot YouTube va Soundcloud tizimlaridan eng sifatli media fayllarni topish va yuklash uchun yaratilgan.")

# --- ISHGA TUSHIRISH ---
async def main():
    # Flaskni alohida oqimda ishga tushiramiz
    Thread(target=run).start()
    # Botni ishga tushirish
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot to'xtatildi")
