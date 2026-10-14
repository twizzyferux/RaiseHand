# -*- coding: utf-8 -*-
"""Кегли макетов — из самих макетов, а не «на глаз».

В папке «проект/проект экран» лежат выгрузки из Figma: отдельный PNG
на каждую строку текста (в имени файла — сам текст) и Screen.png на
весь экран. Экспорт 4x: 1608x3496 — это холст 402x874.

ЧТО НЕ РАБОТАЕТ
---------------
Screen.png бесполезен: это пустая рамка Figma, элементов в ней нет.
Проверено — непрозрачные пиксели есть (фон), а самого дизайна нет.
Поэтому меряем отдельные выгрузки.

Как считаем кегль
-----------------
Сначала снимаем «чернила» — пиксели, отличные от фона, причём
прозрачные не в счёт: у выгрузок углы прозрачные, и если считать их
не фоном, в чернила попадала вся кнопка целиком.

Дальше два независимых способа получить кегль, и они должны сойтись:

  1. ПО ВЫСОТЕ первой строки чернил;
  2. ПО ШИРИНЕ тех же чернил — строку-то мы знаем точно, из имени файла.

Если способы расходятся больше чем на 12%, значит первая строка блока —
не та, что в имени, и кегль брать нельзя: такие строки помечены
СОМНЕНИЕ и в правку не идут.

Запуск:  .venv312\\Scripts\\python.exe _mock_type.py
"""
import os
import re

from PIL import Image, ImageChops, ImageFont

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(BASE, 'проект', 'проект экран')
FONTS = os.path.join(BASE, 'assets', 'fonts')
EXPORT = 4.0                     # выгрузка Figma вчетверо больше холста
MOCK_W, SCENE_W = 402.0, 450.0   # холст выгрузки и холст сцены приложения
REF = 200                        # кегль, в котором меряем эталон
CREAM = (255, 251, 247)

FACES = {
    'Regular': os.path.join(FONTS, 'SF-Pro-Text-Regular.otf'),
    'Semibold': os.path.join(FONTS, 'SF-Pro-Text-Semibold.otf'),
}
_cache = {}

# Выгрузки, которые не являются текстом: рамки, аватары, иконки,
# разделители и прочее оформление.
SKIP = ('Screen.png', 'интерфейс.png', 'пузырики.png', 'точки текста.png',
        'линия 1.png', 'Rectangle', 'image-no-bg', 'аватарка',
        'raisehand-wordmark', 'start-icon')


def face(name, size):
    key = (name, size)
    if key not in _cache:
        _cache[key] = ImageFont.truetype(FACES[name], size)
    return _cache[key]


def clean(text):
    """Имя файла -> текст: убираем «Кнопка _…_»."""
    text = re.sub(r'^Кнопка\s*_', '', text)
    return text.replace('_', ' ').strip()


def ink_mask(path):
    """Маска чернил: непрозрачные пиксели, отличные от фона."""
    raw = Image.open(path).convert('RGBA')
    flat = Image.new('RGB', raw.size, CREAM)
    flat.paste(raw, (0, 0), raw)
    colors = flat.getcolors(maxcolors=raw.size[0] * raw.size[1])
    background = max(colors)[1] if colors else CREAM
    solid = Image.new('RGB', raw.size, background)
    diff = ImageChops.difference(flat, solid).convert('L')
    diff = diff.point(lambda v: 255 if v > 30 else 0)
    alpha = raw.getchannel('A').point(lambda v: 255 if v > 16 else 0)
    return ImageChops.multiply(diff, alpha), raw.size


def first_line(mask):
    """Габариты первой непрерывной строки чернил: (x0, y0, x1, y1)."""
    box = mask.getbbox()
    if box is None:
        return None
    x0, y0, x1, y1 = box
    top = y0
    while top < y1 and mask.crop((x0, top, x1, top + 1)).getbbox() is None:
        top += 1
    bottom = top
    while bottom + 1 < y1 and mask.crop((x0, bottom + 1, x1,
                                         bottom + 2)).getbbox() is not None:
        bottom += 1
    line = mask.crop((x0, top, x1, bottom + 1)).getbbox()
    return (x0 + line[0], top, x0 + line[2], top + line[3])


def text_ink(text, face_name):
    """Чернила текста в эталонном кегле: (ширина, высота)."""
    box = face(face_name, REF).getbbox(text)
    return box[2] - box[0], box[3] - box[1]


def measure(path, text):
    """Кегль по макету: (по высоте, по ширине, расхождение, начертание)."""
    mask, _size = ink_mask(path)
    line = first_line(mask)
    if line is None:
        return None
    x0, y0, x1, y1 = line
    ink_h = (y1 - y0) / EXPORT
    ink_w = (x1 - x0) / EXPORT

    by_height, chosen = None, 'Semibold'
    for name in ('Regular', 'Semibold'):
        ref_w, ref_h = text_ink(text, name)
        if not ref_h:
            continue
        value = ink_h * REF / ref_h
        if by_height is None or value < by_height:
            by_height, chosen = value, name

    ref_w, _ref_h = text_ink(text, chosen)
    by_width = ink_w * REF / ref_w if ref_w else 0.0
    delta = abs(by_width - by_height) / by_height * 100 if by_height else 100
    return by_height, by_width, delta, chosen


def main():
    print('=' * 96)
    print('Кегли макетов. Выгрузка 4x, холст 402x874; сцена приложения 450x920')
    print('=' * 96)
    trusted = []
    for folder in sorted(os.listdir(ROOT)):
        path = os.path.join(ROOT, folder)
        if not os.path.isdir(path):
            continue
        print('\n=== %s ===' % folder)
        for name in sorted(os.listdir(path)):
            if not name.lower().endswith('.png'):
                continue
            if any(mark in name for mark in SKIP):
                continue
            text = clean(os.path.splitext(name)[0])
            if len(text) < 3:
                continue
            result = measure(os.path.join(path, name), text)
            if result is None:
                continue
            by_h, by_w, delta, face_name = result
            scene = by_h * SCENE_W / MOCK_W
            ok = delta <= 12
            if ok:
                trusted.append((folder, text, face_name, scene))
            print('  %-42s %-9s макет=%5.1f сцена=%5.1f  высота/ширина %+5.0f%% %s'
                  % (text[:42], face_name, by_h, scene, delta,
                     'OK' if ok else 'СОМНЕНИЕ'))

    print('\n' + '=' * 96)
    print('ГОДОВЫЕ КЕГЛИ (высота и ширина сошлись)')
    print('=' * 96)
    for folder, text, face_name, scene in trusted:
        print('  %-14s %-40s %-9s %5.1f' % (folder, text[:40], face_name, scene))


if __name__ == '__main__':
    main()