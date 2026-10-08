# -*- coding: utf-8 -*-
"""Значки и разделители: смещения внутри ряда (сцена 450x920).

Разбор полного макета Face ID.svg. Важное из разбора: галочки статуса
в макете стоят НЕ рядом с текстом превью, а на одной линии со временем,
слева от него (серые 28x20 в x 315, фиолетовые 34x25 в x 309) — в
прежней вёрстке они уезжали под превью.

Низ каждого ряда в макете: 254.5, 338.5, 420.5, 506.5, 590.5, 674.5, 758.5.
"""
import io
import os
import re

SRC = os.path.join(r'D:\school_messenger_plain', 'проект', 'проект экран',
                   'основной экран чаты', 'Face ID.svg')
MOCK_W, MOCK_H = 408.0, 874.0
STAGE_W, STAGE_H = 450.0, 920.0
FX, FY = STAGE_W / MOCK_W, STAGE_H / MOCK_H

ROW_BOTTOMS = [254.5, 338.5, 420.5, 506.5, 590.5, 674.5, 758.5]
ROW_H = 88                             # шаг ряда в сцене


def px(x):
    return round(x * FX, 1)


def py(top):
    return round((MOCK_H - top) * FY, 1)


def row_of(y):
    """Номер ряда (с 1) по координате макета сверху."""
    for number, bottom in enumerate(ROW_BOTTOMS, 1):
        if y <= bottom + 2:
            return number
    return len(ROW_BOTTOMS)


def offsets(x, y, w, h):
    """Значок -> (смещение внутри ряда, размер, номер ряда)."""
    row = row_of(y)
    base = py(ROW_BOTTOMS[row - 1])
    return (px(x), round(py(y + h) - base, 1), px(w), py(y) - py(y + h), row)


print('высота ряда: %s (макет 84 -> %s)'
      % (ROW_H, round(84 * FY, 1)))
print('низ 1-го ряда: %s' % py(ROW_BOTTOMS[0]))
print()
print('ЗНАЧКИ (макет -> смещение от низа своего ряда)')
icons = (('закрепление', 367, 206, 30, 30),
         ('закрепление 2', 336, 292, 30, 30),
         ('счётчик 3', 369, 294, 25, 25),
         ('галочка серая', 315, 347, 28, 20),
         ('счётчик 12', 365, 630, 29, 25),
         ('галочка фиолетовая', 309, 429, 34, 25),
         ('галочка серая 2', 315, 683, 28, 20))
for name, x, y, w, h in icons:
    dx, dy, dw, dh, row = offsets(x, y, w, h)
    print('  %-20s pos x %-6s y %-6s  размер %sx%s   (ряд %d)'
          % (name, dx, dy, dw, round(dh, 1), row))
print()
print('БАЗОВЫЕ ЛИНИИ текстов (макет -> от низа ряда)')
base = py(ROW_BOTTOMS[0])
for name, top in (('имя', 196.21), ('превью', 229.97), ('время', 195.27)):
    print('  %-8s %s' % (name, round(py(top) - base, 1)))
print()
print('РАЗДЕЛИТЕЛИ (сцена, y снизу)')
for m in re.finditer(r'<line x1="([\d.]+)" y1="([\d.]+)"', io.open(
        SRC, encoding='utf-8').read()):
    x, y = float(m.group(1)), float(m.group(2))
    print('  y %-8s от x %s' % (py(y), px(x)))
print()
print('КЕГЛИ')
for name, cap in (('имя', 14.30), ('превью (без запятой)', 13.60),
                  ('время', 11.81)):
    print('  %-22s %s' % (name, round(cap * FY / 0.714, 1)))
print('  инициалы (33%% от 68)    %s'
      % round(0.33 * 68 * FY / 0.714, 1))