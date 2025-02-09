# bot/handlers.py
import logging
from aiogram import types, Dispatcher, Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ForceReply
from sqlalchemy.sql import func
from datetime import datetime
from bot.database import SessionLocal, Word, UserSettings, UserWordStatus
import random

# Настройка логирования
logger = logging.getLogger(__name__)

# Глобальный словарь для ожидающих тестов с набором ответа
pending_typing_tests = {}

def mark_word_as_sent(session, chat_id: str, word_id: int):
    user_word = session.query(UserWordStatus).filter_by(chat_id=chat_id, word_id=word_id).first()
    if not user_word:
        user_word = UserWordStatus(chat_id=chat_id, word_id=word_id, sent_count=1, last_sent=datetime.now())
        session.add(user_word)
    else:
        user_word.sent_count += 1
        user_word.last_sent = datetime.now()
        session.add(user_word)

def get_word_message(word_obj):
    """
    Формирует сообщение для слова с кнопками:
      – "🎧 Послушать слово" (для воспроизведения аудио)
      – "Повторять слово чаще" или "Убрать из повторяющихся" (средняя кнопка)
      – "Меню" (для возврата в главное меню)
    """
    text = (
        f"🇪🇪 Sõna: <b>{word_obj.word_et}</b>\n"
        f"🇷🇺 Перевод: <b>{word_obj.translation}</b>\n\n"
        f"📖 Информация:\n{word_obj.ai_generated_text}\n"
    )
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(InlineKeyboardButton("🎧 Послушать слово", callback_data=f"play:{word_obj.word_et}"))
    # Кнопка для частого повторения
    if word_obj.repeat_more:
        repeat_text = "Убрать из повторяющихся"
    else:
        repeat_text = "Повторять слово чаще"
    keyboard.add(InlineKeyboardButton(repeat_text, callback_data=f"toggle_repeat:{word_obj.id}"))
    keyboard.add(InlineKeyboardButton("Меню", callback_data="menu"))
    return text, keyboard

async def start_handler(message: types.Message):
    # Создаем запись настроек, если у пользователя её еще нет
    chat_id = str(message.chat.id)
    session = SessionLocal()
    user = session.query(UserSettings).filter_by(chat_id=chat_id).first()
    if not user:
        # При создании нового пользователя устанавливаем defaults:
        # words_per_hour = 5, interval_minutes = 60, start_time = "09:00", end_time = "23:00"
        user = UserSettings(chat_id=chat_id, words_per_hour=5, interval_minutes=60, start_time="09:00", end_time="23:00")
        session.add(user)
        session.commit()
        logger.info(f"Создан новый пользователь {chat_id} с настройками по умолчанию.")
    session.close()
    
    text = (
        "Привет! Я бот для изучения эстонского языка на уровни A1–A2.\n"
        "В моей базе 1781 слово, которые полностью покрывают эти уровни.\n\n"
        "Меню команд:\n"
        "• /startmailing – Начать рассылку слов\n"
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

async def startmailing_handler(message: types.Message):
    chat_id = str(message.chat.id)
    await send_five_words(chat_id, message.bot)

async def help_handler(message: types.Message):
    help_text = (
        "Список команд:\n"
        "/start – Запуск и меню\n"
        "/random_word – Получить случайное слово\n"
        "/random_test – Получить случайный тест\n"
        "/progress – Ваш прогресс\n"
        "/settings – Настроить рассылку\n"
        "<code>/setsettings &lt;слова в час&gt; &lt;интервал в минутах&gt; &lt;начало&gt; &lt;окончание&gt;</code> – Изменить настройки\n"
        "Например: <code>/setsettings 5 60 09:00 23:00</code>\n"
        "/get5words – Получить 5 слов прямо сейчас\n"
        "/help – Помощь\n\n"
        "Для помощи обращайтесь: <a href='https://t.me/seoandrey1'>seoandrey1</a>"
    )
    await message.answer(help_text, parse_mode="HTML")

async def random_word_handler(message: types.Message):
    session = SessionLocal()
    word_obj = session.query(Word).order_by(func.random()).first()
    if not word_obj:
        await message.answer("База слов пуста!", parse_mode="HTML")
        session.close()
        return
    text, keyboard = get_word_message(word_obj)
    await message.answer(text, parse_mode="HTML", reply_markup=keyboard)
    mark_word_as_sent(session, str(message.chat.id), word_obj.id)
    session.commit()
    session.close()

async def random_test_handler(message: types.Message):
    session = SessionLocal()
    chat_id = str(message.chat.id)
    # Выбираем тип теста: 1 - классический, 2 - обратный, 3 - тест с набором ответа
    test_type = random.choice([1, 2, 3])
    
    if test_type == 3:
        # Тест с набором ответа: берем слово из уже отправленных пользователю
        user_words = session.query(UserWordStatus).filter_by(chat_id=chat_id).all()
        if not user_words:
            test_type = random.choice([1, 2])  # fallback на тип 1 или 2
        else:
            chosen_status = random.choice(user_words)
            word_obj = session.query(Word).filter_by(id=chosen_status.word_id).first()
            if not word_obj:
                test_type = random.choice([1, 2])
    if test_type in [1, 2]:
        # Для типов 1 и 2 выбираем случайное слово из всей базы
        word_obj = session.query(Word).order_by(func.random()).first()
    
    if not word_obj:
        await message.answer("База слов пуста!", parse_mode="HTML")
        session.close()
        return

    # Тип 1: Классический тест – "Как переводится слово <b>word_et</b>?"
    if test_type == 1:
        correct = word_obj.translation
        options = [correct]
        others = session.query(Word).filter(
            Word.part_of_speech == word_obj.part_of_speech,
            Word.id != word_obj.id
        ).order_by(func.random()).limit(3).all()
        if len(others) < 3:
            test_type = 3
        else:
            for w in others:
                options.append(w.translation)
            random.shuffle(options)
            correct_index = options.index(correct)
            keyboard = InlineKeyboardMarkup(row_width=2)
            for idx, option in enumerate(options):
                keyboard.add(InlineKeyboardButton(option, callback_data=f"test_answer:{word_obj.id}:{idx}:{correct_index}"))
            test_text = f"❓ Как переводится слово <b>{word_obj.word_et}</b>?"
            await message.answer(test_text, parse_mode="HTML", reply_markup=keyboard)
            mark_word_as_sent(session, chat_id, word_obj.id)
            session.commit()
            session.close()
            return

    if test_type == 2:
        # Тип 2: Обратный тест – "Как по‑эстонски будет слово <b>translation</b>?"
        correct = word_obj.word_et
        options = [correct]
        others = session.query(Word).filter(
            Word.part_of_speech == word_obj.part_of_speech,
            Word.id != word_obj.id
        ).order_by(func.random()).limit(3).all()
        if len(others) < 3:
            test_type = 3
        else:
            for w in others:
                options.append(w.word_et)
            random.shuffle(options)
            correct_index = options.index(correct)
            keyboard = InlineKeyboardMarkup(row_width=2)
            for idx, option in enumerate(options):
                keyboard.add(InlineKeyboardButton(option, callback_data=f"test_answer_rev:{word_obj.id}:{idx}:{correct_index}"))
            test_text = f"❓ Как по‑эстонски будет слово <b>{word_obj.translation}</b>?"
            await message.answer(test_text, parse_mode="HTML", reply_markup=keyboard)
            mark_word_as_sent(session, chat_id, word_obj.id)
            session.commit()
            session.close()
            return

    if test_type == 3:
        # Тест с набором ответа – "Введите перевод для слова <b>word_et</b>:"
        test_text = f"❓ Введите перевод для слова <b>{word_obj.word_et}</b>:"
        await message.answer(test_text, parse_mode="HTML", reply_markup=ForceReply(selective=True))
        # Сохраняем ожидаемый ответ в глобальном словаре
        pending_typing_tests[chat_id] = {
            'word_id': word_obj.id,
            'expected': word_obj.translation
        }
        mark_word_as_sent(session, chat_id, word_obj.id)
        session.commit()
        session.close()
        return

async def get_five_words_handler(message: types.Message):
    chat_id = str(message.chat.id)
    await send_five_words(chat_id, message.bot)

async def settings_handler(message: types.Message):
    chat_id = str(message.chat.id)
    session = SessionLocal()
    user = session.query(UserSettings).filter_by(chat_id=chat_id).first()
    if not user:
        # Если пользователь не найден, создаём запись с настройками по умолчанию
        user = UserSettings(chat_id=chat_id, words_per_hour=5, interval_minutes=60, start_time="09:00", end_time="23:00")
        session.add(user)
        session.commit()
        logger.info(f"В /settings создан новый пользователь {chat_id} с настройками по умолчанию.")
    else:
        logger.info(f"В /settings для пользователя {chat_id} обнаружены настройки: words_per_hour={user.words_per_hour}, interval_minutes={user.interval_minutes}, start_time={user.start_time}, end_time={user.end_time}")
    text = (
        f"Ваши настройки рассылки:\n"
        f"Слов в час: <b>{user.words_per_hour}</b>\n"
        f"Интервал отправки: <b>{user.interval_minutes}</b> минут\n"
        f"Начало рассылки: <b>{user.start_time}</b>\n"
        f"Окончание рассылки: <b>{user.end_time}</b>\n\n"
        "Чтобы изменить настройки, отправьте сообщение в формате:\n"
        "<code>/setsettings &lt;слова в час&gt; &lt;интервал в минутах&gt; &lt;начало&gt; &lt;окончание&gt;</code>\n"
        "Например: <code>/setsettings 5 60 09:00 23:00</code>"
    )
    await message.answer(text, parse_mode="HTML")
    session.close()

async def set_settings_handler(message: types.Message):
    try:
        args = message.get_args().split()
        # Теперь ожидается 4 параметра: слова_в_час, интервал_в_минутах, начало, окончание
        words_per_hour = int(args[0])
        interval_minutes = int(args[1])
        start_time = args[2]
        end_time = args[3]
    except Exception as e:
        logger.exception("Ошибка при разборе аргументов команды /setsettings")
        await message.answer("Неверный формат. Используйте: /setsettings &lt;слова в час&gt; &lt;интервал в минутах&gt; &lt;начало&gt; &lt;окончание&gt;", parse_mode="HTML")
        return
    chat_id = str(message.chat.id)
    session = SessionLocal()
    user = session.query(UserSettings).filter_by(chat_id=chat_id).first()
    if not user:
        # Если записи нет, создаём нового пользователя.
        logger.info(f"В /setsettings для пользователя {chat_id} запись не найдена – создаём новую.")
        user = UserSettings(chat_id=chat_id)
        session.add(user)
    # Логируем перед обновлением
    logger.info(f"Обновление настроек для пользователя {chat_id}: words_per_hour={words_per_hour}, interval_minutes={interval_minutes}, start_time={start_time}, end_time={end_time}")
    user.words_per_hour = words_per_hour
    user.interval_minutes = interval_minutes
    user.start_time = start_time
    user.end_time = end_time
    session.commit()
    session.close()
    await message.answer("Настройки обновлены!", parse_mode="HTML")

async def progress_handler(message: types.Message):
    chat_id = str(message.chat.id)
    session = SessionLocal()
    total = session.query(Word).count()
    user_sent = session.query(UserWordStatus).filter_by(chat_id=chat_id).count()
    text = f"Прогресс:\nВыучено {user_sent} из {total} слов."
    await message.answer(text, parse_mode="HTML")
    session.close()

async def send_five_words(chat_id: str, bot: Bot):
    session = SessionLocal()
    sent_word_ids = [uw.word_id for uw in session.query(UserWordStatus).filter_by(chat_id=chat_id).all()]
    query = session.query(Word)
    # Сначала подбираем слова, помеченные для частого повторения, если прошло более суток с последней отправки
    frequent_words = session.query(Word).filter(Word.repeat_more == True).all()
    selected_words = []
    for word in frequent_words:
        user_word = session.query(UserWordStatus).filter_by(chat_id=chat_id, word_id=word.id).first()
        if user_word is None or (user_word.last_sent and (datetime.now() - user_word.last_sent).total_seconds() > 86400):
            selected_words.append(word)
    remaining = 5 - len(selected_words)
    if remaining > 0:
        if sent_word_ids:
            query = query.filter(~Word.id.in_(sent_word_ids))
        additional_words = query.order_by(func.random()).limit(remaining).all()
        selected_words.extend(additional_words)
        if not additional_words:
            # Если все слова отправлены, сбрасываем прогресс
            session.query(UserWordStatus).filter_by(chat_id=chat_id).delete()
            session.commit()
            additional_words = session.query(Word).order_by(func.random()).limit(remaining).all()
            selected_words.extend(additional_words)
    for word in selected_words:
        text, keyboard = get_word_message(word)
        await bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=keyboard)
        mark_word_as_sent(session, chat_id, word.id)
    session.commit()
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
        "<code>/setsettings &lt;слова в час&gt; &lt;интервал в минутах&gt; &lt;начало&gt; &lt;окончание&gt;</code> – Изменить настройки\n"
        "Например: <code>/setsettings 5 60 09:00 23:00</code>\n"
        "/get5words – Получить 5 слов прямо сейчас\n"
        "/help – Помощь\n\n"
        "Для помощи обращайтесь: <a href='https://t.me/seoandrey1'>seoandrey1</a>"
    )
    await callback_query.message.edit_text(help_text, parse_mode="HTML")
    await callback_query.answer()

async def settings_inline_handler(callback_query: types.CallbackQuery):
    settings_text = (
        "Чтобы изменить настройки рассылки, отправьте сообщение в формате:\n"
        "<code>/setsettings &lt;слова в час&gt; &lt;интервал в минутах&gt; &lt;начало&gt; &lt;окончание&gt;</code>\n"
        "Например: <code>/setsettings 5 60 09:00 23:00</code>"
    )
    await callback_query.message.edit_text(settings_text, parse_mode="HTML")
    await callback_query.answer()

async def menu_inline_handler(callback_query: types.CallbackQuery):
    text = (
        "Привет! Я бот для изучения эстонского языка на уровни A1–A2.\n"
        "В моей базе 1781 слово, которые полностью покрывают эти уровни.\n\n"
        "Меню команд:\n"
        "• /startmailing – Начать рассылку слов\n"
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

    # Обработка кнопки "toggle_repeat"
    if data.startswith("toggle_repeat:"):
        try:
            _, word_id = data.split(":", 1)
        except ValueError:
            await callback_query.answer("Некорректные данные!")
            return
        session = SessionLocal()
        word_obj = session.query(Word).filter_by(id=int(word_id)).first()
        if word_obj:
            word_obj.repeat_more = not word_obj.repeat_more
            session.commit()
            status = "помечено" if word_obj.repeat_more else "убрано из повторяющихся"
            await bot.send_message(chat_id, f"Слово {word_obj.word_et} теперь {status}.", parse_mode="HTML")
        session.close()
        await callback_query.answer()
        return

    # Обработка ответов тестов с кнопками (тип 1)
    if data.startswith("test_answer:"):
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
            response = f"❌ Неверно. Правильный ответ: {word_obj.translation if word_obj else 'Неизвестно'}"
            session.close()
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton("Следующий тест", callback_data="random_test"),
            InlineKeyboardButton("Меню", callback_data="menu")
        )
        await bot.send_message(chat_id, response, parse_mode="HTML", reply_markup=keyboard)
        await callback_query.answer()
        return

    # Обработка ответов тестов с кнопками (тип 2 – обратный тест)
    if data.startswith("test_answer_rev:"):
        parts = data.split(":")
        if len(parts) != 4:
            await callback_query.answer("Некорректные данные теста.")
            return
        _, word_id, selected_index, correct_index = parts
        session = SessionLocal()
        word_obj = session.query(Word).filter_by(id=int(word_id)).first()
        session.close()
        if selected_index == correct_index:
            response = "✅ Верно!"
        else:
            response = f"❌ Неверно. Правильный ответ: {word_obj.word_et if word_obj else 'Неизвестно'}"
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton("Следующий тест", callback_data="random_test"),
            InlineKeyboardButton("Меню", callback_data="menu")
        )
        await bot.send_message(chat_id, response, parse_mode="HTML", reply_markup=keyboard)
        await callback_query.answer()
        return

    # Обработка команды "random_test" (а также кнопки "Следующий тест")
    if data == "random_test":
        session = SessionLocal()
        # Выбираем тип теста случайно из [1, 2]
        test_type = random.choice([1, 2])
        word_obj = session.query(Word).order_by(func.random()).first()
        if not word_obj:
            await bot.send_message(chat_id, "База слов пуста!", parse_mode="HTML")
            session.close()
            await callback_query.answer()
            return
        if test_type == 1:
            correct = word_obj.translation
            options = [correct]
            others = session.query(Word).filter(
                Word.part_of_speech == word_obj.part_of_speech,
                Word.id != word_obj.id
            ).order_by(func.random()).limit(3).all()
            if len(others) < 3:
                await bot.send_message(chat_id, "Недостаточно вариантов для теста.", parse_mode="HTML")
                session.close()
                await callback_query.answer()
                return
            for w in others:
                options.append(w.translation)
            random.shuffle(options)
            correct_index = options.index(correct)
            keyboard = InlineKeyboardMarkup(row_width=2)
            for idx, option in enumerate(options):
                keyboard.add(InlineKeyboardButton(option, callback_data=f"test_answer:{word_obj.id}:{idx}:{correct_index}"))
            test_text = f"❓ Как переводится слово <b>{word_obj.word_et}</b>?"
            await bot.send_message(chat_id, test_text, parse_mode="HTML", reply_markup=keyboard)
        elif test_type == 2:
            correct = word_obj.word_et
            options = [correct]
            others = session.query(Word).filter(
                Word.part_of_speech == word_obj.part_of_speech,
                Word.id != word_obj.id
            ).order_by(func.random()).limit(3).all()
            if len(others) < 3:
                await bot.send_message(chat_id, "Недостаточно вариантов для теста.", parse_mode="HTML")
                session.close()
                await callback_query.answer()
                return
            for w in others:
                options.append(w.word_et)
            random.shuffle(options)
            correct_index = options.index(correct)
            keyboard = InlineKeyboardMarkup(row_width=2)
            for idx, option in enumerate(options):
                keyboard.add(InlineKeyboardButton(option, callback_data=f"test_answer_rev:{word_obj.id}:{idx}:{correct_index}"))
            test_text = f"❓ Как по‑эстонски будет слово <b>{word_obj.translation}</b>?"
            await bot.send_message(chat_id, test_text, parse_mode="HTML", reply_markup=keyboard)
        session.commit()
        session.close()
        await callback_query.answer("Тест отправлен!")
        return

    if data == "startmailing":
        await send_five_words(chat_id, bot)
        await callback_query.answer("Рассылка запущена!")
        return

    if data == "random_word":
        session = SessionLocal()
        word_obj = session.query(Word).order_by(func.random()).first()
        if word_obj:
            text, keyboard = get_word_message(word_obj)
            await bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=keyboard)
            mark_word_as_sent(session, chat_id, word_obj.id)
        session.commit()
        session.close()
        await callback_query.answer("Случайное слово!")
        return

    if data == "progress":
        session = SessionLocal()
        total = session.query(Word).count()
        user_sent = session.query(UserWordStatus).filter_by(chat_id=chat_id).count()
        text = f"Прогресс:\nВыучено {user_sent} из {total} слов."
        await bot.send_message(chat_id, text, parse_mode="HTML")
        session.close()
        await callback_query.answer()
        return

    # Если ни один вариант не сработал – просто отвечаем
    await callback_query.answer()

async def typing_test_answer_handler(message: types.Message):
    chat_id = str(message.chat.id)
    if chat_id not in pending_typing_tests:
        return  # Если нет ожидаемого ответа, ничего не делаем
    expected = pending_typing_tests[chat_id]['expected']
    word_id = pending_typing_tests[chat_id]['word_id']
    user_answer = message.text.strip().lower()
    if user_answer == expected.lower():
        response = "✅ Верно!"
    else:
        response = f"❌ Неверно. Правильный ответ: {expected}"
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("Следующий тест", callback_data="random_test"),
        InlineKeyboardButton("Меню", callback_data="menu")
    )
    await message.answer(response, parse_mode="HTML", reply_markup=keyboard)
    del pending_typing_tests[chat_id]

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
    # Регистрируем inline‑обработчики для кнопок "help", "settings" и "menu"
    dp.register_callback_query_handler(help_inline_handler, lambda c: c.data == "help")
    dp.register_callback_query_handler(settings_inline_handler, lambda c: c.data == "settings")
    dp.register_callback_query_handler(menu_inline_handler, lambda c: c.data == "menu")
    # Регистрируем общий обработчик для остальных inline кнопок (кроме "play:")
    dp.register_callback_query_handler(
        inline_button_handler,
        lambda c: c.data is not None and not c.data.startswith("play:")
    )
    # Регистрируем handler для ответов на тест с набором текста
    dp.register_message_handler(typing_test_answer_handler)
