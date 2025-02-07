# config/settings.py
import os

# Задайте ваш Telegram Token
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', '8032455890:AAElHeT5g6m11o0OVpmNaReEHuhThPYQcXI')

# Если понадобятся глобальные настройки рассылки (используются в планировщике по умолчанию)
START_HOUR = 9
END_HOUR = 23