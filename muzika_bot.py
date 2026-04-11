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

# ---------- KEEP ALIVE ----------
app = Flask('')
@app.route('/')
def home():
    return "🔥 Bot ishlayapti!"

def run():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

# ---------- CONFIG ----------
TOKEN = os.environ.get("BOT_TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

# ---------- STATE ----------
class SearchState(StatesGroup):
    music = State()
    video = State()

# ---------- MENU ----------
def menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎵 Musiqa topish")],
            [KeyboardButton(text="🎬 Video topish")],
            [KeyboardButton(text="ℹ️ Yordam")]
        ],
        resize_keyboard=True
    )

# ---------- ENGINE ----------
class Engine:
    def __init__(self):
        self.path = "downloads"
        if not os.path.exists(self.path):
            os.makedirs(self.path)

    # 🔍 MULTI SEARCH
    async def search(self, query):
        results = []

        # YouTube
        try:
            with yt_dlp.YoutubeDL({'quiet': True, 'extract_flat': True}) as ydl:
                data = await asyncio.to_thread(
                    ydl.extract_info,
                    f"ytsearch5:{query}",
                    download=False
                )
                for v in data['entries']:
                    results.append({
                        'id': v['id'],
                        'title': "🎬 " + v['title'][:40],
                        'source': 'yt'
                    })
        except:
            pass

        # SoundCloud
        try:
            with yt_dlp.YoutubeDL({'quiet': True, 'extract_flat': True}) as ydl:
                data = await asyncio.to_thread(
                    ydl.extract_info,
                    f"scsearch5:{query}",
                    download=False
                )
                for v in data['entries']:
                    results.append({
                        'id': v['id'],
                        'title': "🎧 " + v['title'][:40],
                        'source': 'sc'
                    })
        except:
            pass

        return results[:10]

    # 🚀 ANTI-BLOCK DOWNLOAD
    async def download(self, vid, source, is_video):
        urls = []

        if source == "yt":
            urls = [
                f"https://www.youtube.com/watch?v={vid}",
                f"https://piped.video/watch?v={vid}",
                f"https://yewtu.be/watch?v={vid}"
            ]
        elif source == "sc":
            urls = [f"https://soundcloud.com/{vid}"]

        filename = f"{self.path}/{int(time.time())}.{'mp4' if is_video else 'mp3'}"

        base_opts = {
            'outtmpl': filename,
            'quiet': True,
            'noplaylist': True,
            'retries': 3,
            'fragment_retries': 3,
            'geo_bypass': True,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0'
            }
        }

        if is_video:
            base_opts.update({
                'format': 'bestvideo[height<=360]+bestaudio/best',
                'merge_output_format': 'mp4'
            })
        else:
            base_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192'
                }]
            })

        # 🔁 TRY ALL URLS
        for url in urls:
            try:
                with yt_dlp.YoutubeDL(base_opts) as ydl:
                    await asyncio.to_thread(ydl.download, [url])
                return filename
            except Exception as e:
                print("❌ Failed:", url)

        raise Exception("Download failed")

engine = Engine()

# ---------- START ----------
@dp.message(Command("start"))
async def start(m: types.Message, state: FSMContext):
    await state.clear()
    await m.answer(
        f"👋 Salom {m.from_user.first_name}!\n\n"
        "🤖 MEN UNIVERSAL MEDIA BOTMAN!\n\n"
        "🎧 Musiqa yuklab beraman\n"
        "🎬 Video yuklab beraman (360p)\n"
        "🚫 Block bo‘lsa ham ishlayman\n\n"
        "👇 Boshlash uchun tanlang:",
        reply_markup=menu()
    )

# ---------- HELP ----------
@dp.message(F.text == "ℹ️ Yordam")
async def help_cmd(m: types.Message):
    await m.answer(
        "📌 BOT IMKONIYATLARI:\n\n"
        "🎵 Musiqa topish → MP3 yuklaydi\n"
        "🎬 Video topish → 360p video\n"
        "🌐 YouTube + SoundCloud\n"
        "🚀 Anti-block system\n\n"
        "💡 Faqat nom yozing va tanlang!"
    )

# ---------- MODE ----------
@dp.message(F.text == "🎵 Musiqa topish")
async def music(m: types.Message, state: FSMContext):
    await state.set_state(SearchState.music)
    await m.answer("🎵 Qo‘shiq nomini yozing:")

@dp.message(F.text == "🎬 Video topish")
async def video(m: types.Message, state: FSMContext):
    await state.set_state(SearchState.video)
    await m.answer("🎬 Video nomini yozing:")

# ---------- SEARCH ----------
@dp.message(SearchState.music)
@dp.message(SearchState.video)
async def search(m: types.Message, state: FSMContext):
    st = await state.get_state()
    is_video = st == SearchState.video

    msg = await m.answer("🔍 Qidirilmoqda...")

    results = await engine.search(m.text)

    if not results:
        return await msg.edit_text("❌ Hech narsa topilmadi")

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=r['title'],
                callback_data=f"dl|{'v' if is_video else 'm'}|{r['source']}|{r['id']}"
            )] for r in results
        ]
    )

    await msg.delete()
    await m.answer("✨ Tanlang:", reply_markup=kb)

# ---------- DOWNLOAD ----------
@dp.callback_query(F.data.startswith("dl|"))
async def download(call: types.CallbackQuery):
    _, t, source, vid = call.data.split('|')
    is_video = t == 'v'

    await call.message.edit_text("🚀 Yuklanmoqda...")

    try:
        file_path = await engine.download(vid, source, is_video)

        size = os.path.getsize(file_path) / (1024 * 1024)
        if size > 49:
            os.remove(file_path)
            return await call.message.answer("❌ Fayl juda katta (>50MB)")

        file = FSInputFile(file_path)

        if is_video:
            await call.message.answer_video(file, caption="🎬 Tayyor! (360p)")
        else:
            await call.message.answer_audio(file, caption="🎧 Tayyor MP3!")

        os.remove(file_path)
        await call.message.answer("🙏 Foydalanganingiz uchun rahmat!")

        await call.message.delete()

    except Exception as e:
        await call.message.answer("⚠️ Yuklab bo‘lmadi (block yoki xatolik)")

# ---------- MAIN ----------
async def main():
    Thread(target=run).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
