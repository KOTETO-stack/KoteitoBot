import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile, LabeledPrice
import yt_dlp

BOT_TOKEN = os.getenv("BOT_TOKEN")
SOCKS5_PROXY = os.getenv("SOCKS5_PROXY")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer(
        "👋 Привет! Я бот для скачивания видео.\n\n"
        "Просто отправь мне ссылку на видео из YouTube, VK, Pinterest и других сервисов.\n\n"
        "⭐ Поддержать проект звездами: /buy"
    )

@dp.message(Command("buy"))
async def buy_stars(message: types.Message):
    await message.answer_invoice(
        title="Поддержка бота",
        description="Отправьте 1 звезду для поддержки разработчика.",
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
    msg = await message.answer("⏳ Начинаю скачивание, подождите...")
    
    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'outtmpl': 'downloads/%(id)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        # Маскировка под ТВ и мобильные устройства + принудительный вызов PO Token
        'extractor_args': {
            'youtube': {
                'player_client': ['tv', 'mweb', 'web_safari'],
                'player_skip': ['configs'],
            }
        },
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
        logging.error(f"Ошибка скачивания: {e}")
        await msg.edit_text("❌ Ошибка при скачивании. Проверьте ссылку или попробуйте позже.")

async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())