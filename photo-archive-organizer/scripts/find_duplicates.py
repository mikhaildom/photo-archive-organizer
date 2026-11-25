"""Поиск дублей (только чтение): точные (sha1) и та же картинка в другом размере/повороте/сжатии.

python find_duplicates.py "<папка>" [--also "<другая папка>"] --out work/dups.csv [--threshold 0.97]
Серии похожих кадров одной сцены часто дают 0.90–0.96 — это НЕ дубли, поэтому порог высокий.
"""
import argparse
import collections
import csv
import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import IMAGE_EXT, walk, open_upright  # noqa: E402

try:
    import numpy as np
except ImportError:
    np = None


def sha1(path):
    h = hashlib.sha1()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def vec(im, w=32, h=24):
    g = im.convert('L').resize((w, h))
    v = np.asarray(g, dtype=np.float32).ravel()
    v -= v.mean()
    n = np.linalg.norm(v)
    return v / n if n else v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('root')
    ap.add_argument('--also', action='append', default=[])
    ap.add_argument('--out', required=True)
    ap.add_argument('--threshold', type=float, default=0.97)
    a = ap.parse_args()

    paths = [p for r in [a.root] + a.also for p in walk(r, IMAGE_EXT)]
    print('снимков:', len(paths))
    out = []

    by_size = collections.defaultdict(list)
    for p in paths:
        by_size[os.path.getsize(p)].append(p)
    by_hash = collections.defaultdict(list)
    for group in by_size.values():
        if len(group) > 1:
            for p in group:
                by_hash[sha1(p)].append(p)
    exact = set()
    for h, group in by_hash.items():
        if len(group) > 1:
            # оставить файл с самым коротким именем (обычно оригинал, а не «(2)»/«копия»)
            group.sort(key=lambda x: (len(os.path.basename(x)), x))
            for p in group[1:]:
                out.append(dict(kind='exact', keep=group[0], copy=p, score='1.000', note='байт в байт'))
                exact.add(p)

    if np is None:
        print('numpy не установлен — визуальные дубли пропущены (pip install numpy)')
    else:
        items = []
        for p in paths:
            if p in exact:
                continue
            try:
                im = open_upright(p)
            except Exception:
                continue
            base = im.copy()
            base.thumbnail((256, 256))
            # ориентация-независимое сравнение: 4 поворота
            rots = [vec(base.rotate(r, expand=True)) for r in (0, 90, 180, 270)]
            items.append((p, im.width * im.height, rots))
        flat = np.stack([it[2][0] for it in items]) if items else None
        for i, (p, area, rots) in enumerate(items):
            best = None
            for r, v in enumerate(rots):
                sims = flat[i + 1:] @ v
                for j in np.nonzero(sims >= a.threshold)[0]:
                    q = items[i + 1 + j]
                    s = float(sims[j])
                    if best is None or s > best[1]:
                        best = (q, s, r * 90)
            if best:
                q, s, rot = best
                keep, copy = (p, q[0]) if area >= q[1] else (q[0], p)
                note = 'та же картинка' + (f', повёрнута на {rot}°' if rot else '') + (', другой размер' if area != q[1] else '')
                out.append(dict(kind='same_picture', keep=keep, copy=copy, score=f'{s:.3f}', note=note))

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=['kind', 'keep', 'copy', 'score', 'note'])
        w.writeheader()
        w.writerows(out)
    c = collections.Counter(r['kind'] for r in out)
    print(f'точных дублей: {c["exact"]}, та же картинка: {c["same_picture"]} → {a.out}')
    print('Ничего не удалено. Покажи пары владельцу (contact_sheet.py --list) и получи «да».')


if __name__ == '__main__':
    main()
