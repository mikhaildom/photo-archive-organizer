"""Отправить файлы в Корзину (не удаляет навсегда). Только после «да» владельца на этот список.

python to_trash.py list.txt --log work/корзина.txt          # проверка
python to_trash.py list.txt --log work/корзина.txt --go     # в Корзину
list.txt — по одному пути в строке. Можно передать и dups.csv (берётся колонка copy).
"""
import argparse
import csv
import datetime
import os
import subprocess
import sys


def read_list(path):
    if path.lower().endswith('.csv'):
        with open(path, encoding='utf-8-sig') as f:
            return [r['copy'] for r in csv.DictReader(f) if r.get('copy')]
    return [l.strip() for l in open(path, encoding='utf-8-sig') if l.strip() and not l.startswith('#')]


def trash(p):
    try:
        from send2trash import send2trash
        send2trash(p)
        return
    except ImportError:
        pass
    if os.name == 'nt':
        kind = 'DeleteDirectory' if os.path.isdir(p) else 'DeleteFile'
        ps = ("Add-Type -AssemblyName Microsoft.VisualBasic; "
              f"[Microsoft.VisualBasic.FileIO.FileSystem]::{kind}($env:TRASH_PATH,'OnlyErrorDialogs','SendToRecycleBin')")
        subprocess.run(['powershell', '-NoProfile', '-Command', ps], check=True,
                       env={**os.environ, 'TRASH_PATH': p})
        return
    sys.exit('Нужен send2trash: pip install send2trash')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('list')
    ap.add_argument('--log', required=True)
    ap.add_argument('--go', action='store_true')
    a = ap.parse_args()
    paths = read_list(a.list)
    missing = [p for p in paths if not os.path.exists(p)]
    if missing:
        print('Нет таких файлов:', *missing, sep='\n  ')
        sys.exit(1)
    size = sum(os.path.getsize(p) for p in paths if os.path.isfile(p))
    print(f'{len(paths)} шт., {size / 2**20:.1f} МБ → Корзина')
    if not a.go:
        print('Проверка. Чтобы отправить в Корзину, добавь --go.')
        return
    os.makedirs(os.path.dirname(os.path.abspath(a.log)), exist_ok=True)
    with open(a.log, 'a', encoding='utf-8') as lf:
        for p in paths:
            trash(p)
            assert not os.path.exists(p), p
            lf.write(f'{datetime.datetime.now():%Y-%m-%d %H:%M:%S}\ttrash\t{p}\n')
            lf.flush()
    print('готово, журнал:', a.log, '— вернуть можно из Корзины')


if __name__ == '__main__':
    main()
