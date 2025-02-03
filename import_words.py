import os
from openpyxl import load_workbook
from bot.database import SessionLocal, Word, init_db

def import_words_from_excel(excel_path):
    session = SessionLocal()
    wb = load_workbook(excel_path)
    sheet = wb.active

    # Предполагаем, что в первой строке заголовки:
    for row in sheet.iter_rows(min_row=2, values_only=True):
        # Пример: слово, часть речи, перевод
        word_et, part_of_speech, translation = row[:3]
        # Проверяем наличие слова в БД, чтобы избежать дублирования
        if session.query(Word).filter_by(word_et=word_et, part_of_speech=part_of_speech).first():
            continue
        new_word = Word(
            word_et=word_et,
            part_of_speech=part_of_speech,
            translation=translation,
            ai_generated_text=''  # Здесь можно сохранить уже сгенерированный текст, если он есть
        )
        session.add(new_word)
    session.commit()
    session.close()

if __name__ == '__main__':
    init_db()
    excel_file = os.path.join('data', 'words.xlsx')
    import_words_from_excel(excel_file)
    print("Импорт завершен!")
