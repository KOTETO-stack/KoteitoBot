import os
import logging
import asyncio
import aiohttp
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
    
    if "youtu" in url:
        try:
            await msg.edit_text("⏳ Скачиваю через Cobalt...")
            api_url = "https://api.cobalt.tools/api/json"
            headers = {"Accept": "application/json", "Content-Type": "application/json"}
            payload = {"url": url, "vQuality": "720"}
            
            async with aiohttp.ClientSession() as session:
                async with session.post(api_url, json=payload, headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        video_url = data.get("url")
                        if not video_url:
                            raise Exception("Cobalt не вернул ссылку.")
                        
                        filepath = f"downloads/{message.message_id}.mp4"
                        os.makedirs('downloads', exist_ok=True)
                        
                        async with session.get(video_url) as video_resp:
                            if video_resp.status == 200:
                                with open(filepath, 'wb') as f:
                                    async for chunk in video_resp.content.iter_chunked(1024*1024):
                                        f.write(chunk)
                            else:
                                raise Exception("Не удалось скачать файл с Cobalt.")
                        
                        await message.answer_video(FSInputFile(filepath))
                        os.remove(filepath)
                        await msg.delete()
                        return
                    else:
                        error_data = await resp.text()
                        raise Exception(f"Ошибка Cobalt API: {resp.status} - {error_data}")
        except Exception as e:
            logging.error(f"Cobalt Error: {e}")
            await msg.edit_text("❌ Сервер Cobalt перегружен. Попробуйте позже.")
            return

    await msg.edit_text("⏳ Скачиваю через yt-dlp...")
    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'outtmpl': 'downloads/%(id)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'rm_cachedir': True, # Очистка кэша
        'extractor_args': {
            'youtube': {
                'player_client': ['web_safari', 'tv', 'mweb'], # web_safari первым
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
        logging.error(f"yt-dlp Error: {e}")
        await msg.edit_text(f"❌ Ошибка при скачивании. Попробуйте позже.")

async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())