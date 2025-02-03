import os
from google.cloud import texttospeech
from config.settings import TTS_CACHE_DIR

# Создаем клиента
client = texttospeech.TextToSpeechClient()

def get_tts_audio(word: str, part_of_speech: str) -> str:
    """
    Возвращает путь к mp3 файлу с озвучкой. Если файл уже есть в кэше, возвращает его.
    Идентификация по связке слово-часть речи.
    """
    # Формируем имя файла
    filename = f"{word}_{part_of_speech}.mp3".replace(" ", "_")
    filepath = os.path.join(TTS_CACHE_DIR, filename)
    
    # Если файл существует, вернуть путь
    if os.path.exists(filepath):
        return filepath

    # Если директории кэша нет, создаем её
    os.makedirs(TTS_CACHE_DIR, exist_ok=True)
    
    synthesis_input = texttospeech.SynthesisInput(text=word)
    voice = texttospeech.VoiceSelectionParams(
        language_code="et-EE",  # эстонский
        ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )
    
    response = client.synthesize_speech(
        input=synthesis_input,
        voice=voice,
        audio_config=audio_config
    )
    
    with open(filepath, "wb") as out:
        out.write(response.audio_content)
    
    return filepath
