import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile, LabeledPrice
import yt_dlp

# Берем токен из секретов GitHub
BOT_TOKEN = os.getenv("BOT_TOKEN")
# Берем прокси (если найден в workflow)
SOCKS5_PROXY = os.getenv("SOCKS5_PROXY")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer(
        "👋 Привет! Я бот для скачивания видео.\n\n"
        "Просто отправь мне ссылку на видео из YouTube, VK, Pinterest, Яндекс Музыки и других сервисов.\n\n"
        "⭐ Поддержать проект звездами: /buy"
    )

# --- БЛОК ОПЛАТЫ ЗВЕЗДАМИ (TELEGRAM STARS) ---
@dp.message(Command("buy"))
async def buy_stars(message: types.Message):
    await message.answer_invoice(
        title="Поддержка бота",
        description="Отправьте 1 звезду для поддержки разработчика.",
        payload="donate_1_star",
        provider_token="",  # Для звезд оставляем пустым
        currency="XTR",     # Код валюты Telegram Stars
        prices=[LabeledPrice(label="Звезда", amount=1)]
    )

@dp.pre_checkout_query()
async def pre_checkout(pre_checkout_q: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_q.id, ok=True)

@dp.message(F.successful_payment)
async def successful_payment(message: types.Message):
    await message.answer("Спасибо огромное за поддержку! ⭐️❤️")
# ---------------------------------------------

@dp.message(F.text.regexp(r'https?://[^\s]+'))
async def download_media(message: types.Message):
    url = message.text
    msg = await message.answer("⏳ Начинаю скачивание, подождите...")
    
    # Настройки скачивания
    ydl_opts = {
        'format': 'best[ext=mp4]/best', # Качаем лучшее видео в mp4
        'outtmpl': 'downloads/%(id)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
    }
    
    # Если workflow нашел прокси - используем его
    if SOCKS5_PROXY:
        ydl_opts['proxy'] = SOCKS5_PROXY

    try:
        os.makedirs('downloads', exist_ok=True)
        
        # Запускаем скачивание в отдельном потоке, чтобы бот не зависал
        loop = asyncio.get_event_loop()
        def _download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return ydl.prepare_filename(info)
        
        filepath = await loop.run_in_executor(None, _download)
        
        # Отправляем видео
        await message.answer_video(FSInputFile(filepath))
        
        # Удаляем файл, чтобы не забивать память
        os.remove(filepath)
        await msg.delete()
        
    except Exception as e:
        await msg.edit_text(f"❌ Ошибка при скачивании: возможно, ссылка неверна или сервис заблокирован.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())