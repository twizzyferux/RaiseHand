# -*- coding: utf-8 -*-
"""Глаз в поле пароля и контур панели — снимки.

Запуск:  .venv312\\Scripts\\python.exe -X utf8 _eye_check.py
"""
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
os.chdir(BASE)
os.environ['RH_DB'] = os.path.join(BASE, '_shots', 'probe.db')

from main import MessengerApp                    # noqa: E402
from kivy.clock import Clock                     # noqa: E402
from kivy.core.window import Window              # noqa: E402

app = MessengerApp()
SHOTS = os.path.join(BASE, '_shots')

# экран -> имя снимка
PLAN = [('welcome', 'welcome'), ('login', 'login')]


def start(dt):
    run(0)


def run(index):
    if index >= len(PLAN):
        app.stop()
        return
    target, name = PLAN[index]
    app.go(target)
    Clock.schedule_once(lambda _d: shot(index, name), 1.3)


def shot(index, name):
    path = Window.screenshot(name=os.path.join(SHOTS, 'eye_%s.png' % name))
    print('сняли', os.path.basename(path), flush=True)
    run(index + 1)


if __name__ == '__main__':
    Clock.schedule_once(start, 2.6)
    app.run()