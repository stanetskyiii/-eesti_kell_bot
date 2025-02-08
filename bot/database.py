# bot/database.py
import os
import logging
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Получаем строку подключения из переменной окружения.
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///estonian_bot.db')
logger.info(f"Используется база данных: {DATABASE_URL}")

# Создаем engine и sessionmaker
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

Base = declarative_base()

class Word(Base):
    __tablename__ = 'words'
    id = Column(Integer, primary_key=True)
    word_et = Column(String, nullable=False)           # Эстонское слово
    part_of_speech = Column(String, nullable=False)      # Часть речи
    translation = Column(String, nullable=False)         # Перевод
    ai_generated_text = Column(Text, nullable=True)      # Пример использования
    correct_answers = Column(Integer, default=0)
    incorrect_answers = Column(Integer, default=0)
    repeat_more = Column(Boolean, default=False)         # Флаг для частого повторения

class UserSettings(Base):
    __tablename__ = 'user_settings'
    id = Column(Integer, primary_key=True)
    chat_id = Column(String, nullable=False, unique=True)  # Идентификатор пользователя
    words_per_hour = Column(Integer, default=5)             # Сколько слов отправлять за цикл
    start_time = Column(String, default="09:00")            # Начало рассылки
    end_time = Column(String, default="23:00")              # Окончание рассылки

class UserWordStatus(Base):
    __tablename__ = 'user_word_status'
    id = Column(Integer, primary_key=True)
    chat_id = Column(String, nullable=False)
    word_id = Column(Integer, nullable=False)
    sent_count = Column(Integer, default=0)
    last_sent = Column(DateTime, nullable=True)

def init_db():
    Base.metadata.create_all(engine)
