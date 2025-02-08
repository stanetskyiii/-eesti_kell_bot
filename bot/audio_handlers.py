# bot/audio_handlers.py
import os
from aiogram import types
import requests
from io import BytesIO

# Получаем базовый URL для аудиофайлов из переменной окружения,
# иначе используем значение по умолчанию.
AUDIO_BASE_URL = os.getenv('AUDIO_BASE_URL', 'https://storage.googleapis.com/eesti-bot-project')

def get_audio_url(word: str) -> str:
    """
    Формирует URL аудиофайла по шаблону:
    https://storage.googleapis.com/eesti-bot-project/<слово>.mp3
    """
    filename = f"{word}.mp3"
    return f"{AUDIO_BASE_URL}/{filename}"

async def send_word_audio(callback_query: types.CallbackQuery):
    data = callback_query.data  # ожидается формат "play:<слово>"
    try:
        prefix, word = data.split(":", 1)
    except ValueError:
        await callback_query.answer("Некорректные данные!")
        return

    audio_url = get_audio_url(word)
    try:
        response = requests.get(audio_url)
        response.raise_for_status()
    except Exception as e:
        await callback_query.answer("Аудиофайл не найден!")
        return

    # Читаем аудио как байты, задаём имя файла (оно будет использовано при отправке)
    audio_bytes = BytesIO(response.content)
    audio_bytes.name = f"{word}.mp3"  # имя файла теперь соответствует слову
    # Используем метод answer_audio, который при отправке аудио отображает имя файла
    await callback_query.message.answer_voice(types.InputFile(audio_bytes, filename=f"{word}.mp3"))
    await callback_query.answer()

def register_audio_handlers(dp):
    dp.register_callback_query_handler(
        send_word_audio,
        lambda c: c.data is not None and c.data.startswith("play:")
    )
