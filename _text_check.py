# -*- coding: utf-8 -*-
"""Текст на кремовом фоне: виден ли он на всех формовых экранах.

В Kivy текст по умолчанию белый. На старом чёрном фоне это не было
заметно, а на кремовом (как в макете) текст сливался с фоном. Цвета
заданы в theme.kv — здесь просто снимаем каждый экран, чтобы глазами
проверить, что заголовки, подписи и кнопки читаются.

Запуск:  .venv312\\Scripts\\python.exe _text_check.py
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

from _probe_account import ensure_account        # noqa: E402

app = MessengerApp()
LOG = os.path.join(BASE, '_shots', 'text.log')
SCREENS = ['settings', 'logs', 'verify', 'register_teacher',
           'register_student', 'teacher_proof']


def log(text):
    print(text, flush=True)
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(text + '\n')


def start(dt):
    me = ensure_account()
    app.current_user = me
    app.go('home')
    Clock.schedule_once(lambda _d: run(0), 2.0)


def run(index):
    if index >= len(SCREENS):
        app.stop()
        return
    name = SCREENS[index]
    app.go(name)
    Clock.schedule_once(lambda _d: shot(index, name), 1.2)


def shot(index, name):
    path = Window.screenshot(name=os.path.join(BASE, '_shots',
                                               'txt_%s.png' % name))
    log('сняли %-22s -> %s' % (name, os.path.basename(path)))
    Clock.schedule_once(lambda _d: run(index + 1), 0.2)


if __name__ == '__main__':
    os.makedirs(os.path.join(BASE, '_shots'), exist_ok=True)
    open(LOG, 'w', encoding='utf-8').close()
    Clock.schedule_once(start, 2.6)
    app.run()
