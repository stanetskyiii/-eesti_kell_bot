import asyncio
from aiogram import Bot, Dispatcher
from config.settings import TELEGRAM_TOKEN
from bot import handlers, scheduler
from bot.database import init_db

async def main():
    # Инициализация БД
    init_db()

    bot = Bot(token=TELEGRAM_TOKEN)
    dp = Dispatcher(bot)

    # Регистрация обработчиков команд
    handlers.register_handlers(dp)

    # Запуск планировщика задач (авторассылка, тесты)
    scheduler.start_scheduler(dp)

    # Запуск поллинга
    try:
        await dp.start_polling()
    finally:
        await bot.session.close()

if __name__ == '__main__':
    asyncio.run(main())
