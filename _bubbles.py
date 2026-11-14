# -*- coding: utf-8 -*-
"""Рисуем декоративные пузыри welcome одним PNG (как в макете)."""
from PIL import Image, ImageDraw

# координаты из макета (холст 450x..., y от низа)
RAW = [
    ((0.655, 0.545, 0.98), 56, 172, 127, 39, [(44, 147, 25), (34, 127, 20), (29, 110, 15)]),
    ((0.502, 0.749, 1.00), 276, 152, 127, 39, [(393, 129, 20), (406, 113, 15)]),
    ((1.00, 0.561, 0.671), 141, 125, 127, 39, [(134, 110, 15)]),
    ((0.549, 0.878, 0.69), 230, 79, 127, 39, [(218, 54, 25), (208, 34, 20), (203, 17, 15)]),
    ((1.00, 0.541, 0.502), 44, 64, 127, 39, [(159, 37, 25), (174, 17, 20)]),
    ((1.00, 0.69, 0.486), 247, 34, 127, 39, [(367, 17, 15)]),
]

W, H = 390, 230
# композиция: x 29..421 (392), y 17..211 (194) -> вписываем в ширину 390
sx = W / 392.0
sy = sx  # сохраняем пропорции
comp_w = 392 * sx
comp_h = 194 * sy
off_x = 0.0
off_y = H - comp_h  # прижимаем к низу

img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
d = ImageDraw.Draw(img)


def hexcol(rgb):
    return (int(rgb[0] * 255), int(rgb[1] * 255), int(rgb[2] * 255), 255)


def rr(box, rad):
    d.rounded_rectangle(box, radius=rad, fill=hexcol(rgb))


for rgb, x, y, w, h, dots in RAW:
    # y в макете от низа; переводим в верхнюю систему композиции
    top = (211 - (y + h)) * sy + off_y
    left = (x - 29) * sx + off_x
    ww = w * sx
    hh = h * sy
    rr([left, top, left + ww, top + hh], hh / 2)
    for cx, cy, dd in dots:
        dtop = (211 - (cy + dd)) * sy + off_y
        dleft = (cx - 29) * sx + off_x
        ds = dd * sx
        d.ellipse([dleft, dtop, dleft + ds, dtop + ds], fill=hexcol(rgb))

img.save(r"assets/images/raisehand/bubbles.png")
print("saved bubbles.png", img.size)
