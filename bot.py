import asyncio
import os
import yt_dlp
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, FSInputFile
from aiogram.enums import ParseMode

# Токен будет браться из переменных окружения сервера (безопасно)
BOT_TOKEN = os.getenv("BOT_TOKEN")

dp = Dispatcher()

@dp.message(CommandStart())
async def start_handler(message: Message):
    await message.answer(
        f"Привет, {message.from_user.first_name}! 👋\n"
        "Я бот для скачивания видео. Просто отправь мне ссылку на видео "
        "(YouTube, VK, Pinterest и т.д.), и я попробую его скачать."
    )

@dp.message(F.text.startswith("http"))
async def download_video(message: Message):
    url = message.text.strip()
    status_msg = await message.answer("⏳ Начинаю загрузку, подожди...")
    
    # Настройки yt-dlp
    ydl_opts = {
        'format': 'best[ext=mp4]/best', # Скачиваем лучшее качество в mp4
        'outtmpl': 'downloads/%(title)s.%(ext)s', # Куда сохранять
        'max_filesize': 50 * 1024 * 1024, # Ограничение Telegram в 50 МБ
        'quiet': True,
        'no_warnings': True,
    }

    try:
        # Создаем папку для загрузок, если её нет
        if not os.path.exists('downloads'):
            os.makedirs('downloads')

        # Скачиваем видео (это блокирующая функция, запускаем в отдельном потоке)
        loop = asyncio.get_event_loop()
        
        def download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return ydl.prepare_filename(info)

        filename = await loop.run_in_executor(None, download)
        
        await status_msg.edit_text("📤 Отправляю видео в Telegram...")
        
        # Отправляем видео
        video_file = FSInputFile(filename)
        await message.answer_video(video=video_file, caption="Готово! 🎬")
        
        # Удаляем файл с сервера, чтобы не забивать память
        os.remove(filename)
        await status_msg.delete()

    except Exception as e:
        error_text = str(e)
        if "File is larger than max-filesize" in error_text or "larger than" in error_text:
            await status_msg.edit_text("❌ Видео весит больше 50 МБ. Telegram не позволяет ботам отправлять такие файлы.")
        else:
            await status_msg.edit_text(f"❌ Ошибка при скачивании:\n`{error_text[:100]}`", parse_mode=ParseMode.MARKDOWN)

async def main():
    print("Бот запущен...")
    bot = Bot(token=BOT_TOKEN)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())