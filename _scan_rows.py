# -*- coding: utf-8 -*-
"""Сверка экрана чатов с макетом: шапка, ряды, нижняя панель.

Все координаты — снизу вверх, как в вёрстке (y = 0 — низ сцены 450x920).
Снимок окна в сцену переводится по масштабу и переворотом по Y: строки
пикселей идут сверху вниз, а сцена растёт снизу вверх, поэтому без
переворота зоны попадали в пустое место экрана и замер ничего не находил.

Зоны рядов берутся из геометрии Face ID.svg: аватар первого ряда
y 178..246, шаг 84, низ ряда 1 по разделителю 254.5. Переведённые в сцену
снизу: низ ряда 1 = 652.1, высота ячейки 88.4.
"""
import glob
import os
from PIL import Image

BASE = os.path.dirname(os.path.abspath(__file__))
shots = sorted(glob.glob(os.path.join(BASE, '_shots', 'chats_list*.png')))
MINE = shots[-1]
REF = os.path.join(BASE, '_shots', 'full_ref450.png')
CREAM = (255, 251, 247)

SCENE_W, SCENE_H = 450.0, 920.0
MOCK_W, MOCK_H = 408.0, 874.0
FX, FY = SCENE_W / MOCK_W, SCENE_H / MOCK_H

ROW_BOTTOM_1 = (MOCK_H - 254.5) * FY      # 652.1 — низ ряда 1
ROW_CELL = 84 * FY                         # 88.4
NAME_BASELINE_1 = (MOCK_H - 196.21) * FY   # 713.5 — базовая линия имени
PANEL_Y = (MOCK_H - 840) * FY              # 35.8 — низ плашки


class Shot:
    """Картинка в координатах сцены снизу вверх."""

    def __init__(self, path, background=None):
        im = Image.open(path)
        if background is not None:
            base = Image.new('RGB', im.size, background)
            base.paste(im, (0, 0), im)
            im = base
        self.im = im.convert('RGB')
        scale = min(self.im.size[0] / SCENE_W, self.im.size[1] / SCENE_H)
        self.scale = scale
        self.ox = (self.im.size[0] - SCENE_W * scale) / 2
        self.oy = (self.im.size[1] - SCENE_H * scale) / 2
        self.px = self.im.load()

    def color(self, x, y):
        return self.px[min(max(int(round(self.ox + x * self.scale)), 0),
                            self.im.size[0] - 1),
                        min(max(int(round(self.im.size[1] - self.oy
                                           - y * self.scale)), 0),
                            self.im.size[1] - 1)]

    def dark(self, x, y):
        return sum(self.color(x, y)) < 480

    def grey(self, x, y):
        r, g, b = self.color(x, y)
        return abs(r - g) < 16 and abs(g - b) < 16 and 130 < r < 225

    def box(self, x0, y0, x1, y1, test=None):
        test = test or self.dark
        xs, ys = [], []
        for yi in range(int(y0), int(y1)):
            for xi in range(int(x0), int(x1)):
                if test(xi, yi):
                    xs.append(xi)
                    ys.append(yi)
        if not xs:
            return None
        return (min(xs), max(xs), min(ys), max(ys))

    def spans(self, x0, x1, y0, y1, gap=3, test=None):
        """Пятна по X — отдельные значки в ряду."""
        test = test or self.dark
        active, out = [], []
        for xi in range(int(x0), int(x1)):
            if any(test(xi, yi) for yi in range(int(y0), int(y1))):
                active.append(xi)
            elif active:
                out.append((active[0], active[-1]))
                active = []
        if active:
            out.append((active[0], active[-1]))
        merged = []
        for span in out:
            if merged and span[0] - merged[-1][1] <= gap:
                merged[-1] = (merged[-1][0], span[1])
            else:
                merged.append(span)
        return merged


def fmt(box):
    if box is None:
        return 'пусто'
    return ('x %6.1f..%6.1f (%5.1f) y %6.1f..%6.1f (%5.1f)'
            % (box[0], box[1], box[1] - box[0] + 1,
               box[2], box[3], box[3] - box[2] + 1))


def report(title, zones, both):
    print(title)
    for zone, x0, y0, x1, y1 in zones:
        line = '   %-18s' % zone
        for label, shot in both:
            line += '  %s %s' % (label, fmt(shot.box(x0, y0, x1, y1)))
        print(line)
    print()


mine = Shot(MINE)
ref = Shot(REF, background=CREAM)
both = (('мой  ', mine), ('макет', ref))

print('снимок %s (%dx%d)' % (os.path.basename(MINE), *mine.im.size))
print('сцена снизу вверх: масштаб %.4f' % mine.scale)
print('низ ряда 1 = %.1f, ячейка = %.1f, плашка снизу = %.1f'
      % (ROW_BOTTOM_1, ROW_CELL, PANEL_Y))
print()

report('ШАПКА', (
    ('заголовок', 10, 740, 300, 880),
    ('кнопка «+»', 340, 740, 440, 880),
), both)

for number in (1, 2, 3):
    bottom = ROW_BOTTOM_1 - (number - 1) * ROW_CELL
    top = bottom + ROW_CELL
    name_baseline = NAME_BASELINE_1 - (number - 1) * ROW_CELL
    report('РЯД %d (ячейка y %.1f..%.1f)' % (number, bottom, top), (
        ('аватар', 0, bottom, 100, top),
        ('имя', 96, name_baseline - 30, 380, name_baseline + 5),
        ('превью', 96, bottom, 380, name_baseline - 8),
        ('время', 380, name_baseline - 30, 450, name_baseline + 5),
        ('значки', 300, bottom, 450, top),
    ), both)

report('НИЖНЯЯ ПАНЕЛЬ', (
    ('плашка', 0, PANEL_Y - 5, 450, PANEL_Y + 70),
    ('иконка Поиск', 40, PANEL_Y + 25, 125, PANEL_Y + 70),
    ('иконка Чаты', 130, PANEL_Y + 25, 220, PANEL_Y + 70),
    ('иконка Группы', 220, PANEL_Y + 25, 315, PANEL_Y + 70),
    ('иконка Настройки', 315, PANEL_Y + 25, 435, PANEL_Y + 70),
    ('подпись Поиск', 40, PANEL_Y, 125, PANEL_Y + 25),
    ('подпись Чаты', 130, PANEL_Y, 220, PANEL_Y + 25),
    ('подпись Группы', 220, PANEL_Y, 315, PANEL_Y + 25),
    ('подпись Настройки', 315, PANEL_Y, 435, PANEL_Y + 25),
), both)

print('РАЗДЕЛИТЕЛИ (серые горизонтальные полосы в x 100..440)')
for label, shot in both:
    found = []
    for y in range(0, 900):
        if sum(1 for x in range(100, 440, 2) if shot.grey(x, y)) > 150:
            found.append(y)
    print('   %s %s' % (label, found))
print()

TINT = (249, 246, 251)          # #F3F1FF при 50% поверх кремового
PROBE_X = (160, 200, 240, 280)   # пустая полоса ряда, без текста и значков

print('ПОДЛОЖКА ЗАКРЕПЛЁННЫХ (цвет #F3F1FF при 50%)')
for label, shot in both:
    hits = []
    for y in range(100, 800):
        matches = sum(1 for x in PROBE_X
                      if sum(abs(shot.color(x, y)[i] - TINT[i])
                             for i in range(3)) < 6)
        if matches >= 3:
            hits.append(y)
    print('   %s подложка y %s..%s' % (label,
                                       min(hits) if hits else '-',
                                       max(hits) if hits else '-'))