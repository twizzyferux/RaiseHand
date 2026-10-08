# -*- coding: utf-8 -*-
"""Экран чатов рядом с макетом — наглядная сверка.

Макет нарисован на холсте 404x874, сцена приложения — 450x920, поэтому
пропорции у них разные (0.462 против 0.489) и точное совпадение пиксель
в пиксель невозможно: приходится слегка растягивать по каждой оси
(x * 450/404, y * 920/874). Здесь оба кадра приводятся к общей высоте,
чтобы видеть расхождения по пропорциям, размерам и цветам.
"""
import os

from PIL import Image, ImageDraw

BASE = os.path.dirname(os.path.abspath(__file__))
SHOTS = os.path.join(BASE, '_shots')

app = Image.open(os.path.join(SHOTS, 'chats_list0001.png')).convert('RGB')
ref = Image.open(os.path.join(SHOTS, 'ref_chats.png')).convert('RGB')

HEIGHT = 1100


def fit(image):
    width = int(image.size[0] * HEIGHT / image.size[1])
    return image.resize((width, HEIGHT), Image.LANCZOS)


app_f, ref_f = fit(app), fit(ref)
gap = 24
sheet = Image.new('RGB', (app_f.size[0] + ref_f.size[0] + gap * 3, HEIGHT + 40),
                  (230, 230, 235))
sheet.paste(ref_f, (gap, 20))
sheet.paste(app_f, (gap * 2 + ref_f.size[0], 20))
draw = ImageDraw.Draw(sheet)
draw.text((gap + 6, 4), 'МАКЕТ 404x874', fill=(60, 60, 70))
draw.text((gap * 2 + ref_f.size[0] + 6, 4), 'ПРИЛОЖЕНИЕ 450x920',
          fill=(60, 60, 70))
sheet.save(os.path.join(SHOTS, 'compare_chats.png'))
print('сравнение ->', os.path.join(SHOTS, 'compare_chats.png'), sheet.size)