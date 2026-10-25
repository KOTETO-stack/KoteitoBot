import asyncio
import os
import yt_dlp
import glob
import base64
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, FSInputFile
from aiogram.enums import ParseMode

# Получаем токен и куки из секретов GitHub
BOT_TOKEN = os.getenv("BOT_TOKEN")
YOUTUBE_COOKIES_B64 = os.getenv("YOUTUBE_COOKIES")

# Если куки переданы (в формате Base64), создаем файл cookies.txt
if YOUTUBE_COOKIES_B64:
    try:
        cookie_data = base64.b64decode(YOUTUBE_COOKIES_B64).decode('utf-8')
        with open('cookies.txt', 'w', encoding='utf-8') as f:
            f.write(cookie_data)
        print("Cookies для YouTube успешно загружены.")
    except Exception as e:
        print(f"Ошибка при загрузке cookies: {e}")

dp = Dispatcher()

@dp.message(CommandStart())
async def start_handler(message: Message):
    await message.answer(
        f"Привет, {message.from_user.first_name}! 👋\n"
        "Я бот для скачивания видео. Просто отправь мне ссылку "
        "(YouTube, VK, Pinterest и т.д.), и я скачаю видео (до 50 МБ)."
    )

@dp.message(F.text.startswith("http"))
async def download_video(message: Message):
    url = message.text.strip()
    status_msg = await message.answer("⏳ Начинаю загрузку, подожди...")
    
    # Настройки yt-dlp
    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'outtmpl': 'downloads/%(id)s.%(ext)s', 
        'max_filesize': 50 * 1024 * 1024, 
        'quiet': True,
        'no_warnings': True,
        # Хитрость для обхода блокировки YouTube на серверах
        'extractor_args': {'youtube': {'player_client': ['tv', 'mweb', 'android', 'ios']}},
    }

    # Если файл cookies.txt существует, используем его
    if os.path.exists('cookies.txt'):
        ydl_opts['cookiefile'] = 'cookies.txt'

    try:
        if not os.path.exists('downloads'):
            os.makedirs('downloads')

        loop = asyncio.get_event_loop()
        
        def download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return info['id']

        video_id = await loop.run_in_executor(None, download)
        
        # Ищем скачанный файл по ID
        downloaded_files = glob.glob(f'downloads/{video_id}.*')
        
        if not downloaded_files:
            await status_msg.edit_text("❌ Ошибка: файл не был найден после скачивания.")
            return
            
        filepath = downloaded_files[0]
        
        # Проверяем размер файла
        file_size = os.path.getsize(filepath)
        if file_size > 50 * 1024 * 1024:
            os.remove(filepath)
            await status_msg.edit_text("❌ Видео весит больше 50 МБ. Telegram не пропустит его.")
            return

        await status_msg.edit_text("📤 Отправляю видео в Telegram...")
        
        video_file = FSInputFile(filepath)
        await message.answer_video(video=video_file, caption="Готово! 🎬")
        
        os.remove(filepath)
        await status_msg.delete()

    except Exception as e:
        error_text = str(e)
        if "File is larger than max-filesize" in error_text or "larger than" in error_text:
            await status_msg.edit_text("❌ Видео слишком большое (больше 50 МБ).")
        elif "Sign in to confirm you’re not a bot" in error_text:
            await status_msg.edit_text("❌ YouTube заблокировал запрос. Нужны Cookies (инструкция в чате).")
        else:
            await status_msg.edit_text(f"❌ Ошибка при скачивании:\n`{error_text[:100]}`", parse_mode=ParseMode.MARKDOWN)

async def main():
    print("Бот запущен...")
    bot = Bot(token=BOT_TOKEN)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())