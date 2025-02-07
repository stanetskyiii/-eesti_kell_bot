# bot/scheduler.py
import asyncio
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from bot.database import SessionLocal, Word, UserSettings, UserWordStatus
from aiogram import Dispatcher
from sqlalchemy.sql import func
import random

scheduler = AsyncIOScheduler()

async def send_new_words(dp: Dispatcher):
    session = SessionLocal()
    users = session.query(UserSettings).all()
    for user in users:
        now = datetime.now().strftime("%H:%M")
        if user.start_time <= now <= user.end_time:
            bot = dp.bot
            chat_id = user.chat_id
            sent_word_ids = [uw.word_id for uw in session.query(UserWordStatus).filter_by(chat_id=chat_id).all()]
            query = session.query(Word)
            if sent_word_ids:
                query = query.filter(~Word.id.in_(sent_word_ids))
            words = query.order_by(func.random()).limit(user.words_per_hour).all()
            if not words:
                session.query(UserWordStatus).filter_by(chat_id=chat_id).delete()
                session.commit()
                words = session.query(Word).order_by(func.random()).limit(user.words_per_hour).all()
            for word in words:
                # Импортируем get_word_message здесь, чтобы избежать циклического импорта
                from bot.handlers import get_word_message
                text, keyboard = get_word_message(word)
                await bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=keyboard)
                user_word = session.query(UserWordStatus).filter_by(chat_id=chat_id, word_id=word.id).first()
                if not user_word:
                    user_word = UserWordStatus(chat_id=chat_id, word_id=word.id, sent_count=1, last_sent=datetime.now())
                    session.add(user_word)
                else:
                    user_word.sent_count += 1
                    user_word.last_sent = datetime.now()
                    session.add(user_word)
            session.commit()
    session.close()

async def send_test_question(dp: Dispatcher):
    session = SessionLocal()
    users = session.query(UserSettings).all()
    for user in users:
        bot = dp.bot
        chat_id = user.chat_id
        word = session.query(Word).order_by(func.random()).first()
        if not word:
            continue
        correct = word.translation
        options = [correct]
        others = session.query(Word).filter(
            Word.part_of_speech == word.part_of_speech,
            Word.id != word.id
        ).order_by(func.random()).limit(3).all()
        for w in others:
            options.append(w.translation)
        random.shuffle(options)
        question_text = f"❓ Как переводится слово <b>{word.word_et}</b>?\n"
        for idx, option in enumerate(options, start=1):
            question_text += f"{idx}️⃣ {option}\n"
        await bot.send_message(chat_id, question_text, parse_mode="HTML")
    session.close()

def start_scheduler(dp: Dispatcher):
    scheduler.add_job(send_new_words, 'interval', hours=1, args=[dp])
    scheduler.add_job(send_test_question, 'interval', minutes=90, args=[dp])
    scheduler.start()
