"""Опись архива (только чтение): дата из EXIF, дата из имени, камера, размер, подозрительные даты.

python inventory.py "<папка>" --out work/inventory.csv [--hash]
"""
import argparse
import collections
import csv
import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import IMAGE_EXT, VIDEO_EXT, walk, date_from_name, exif_info  # noqa: E402


def sha1(path):
    h = hashlib.sha1()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('root')
    ap.add_argument('--out', required=True)
    ap.add_argument('--hash', action='store_true', help='посчитать sha1 (медленнее)')
    ap.add_argument('--same-stamp', type=int, default=20,
                    help='одна и та же метка времени у стольких файлов = часы не выставлены')
    a = ap.parse_args()

    rows = []
    for p in walk(a.root, IMAGE_EXT | VIDEO_EXT):
        ext = os.path.splitext(p)[1].lower()
        exif, cam, gps = exif_info(p) if ext in IMAGE_EXT else ('', '', False)
        rows.append(dict(
            path=os.path.relpath(p, a.root), folder=os.path.relpath(os.path.dirname(p), a.root),
            kind='video' if ext in VIDEO_EXT else 'image', size=os.path.getsize(p),
            exif_date=exif, name_date=date_from_name(os.path.basename(p)), camera=cam,
            gps='yes' if gps else '', sha1=sha1(p) if a.hash else ''))

    stamps = collections.Counter(r['exif_date'] for r in rows if r['exif_date'])
    bad = {s for s, n in stamps.items() if n >= a.same_stamp}
    for r in rows:
        flags = []
        if r['exif_date'] in bad:
            flags.append('suspicious_date')
        if r['exif_date'] and r['name_date'] and r['exif_date'][:10] != r['name_date'][:10]:
            flags.append('exif_name_differ')
        r['flags'] = ' '.join(flags)

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ['path'])
        w.writeheader()
        w.writerows(rows)

    print(f'файлов: {len(rows)} (фото {sum(r["kind"] == "image" for r in rows)}, '
          f'видео {sum(r["kind"] == "video" for r in rows)})')
    years = collections.Counter((r['exif_date'] or r['name_date'])[:4] or '????'
                                for r in rows if 'suspicious_date' not in r['flags'])
    print('по годам:', ', '.join(f'{y}: {n}' for y, n in sorted(years.items())))
    cams = collections.Counter(r['camera'] or '(нет)' for r in rows if r['kind'] == 'image')
    print('камеры:', '; '.join(f'{c}: {n}' for c, n in cams.most_common(10)))
    for s in sorted(bad):
        print(f'подозрительная дата {s} — у {stamps[s]} файлов (часы камеры не выставлены?)')
    print('опись:', a.out)


if __name__ == '__main__':
    main()
