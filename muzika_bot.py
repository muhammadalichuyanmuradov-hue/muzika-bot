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
            [KeyboardButton(text="🎬 Video topish")]
        ],
        resize_keyboard=True
    )

# ---------- ENGINE ----------
class Engine:
    def __init__(self):
        self.path = "downloads"
        if not os.path.exists(self.path):
            os.makedirs(self.path)

    async def search(self, query):
        ydl_opts = {'quiet': True, 'extract_flat': True}
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                data = await asyncio.to_thread(
                    ydl.extract_info,
                    f"ytsearch10:{query}",
                    download=False
                )
                return [
                    {'id': v['id'], 'title': v['title'][:40]}
                    for v in data['entries']
                ]
        except:
            return []

    async def download(self, url, is_video):
        filename = f"{self.path}/{int(time.time())}.{'mp4' if is_video else 'mp3'}"

        if is_video:
            opts = {
                'format': 'bestvideo[height<=360]+bestaudio/best',
                'merge_output_format': 'mp4',
                'outtmpl': filename,
                'noplaylist': True
            }
        else:
            opts = {
                'format': 'bestaudio/best',
                'outtmpl': filename,
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'noplaylist': True
            }

        with yt_dlp.YoutubeDL(opts) as ydl:
            await asyncio.to_thread(ydl.download, [url])

        return filename

engine = Engine()

# ---------- START ----------
@dp.message(Command("start"))
async def start(m: types.Message, state: FSMContext):
    await state.clear()
    await m.answer(
        f"👋 Salom {m.from_user.first_name}!\n\n"
        "🎧 Musiqa yoki 🎬 video yuklab beraman\n"
        "👇 Quyidagidan tanlang:",
        reply_markup=menu()
    )

# ---------- MODE ----------
@dp.message(F.text == "🎵 Musiqa topish")
async def music(m: types.Message, state: FSMContext):
    await state.set_state(SearchState.music)
    await m.answer("🎵 Musiqa nomini yozing:")

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
                callback_data=f"dl|{'v' if is_video else 'm'}|{r['id']}"
            )] for r in results
        ]
    )

    await msg.delete()
    await m.answer("✨ Tanlang:", reply_markup=kb)

# ---------- DOWNLOAD ----------
@dp.callback_query(F.data.startswith("dl|"))
async def download(call: types.CallbackQuery):
    _, t, vid = call.data.split('|')
    is_video = t == 'v'
    url = f"https://www.youtube.com/watch?v={vid}"

    await call.message.edit_text("🚀 Yuklanmoqda...")

    try:
        file_path = await engine.download(url, is_video)

        # size check
        size = os.path.getsize(file_path) / (1024 * 1024)
        if size > 49:
            os.remove(file_path)
            return await call.message.answer("❌ Fayl 50MB dan katta")

        file = FSInputFile(file_path)

        if is_video:
            await call.message.answer_video(
                file,
                caption="🎬 Tayyor! 360p sifat"
            )
        else:
            await call.message.answer_audio(
                file,
                caption="🎧 MP3 tayyor!"
            )

        os.remove(file_path)
        await call.message.delete()

    except Exception as e:
        await call.message.answer("⚠️ Xatolik yuz berdi")

# ---------- EFFECT (typing) ----------
async def typing_effect(chat_id):
    await bot.send_chat_action(chat_id, "typing")

# ---------- MAIN ----------
async def main():
    Thread(target=run).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
