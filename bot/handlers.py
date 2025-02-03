from aiogram import types, Dispatcher
from aiogram.dispatcher.filters import Command
from bot.database import SessionLocal, Word
from bot.tts import get_tts_audio

async def start_handler(message: types.Message):
    await message.answer("Привет! Я бот для изучения эстонского языка. Используй /help для получения инструкций.")

async def help_handler(message: types.Message):
    help_text = (
        "/start - Запуск бота\n"
        "/help - Помощь\n"
        "/progress - Прогресс обучения\n"
        "/say <слово> - Озвучка слова\n"
        "/random_word - Случайное слово\n"
        "/stop - Остановка авторассылки"
    )
    await message.answer(help_text)

async def say_handler(message: types.Message):
    args = message.get_args()
    if not args:
        await message.answer("Укажи слово, например: /say auto")
        return

    # Здесь можно добавить поиск слова в БД для получения part_of_speech
    session = SessionLocal()
    word_obj = session.query(Word).filter(Word.word_et == args).first()
    if not word_obj:
        await message.answer("Слово не найдено в базе!")
        session.close()
        return

    audio_path = get_tts_audio(word_obj.word_et, word_obj.part_of_speech)
    session.close()
    with open(audio_path, 'rb') as audio:
        await message.answer_voice(audio)

# Пример для /random_word
async def random_word_handler(message: types.Message):
    session = SessionLocal()
    # Выбираем случайное слово
    word_obj = session.query(Word).order_by(func.random()).first()
    if not word_obj:
        await message.answer("База слов пуста!")
        session.close()
        return

    text = (
        f"🇪🇪 Sõna: *{word_obj.word_et}*\n"
        f"🇷🇺 Перевод: *{word_obj.translation}*\n\n"
        f"📖 Информация:\n{word_obj.ai_generated_text}\n\n"
        f"🎧 /say {word_obj.word_et}"
    )
    await message.answer(text, parse_mode="Markdown")
    session.close()

def register_handlers(dp: Dispatcher):
    dp.register_message_handler(start_handler, commands=["start"])
    dp.register_message_handler(help_handler, commands=["help"])
    dp.register_message_handler(say_handler, commands=["say"])
    dp.register_message_handler(random_word_handler, commands=["random_word"])
    # Добавляйте другие обработчики по мере необходимости
