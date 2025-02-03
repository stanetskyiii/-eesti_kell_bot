import asyncio
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from config.settings import START_HOUR, END_HOUR
from bot.database import SessionLocal, Word
from aiogram import Dispatcher
from sqlalchemy.sql import func

scheduler = AsyncIOScheduler()

async def send_new_words(dp: Dispatcher):
    """
    Функция для авторассылки 5 новых слов каждые 60 минут,
    только в промежутке с 9:00 до 23:00 с учетом часового пояса.
    """
    current_hour = datetime.now().hour
    if not (START_HOUR <= current_hour <= END_HOUR):
        return

    session = SessionLocal()
    # Выбираем 5 слов, которые еще не были отправлены (last_sent is null) или отправляем слова из очереди.
    words = session.query(Word).filter(Word.last_sent == None).limit(5).all()
    if not words:
        # Если нет новых слов, выбираем 5 случайных
        words = session.query(Word).order_by(func.random()).limit(5).all()

    # Для каждого пользователя может понадобиться своя логика очереди.
    # Здесь отправляем сообщение во все чаты, в данном примере логика упрощена.
    for word in words:
        text = (
            f"🇪🇪 Sõna: *{word.word_et}*\n"
            f"🇷🇺 Перевод: *{word.translation}*\n\n"
            f"📖 Информация:\n{word.ai_generated_text}\n\n"
            f"🎧 /say {word.word_et}"
        )
        # Пример: отправляем в общий чат (в реальном проекте потребуется хранить id пользователей)
        # dp.bot.send_message(chat_id=..., text=text, parse_mode="Markdown")
        print(f"Отправка слова: {word.word_et}")  # Заглушка
        word.last_sent = datetime.now()
        session.add(word)
    session.commit()
    session.close()

async def send_test_question(dp: Dispatcher):
    """
    Функция для отправки теста (вызов каждые 2 часа).
    """
    session = SessionLocal()
    # Выбираем случайное слово для теста
    word = session.query(Word).order_by(func.random()).first()
    if not word:
        session.close()
        return

    # Формируем варианты ответа:
    # Вариант с правильным переводом и 3 случайными из других слов той же части речи.
    correct = word.translation
    options = [correct]
    other_words = session.query(Word).filter(
        Word.part_of_speech == word.part_of_speech,
        Word.id != word.id
    ).order_by(func.random()).limit(3).all()
    for w in other_words:
        options.append(w.translation)
    # Перемешиваем варианты
    import random
    random.shuffle(options)

    question_text = f"❓ Как переводится слово *\"{word.word_et}\"*?\n"
    for idx, option in enumerate(options, 1):
        question_text += f"{idx}️⃣ {option}\n"

    # Здесь отправляем сообщение в чат (логика для конкретного пользователя)
    # Пример:
    # await dp.bot.send_message(chat_id=..., text=question_text, parse_mode="Markdown")
    print("Отправка тестового вопроса:", question_text)
    session.close()

def start_scheduler(dp):
    # Планируем авторассылку каждые 60 минут
    scheduler.add_job(send_new_words, 'interval', hours=1, args=[dp])
    # Планируем тесты каждые 2 часа
    scheduler.add_job(send_test_question, 'interval', hours=2, args=[dp])
    scheduler.start()
