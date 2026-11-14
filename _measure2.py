# -*- coding: utf-8 -*-
from PIL import Image


def runs(im, pred, min_len, ystep=10, xstep=1):
    w, h = im.size
    out = []
    for y in range(0, h, ystep):
        run = 0
        best = 0
        start = 0
        beststart = 0
        for x in range(0, w, xstep):
            if pred(im.getpixel((x, y))):
                if run == 0:
                    start = x
                run += 1
                if run > best:
                    best = run
                    beststart = start
            else:
                run = 0
        if best >= min_len:
            out.append((y, beststart, beststart + best, best))
    return out


def is_violet(p):
    return abs(p[0] - 0x4B) < 25 and abs(p[1] - 0x2F) < 25 and abs(p[2] - 0xE0) < 25


def is_dark(p):
    return p[0] < 70 and p[1] < 70 and p[2] < 70


def is_field(p):
    return abs(p[0] - 0xEF) < 8 and abs(p[1] - 0xEF) < 8 and abs(p[2] - 0xF4) < 8


def is_pink(p):
    return p[0] > 200 and p[1] < 140 and p[2] > 120 and p[2] < 200


w = Image.open(r'проект/финал/Регистрация/01_welcome.png').convert('RGB')
print('=== WELCOME', w.size)
for r in runs(w, is_violet, 400, ystep=20):
    print('violet', r)
print('--- dark text rows')
for r in runs(w, is_dark, 200, ystep=40):
    print('dark', r)

s5 = Image.open(r'проект/финал/Регистрация/06_shag-5-gotovo.png').convert('RGB')
print('=== STEP5', s5.size)
print('--- pink avatar rows')
for r in runs(s5, is_pink, 100, ystep=20):
    print('pink', r)
print('--- field cards')
for r in runs(s5, is_field, 400, ystep=20):
    print('card', r)
print('--- violet button')
for r in runs(s5, is_violet, 400, ystep=20):
    print('violet', r)
