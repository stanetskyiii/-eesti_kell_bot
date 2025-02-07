# test_queries.py
from bot.database import SessionLocal, Word, init_db

def test_queries():
    session = SessionLocal()

    # 1. Вывести общее количество слов в базе
    total = session.query(Word).count()
    print(f"Всего слов в базе: {total}")

    # 2. Вывести все слова с определенной частью речи (например, "существительное")
    part = "nimisõna"  # измените на нужное значение для теста
    words_noun = session.query(Word).filter(Word.part_of_speech == part).all()
    print(f"\nСлова с частью речи '{part}':")
    for word in words_noun:
        print(f"ID: {word.id}, Слово: {word.word_et}, Перевод: {word.translation}")

    # 3. Выбрать случайное слово (для теста вопросов)
    from sqlalchemy.sql import func
    random_word = session.query(Word).order_by(func.random()).first()
    if random_word:
        print(f"\nСлучайное слово: {random_word.word_et} ({random_word.translation}) - Часть речи: {random_word.part_of_speech}")

    session.close()

if __name__ == '__main__':
    init_db()
    test_queries()
