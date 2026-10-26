import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile, LabeledPrice
import yt_dlp
from pytubefix import YouTube

BOT_TOKEN = os.getenv("BOT_TOKEN")
SOCKS5_PROXY = os.getenv("SOCKS5_PROXY")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer("👋 Привет! Отправь мне ссылку на видео (YouTube, VK, Pinterest и др.).")

@dp.message(Command("buy"))
async def buy_stars(message: types.Message):
    await message.answer_invoice(
        title="Поддержка бота",
        description="Отправьте 1 звезду.",
        payload="donate_1_star",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label="Звезда", amount=1)]
    )

@dp.pre_checkout_query()
async def pre_checkout(pre_checkout_q: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_q.id, ok=True)

@dp.message(F.successful_payment)
async def successful_payment(message: types.Message):
    await message.answer("Спасибо огромное за поддержку! ⭐️❤️")

@dp.message(F.text.regexp(r'https?://[^\s]+'))
async def download_media(message: types.Message):
    url = message.text
    msg = await message.answer("⏳ Обрабатываю ссылку...")
    
    # --- ЛОГИКА ДЛЯ YOUTUBE (pytubefix) ---
    if "youtu" in url:
        try:
            await msg.edit_text("⏳ Скачиваю с YouTube...")
            
            def _download_yt():
                yt = YouTube(url)
                stream = yt.streams.get_highest_resolution()
                if not stream:
                    raise Exception("Не найден подходящий поток")
                
                os.makedirs('downloads', exist_ok=True)
                filepath = stream.download(output_path='downloads')
                return filepath

            loop = asyncio.get_event_loop()
            filepath = await loop.run_in_executor(None, _download_yt)
            
            await message.answer_video(FSInputFile(filepath))
            os.remove(filepath)
            await msg.delete()
            return
            
        except Exception as e:
            logging.error(f"pytubefix Error: {e}")
            await msg.edit_text("❌ Не удалось скачать с YouTube. Возможно, видео заблокировано или требует входа.")
            return

    # --- ЛОГИКА ДЛЯ ОСТАЛЬНЫХ САЙТОВ (yt-dlp) ---
    await msg.edit_text("⏳ Скачиваю через встроенный движок...")
    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'outtmpl': 'downloads/%(id)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
    }
    
    if SOCKS5_PROXY:
        ydl_opts['proxy'] = SOCKS5_PROXY

    try:
        os.makedirs('downloads', exist_ok=True)
        loop = asyncio.get_event_loop()
        def _download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return ydl.prepare_filename(info)
        
        filepath = await loop.run_in_executor(None, _download)
        await message.answer_video(FSInputFile(filepath))
        os.remove(filepath)
        await msg.delete()
        
    except Exception as e:
        logging.error(f"yt-dlp Error: {e}")
        await msg.edit_text(f"❌ Ошибка при скачивании. Проверьте ссылку.")

async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())