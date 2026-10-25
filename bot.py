import asyncio
import os
import yt_dlp
import glob
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, FSInputFile
from aiogram.enums import ParseMode

# Токен берется из секретов GitHub Actions
BOT_TOKEN = os.getenv("BOT_TOKEN")

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
        # Пытаемся скачать в mp4, чтобы Telegram точно его принял
        'format': 'best[ext=mp4]/best', 
        # Сохраняем файл под именем его ID (чтобы избежать проблем с русскими буквами и спецсимволами)
        'outtmpl': 'downloads/%(id)s.%(ext)s', 
        'max_filesize': 50 * 1024 * 1024, # Лимит 50 МБ
        'quiet': True,
        'no_warnings': True,
    }

    try:
        # Создаем папку для загрузок
        if not os.path.exists('downloads'):
            os.makedirs('downloads')

        # Скачиваем видео в отдельном потоке, чтобы не блокировать бота
        loop = asyncio.get_event_loop()
        
        def download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return info['id']

        video_id = await loop.run_in_executor(None, download)
        
        # Ищем скачанный файл по его ID (yt-dlp мог изменить расширение на .webm или .mkv)
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
        
        # Отправляем видео
        video_file = FSInputFile(filepath)
        await message.answer_video(video=video_file, caption="Готово! 🎬")
        
        # Удаляем файл с сервера, чтобы не забивать память
        os.remove(filepath)
        await status_msg.delete()

    except Exception as e:
        error_text = str(e)
        if "File is larger than max-filesize" in error_text or "larger than" in error_text:
            await status_msg.edit_text("❌ Видео слишком большое (больше 50 МБ).")
        else:
            # Выводим только первые 100 символов ошибки, чтобы сообщение в ТГ не было огромным
            await status_msg.edit_text(f"❌ Ошибка при скачивании:\n`{error_text[:100]}`", parse_mode=ParseMode.MARKDOWN)

async def main():
    print("Бот запущен...")
    bot = Bot(token=BOT_TOKEN)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())