import asyncio
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
import yt_dlp
from aiohttp import web

# --- KONFIGURATSIYA ---
TOKEN = '8566763003:AAHXP1TEgqchjRGB8yzghjB9z8HW58FdcpM'

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Render uchun Health Check veb-serveri
async def handle(request):
    return web.Response(text="Bot is running!")

app = web.Application()
app.router.add_get("/", handle)

# Audio qidiruv sozlamalari (SoundCloud)
AUDIO_OPTIONS = {
    'format': 'bestaudio/best',
    'outtmpl': 'audio_%(title)s.%(ext)s',
    'default_search': 'scsearch1',
    'noplaylist': True,
    'quiet': True,
    'add_header': [
        'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    ]
}

# Video qidiruv sozlamalari (YouTube 360p)
VIDEO_OPTIONS = {
    'format': 'best[height<=360]/bestvideo[height<=360]+bestaudio/best',
    'outtmpl': 'video_%(title)s.%(ext)s',
    'default_search': 'ytsearch1',
    'noplaylist': True,
    'quiet': True,
    'merge_output_format': 'mp4',
    'add_header': [
        'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    ]
}

# --- BUYRUQLAR ---

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer(
        "👋 **Assalomu alaykum! Botimizga xush kelibsiz!**\n\n"
        "Men sizga eng yaxshi musiqalar va videolarni topib beraman. ✨\n\n"
        "🔹 **Imkoniyatlarim:**\n"
        "🎵 **Musiqa:** Qo'shiqchi yoki qo'shiq nomini yozing.\n"
        "🎬 **Video (360p):** `/video qo'shiq nomi` deb yozing.\n"
        "📜 Qo'shiq matni va manbasini ham ulashaman!\n\n"
        "🎹 Qani, boshladik! Nima qidiramiz? 😊"
    )

# Video handler (/video buyrug'i uchun)
@dp.message(Command("video"))
async def video_handler(message: types.Message):
    query = message.text.replace('/video', '').strip()
    if not query:
        await message.answer("🎬 **Iltimos, video nomini yozing!**\n\nMisol: `/video Janob Rasul` 📽")
        return

    status_msg = await message.answer("🔍 **Siz uchun videoni qidiryapman...** ✨")
    
    try:
        with yt_dlp.YoutubeDL(VIDEO_OPTIONS) as ydl:
            await status_msg.edit_text("⏳ **Video yuklanyapti...** (Sifati: 360p) 📽")
            info = ydl.extract_info(f"ytsearch1:{query}", download=True)
            video_data = info['entries'][0] if 'entries' in info else info
            filename = ydl.prepare_filename(video_data)

        await status_msg.edit_text("📤 **Video tayyor! Yuboryapman...** 🚀")
        
        video_file = types.FSInputFile(filename)
        await message.answer_video(
            video_file, 
            caption=f"🎬 **Nomi:** {video_data.get('title')}\n📺 **Sifati:** 360p\n\n🌟 Botimizdan foydalanganingiz uchun rahmat! 😊"
        )
        await status_msg.delete()
        if os.path.exists(filename): os.remove(filename)
        
        # Yakuniy tabrik
        await message.answer("🍿 Videoni maza qilib tomosha qiling! ✨")
            
    except Exception as e:
        await status_msg.edit_text(
            "😔 **Uzur so'rayman, videoni topa olmadim.**\n\n"
            "Meni kamchiliklarim uchun uzr so'rayman. ✨\n"
            "🤔 **Boshqa yordam kerakmi?**"
        )

# Audio handler (Oddiy xabarlar uchun)
@dp.message()
async def audio_handler(message: types.Message):
    query = message.text
    if query.startswith('/') or not query: return
    
    status_msg = await message.answer("🔍 **Musiqa qidirilmoqda...** ✨")
    
    try:
        with yt_dlp.YoutubeDL(AUDIO_OPTIONS) as ydl:
            await status_msg.edit_text("⏳ **Musiqa yuklanyapti...** 🎧")
            info = ydl.extract_info(f"scsearch1:{query}", download=True)
            video_data = info['entries'][0] if 'entries' in info else info
            filename = ydl.prepare_filename(video_data)
            
            artist = video_data.get('uploader', 'Noma\'lum ijrochi')
            title = video_data.get('title', 'Noma\'lum')
            link = video_data.get('webpage_url', '#')
            lyrics_url = f"https://www.google.com/search?q={query.replace(' ', '+')}+lyrics"

        await status_msg.edit_text("📤 **Musiqa yuborilmoqda...** 🚀")
        
        audio_file = types.FSInputFile(filename)
        await message.answer_audio(
            audio_file, 
            caption=(
                f"👤 **Ijrochi:** {artist}\n"
                f"🎵 **Nomi:** {title}\n\n"
                f"🔗 **Manba:** [Havola]({link})\n"
                f"📜 **Matni:** [Qo'shiq matni]({lyrics_url})\n\n"
                f"🌟 **Botimizdan foydalanganingiz uchun rahmat!** 😊"
            ),
            parse_mode="Markdown"
        )
        await status_msg.delete()
        if os.path.exists(filename): os.remove(filename)
        
        # Yakuniy tabrik
        await message.answer("💖 Musiqa yoqdimi? Yana biron nima qidiramizmi? ✨")
            
    except Exception as e:
        await status_msg.edit_text(
            "😔 **Uzur so'rayman, qo'shiqni topa olmadim.**\n\n"
            "Meni kamchiliklarim uchun uzr so'rayman. 🛠\n"
            "🤔 **Boshqa yordam kerakmi?** ✨"
        )

# --- ISHGA TUSHIRISH ---
async def main():
    # Render uchun veb-serverni fonda ishga tushirish
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    # Botni ishga tushirish
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
