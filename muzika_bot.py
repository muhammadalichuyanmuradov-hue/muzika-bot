import os, asyncio, logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import yt_dlp
from flask import Flask
from threading import Thread

# --- RENDER UCHUN SERVER ---
app = Flask('')
@app.route('/')
def home(): return "Bot uyg'oq!"

def run():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))

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
    keyboard=,
    ],
    resize_keyboard=True
)

# --- MEDIA ENGINE (KUCHAYTIRILGAN) ---
class ImperatorEngine:
    def __init__(self):
        self.path = "downloads"
        if not os.path.exists(self.path):
            os.makedirs(self.path)

    async def search_media(self, query, is_video=False):
        # Agar YouTube bloklasa, umumiy qidiruvga o'tadi
        search_engine = "ytsearch5" if is_video else "scsearch5"
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'source_address': '0.0.0.0', # DNS xatolarini oldini olish
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = await asyncio.to_thread(ydl.extract_info, f"{search_engine}:{query}", download=False)
                return [{'id': e['id'], 'title': e.get('title', 'Noma\'lum')[:45], 'url': e.get('url') or f"https://youtube.com{e['id']}"} for e in info.get('entries', [])]
        except: return []

    async def download_file(self, url, is_video=False):
        file_id = "".join(x for x in url if x.isalnum())[-10:]
        ext = 'mp4' if is_video else 'mp3'
        out_path = f"{self.path}/{file_id}.{ext}"
        
        ydl_opts = {
            'format': 'bestvideo[ext=mp4][height<=720]+bestaudio[ext=m4a]/best[ext=mp4]/best' if is_video else 'bestaudio/best',
            'outtmpl': out_path,
            'geo_bypass': True,
            'nocheckcertificate': True,
            'socket_timeout': 20,
            'source_address': '0.0.0.0',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            await asyncio.to_thread(ydl.download, [url])
            return out_path

engine = ImperatorEngine()

# --- BUYRUQLAR ---
@dp.message(Command("start"))
async def start(m: types.Message, state: FSMContext):
    await state.clear()
    await m.answer(
        f"🌟 **Assalomu alaykum, {m.from_user.first_name}!**\n\n"
        "Men sizga eng yaxshi musiqa va videolarni topishda yordam beraman. 🤖\n"
        "Marhamat, quyidagi bo'limlardan birini tanlang:", 
        reply_markup=menu
    )

@dp.message(F.text == "🎵 Musiqa topish")
async def music_mode(m: types.Message, state: FSMContext):
    await state.set_state(SearchState.waiting_music)
    await m.answer("🎵 Musiqa nomini yoki linkini yuboring:")

@dp.message(F.text == "🎬 Video topish")
async def video_mode(m: types.Message, state: FSMContext):
    await state.set_state(SearchState.waiting_video)
    await m.answer("🎬 Video nomini yoki YouTube linkini yuboring:")

@dp.message(SearchState.waiting_music)
@dp.message(SearchState.waiting_video)
async def process_search(m: types.Message, state: FSMContext):
    is_video = (await state.get_state()) == SearchState.waiting_video
    wait = await m.answer("🔍 Galaktik qidiruv ketmoqda, iltimos kuting...")
    
    results = await engine.search_media(m.text, is_video)
    if not results:
        return await wait.edit_text("❌ Kechirasiz, hech narsa topilmadi. Iltimos, boshqa so'z bilan urinib ko'ring.")

    keyboard =}", callback_data=f"dl|{'v' if is_video else 'm'}|{r['id']}")] for r in results]
    await wait.delete()
    await m.answer("✨ Siz uchun bir nechta ajoyib variantlarni topdim:", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@dp.callback_query(F.data.startswith("dl|"))
async def handle_download(call: types.CallbackQuery):
    _, f_type, f_id = call.data.split('|')
    is_video = f_type == 'v'
    url = f"https://youtube.com{f_id}"
    
    await call.message.edit_text("🚀 Yuklash boshlandi, hozir yuboraman...")
    
    try:
        res = await engine.download_file(url, is_video)
        file = FSInputFile(res)
        
        if is_video:
            await call.message.answer_video(file, caption="✅ Video tayyor! Maroqli hordiq tilayman! ✨")
        else:
            await call.message.answer_audio(file, caption="✅ Musiqa tayyor! Yoqimli tinglov! 🎵")
        
        if os.path.exists(res): os.remove(res)
        await call.message.delete()
        await call.message.answer("😊 Xizmatingizda bo'lganimdan xursandman! Yana nimadir topaymi?", reply_markup=menu)
    except Exception as e:
        logging.error(f"Xatolik: {e}")
        await call.message.answer("⚠️ Kechirasiz, ushbu faylni yuklashda muammo bo'ldi. Balki u juda kattadir yoki manba cheklangandir.")

# --- ISHGA TUSHIRISH ---
async def main():
    Thread(target=run).start() # Render uyg'oq turishi uchun
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
