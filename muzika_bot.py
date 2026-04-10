import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import yt_dlp

# 1. BOT TOKENINGIZNI SHU YERGA QO'YING
TOKEN = '8566763003:AAHXP1TEgqchjRGB8yzghjB9z8HW58FdcpM'

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Yuklash sozlamalari
YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'outtmpl': 'music_fayl.%(ext)s',
    'default_search': 'ytsearch1', # Nomi bo'yicha qidirish uchun
    'noplaylist': True,
    'quiet': True,
}

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer(
        "👋 Salom! Men universal musiqa botiman.\n\n"
        "✅ **Link** yuborsangiz yuklab beraman.\n"
        "🔎 **Qo'shiq nomi**ni yozsangiz o'zim topaman!",
        parse_mode="Markdown"
    )

@dp.message()
async def handle_message(message: types.Message):
    query = message.text
    if query.startswith('/'): return

    wait_msg = await message.answer("Qidirilmoqda va yuklanmoqda... 🔎")
    
    try:
        # Link bo'lsa linkdan, nomi bo'lsa YouTube qidiruvidan foydalanamiz
        search_query = query if "http" in query else f"ytsearch1:{query}"
        
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(search_query, download=True)
            
            # Ma'lumotni to'g'ri olish
            video_data = info['entries'][0] if 'entries' in info else info
            filename = ydl.prepare_filename(video_data)
        
        audio_file = types.FSInputFile(filename)
        caption_text = f"✅ **{video_data.get('title')}**\n\n🌟 Botdan foydalanganingiz uchun raxmat!"
        
        await message.answer_audio(audio_file, caption=caption_text, parse_mode="Markdown")
        await wait_msg.delete()
        
        # Server joyini tejash uchun faylni o'chirish
        if os.path.exists(filename):
            os.remove(filename)
            
    except Exception as e:
        await message.answer(f"⚠️ Xatolik yuz berdi: {str(e)}")

async def main():
    print("Bot Render-da ishga tushishga tayyor!")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
