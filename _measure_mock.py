# -*- coding: utf-8 -*-
"""Габариты макета и кегли под них — то, что нужно ui/chats.py.

Кегль раньше выводился из высоты букв через «cap = 0.714 кегля». Это
приближение: у заголовка оно давало 51 вместо 64, и текст выходил
заметно меньше макета. Здесь наоборот — сначала измеряются реальные
чернила в эталоне, потом подбирается кегль, при котором тот же текст
тем же шрифтом совпадает и по ширине, и по высоте.

Полосы измерения выводятся из шага рядов (84 макетных пикселя), а не
задаются руками: иначе они обрезают строки и меряют не то.
"""
import os
from PIL import Image, ImageFont

BASE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(BASE, '_shots', 'full_ref450.png')
SCENE_W, SCENE_H = 450.0, 920.0
REGULAR = os.path.join(BASE, 'assets', 'fonts', 'SF-Pro-Text-Regular.otf')
SEMIBOLD = os.path.join(BASE, 'assets', 'fonts', 'SF-Pro-Text-Semibold.otf')

# Эталон прозрачен вне заливки: композитим на фон макета, иначе
# прозрачные пиксели станут чёрными и попадут в «чернила».
raw = Image.open(REF)
flat = Image.new('RGB', raw.size, (255, 251, 247))
flat.paste(raw, (0, 0), raw)
REF_IM = flat.convert('RGB')
SX, SY = REF_IM.size[0] / SCENE_W, REF_IM.size[1] / SCENE_H
PX = REF_IM.load()

# Геометрия макета (Face ID.svg, холст 408x874), переведённая в сцену.
MOCK_W, MOCK_H = 408.0, 874.0
FX, FY = SCENE_W / MOCK_W, SCENE_H / MOCK_H
ROW_STEP = 84 * FY                      # шаг ряда в сцене

# ВАЖНО: ink() считает Y сверху вниз (номер строки пикселя), а позиции
# вёрстки нужны снизу вверх. Поэтому полосы задаём сверху (y_макета *
# FY), а для вёрстки печатаем (874 - y_макета) * FY.
NAME_TOP_1 = 196.21 * FY                # базовая линия имени ряда 1 сверху
PREVIEW_TOP_1 = 229.97 * FY
TIME_TOP_1 = 195.27 * FY
AVATAR_TOP_1 = 212.0 * FY               # центр аватара ряда 1 сверху
ROW_BOTTOM_1 = (MOCK_H - 254.5) * FY      # низ ряда 1 (по разделителю)


def ink(box, test=None):
    """Габариты пикселей, подходящих под условие (условие по умолчанию —
    чёрное: текст и чёрные значки)."""
    x0, y0, x1, y1 = box
    test = test or (lambda r, g, b: r + g + b < 420)
    xs, ys = [], []
    for y in range(int(y0 * SY), int(y1 * SY)):
        for x in range(int(x0 * SX), int(x1 * SX)):
            if test(*PX[x, y]):
                xs.append(x / SX)
                ys.append(y / SY)
    if not xs:
        return None
    return (round(min(xs), 1), round(min(ys), 1),
            round(max(xs), 1), round(max(ys), 1))


def fit(text, width, height, font_path, label, lo=8, hi=90):
    """Кегль, при котором текст даёт макетовую ширину и высоту букв.

    Перебираем кегли и берём тот, где расхождение по ширине и высоте
    минимально одновременно: так результат не зависит от того, какая из
    двух мер оказалась точнее.
    """
    best = None
    for size in range(lo, hi):
        left, top, right, bottom = ImageFont.truetype(font_path,
                                                       size).getbbox(text)
        w, h = right - left, bottom - top
        error = abs(w - width) + abs(h - height) * 1.5
        if best is None or error < best[0]:
            best = (error, size, w, h)
    error, size, w, h = best
    print('   %-12s %-16s макет %5.1f x %4.1f  ->  кегль %2d  '
          'даёт %5.1f x %4.1f  (ошибка %.1f)'
          % (label, text, width, height, size, w, h, error))
    return size


print('# Числа из Face ID.svg, переведённые в сцену %gx%g' % (SCENE_W, SCENE_H))
print('#   x = x_макета * %.5f,  y = (874 - y_макета) * %.5f' % (FX, FY))
print('# шаг ряда %.1f, низ ряда 1 = %.1f' % (ROW_STEP, ROW_BOTTOM_1))
print()
print('--- КЕГЛИ (подобраны по чернилам макета) ---')

# ВНИМАНИЕ: поиск тёмного в зоне заголовка цепляет артефакт рендера —
# два чёрных прямоугольника 10x49 над буквами (x 25..34 и 56..65, y 89..100).
# Настоящие буквы начинаются ниже: высота их 47 при кегле 64 (_letterbox.py).
# Поэтому здесь меряется только полоса букв.
title = ink((10, 101, 250, 140))
print('заголовок: макет x %.1f..%.1f  y %.1f..%.1f'
      % (title[0], title[2], title[1], title[3]))
TITLE_SIZE = fit('Чаты', title[2] - title[0], title[3] - title[1],
                 SEMIBOLD, 'заголовок')
print()

name = ink((95, NAME_TOP_1 - 22, 300, NAME_TOP_1 + 4))
print('имя ряда 1: макет x %.1f..%.1f  y %.1f..%.1f'
      % (name[0], name[2], name[1], name[3]))
NAME_SIZE = fit('Иван Иванов', name[2] - name[0], name[3] - name[1],
                SEMIBOLD, 'имя')
print()

prev = ink((95, PREVIEW_TOP_1 - 22, 330, PREVIEW_TOP_1 + 8))
print('превью ряда 1: макет x %.1f..%.1f  y %.1f..%.1f'
      % (prev[0], prev[2], prev[1], prev[3]))
PREVIEW_SIZE = fit('Hello, Vinograd!', prev[2] - prev[0], prev[3] - prev[1],
                   REGULAR, 'превью')
print()

stamp = ink((330, TIME_TOP_1 - 22, 440, TIME_TOP_1 + 4))
print('время ряда 1: макет x %.1f..%.1f  y %.1f..%.1f'
      % (stamp[0], stamp[2], stamp[1], stamp[3]))
TIME_SIZE = fit('19:36', stamp[2] - stamp[0], stamp[3] - stamp[1],
                REGULAR, 'время')
print()

# инициалы — светлые пиксели внутри круга аватара
initials = ink((28, AVATAR_TOP_1 - 24, 64, AVATAR_TOP_1 + 24),
               lambda r, g, b: r > 240 and g > 238 and b > 245)
print('инициалы: макет x %.1f..%.1f  y %.1f..%.1f (центр аватара y %.1f)'
      % (initials[0], initials[2], initials[1], initials[3],
         AVATAR_TOP_1))
INITIALS_SIZE = fit('ИИ', initials[2] - initials[0],
                    initials[3] - initials[1], REGULAR, 'инициалы')
INITIALS_CENTER = ((initials[0] + initials[2]) / 2,
                   (initials[1] + initials[3]) / 2)
print('   центр инициалов: x %.1f  y %.1f' % INITIALS_CENTER)
print()

for label, band in (('Поиск', (40, 860, 125, 900)),
                    ('Чаты', (135, 860, 215, 900)),
                    ('Группы', (225, 860, 312, 900)),
                    ('Настройки', (320, 860, 425, 900))):
    box = ink(band)
    if not box:
        print('   подпись %-10s не найдена' % label)
        continue
    print('подпись %-10s макет x %.1f..%.1f  y %.1f..%.1f'
          % (label, box[0], box[2], box[1], box[3]))
    fit(label, box[2] - box[0], box[3] - box[1], REGULAR, '  подпись')

print()
print('--- ПОЗИЦИИ В СЦЕНЕ (y снизу) ---')
print('базовая линия имени   %.1f' % ((MOCK_H - NAME_TOP_1 / FY) * FY))
print('базовая линия превью  %.1f' % ((MOCK_H - PREVIEW_TOP_1 / FY) * FY))
print('базовая линия времени %.1f' % ((MOCK_H - TIME_TOP_1 / FY) * FY))
print('низ ряда 1            %.1f  (отсюда и считаются смещения в ряду)' % ROW_BOTTOM_1)
print('шаг ряда              %.1f' % ROW_STEP)
print('имя  x %.1f' % name[0])
print('превью x %.1f' % prev[0])
print('время правый край %.1f' % stamp[2])
print('инициалы: центр x %.1f, размер кегля %d' % (INITIALS_CENTER[0],
                                                 INITIALS_SIZE))

print()
print('--- ЗНАЧКИ (центрированные прямоугольники из макета) ---')
ICONS = (
    ('закрепление 1', 367, 206, 30, 30),
    ('закрепление 2', 336, 292, 30, 30),
    ('закрепление 3', 367, 374, 30, 30),
    ('счётчик 3', 369, 294, 25, 25),
    ('счётчик 12', 365, 630, 29, 25),
    ('галочка серая 1', 315, 347, 28, 20),
    ('галочка фиолет.', 309, 429, 34, 25),
    ('галочка серая 2', 315, 683, 28, 20),
)
ROW_BOTTOMS = [(MOCK_H - (254.5 + 84 * i)) * FY for i in range(7)]
for name_icon, x, y, w, h in ICONS:
    top = y * FY                                   # верх в сцене (y снизу)
    bottom = (MOCK_H - y) * FY
    row = 1 + min(range(7), key=lambda i: abs(ROW_BOTTOMS[i] - bottom))
    base = ROW_BOTTOMS[row - 1]
    print('   %-16s макет %2dx%-2d в (%d, %d)  ->  pos (%.1f, %.1f) '
          'размер %.1f x %.1f   ряд %d'
          % (name_icon, w, h, x, y, x * FX, bottom - base, w * FX, h * FY,
             row))

print()
print('--- РАЗДЕЛИТЕЛИ ---')
for x1, y in ((86, 254.5), (86, 338.5), (4, 420.5), (86, 506.5), (80, 590.5),
              (86, 674.5), (86, 758.5)):
    print('   макет y %.1f от x %d  ->  сцена y %.1f от x %.1f'
          % (y, x1, (MOCK_H - y) * FY, x1 * FX))

print()
print('--- НИЖНЯЯ ПАНЕЛЬ ---')
print('плашка макет 360x60 в (24, 780) -> x %.1f, y %.1f, размер %.1f x %.1f, '
      'радиус %.1f' % (24 * FX, (MOCK_H - 840) * FY, 360 * FX, 60 * FY, 30 * FY))
for name_icon, x, y, w, h in (('иконка Чаты', 139, 785, 38, 38),
                              ('иконка Группы', 226, 782, 44, 44),
                              ('иконка Настройки', 322, 787, 34, 34)):
    print('   %-16s макет %dx%d в (%d, %d) -> x %.1f, y %.1f, размер %.1f x %.1f'
          % (name_icon, w, h, x, y, x * FX, (MOCK_H - y - h) * FY,
             w * FX, h * FY))
print('   лупа: круг макет (72, 800) r 8 -> центр (%.1f, %.1f) r %.1f'
      % (72 * FX, (MOCK_H - 800) * FY, 8 * FX))
print('   ручка лупы: (66, 806.1) -> (59.1, 813) = (%.1f, %.1f) -> (%.1f, %.1f)'
      % (66 * FX, (MOCK_H - 806.1) * FY, 59.1 * FX, (MOCK_H - 813) * FY))

print()
print('--- ШАПКА ---')
print('кнопка «+»: макет круг (357.5, 114.5) r 29.5 -> x %.1f, y %.1f, '
      'размер %.1f' % ((357.5 - 29.5) * FX, (MOCK_H - 144) * FY, 59 * FX))
print('плюс: макет x 344.5..371.5 на y 114.5 -> сцена x %.1f..%.1f на y %.1f'
      % (344.5 * FX, 371.5 * FX, (MOCK_H - 114.5) * FY))
print('плюс вертикаль: макет x 358, y 99..129 -> сцена x %.1f, y %.1f..%.1f'
      % (358 * FX, (MOCK_H - 129) * FY, (MOCK_H - 99) * FY))