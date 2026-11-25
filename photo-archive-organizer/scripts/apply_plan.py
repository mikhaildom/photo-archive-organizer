"""Выполнение плана: папки, переносы, переименования, заметки. Журнал и откат.

python apply_plan.py plan.json --root "<архив>" --log work/журнал.txt          # проверка, ничего не меняет
python apply_plan.py plan.json --root "<архив>" --log work/журнал.txt --go     # выполнить
python apply_plan.py --undo work/журнал.txt --root "<архив>" [--go]            # откатить (сначала проверка)
Формат плана — references/plan-format.md.
"""
import argparse
import datetime
import json
import os
import shutil
import sys


def full(root, p):
    return os.path.abspath(p if os.path.isabs(p) else os.path.join(root, p))


def check(ops, root):
    """Симуляция плана: какие пути будут существовать. Возвращает список ошибок."""
    errs, created, removed, targets = [], set(), set(), set()

    def exists(p):
        return (p in created) or (os.path.exists(p) and p not in removed)

    for i, o in enumerate(ops, 1):
        op = o.get('op')
        if op in ('move', 'rename'):
            s, d = full(root, o['src']), full(root, o['dst'])
            if not exists(s):
                errs.append(f'{i}: нет источника {s}')
            if exists(d):
                errs.append(f'{i}: цель уже есть {d}')
            if not exists(os.path.dirname(d)):
                errs.append(f'{i}: нет папки назначения {os.path.dirname(d)}')
            if d in targets:
                errs.append(f'{i}: цель дважды в плане {d}')
            targets.add(d)
            removed.add(s); created.discard(s)
            created.add(d); removed.discard(d)
        elif op in ('mkdir', 'note'):
            p = full(root, o['path'])
            if exists(p):
                errs.append(f'{i}: уже есть {p}')
            if op == 'note' and not exists(os.path.dirname(p)):
                errs.append(f'{i}: нет папки {os.path.dirname(p)}')
            if op == 'note' and 'text' not in o:
                errs.append(f'{i}: у заметки нет text')
            created.add(p); removed.discard(p)
        else:
            errs.append(f'{i}: неизвестная операция {op!r}')
    return errs


def run(ops, root, log):
    os.makedirs(os.path.dirname(os.path.abspath(log)), exist_ok=True)
    with open(log, 'a', encoding='utf-8') as lf:
        for o in ops:
            op = o['op']
            t = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            if op in ('move', 'rename'):
                s, d = full(root, o['src']), full(root, o['dst'])
                shutil.move(s, d)
                assert os.path.exists(d), d
                lf.write(f'{t}\tmove\t{s}\t{d}\n')
            elif op == 'mkdir':
                p = full(root, o['path'])
                os.makedirs(p)
                lf.write(f'{t}\tmkdir\t{p}\t\n')
            elif op == 'note':
                p = full(root, o['path'])
                with open(p, 'x', encoding='utf-8-sig') as f:
                    f.write(o['text'])
                lf.write(f'{t}\tnote\t{p}\t\n')
            lf.flush()
            print('✓', op, o.get('src') or o.get('path'), '→', o.get('dst', ''))


def undo_ops(log):
    ops = []
    for line in open(log, encoding='utf-8'):
        parts = line.rstrip('\n').split('\t')
        if len(parts) < 4 or parts[1] not in ('move', 'mkdir', 'note'):
            continue
        _, op, a, b = parts[:4]
        if op == 'move':
            ops.append({'op': 'move', 'src': b, 'dst': a})
        elif op == 'mkdir':
            ops.append({'op': 'rmdir', 'path': a})
        elif op == 'note':
            ops.append({'op': 'move', 'src': a, 'dst': a + '.undone'})
    return list(reversed(ops))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('plan', nargs='?')
    ap.add_argument('--root', required=True)
    ap.add_argument('--log')
    ap.add_argument('--undo')
    ap.add_argument('--go', action='store_true')
    a = ap.parse_args()

    if a.undo:
        ops = undo_ops(a.undo)
        print(f'откат, операций: {len(ops)}')
        for o in ops:
            print(' ', o)
        if not a.go:
            print('Проверка. Для отката добавь --go.')
            return
        log = a.undo + '.undo.txt'
        for o in ops:
            if o['op'] == 'rmdir':
                if os.path.isdir(o['path']) and not os.listdir(o['path']):
                    os.rmdir(o['path'])
                else:
                    print('папка не пуста, оставлена:', o['path'])
            elif os.path.exists(o['src']) and not os.path.exists(o['dst']):
                run([o], a.root, log)
            else:
                print('пропущено (нет источника или цель занята):', o['src'])
        return

    if not a.plan or not a.log:
        sys.exit('нужны plan и --log')
    plan = json.load(open(a.plan, encoding='utf-8-sig'))
    ops = plan['ops'] if isinstance(plan, dict) else plan
    errs = check(ops, a.root)
    if errs:
        print('ПЛАН НЕ ВЫПОЛНЕН, ошибки:')
        print('\n'.join(errs))
        sys.exit(1)
    print(f'план в порядке, операций: {len(ops)}')
    if not a.go:
        print('Это проверка. Чтобы выполнить, добавь --go.')
        return
    with open(a.log, 'a', encoding='utf-8') as lf:
        lf.write(f'# {datetime.datetime.now():%Y-%m-%d %H:%M} {plan.get("title", a.plan) if isinstance(plan, dict) else a.plan}\n')
    run(ops, a.root, a.log)
    print('готово, журнал:', a.log)


if __name__ == '__main__':
    main()
