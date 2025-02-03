from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from config.settings import DATABASE_URL

Base = declarative_base()

class Word(Base):
    __tablename__ = 'words'
    id = Column(Integer, primary_key=True)
    word_et = Column(String, nullable=False)
    part_of_speech = Column(String, nullable=False)
    translation = Column(String, nullable=False)
    ai_generated_text = Column(Text)
    last_sent = Column(DateTime)
    correct_answers = Column(Integer, default=0)
    incorrect_answers = Column(Integer, default=0)

# Инициализация подключения к БД
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def init_db():
    Base.metadata.create_all(engine)
