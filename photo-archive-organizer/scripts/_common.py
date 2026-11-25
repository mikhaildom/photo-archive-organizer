"""Общие функции: поиск снимков, чтение дат, открытие картинок. Только чтение."""
import os
import re

from PIL import Image, ImageOps

try:  # фото iPhone (.heic) — по желанию
    from pillow_heif import register_heif_opener
    register_heif_opener()
    HEIF = True
except Exception:
    HEIF = False

IMAGE_EXT = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tif', '.tiff', '.webp'}
if HEIF:
    IMAGE_EXT |= {'.heic', '.heif'}
VIDEO_EXT = {'.mp4', '.mov', '.avi', '.3gp', '.mkv', '.mts', '.m2ts', '.wmv', '.mpg', '.mpeg'}

NAME_DATE = [
    re.compile(r'(?<!\d)(19[89]\d|20[0-4]\d)[-_.]?(0[1-9]|1[0-2])[-_.]?(0[1-9]|[12]\d|3[01])(?:[-_ .T]?([01]\d|2[0-3])[-_.:]?([0-5]\d)[-_.:]?([0-5]\d))?'),
]


def walk(root, exts):
    for d, dirs, files in os.walk(root):
        dirs.sort()
        for n in sorted(files):
            if os.path.splitext(n)[1].lower() in exts:
                yield os.path.join(d, n)


def date_from_name(name):
    for rx in NAME_DATE:
        m = rx.search(name)
        if m:
            y, mo, da, hh, mi, ss = m.groups()
            s = f'{y}-{mo}-{da}'
            if hh:
                s += f' {hh}:{mi}:{ss}'
            return s
    return ''


def exif_info(path):
    """-> (DateTimeOriginal или DateTime как 'ГГГГ-ММ-ДД чч:мм:сс', камера, gps есть?)"""
    try:
        with Image.open(path) as im:
            ex = im.getexif()
            sub = ex.get_ifd(0x8769)
            v = sub.get(36867) or ex.get(306) or ''
            cam = ' '.join(str(x).strip() for x in (ex.get(271), ex.get(272)) if x).strip()
            gps = bool(ex.get_ifd(0x8825))
    except Exception:
        return '', '', False
    v = str(v).strip().replace('\x00', '')
    if re.match(r'\d{4}:\d\d:\d\d \d\d:\d\d:\d\d', v):
        v = v[:10].replace(':', '-') + v[10:19]
    elif v:
        v = ''
    if v.startswith('0000'):
        v = ''
    return v, cam, gps


def open_upright(path):
    im = Image.open(path)
    im = ImageOps.exif_transpose(im)
    return im.convert('RGB')
