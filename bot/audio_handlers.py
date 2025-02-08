import os
import aiohttp
from aiogram import types
from io import BytesIO
from aiogram.filters import Text

AUDIO_BASE_URL = os.getenv('AUDIO_BASE_URL', 'https://storage.googleapis.com/eesti-bot-project')

def get_audio_url(word: str) -> str:
    return f"{AUDIO_BASE_URL}/{word}.mp3"

async def fetch_audio(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                return await response.read()
            return None

async def send_word_audio(callback_query: types.CallbackQuery):
    data = callback_query.data
    try:
        _, word = data.split(":", 1)
    except ValueError:
        await callback_query.message.answer("Некорректные данные!")
        return

    audio_url = get_audio_url(word)
    audio_content = await fetch_audio(audio_url)

    if audio_content is None:
        await callback_query.message.answer("Аудиофайл не найден!")
        return

    # Сохраняем аудиофайл во временный файл, чтобы передать имя
    temp_filename = f"{word}.mp3"
    with open(temp_filename, "wb") as f:
        f.write(audio_content)

    # Отправляем аудиофайл с корректным именем
    await callback_query.message.answer_voice(types.FSInputFile(temp_filename))

    # Удаляем временный файл после отправки
    os.remove(temp_filename)

    await callback_query.answer()

def register_audio_handlers(dp):
    dp.register_callback_query_handler(send_word_audio, Text(startswith="play:"))
