# -*- coding: utf-8 -*-
"""Отрендерить полный макет Face ID.svg в PNG — эталон для сверки.

Холст макета 408x874, сцена приложения 450x920 — пропорции разные,
поэтому рендерим с растяжкой по каждой оси отдельно (preserveAspectRatio
none): иначе Chrome впишет макет по меньшему коэффициенту, оставит поля,
и сравнение со снимком покажет сдвиг, которого в приложении нет.
"""
import io
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE, 'tools'))
from svg2png import render  # noqa: E402

SRC = os.path.join(BASE, 'проект', 'проект экран', 'основной экран чаты',
                   'Face ID.svg')
text = io.open(SRC, encoding='utf-8').read()

render(text, os.path.join(BASE, '_shots', 'full_ref.png'), 408, 874,
       stretch=True)
print('эталон 408x874 (как есть в макете) -> _shots/full_ref.png')

render(text, os.path.join(BASE, '_shots', 'full_ref450.png'), 450, 920,
       stretch=True)
print('эталон 450x920 (размер сцены) -> _shots/full_ref450.png')

render(text, os.path.join(BASE, '_shots', 'full_ref2x.png'), 816, 1748,
       stretch=True)
print('эталон 816x1748 (2x) -> _shots/full_ref2x.png')