"""Листы миниатюр с подписями (только чтение архива).

python contact_sheet.py "<папка>" --out work/sheets/имя [--cols 6] [--size 260] [--per-sheet 60] [--recursive]
python contact_sheet.py --list files.txt --out work/sheets/имя     # свой список путей, по одному в строке
Выход: имя-01.jpg, имя-02.jpg, ...
"""
import argparse
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import IMAGE_EXT, walk, exif_info, date_from_name, open_upright  # noqa: E402


def font(size):
    for f in ('arial.ttf', 'DejaVuSans.ttf', '/System/Library/Fonts/Supplemental/Arial.ttf',
              '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'):
        try:
            return ImageFont.truetype(f, size)
        except Exception:
            pass
    return ImageFont.load_default()


def label(p):
    d = exif_info(p)[0] or date_from_name(os.path.basename(p))
    return os.path.basename(p), d


def sheet(paths, out, cols, size):
    rows = (len(paths) + cols - 1) // cols
    lh = max(14, size // 14)
    f = font(lh - 2)
    W, H = cols * size, rows * (size + 2 * lh)
    canvas = Image.new('RGB', (W, H), 'white')
    dr = ImageDraw.Draw(canvas)
    for i, p in enumerate(paths):
        x, y = (i % cols) * size, (i // cols) * (size + 2 * lh)
        try:
            im = open_upright(p)
            im.thumbnail((size - 4, size - 4))
            canvas.paste(im, (x + (size - im.width) // 2, y + (size - im.height) // 2))
        except Exception as e:
            dr.text((x + 4, y + size // 2), f'не открылся: {e.__class__.__name__}', fill='red', font=f)
        n, d = label(p)
        dr.text((x + 3, y + size), n[:40], fill='black', font=f)
        dr.text((x + 3, y + size + lh), d or '(без даты)', fill='#555', font=f)
    canvas.save(out, quality=85)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('folder', nargs='?')
    ap.add_argument('--list')
    ap.add_argument('--out', required=True)
    ap.add_argument('--cols', type=int, default=6)
    ap.add_argument('--size', type=int, default=260)
    ap.add_argument('--per-sheet', type=int, default=60)
    ap.add_argument('--recursive', action='store_true')
    a = ap.parse_args()
    if a.list:
        paths = [l.strip() for l in open(a.list, encoding='utf-8-sig') if l.strip()]
    elif a.recursive:
        paths = list(walk(a.folder, IMAGE_EXT))
    else:
        paths = sorted(os.path.join(a.folder, n) for n in os.listdir(a.folder)
                       if os.path.splitext(n)[1].lower() in IMAGE_EXT)
    if not paths:
        sys.exit('нет снимков')
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    k = 0
    for k, i in enumerate(range(0, len(paths), a.per_sheet), 1):
        sheet(paths[i:i + a.per_sheet], f'{a.out}-{k:02d}.jpg', a.cols, a.size)
    print(f'{len(paths)} снимков → {k} лист(ов): {a.out}-01.jpg …')


if __name__ == '__main__':
    main()
