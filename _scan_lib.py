# -*- coding: utf-8 -*-
"""Сверка снимка с эталоном по числам.

Эталон (Face ID.svg -> PNG) прозрачен там, где фон не залит, и при
переводе в RGB прозрачные пиксели становятся чёрными — поиск «тёмного»
находит их вместо рисунка. Поэтому эталон сначала композится на фон
макета (#FFFBF7), и только потом измеряется.

Полосы берутся узкие и не пересекаются, иначе результат одной полосы
попадает в соседнюю и сравнение бессмысленно.
"""
import os
from PIL import Image

SCENE_W, SCENE_H = 450.0, 920.0
MOCK_BG = (255, 251, 247)          # #FFFBF7 — фон экрана в макете


class View:
    """Картинка в системе координат сцены 450x920.

    Сцена не растягивается на окно, а стоит по центру (PhoneStage —
    FloatLayout с pos_hint center). Поэтому в снимке окна она занимает
    прямоугольник меньше окна, и координаты сцены получаются простым
    масштабированием этого прямоугольника: (x - левый) / (ширина / 450).
    Иначе все координаты смещены на неучтённое поле окна.
    """

    def __init__(self, path, background=None, scene_rect=None):
        im = Image.open(path)
        if im.mode == 'RGBA' and background is not None:
            base = Image.new('RGB', im.size, background)
            base.paste(im, (0, 0), im)
            im = base
        self.im = im.convert('RGB')
        if scene_rect is None:
            # сцена вписана в окно по большей стороне
            scale = min(self.im.size[0] / SCENE_W, self.im.size[1] / SCENE_H)
            width, height = SCENE_W * scale, SCENE_H * scale
            left = (self.im.size[0] - width) / 2
            bottom = (self.im.size[1] - height) / 2
        else:
            left, bottom, width, height = scene_rect
        self.ox, self.oy = left, bottom
        self.sx = width / SCENE_W
        self.sy = height / SCENE_H

    def to_x(self, pixel_x):
        return (pixel_x - self.ox) / self.sx

    def to_y(self, pixel_y):
        return (pixel_y - self.oy) / self.sy

    def pixel_box(self, box):
        """Полоса в координатах сцены -> прямоугольник пикселей снимка."""
        x0, y0, x1, y1 = box
        return (int(round(self.ox + x0 * self.sx)),
                int(round(self.oy + y0 * self.sy)),
                int(round(self.ox + x1 * self.sx)),
                int(round(self.oy + y1 * self.sy)))

    def pixels(self, box):
        x0, y0, x1, y1 = self.pixel_box(box)
        px = self.im.load()
        for y in range(max(0, y0), min(self.im.size[1], y1)):
            for x in range(max(0, x0), min(self.im.size[0], x1)):
                yield self.to_x(x), self.to_y(y), px[x, y]

    def ink(self, box, test):
        xs, ys = [], []
        for x, y, color in self.pixels(box):
            if test(color):
                xs.append(x)
                ys.append(y)
        if not xs:
            return None
        return (min(xs), max(xs), min(ys), max(ys))

    def blobs(self, box, test, min_width=2.0):
        """Отдельные пятна по X — например, счётчики и значки в ряду."""
        x0, y0, x1, y1 = self.pixel_box(box)
        columns = []
        px = self.im.load()
        for xi in range(max(0, x0), min(self.im.size[0], x1)):
            height = sum(1 for yi in range(max(0, y0),
                                          min(self.im.size[1], y1))
                         if test(px[xi, yi]))
            columns.append((self.to_x(xi), height))
        out = []
        current = []
        for x, height in columns:
            if height >= 2:
                current.append((x, height))
            elif current:
                out.append(current)
                current = []
        if current:
            out.append(current)
        return [(part[0][0], part[-1][0]) for part in out
                if part[-1][0] - part[0][0] >= min_width]


# --- условия «есть рисунок» ------------------------------------------------ #

def ink_dark(color):
    """Текст и чёрные значки."""
    return sum(color) < 480


def ink_violet(color):
    return color[2] > 130 and color[0] < 160 and color[1] < 130


def ink_pink(color):
    """Счётчик новых сообщений #F0447C."""
    return (color[0] > 190 and color[1] < 130 and 90 < color[2] < 210
            and color[0] - color[1] > 70)


def ink_line(color):
    """Разделитель #C5C5C5 и обводка панели."""
    return (abs(color[0] - color[1]) < 16 and abs(color[1] - color[2]) < 16
            and 130 < color[0] < 225)


def ink_tint(color):
    """Подложка закреплённых #F3F1FF при 50% на кремовом фоне."""
    return (color[2] - color[0] > 4 and 230 < color[0] < 253
            and 226 < color[1] < 250)


def ink_avatar_mine(color):
    """Мой аватар: личный градиент (насыщенный, не чёрный)."""
    return (max(color) - min(color) > 45 and color[1] > 90
            and not ink_dark(color))


def ink_avatar_mock(color):
    """Аватар макета: розово-фиолетовый градиент."""
    return (color[0] > 190 and color[2] > 190 and color[1] < 235
            and max(color) - min(color) > 12)


def fmt(r):
    if r is None:
        return 'пусто'
    return 'x %6.1f..%6.1f (%5.1f)  y %6.1f..%6.1f (%5.1f)' % (
        r[0], r[1], r[1] - r[0], r[2], r[3], r[3] - r[2])


def shift(a, b):
    if not (a and b):
        return ''
    return 'сдвиг x %+5.1f  y %+5.1f' % (a[0] - b[0], a[2] - b[2])


def compare(bands, mine_path, ref_path):
    mine = View(mine_path)
    ref = View(ref_path, background=MOCK_BG)
    print('снимок %dx%d, эталон %dx%d (сцена %gx%g)'
          % (mine.im.size[0], mine.im.size[1], ref.im.size[0], ref.im.size[1],
             SCENE_W, SCENE_H))
    print()
    for label, box, test in bands:
        a = mine.ink(box, test)
        b = ref.ink(box, test)
        print('%-26s' % label)
        print('   мой    %s' % fmt(a))
        print('   макет  %s' % fmt(b))
        if shift(a, b):
            print('   %s' % shift(a, b))
        print()