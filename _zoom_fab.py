# -*- coding: utf-8 -*-
"""Крупный план кнопки «+» и лупы «Поиска».

Обе рисуются линиями, а не картинками, поэтому у них другая природа
артефактов, чем у PNG-иконок. Увеличение — вчетверо БЕЗ сглаживания,
чтобы видеть реальные пиксели видеокарты.

Запуск:  .venv312\\Scripts\\python.exe -X utf8 _zoom_fab.py
"""
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
os.chdir(BASE)
os.environ['RH_DB'] = os.path.join(BASE, '_shots', 'probe.db')

from PIL import Image                          # noqa: E402

from main import MessengerApp                 # noqa: E402
from kivy.clock import Clock                  # noqa: E402
from kivy.core.window import Window           # noqa: E402

from _probe_account import ensure_account     # noqa: E402

app = MessengerApp()
SHOTS = os.path.join(BASE, '_shots')
ZOOM = 4

# Что смотрим: имя -> прямоугольник в координатах сцены 450x920.
TARGETS = {
    'fab': (352, 762, 440, 846),      # кнопка «+»
    'search': (50, 22, 130, 104),     # лупа «Поиска»
}


def start(dt):
    me = ensure_account()
    app.current_user = me
    app.go('home')
    Clock.schedule_once(grab, 2.2)


def grab(dt):
    path = Window.screenshot(name=os.path.join(SHOTS, 'zoom_fab_src.png'))
    src = Image.open(path).convert('RGB')
    scale = src.size[0] / 450.0
    height = src.size[1]
    for name, (x0, y0, x1, y1) in TARGETS.items():
        box = (int(x0 * scale), int(height - y1 * scale),
               int(x1 * scale), int(height - y0 * scale))
        strip = src.crop(box)
        out = os.path.join(SHOTS, 'zoom_%s.png' % name)
        strip.resize((strip.width * ZOOM, strip.height * ZOOM),
                     Image.NEAREST).save(out)
        print('%s: полоса %dx%d -> %s' % (name, strip.width, strip.height,
                                         os.path.basename(out)), flush=True)
    app.stop()


if __name__ == '__main__':
    Clock.schedule_once(start, 2.6)
    app.run()