#!/usr/bin/env python3
"""
convert_csv_to_ics.py
Пример:
  python convert_csv_to_ics.py 190925-wdm.csv
  python convert_csv_to_ics.py D:\Projects\Python\csv\190925-wdm.csv output.ics
"""
import argparse, csv, os, sys
from datetime import datetime

# zoneinfo доступен в Python 3.9+
try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None

def try_open(path):
    encodings = ("utf-8-sig", "utf-8", "cp1251")
    last_exc = None
    for enc in encodings:
        try:
            f = open(path, "r", encoding=enc)
            # проверим, что чтение работает
            _ = f.readline()
            f.seek(0)
            return f, enc
        except Exception as e:
            last_exc = e
    raise last_exc

def detect_delimiter(sample):
    try:
        sniffer = csv.Sniffer()
        return sniffer.sniff(sample).delimiter
    except Exception:
        return ','

def find_column_names(fieldnames):
    mapping = {}
    if not fieldnames:
        return mapping
    for name in fieldnames:
        n = (name or "").lower()
        if 'subject' in n or 'summary' in n or 'title' in n:
            mapping['subject'] = name
        if 'start' in n:
            mapping['start'] = name
        if 'end' in n or 'finish' in n or 'until' in n:
            mapping['end'] = name
    return mapping

def parse_date(s):
    s = s.strip()
    fmts = ("%d.%m.%Y %H:%M", "%d.%m.%Y %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S")
    for fmt in fmts:
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            pass
    raise ValueError(f"Не удалось распознать дату: {s!r}")

def main():
    parser = argparse.ArgumentParser(description="CSV -> ICS (Europe/Berlin)")
    parser.add_argument("input", help="входной CSV-файл")
    parser.add_argument("output", nargs='?', help="выходной ICS (опционально)")
    args = parser.parse_args()

    csv_path = args.input
    if not os.path.exists(csv_path):
        print("Ошибка: файл не найден:", csv_path)
        print("Текущая рабочая папка:", os.getcwd())
        print("Файлы в текущей папке:", os.listdir())
        sys.exit(2)

    try:
        f, used_enc = try_open(csv_path)
    except Exception as e:
        print("Не удалось открыть файл. Ошибка:", e)
        sys.exit(3)

    sample = f.read(4096)
    f.seek(0)
    delim = detect_delimiter(sample)
    reader = csv.DictReader(f, delimiter=delim)
    mapping = find_column_names(reader.fieldnames or [])
    if 'subject' not in mapping or 'start' not in mapping or 'end' not in mapping:
        cols = reader.fieldnames or []
        if len(cols) >= 3:
            mapping = {'subject': cols[0], 'start': cols[1], 'end': cols[2]}
        else:
            print("Не удалось найти колонки SUBJECT/START/END. Заголовки:", reader.fieldnames)
            sys.exit(4)

    events = []
    seen_dtstarts = {}
    berlin = ZoneInfo("Europe/Berlin") if ZoneInfo else None

    for idx, row in enumerate(reader, start=1):
        subj = row.get(mapping['subject'], "").strip()
        raw_start = row.get(mapping['start'], "").strip()
        raw_end = row.get(mapping['end'], "").strip()
        if not raw_start or not raw_end:
            print("Пропускаю строку", idx, "- нет дат:", subj)
            continue
        try:
            dt_start = parse_date(raw_start)
            dt_end = parse_date(raw_end)
        except ValueError as e:
            print("Ошибка разбора даты в строке", idx, ":", e)
            continue

        if berlin:
            dt_start = dt_start.replace(tzinfo=berlin)
            dt_end = dt_end.replace(tzinfo=berlin)

        dtstart_str = dt_start.strftime("%Y%m%dT%H%M%S")
        dtend_str = dt_end.strftime("%Y%m%dT%H%M%S")
        dtstamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

        base_uid = dtstart_str
        count = seen_dtstarts.get(base_uid, 0) + 1
        seen_dtstarts[base_uid] = count
        base_name = os.path.splitext(os.path.basename(csv_path))[0] or "csv2ics"
        uid = f"{base_uid}{'-'+str(count) if count>1 else ''}@{base_name}"

        if berlin:
            dtstart_line = f"DTSTART;TZID=Europe/Berlin:{dtstart_str}"
            dtend_line = f"DTEND;TZID=Europe/Berlin:{dtend_str}"
        else:
            dtstart_line = f"DTSTART:{dtstart_str}Z"
            dtend_line = f"DTEND:{dtend_str}Z"

        ev = (
            "BEGIN:VEVENT\n"
            f"UID:{uid}\n"
            f"DTSTAMP:{dtstamp}\n"
            f"{dtstart_line}\n"
            f"{dtend_line}\n"
            f"SUMMARY:{subj}\n"
            "END:VEVENT\n"
        )
        events.append(ev)

    out_path = args.output or (os.path.splitext(csv_path)[0] + ".ics")
    with open(out_path, "w", encoding="utf-8") as fo:
        fo.write("BEGIN:VCALENDAR\n")
        fo.write("VERSION:2.0\n")
        fo.write("CALSCALE:GREGORIAN\n")
        fo.write("PRODID:-//csv2ics//EN\n")
        for e in events:
            fo.write(e)
        fo.write("END:VCALENDAR\n")

    print("Готово. Файл создан:", out_path)
    if not ZoneInfo:
        print("Замечание: ваша версия Python не поддерживает zoneinfo (3.9+).")
        print("В этом случае времена будут записаны без TZID. Рекомендуется Python 3.9+.")

if __name__ == "__main__":
    main()
# Конвертация CSV в ICS (iCalendar)
# Читает CSV файл с колонками SUBJECT, START DATE, END DATE