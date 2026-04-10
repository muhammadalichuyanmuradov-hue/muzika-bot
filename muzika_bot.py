import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import yt_dlp
from aiohttp import web

TOKEN = '8566763003:AAHXP1TEgqchjRGB8yzghjB9z8HW58FdcpM'

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Render uchun Health Check
async def handle(request):
    return web.Response(text="Bot is running!")

app = web.Application()
app.router.add_get("/", handle)

# Qidiruv sozlamalari
YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'outtmpl': 'music_fayl.%(ext)s',
    'default_search': 'scsearch1', # SoundCloud qidiruvi
    'noplaylist': True,
    'quiet': True,
}

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer(
        "👋 **Assalomu alaykum, aziz foydalanuvchi!**\n\n"
        "✨ Men sizning shaxsiy musiqa yordamchingizman! ✨\n\n"
        "🔹 **Imkoniyatlarim:**\n"
        "🎵 Musiqalarni nomi bo'yicha topaman\n"
        "🔗 YouTube linki orqali yuklab beraman\n"
        "🎬 Videolardagi qo'shiqlarni audio qilib beraman\n"
        "📜 Qo'shiq matnini (link ko'rinishida) topaman\n\n"
        "🎹 Menga qo'shiqchi yoki qo'shiq nomini yozing, men darhol qidirishni boshlayman! 🚀"
    )

@dp.message()
async def handle_message(message: types.Message):
    query = message.text
    if query.startswith('/'): return
    
    status_msg = await message.answer("🔍 **Siz uchun eng yaxshisini qidiryapman...** ✨")
    
    try:
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            await status_msg.edit_text("⏳ **Musiqa yuklanyapti, ozgina sabr qiling...** 🎧")
            info = ydl.extract_info(f"scsearch1:{query}", download=True)
            video_data = info['entries'][0] if 'entries' in info else info
            filename = ydl.prepare_filename(video_data)
            
            # Qo'shimcha ma'lumotlar
            title = video_data.get('title', 'Noma\'lum')
            link = video_data.get('webpage_url', 'Topilmadi')
            # Musiqa matni uchun Google qidiruv havolasi (avtomatik yaratish)
            lyrics_url = f"https://www.google.com/search?q={query.replace(' ', '+')}+lyrics"

        await status_msg.edit_text("📤 **Tayyor! Telegramga yuboryapman...** 🚀")
        
        audio_file = types.FSInputFile(filename)
        await message.answer_audio(
            audio_file, 
            caption=(
                f"🎵 **Nomi:** {title}\n\n"
                f"🔗 **Manba (link):** [Havola]({link})\n"
                f"📜 **Matni:** [Qo'shiq matnini o'qish]({lyrics_url})\n\n"
                f"🌟 **Botimizdan foydalanganingiz uchun rahmat!** 😊"
            ),
            parse_mode="Markdown"
        )
        await status_msg.delete()
        
        if os.path.exists(filename):
            os.remove(filename)
            
    except Exception as e:
        await status_msg.edit_text(
            "😔 **Uzur so'rayman, qo'shiqni topa olmadim...**\n\n"
            "Meni kamchiliklarim uchun uzr so'rayman, bazamda hali hamma narsa yo'q ekan. 🛠\n\n"
            "🤔 **Boshqa yordam kerakmi?** Yoki boshqa qo'shiq nomini yozib ko'rasizmi? ✨"
        )

async def main():
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.environ.get("PORT", 10000)))
    await site.start()
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
