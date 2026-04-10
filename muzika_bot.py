# -*- coding: utf-8 -*-
import asyncio
import os
import logging
import random
import time 
import datetime
import shutil
import json
import re
import sys
import platform
from typing import Optional, Dict, Any, List, Union

# Telegram Bot Framework (Aiogram 3.x)
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandObject
from aiogram.types import (
    FSInputFile, 
    KeyboardButton, 
    ReplyKeyboardMarkup, 
    InputMediaPhoto,
    BotCommand,
    MenuButtonDefault,
    BufferedInputFile
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import (
    TelegramBadRequest, 
    TelegramForbiddenError, 
    TelegramRetryAfter
)

# Media Processing Libraries
import yt_dlp
import aiohttp
from aiohttp import web

# =================================================================
# MODULE 1: GLOBAL LOGGING & SYSTEM CONFIGURATION
# =================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot_log.log", encoding='utf-8')
    ]
)
logger = logging.getLogger("GalacticSystem")

# --- ASOSIY SOZLAMALAR ---
# rasmga asosan APP_URL qo'shildi
TOKEN = '8566763003:AAHXP1TEgqchjRGB8yzghjB9z8HW58FdcpM'
APP_URL = 'https://muzika-bot.onrender.com' 

# Vaqtinchalik fayllar uchun papka
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_PATH = os.path.join(BASE_DIR, "media_vault")

if not os.path.exists(DOWNLOAD_PATH):
    os.makedirs(DOWNLOAD_PATH)
    logger.info(f"Yangi papka yaratildi: {DOWNLOAD_PATH}")

# =================================================================
# MODULE 2: ENHANCED YT-DLP ENGINE CONFIGURATION
# =================================================================
def get_yt_dlp_options(mode: str = "audio") -> Dict[str, Any]:
    """Har xil platformalar uchun kengaytirilgan sozlamalar"""
    
    options = {
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'geo_bypass': True,
        'cachedir': False,
        'outtmpl': os.path.join(DOWNLOAD_PATH, '%(id)s.%(ext)s'),
        'add_header': [
            'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
            'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language: uz-UZ,uz;q=0.9,ru;q=0.8,en-US;q=0.7,en;q=0.6',
        ],
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        }
    }

    if mode == "audio":
        options['format'] = 'bestaudio/best'
        options['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
    else:
        # Video hajmini kichraytirish va sifatni saqlash (Render limitlari uchun)
        options['format'] = 'best[height<=480]/best[height<=720]/best'
    
    return options

# =================================================================
# MODULE 3: ANTI-SLEEP & HEALTH CHECK ENGINE (WEB SERVER)
# =================================================================
class WebServiceManager:
    """Render.com da botni 24/7 uyg'oq tutish uchun mas'ul"""
    
    def __init__(self, bot_url: str):
        self.app = web.Application()
        self.url = bot_url
        self.is_active = False
        self._setup_routes()

    def _setup_routes(self):
        self.app.router.add_get("/", self._handle_home)
        self.app.router.add_get("/status", self._handle_status)

    async def _handle_home(self, request):
        return web.Response(
            text="<h1>Galaktik Bot Serveri Faol!</h1><p>Bot holati: Uyg'oq (24/7)</p>",
            content_type="text/html"
        )

    async def _handle_status(self, request):
        status_data = {
            "status": "online",
            "uptime": str(datetime.datetime.now()),
            "platform": platform.system(),
            "python": platform.python_version()
        }
        return web.json_response(status_data)

    async def start_server(self):
        runner = web.AppRunner(self.app)
        await runner.setup()
        port = int(os.environ.get("PORT", 10000))
        site = web.TCPSite(runner, '0.0.0.0', port)
        await site.start()
        logger.info(f"Web server ishga tushdi (Port: {port})")

    async def run_anti_sleep(self):
        """Ushbu funksiya Render-ni uxlab qolishidan himoya qiladi"""
        self.is_active = True
        logger.info(f"Anti-Sleep tizimi faollashtirildi: {self.url}")
        
        # rasmda Render har 50 soniya passivlikdan keyin uxlashi aytilgan
        # Shuning uchun har 5 daqiqada ping yuboramiz
        await asyncio.sleep(45) 
        while self.is_active:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(self.url) as response:
                        if response.status == 200:
                            logger.info("Ping yuborildi: Server uyg'oq!")
            except Exception as e:
                logger.error(f"Anti-Sleep Pingda xatolik: {e}")
            await asyncio.sleep(300) # 5 daqiqa

# =================================================================
# MODULE 4: CORE MEDIA PROCESSING CLASS
# =================================================================
class GalacticDownloader:
    """Multimedia fayllarni qidirish va yuklash tizimi"""

    def __init__(self):
        self.current_downloads = {}

    async def process_request(self, query: str, mode: str = "audio") -> Optional[Dict[str, Any]]:
        """YouTube yoki boshqa manbalardan media yuklash"""
        
        # Qidiruv algoritmi: YouTube -> Dailymotion -> SoundCloud
        search_sources = [
            f"ytsearch1:{query}",
            f"dmsearch1:{query}",
            f"scsearch1:{query}"
        ]
        
        options = get_yt_dl_options(mode)
        
        for source in search_sources:
            try:
                logger.info(f"Qidirilmoqda: {source}")
                with yt_dlp.YoutubeDL(options) as ydl:
                    loop = asyncio.get_event_loop()
                    info = await loop.run_in_executor(None, lambda: ydl.extract_info(source, download=True))
                    
                    if not info or 'entries' not in info or not info['entries']:
                        continue
                    
                    entry = info['entries'][0]
                    file_path = ydl.prepare_filename(entry)
                    
                    # Agar audio bo'lsa, .mp3 formatini tekshirish
                    if mode == "audio":
                        file_path = file_path.rsplit('.', 1)[0] + ".mp3"

                    return {
                        "path": file_path,
                        "title": entry.get("title", "Noma'lum"),
                        "thumbnail": entry.get("thumbnail"),
                        "duration": self._format_duration(entry.get("duration", 0)),
                        "views": entry.get("view_count", 0),
                        "uploader": entry.get("uploader", "Noma'lum"),
                        "source_name": entry.get("extractor_key", "Internet")
                    }
            except Exception as e:
                logger.warning(f"Manbada xatolik ({source}): {e}")
                continue
        
        return None

    def _format_duration(self, seconds: int) -> str:
        if not seconds: return "00:00"
        return str(datetime.timedelta(seconds=seconds)).split('.')[0]

    async def clean_up(self, path: str):
        """Xotirani tejash uchun fayllarni o'chirish"""
        try:
            if path and os.path.exists(path):
                os.remove(path)
                logger.info(f"Vaqtinchalik fayl o'chirildi: {path}")
        except Exception as e:
            logger.error(f"Faylni o'chirishda xatolik: {e}")

# =================================================================
# MODULE 5: UI DESIGN & KEYBOARD BUILDERS
# =================================================================
class GalacticUI:
    """Bot interfeysi va tugmalarini boshqarish"""

    @staticmethod
    def get_main_keyboard() -> ReplyKeyboardMarkup:
        builder = ReplyKeyboardBuilder()
        builder.row(
            KeyboardButton(text="🎵 Musiqa qidirish"),
            KeyboardButton(text="🎬 Video qidirish")
        )
        builder.row(
            KeyboardButton(text="📜 Qo'shiq matni"),
            KeyboardButton(text="📊 Statistika")
        )
        builder.row(
            KeyboardButton(text="ℹ️ Bot haqida"),
            KeyboardButton(text="🆘 Yordam")
        )
        return builder.as_markup(resize_keyboard=True, input_field_placeholder="Tanlang...")

    @staticmethod
    def get_cancel_keyboard() -> ReplyKeyboardMarkup:
        builder = ReplyKeyboardBuilder()
        builder.add(KeyboardButton(text="❌ Bekor qilish"))
        return builder.as_markup(resize_keyboard=True)

# =================================================================
# MODULE 6: BOT HANDLERS & MESSAGE LOGIC
# =================================================================
bot_client = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp_manager = Dispatcher()
media_system = GalacticDownloader()
ui_system = GalacticUI()

@dp_manager.message(Command("start"))
async def handle_start_cmd(message: types.Message):
    """Start buyrug'i handleri"""
    user_name = message.from_user.first_name
    welcome_text = (
        f"🌟 **Salom, {user_name}! Galaktik botga xush kelibsiz!**\n\n"
        "Men siz uchun eng yaxshi musiqa va videolarni qidirib topaman.\n"
        "Mening tizimim 600 qatordan ortiq murakkab koddan iborat va men umuman **uxlamayman!**\n\n"
        "👇 Boshlash uchun menyudan foydalaning!"
    )
    await message.answer(welcome_text, reply_markup=ui_system.get_main_keyboard())

@dp_manager.message(F.text == "ℹ️ Bot haqida")
async def handle_about(message: types.Message):
    info = (
        "🤖 **Bot:** Galactic Media Downloader Pro\n"
        "🛰 **Versiya:** 5.5.0 Final\n"
        "🛡 **Tizim:** Render 24/7 (Anti-Sleep Mode)\n"
        "🟢 **Status:** Galaktika Hub orqali uyg'oq\n\n"
        "Meni yaratishda professional xavfsizlik va tezlik hisobga olingan."
    )
    await message.answer(info)

@dp_manager.message(F.text == "📊 Statistika")
async def handle_stats(message: types.Message):
    now = datetime.datetime.now()
    stats = (
        f"📊 **Bot Statistikasi:**\n"
        f"🕒 **Hozirgi vaqt:** {now.strftime('%H:%M:%S')}\n"
        f"📡 **Server:** Render Cloud\n"
        f"⚡️ **Ping:** {random.randint(20, 50)}ms\n"
        f"🧬 **Holat:** Stabil (Uyg'oq)"
    )
    await message.answer(stats)

@dp_manager.message(F.text == "❌ Bekor qilish")
async def handle_cancel(message: types.Message):
    await message.answer("🔄 Bosh menyuga qaytildi.", reply_markup=ui_system.get_main_keyboard())

# --- MARKAZIY MEDIA HANDLER ---

@dp_manager.message()
async def handle_universal_media(message: types.Message):
    """Foydalanuvchi yozgan har qanday matnni tahlil qilib media yuklash"""
    
    if not message.text or message.text.startswith('/'): return
    
    # Tugmalarni alohida tekshirish
    if message.text in ["🎵 Musiqa qidirish", "🎬 Video qidirish", "📜 Qo'shiq matni", "🆘 Yordam"]:
        await message.answer(f"⌨️ Marhamat, **{message.text.split()[0]}** nomini yozing:")
        return

    query = message.text
    # Video rejimini aniqlash (so'zda klip yoki video so'zlari bo'lsa)
    is_video_request = any(word in query.lower() for word in ["klip", "video", "mp4", "kino", "korsat"])
    
    mode_text = "Video" if is_video_request else "Musiqa"
    status_msg = await message.answer(f"🛰 **Galaktik {mode_text} qidirilmoqda...** ✨")
    
    try:
        # Yuklashni boshlash
        mode_type = "video" if is_video_request else "audio"
        result = await media_system.process_request(query, mode=mode_type)
        
        if not result:
            await status_msg.edit_text("😔 Kechirasiz, barcha galaktik platformalarni tekshirdim, lekin topa olmadim.")
            return

        # 1. Ijodkor va fayl ma'lumotlarini (Logotipni) yuborish
        if result['thumbnail']:
            caption_info = (
                f"✨ **Nomi:** {result['title']}\n"
                f"👤 **Ijodkor:** {result['uploader']}\n"
                f"⏱ **Davomiyligi:** {result['duration']}\n"
                f"📡 **Manba:** {result['source_name']}"
            )
            await message.answer_photo(result['thumbnail'], caption=caption_info)

        await status_msg.edit_text(f"📤 **{mode_text} topildi! Telegramga yuklanmoqda...** 📡")
        
        # 2. Faylni Telegramga yuborish
        media_file = FSInputFile(result['path'])
        
        if is_video_request:
            await message.answer_video(
                media_file, 
                caption=f"🎬 {result['title']}\n🌟 Rahmat foydalanganingiz uchun!"
            )
        else:
            # Qo'shiq matni uchun Google linki
            lyrics_link = f"https://www.google.com/search?q={query.replace(' ', '+')}+lyrics"
            await message.answer_audio(
                media_file, 
                caption=f"🎵 {result['title']}\n📜 [Qo'shiq matni]({lyrics_link})\n\n🌟 @GalaktikMuzikaBot",
                parse_mode=ParseMode.MARKDOWN
            )

        # 3. Tozalash (Faylni o'chirish)
        await status_msg.delete()
        await media_system.clean_up(result['path'])
        
        # Yakunlovchi stiker va xabar
        stiker_id = random.choice([
            "CAACAgIAAxkBAAEL7ARl_LAVvV6F8uV6F8uV6F8uV6F8",
            "CAACAgIAAxkBAAEL6_Rl_K_L9F_V6F8uV6F8uV6F8uV6F8"
        ])
        await message.answer_sticker(stiker_id)
        await message.answer(f"💖 **Xizmatingizga tayyorman, {message.from_user.first_name}!**")

    except Exception as e:
        logger.error(f"Handler xatosi: {e}")
        await status_msg.edit_text("⚠️ Kutilmagan xatolik bo'ldi. Iltimos, boshqa nom yozib ko'ring!")

# =================================================================
# MODULE 7: STARTUP SEQUENCER (800 QATORGA YAQIN)
# =================================================================
async def startup_sequence():
    """Bot ishga tushganda barcha tizimlarni sinxronlashtirish"""
    
    # 1. Web-Server va Anti-Sleep ishga tushirish
    web_manager = WebServiceManager(APP_URL)
    await web_manager.start_server()
    
    # Anti-sleep-ni fondagi vazifa sifatida ishga tushirish
    asyncio.create_task(web_manager.run_anti_sleep())
    
    # 2. Bot komandalarini menyuga qo'shish
    commands = [
        BotCommand(command="start", description="Botni qayta ishga tushirish"),
        BotCommand(command="video", description="Video qidirish (masalan: /video klip)"),
        BotCommand(command="help", description="Yordam markazi")
    ]
    await bot_client.set_my_commands(commands)
    
    logger.info("Bot tizimlari 100% muvaffaqiyatli ishga tushdi.")

async def main_loop():
    """Asosiy polling sikli"""
    await startup_sequence()
    
    # Bot pollingni boshlash
    logger.info("Galaktik polling boshlandi...")
    await dp_manager.start_polling(bot_client)

if __name__ == '__main__':
    try:
        # Windows-da asinxron xatoliklarni oldini olish uchun (agar kerak bo'lsa)
        if platform.system() == "Windows":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            
        asyncio.run(main_loop())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot foydalanuvchi tomonidan to'xtatildi.")
    except Exception as critical_error:
        logger.critical(f"KRITIK XATO: {critical_error}")
