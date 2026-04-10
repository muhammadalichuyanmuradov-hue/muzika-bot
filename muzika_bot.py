import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import yt_dlp

TOKEN = '8566763003:AAHXP1TEgqchjRGB8yzghjB9z8HW58FdcpM'

bot = Bot(token=TOKEN)
dp = Dispatcher()

# SOZLAMALAR: Endi YouTube o'rniga SoundCloud-dan qidiradi
YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'outtmpl': 'music_fayl.%(ext)s',
    'default_search': 'scsearch1',  # SoundCloud qidiruvi (Blok yo'q!)
    'noplaylist': True,
    'quiet': True,
}

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer("✅ Bot yangilandi! Endi bloklarsiz ishlaydi.\n\nQo'shiq nomini yozing:")

@dp.message()
async def handle_message(message: types.Message):
    query = message.text
    if query.startswith('/'): return
    
    wait_msg = await message.answer("Qidirilmoqda... 🔎")
    
    try:
        # Agar link bo'lsa o'zi, bo'lmasa SoundCloud-dan qidiradi
        search_query = query if "http" in query else f"scsearch1:{query}"
        
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(search_query, download=True)
            video_data = info['entries'][0] if 'entries' in info else info
            filename = ydl.prepare_filename(video_data)
        
        audio_file = types.FSInputFile(filename)
        await message.answer_audio(audio_file, caption=f"🎵 {video_data.get('title')}")
        await wait_msg.delete()
        
        if os.path.exists(filename):
            os.remove(filename)
            
    except Exception as e:
        await message.answer(f"⚠️ Xatolik: SoundCloud-dan ham topilmadi.")
        await wait_msg.delete()

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
