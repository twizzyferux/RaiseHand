# -*- coding: utf-8 -*-
from PIL import Image

im = Image.open(r'проект/финал/Регистрация/03_shag-2-parol.png').convert('RGB')
w, h = im.size


def is_field(p):
    return abs(p[0] - 0xEF) < 8 and abs(p[1] - 0xEF) < 8 and abs(p[2] - 0xF4) < 8


for y in range(0, h, 20):
    run = 0
    best = 0
    start = 0
    beststart = 0
    for x in range(w):
        if is_field(im.getpixel((x, y))):
            if run == 0:
                start = x
            run += 1
            if run > best:
                best = run
                beststart = start
        else:
            run = 0
    if best > 500:
        print('field y', y, 'run', best, 'x', beststart, '-', beststart + best)


def is_violet(p):
    return abs(p[0] - 0x4B) < 25 and abs(p[1] - 0x2F) < 25 and abs(p[2] - 0xE0) < 25


for y in range(0, h, 20):
    run = 0
    best = 0
    start = 0
    beststart = 0
    for x in range(w):
        if is_violet(im.getpixel((x, y))):
            if run == 0:
                start = x
            run += 1
            if run > best:
                best = run
                beststart = start
        else:
            run = 0
    if best > 200:
        print('violet y', y, 'run', best, 'x', beststart, '-', beststart + best)
