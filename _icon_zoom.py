# -*- coding: utf-8 -*-
"""Крупный план нижней панели: судить о резкости иконок на глаз.

Иконки на экране около 50 пикселей — на снимке всего приложения их
почти не разглядеть. Здесь берётся только полоса панели и увеличивается
вчетверо БЕЗ сглаживания: так видно ровно те пиксели, которые рисует
видеокарта.

Запуск:  .venv312\\Scripts\\python.exe -X utf8 _icon_zoom.py
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


def start(dt):
    me = ensure_account()
    app.current_user = me
    app.go('home')
    Clock.schedule_once(grab, 2.2)


def grab(dt):
    path = Window.screenshot(name=os.path.join(SHOTS, 'zoom_src.png'))
    crop(path)
    app.stop()


def crop(path):
    """Полоса панели в увеличении."""
    im = Image.open(path).convert('RGB')
    width, height = im.size
    scale = width / 450.0
    scene = 450.0, 920.0
    box = (int(20 * scale), int(height - 110 * scale),
           int(430 * scale), int(height - 25 * scale))
    strip = im.crop(box)
    big = strip.resize((strip.width * ZOOM, strip.height * ZOOM),
                       Image.NEAREST)
    out = os.path.join(SHOTS, 'zoom_panel.png')
    big.save(out)
    print('полоса %dx%d -> %s' % (strip.width, strip.height,
                                  os.path.basename(out)))


if __name__ == '__main__':
    Clock.schedule_once(start, 2.6)
    app.run()