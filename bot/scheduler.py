# bot/scheduler.py
import asyncio
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from bot.database import SessionLocal, Word, UserSettings, UserWordStatus
from aiogram import Dispatcher
from sqlalchemy.sql import func
import random
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.handlers import get_word_message, mark_word_as_sent

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
                text, keyboard = get_word_message(word)
                await bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=keyboard)
                mark_word_as_sent(session, chat_id, word.id)
            session.commit()
    session.close()

async def send_test_question(dp: Dispatcher):
    session = SessionLocal()
    users = session.query(UserSettings).all()
    for user in users:
        bot = dp.bot
        chat_id = user.chat_id
        # Для автоматического теста выбираем только тип 1 или 2 (без теста с набором ответа)
        test_type = random.choice([1, 2])
        word = session.query(Word).order_by(func.random()).first()
        if not word:
            continue
        if test_type == 1:
            correct = word.translation
            options = [correct]
            others = session.query(Word).filter(
                Word.part_of_speech == word.part_of_speech,
                Word.id != word.id
            ).order_by(func.random()).limit(3).all()
            if len(others) < 3:
                continue
            for w in others:
                options.append(w.translation)
            random.shuffle(options)
            correct_index = options.index(correct)
            keyboard = InlineKeyboardMarkup(row_width=2)
            for idx, option in enumerate(options):
                keyboard.add(InlineKeyboardButton(option, callback_data=f"test_answer:{word.id}:{idx}:{correct_index}"))
            question_text = f"❓ Как переводится слово <b>{word.word_et}</b>?"
        else:  # test_type == 2
            correct = word.word_et
            options = [correct]
            others = session.query(Word).filter(
                Word.part_of_speech == word.part_of_speech,
                Word.id != word.id
            ).order_by(func.random()).limit(3).all()
            if len(others) < 3:
                continue
            for w in others:
                options.append(w.word_et)
            random.shuffle(options)
            correct_index = options.index(correct)
            keyboard = InlineKeyboardMarkup(row_width=2)
            for idx, option in enumerate(options):
                keyboard.add(InlineKeyboardButton(option, callback_data=f"test_answer_rev:{word.id}:{idx}:{correct_index}"))
            question_text = f"❓ Как по‑эстонски будет слово <b>{word.translation}</b>?"
        await bot.send_message(chat_id, question_text, parse_mode="HTML", reply_markup=keyboard)
        mark_word_as_sent(session, chat_id, word.id)
    session.commit()
    session.close()

async def send_daily_statistics(dp: Dispatcher):
    session = SessionLocal()
    users = session.query(UserSettings).all()
    total_words = session.query(Word).count()
    for user in users:
        chat_id = user.chat_id
        user_sent = session.query(UserWordStatus).filter_by(chat_id=chat_id).count()
        if user_sent < total_words:
            stat_text = (f"Доброе утро!\nПоздравляем – вы уже ознакомились с <b>{user_sent}</b> слов из <b>{total_words}</b>.\n"
                         "Продолжайте в том же духе!")
        else:
            stat_text = (f"Поздравляем!\nВы прошли всю базу из <b>{total_words}</b> слов.\n"
                         f"Всего отправлено (с учётом повторов): <b>{user_sent}</b> слов.")
        await dp.bot.send_message(chat_id, stat_text, parse_mode="HTML")
    session.close()

def start_scheduler(dp: Dispatcher):
    scheduler.add_job(send_new_words, 'interval', hours=1, args=[dp])
    scheduler.add_job(send_test_question, 'interval', minutes=90, args=[dp])
    scheduler.add_job(send_daily_statistics, 'cron', hour=9, minute=0, args=[dp])
    scheduler.start()
