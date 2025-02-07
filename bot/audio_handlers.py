# bot/audio_handlers.py
import os
from aiogram import types

AUDIO_DIR = os.path.join("C:", os.sep, "Users", "Андрей", "Desktop", "телеграм эстонский", "output_audio")

def get_audio_path(word: str) -> str:
    filename = f"{word}.mp3"
    return os.path.join(AUDIO_DIR, filename)

async def send_word_audio(callback_query: types.CallbackQuery):
    data = callback_query.data  # ожидается формат "play:<слово>"
    try:
        prefix, word = data.split(":", 1)
    except ValueError:
        await callback_query.answer("Некорректные данные!")
        return
    audio_path = get_audio_path(word)
    if not os.path.exists(audio_path):
        await callback_query.answer("Аудиофайл не найден!")
        return
    with open(audio_path, "rb") as audio:
        await callback_query.message.answer_voice(audio)
    await callback_query.answer()

def register_audio_handlers(dp):
    dp.register_callback_query_handler(send_word_audio, lambda c: c.data is not None and c.data.startswith("play:"))
