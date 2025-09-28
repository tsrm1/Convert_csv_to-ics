import csv
from datetime import datetime
import os
import sys

csv_file = "190925-wdm.csv"
ics_file = "190925-wdm.ics"

# входной и выходной форматы
date_format_in = "%d.%m.%Y %H:%M"
date_format_out = "%Y%m%dT%H%M%S"

def parse_row(row, lineno):
    # ожидаем минимум 3 колонки; последние две — start и end, всё остальное — subject
    if len(row) < 3:
        raise ValueError(f"строка {lineno}: недостаточно колонок ({len(row)})")
    start_raw = row[-2].strip()
    end_raw = row[-1].strip()
    subject = ",".join(cell.strip() for cell in row[:-2])
    # парсим даты (выбросит ValueError при ошибке формата)
    start_dt = datetime.strptime(start_raw, date_format_in)
    end_dt = datetime.strptime(end_raw, date_format_in)
    return subject, start_dt, end_dt

file_base = os.path.splitext(os.path.basename(csv_file))[0]

events = []
with open(csv_file, "r", encoding="utf-8-sig", newline="") as f:
    reader = csv.reader(f, skipinitialspace=True)
    for i, row in enumerate(reader, start=1):
        # пропускаем возможный заголовок
        if i == 1:
            first_cell = row[0].strip().lower() if row else ""
            if "subject" in first_cell or "start" in first_cell or "дата" in first_cell:
                continue
        # пропуск пустых строк
        if not any(cell.strip() for cell in row):
            continue
        try:
            subject, start_dt, end_dt = parse_row(row, i)
        except Exception as e:
            print(f"Warning: {e} — строка {i} пропущена.")
            print(f"  Содержимое: {row}")
            continue

        dtstart = start_dt.strftime(date_format_out)
        dtend = end_dt.strftime(date_format_out)
        dtstamp = datetime.now().strftime("%Y%m%dT%H%M%SZ")
        uid = f"{dtstart}@{file_base}"

        event = (
            "BEGIN:VEVENT\n"
            f"UID:{uid}\n"
            f"DTSTAMP:{dtstamp}\n"
            f"DTSTART;TZID=Europe/Berlin:{dtstart}\n"
            f"DTEND;TZID=Europe/Berlin:{dtend}\n"
            f"SUMMARY:{subject}\n"
            "END:VEVENT\n"
        )
        events.append(event)

if not events:
    print("Не найдено ни одного события. Проверь CSV.")
    sys.exit(1)

with open(ics_file, "w", encoding="utf-8") as f:
    f.write("BEGIN:VCALENDAR\nVERSION:2.0\nCALSCALE:GREGORIAN\nMETHOD:PUBLISH\n")
    for e in events:
        f.write(e)
    f.write("END:VCALENDAR\n")

print(f"Готово: {ics_file} — записано {len(events)} событий.")
# Конвертация CSV в ICS (iCalendar)
# Читает CSV файл с колонками SUBJECT, START DATE, END DATE