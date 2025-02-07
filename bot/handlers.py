# bot/handlers.py
from aiogram import types, Dispatcher, Bot
from sqlalchemy.sql import func
from datetime import datetime
from bot.database import SessionLocal, Word, UserSettings, UserWordStatus
from bot.audio_handlers import get_audio_path
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import random

def get_word_message(word_obj):
    """
    Формирует сообщение для слова с кнопками:
      – "🎧 Послушать слово" (для воспроизведения аудио)
      – "Меню" (для возврата в главное меню)
    """
    text = (
        f"🇪🇪 Sõna: <b>{word_obj.word_et}</b>\n"
        f"🇷🇺 Перевод: <b>{word_obj.translation}</b>\n\n"
        f"📖 Информация:\n{word_obj.ai_generated_text}\n"
    )
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(InlineKeyboardButton("🎧 Послушать слово", callback_data=f"play:{word_obj.word_et}"))
    keyboard.add(InlineKeyboardButton("Меню", callback_data="menu"))
    return text, keyboard

async def send_five_words(chat_id: str, bot: Bot):
    """
    Отправляет пользователю 5 случайных слов.
    Если все слова уже отправлены, сбрасывает прогресс.
    """
    session = SessionLocal()
    sent_word_ids = [uw.word_id for uw in session.query(UserWordStatus).filter_by(chat_id=chat_id).all()]
    query = session.query(Word)
    if sent_word_ids:
        query = query.filter(~Word.id.in_(sent_word_ids))
    words = query.order_by(func.random()).limit(5).all()
    if not words:
        # Если все слова отправлены, сбрасываем прогресс
        session.query(UserWordStatus).filter_by(chat_id=chat_id).delete()
        session.commit()
        words = session.query(Word).order_by(func.random()).limit(5).all()
    for word in words:
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

# --------------------- Message Handlers ---------------------

# Команда /start – выводит главное меню
async def start_handler(message: types.Message):
    text = (
        "Привет! Я бот для изучения эстонского языка на уровни A1–A2.\n"
        "В моей базе 1781 слово, которые полностью покрывают эти уровни.\n\n"
        "Меню команд:\n"
        "• /startmailing – Начать рассылку 5-ти слов в час (с 09:00 по 23:00)\n"
        "• /random_word – Получить случайное слово\n"
        "• /random_test – Получить случайный тест\n"
        "• /progress – Узнать свой прогресс (выучено X из Y)\n"
        "• /settings – Настроить рассылку\n"
        "• /help – Помощь\n"
        "• /get5words – Получить 5 слов прямо сейчас\n"
    )
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("Начать рассылку", callback_data="startmailing"),
        InlineKeyboardButton("Случайное слово", callback_data="random_word"),
        InlineKeyboardButton("Случайный тест", callback_data="random_test"),
        InlineKeyboardButton("Прогресс", callback_data="progress"),
        InlineKeyboardButton("Настройки", callback_data="settings"),
        InlineKeyboardButton("Помощь", callback_data="help")
    )
    await message.answer(text, parse_mode="HTML", reply_markup=keyboard)

# Команда /startmailing – отправляет 5 слов сразу
async def startmailing_handler(message: types.Message):
    chat_id = str(message.chat.id)
    await send_five_words(chat_id, message.bot)

# Команда /help – выводит справку (отформатированную с использованием <code>)
async def help_handler(message: types.Message):
    help_text = (
        "Список команд:\n"
        "/start – Запуск и меню\n"
        "/random_word – Получить случайное слово\n"
        "/random_test – Получить случайный тест\n"
        "/progress – Ваш прогресс\n"
        "/settings – Настроить рассылку\n"
        "<code>/setsettings &lt;слова в час&gt; &lt;начало&gt; &lt;окончание&gt;</code> – Изменить настройки\n"
        "Например: <code>/setsettings 5 09:00 23:00</code>\n"
        "/get5words – Получить 5 слов прямо сейчас\n"
        "/help – Помощь\n\n"
        "Для помощи обращайтесь: <a href='https://t.me/seoandrey1'>seoandrey1</a>"
    )
    await message.answer(help_text, parse_mode="HTML")

# Команда /random_word – отправляет случайное слово
async def random_word_handler(message: types.Message):
    session = SessionLocal()
    word_obj = session.query(Word).order_by(func.random()).first()
    if not word_obj:
        await message.answer("База слов пуста!", parse_mode="HTML")
        session.close()
        return
    text, keyboard = get_word_message(word_obj)
    await message.answer(text, parse_mode="HTML", reply_markup=keyboard)
    session.close()

# Команда /random_test – отправляет тест с 4 вариантами ответов
async def random_test_handler(message: types.Message):
    session = SessionLocal()
    word = session.query(Word).order_by(func.random()).first()
    if not word:
        await message.answer("База слов пуста!", parse_mode="HTML")
        session.close()
        return
    correct = word.translation
    options = [correct]
    others = session.query(Word).filter(
        Word.part_of_speech == word.part_of_speech,
        Word.id != word.id
    ).order_by(func.random()).limit(3).all()
    for w in others:
        options.append(w.translation)
    random.shuffle(options)
    correct_index = options.index(correct)
    keyboard = InlineKeyboardMarkup(row_width=2)
    for idx, option in enumerate(options):
        button = InlineKeyboardButton(option, callback_data=f"test_answer:{word.id}:{idx}:{correct_index}")
        keyboard.add(button)
    test_text = f"❓ Как переводится слово <b>{word.word_et}</b>?"
    await message.answer(test_text, parse_mode="HTML", reply_markup=keyboard)
    session.close()

# Команда /get5words – отправляет 5 слов сразу
async def get_five_words_handler(message: types.Message):
    chat_id = str(message.chat.id)
    await send_five_words(chat_id, message.bot)

# Команда /settings – выводит текущие настройки пользователя с дополнительной информацией
async def settings_handler(message: types.Message):
    chat_id = str(message.chat.id)
    session = SessionLocal()
    user = session.query(UserSettings).filter_by(chat_id=chat_id).first()
    if not user:
        user = UserSettings(chat_id=chat_id)
        session.add(user)
        session.commit()
    text = (
        f"Ваши настройки рассылки:\n"
        f"Слов в час: <b>{user.words_per_hour}</b>\n"
        f"Начало рассылки: <b>{user.start_time}</b>\n"
        f"Окончание рассылки: <b>{user.end_time}</b>\n\n"
        "Чтобы изменить настройки, отправьте сообщение в формате:\n"
        "<code>/setsettings &lt;слова в час&gt; &lt;начало&gt; &lt;окончание&gt;</code>\n"
        "Например: <code>/setsettings 5 09:00 23:00</code>"
    )
    await message.answer(text, parse_mode="HTML")
    session.close()

# Команда /setsettings – изменяет настройки рассылки
async def set_settings_handler(message: types.Message):
    try:
        args = message.get_args().split()
        words_per_hour = int(args[0])
        start_time = args[1]
        end_time = args[2]
    except Exception:
        await message.answer("Неверный формат. Используйте: /setsettings <слова в час> <начало> <окончание>", parse_mode="HTML")
        return
    chat_id = str(message.chat.id)
    session = SessionLocal()
    user = session.query(UserSettings).filter_by(chat_id=chat_id).first()
    if not user:
        user = UserSettings(chat_id=chat_id)
        session.add(user)
    user.words_per_hour = words_per_hour
    user.start_time = start_time
    user.end_time = end_time
    session.commit()
    session.close()
    await message.answer("Настройки обновлены!", parse_mode="HTML")

# Команда /progress – показывает прогресс пользователя
async def progress_handler(message: types.Message):
    chat_id = str(message.chat.id)
    session = SessionLocal()
    total = session.query(Word).count()
    user_sent = session.query(UserWordStatus).filter_by(chat_id=chat_id).count()
    text = f"Прогресс:\nВыучено {user_sent} из {total} слов."
    await message.answer(text, parse_mode="HTML")
    session.close()

# --------------------- Inline Callback Query Handlers ---------------------

async def help_inline_handler(callback_query: types.CallbackQuery):
    help_text = (
        "Список команд:\n"
        "/start – Запуск и меню\n"
        "/random_word – Получить случайное слово\n"
        "/random_test – Получить случайный тест\n"
        "/progress – Ваш прогресс\n"
        "/settings – Настроить рассылку\n"
        "<code>/setsettings &lt;слова в час&gt; &lt;начало&gt; &lt;окончание&gt;</code> – Изменить настройки\n"
        "Например: <code>/setsettings 5 09:00 23:00</code>\n"
        "/get5words – Получить 5 слов прямо сейчас\n"
        "/help – Помощь\n\n"
        "Для помощи обращайтесь: <a href='https://t.me/seoandrey1'>seoandrey1</a>"
    )
    await callback_query.message.edit_text(help_text, parse_mode="HTML")
    await callback_query.answer()

async def settings_inline_handler(callback_query: types.CallbackQuery):
    settings_text = (
        "Чтобы изменить настройки рассылки, отправьте сообщение в формате:\n"
        "<code>/setsettings &lt;слова в час&gt; &lt;начало&gt; &lt;окончание&gt;</code>\n"
        "Например: <code>/setsettings 5 09:00 23:00</code>"
    )
    await callback_query.message.edit_text(settings_text, parse_mode="HTML")
    await callback_query.answer()

async def menu_inline_handler(callback_query: types.CallbackQuery):
    """
    Обработчик кнопки «Меню»: возвращает главное меню.
    """
    text = (
        "Привет! Я бот для изучения эстонского языка на уровни A1–A2.\n"
        "В моей базе 1781 слово, которые полностью покрывают эти уровни.\n\n"
        "Меню команд:\n"
        "• /startmailing – Начать рассылку 5-ти слов в час (с 09:00 по 23:00)\n"
        "• /random_word – Получить случайное слово\n"
        "• /random_test – Получить случайный тест\n"
        "• /progress – Узнать свой прогресс (выучено X из Y)\n"
        "• /settings – Настроить рассылку\n"
        "• /help – Помощь\n"
        "• /get5words – Получить 5 слов прямо сейчас\n"
    )
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("Начать рассылку", callback_data="startmailing"),
        InlineKeyboardButton("Случайное слово", callback_data="random_word"),
        InlineKeyboardButton("Случайный тест", callback_data="random_test"),
        InlineKeyboardButton("Прогресс", callback_data="progress"),
        InlineKeyboardButton("Настройки", callback_data="settings"),
        InlineKeyboardButton("Помощь", callback_data="help")
    )
    await callback_query.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    await callback_query.answer()

async def inline_button_handler(callback_query: types.CallbackQuery):
    data = callback_query.data
    bot = callback_query.bot
    chat_id = str(callback_query.message.chat.id)
    if data == "startmailing":
        await send_five_words(chat_id, bot)
        await callback_query.answer("Рассылка запущена!")
    elif data == "random_word":
        session = SessionLocal()
        word_obj = session.query(Word).order_by(func.random()).first()
        if word_obj:
            text, keyboard = get_word_message(word_obj)
            await bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=keyboard)
        session.close()
        await callback_query.answer("Случайное слово!")
    elif data == "random_test":
        session = SessionLocal()
        word = session.query(Word).order_by(func.random()).first()
        if not word:
            await bot.send_message(chat_id, "База слов пуста!", parse_mode="HTML")
            session.close()
            await callback_query.answer()
            return
        correct = word.translation
        options = [correct]
        others = session.query(Word).filter(
            Word.part_of_speech == word.part_of_speech,
            Word.id != word.id
        ).order_by(func.random()).limit(3).all()
        for w in others:
            options.append(w.translation)
        random.shuffle(options)
        correct_index = options.index(correct)
        keyboard = InlineKeyboardMarkup(row_width=2)
        for idx, option in enumerate(options):
            button = InlineKeyboardButton(option, callback_data=f"test_answer:{word.id}:{idx}:{correct_index}")
            keyboard.add(button)
        test_text = f"❓ Как переводится слово <b>{word.word_et}</b>?"
        await bot.send_message(chat_id, test_text, parse_mode="HTML", reply_markup=keyboard)
        session.close()
        await callback_query.answer("Тест отправлен!")
    elif data.startswith("test_answer:"):
        parts = data.split(":")
        if len(parts) != 4:
            await callback_query.answer("Некорректные данные теста.")
            return
        _, word_id, selected_index, correct_index = parts
        if selected_index == correct_index:
            response = "✅ Верно!"
        else:
            session = SessionLocal()
            word_obj = session.query(Word).filter_by(id=int(word_id)).first()
            session.close()
            correct_text = word_obj.translation if word_obj else "Неизвестно"
            response = f"❌ Неверно. Правильный ответ: {correct_text}"
        await bot.send_message(chat_id, response, parse_mode="HTML")
        await callback_query.answer()
    elif data == "progress":
        session = SessionLocal()
        total = session.query(Word).count()
        user_sent = session.query(UserWordStatus).filter_by(chat_id=chat_id).count()
        text = f"Прогресс:\nВыучено {user_sent} из {total} слов."
        await bot.send_message(chat_id, text, parse_mode="HTML")
        session.close()
        await callback_query.answer()
    else:
        await callback_query.answer()

def register_handlers(dp: Dispatcher):
    dp.register_message_handler(start_handler, commands=["start"])
    dp.register_message_handler(startmailing_handler, commands=["startmailing"])
    dp.register_message_handler(help_handler, commands=["help"])
    dp.register_message_handler(random_word_handler, commands=["random_word"])
    dp.register_message_handler(random_test_handler, commands=["random_test"])
    dp.register_message_handler(get_five_words_handler, commands=["get5words"])
    dp.register_message_handler(settings_handler, commands=["settings"])
    dp.register_message_handler(set_settings_handler, commands=["setsettings"])
    dp.register_message_handler(progress_handler, commands=["progress"])
    # Регистрируем отдельные inline‑обработчики для кнопок "help", "settings" и "menu"
    dp.register_callback_query_handler(help_inline_handler, lambda c: c.data == "help")
    dp.register_callback_query_handler(settings_inline_handler, lambda c: c.data == "settings")
    dp.register_callback_query_handler(menu_inline_handler, lambda c: c.data == "menu")
    # Регистрируем общий обработчик для остальных inline кнопок (исключая "play:", "help", "settings" и "menu")
    dp.register_callback_query_handler(
        inline_button_handler,
        lambda c: c.data is not None and not c.data.startswith("play:") and c.data not in ["help", "settings", "menu"]
    )
