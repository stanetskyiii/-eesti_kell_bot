# bot/main.py
import asyncio
from aiogram import Bot, Dispatcher
from config.settings import TELEGRAM_TOKEN
from bot import handlers, scheduler
from bot.database import init_db
from bot.audio_handlers import register_audio_handlers

async def main():
    init_db()
    bot = Bot(token=TELEGRAM_TOKEN)
    dp = Dispatcher(bot)
    handlers.register_handlers(dp)
    register_audio_handlers(dp)
    scheduler.start_scheduler(dp)
    try:
        await dp.start_polling()
    finally:
        await bot.session.close()

if __name__ == '__main__':
    asyncio.run(main())
