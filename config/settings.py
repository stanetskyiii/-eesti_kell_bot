import os

# Телеграм токен
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', 'your-telegram-bot-token')

# Параметры БД
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://user:password@localhost:5432/estonian_bot')

# Google Cloud TTS
GOOGLE_APPLICATION_CREDENTIALS = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'tts-key.json')

# Параметры работы планировщика
START_HOUR = 9    # начало авторассылки
END_HOUR = 23     # конец авторассылки (11 вечера)

# Путь к кэшу озвучки
TTS_CACHE_DIR = os.path.join(os.getcwd(), 'data', 'tts_cache')
