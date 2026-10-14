# -*- coding: utf-8 -*-
"""Снимок экрана приложения рядом с макетом того же экрана.

Сравнивать кегли по цифрам рискованно: у выгрузок Figma первый текст
в блоке — не всегда тот, что в имени файла. Наглядное сравнение
надёжнее: слева макет, справа то, что рисует приложение.

Запуск:  .venv312\\Scripts\\python.exe -X utf8 _compare_mock.py [экран]
"""
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
os.chdir(BASE)
os.environ['RH_DB'] = os.path.join(BASE, '_shots', 'probe.db')

from PIL import Image                                  # noqa: E402

from main import MessengerApp                        # noqa: E402
from kivy.clock import Clock                         # noqa: E402
from kivy.core.window import Window                  # noqa: E402

from _probe_account import ensure_account            # noqa: E402

ROOT = os.path.join(BASE, 'проект', 'проект экран')
SHOTS = os.path.join(BASE, '_shots')

# макет -> экран приложения. Порядок тот же, что в макетах.
PAIRS = [
    ('экран 1', 'welcome'),
    ('экран 2', 'register_student'),
    ('экран 3', 'register_student'),
    ('экран 4', 'register_teacher'),
    ('экран 5', 'verify'),
    ('экран 6', 'home'),
    ('основной экран чаты', 'home'),
]

app = MessengerApp()
SCREEN_W, SCREEN_H = 402, 874


def shot_screen(index):
    if index >= len(PAIRS):
        return
    mock, screen_name = PAIRS[index]
    app.go(screen_name)
    Clock.schedule_once(lambda _d: take(index, mock, screen_name), 1.2)


def take(index, mock, screen_name):
    path = Window.screenshot(name=os.path.join(SHOTS,
                                               'cmp_%s.png' % screen_name))
    print('сняли', os.path.basename(path), flush=True)
    side_by_side(mock, os.path.basename(path))
    shot_screen(index + 1)


def side_by_side(mock, app_png):
    """Макет слева, приложение справа — оба приведены к одной ширине."""
    mock_path = os.path.join(ROOT, mock, 'Screen.png')
    if not os.path.exists(mock_path):
        print('  макета нет:', mock_path)
        return
    try:
        left = Image.open(mock_path).convert('RGB').resize(
            (SCREEN_W, SCREEN_H))
        right = Image.open(os.path.join(SHOTS, app_png)).convert('RGB')
        right = right.resize((SCREEN_W, SCREEN_H))
    except Exception as exc:                          # noqa: BLE001
        print('  не собралось:', exc)
        return
    canvas = Image.new('RGB', (SCREEN_W * 2 + 12, SCREEN_H), (40, 40, 40))
    canvas.paste(left, (0, 0))
    canvas.paste(right, (SCREEN_W + 12, 0))
    out = os.path.join(SHOTS, 'pair_%s.png' % mock.replace(' ', '_'))
    canvas.save(out)
    print('  пара ->', os.path.basename(out), flush=True)


def start(dt):
    me = ensure_account()
    app.current_user = me
    app.go('welcome')
    Clock.schedule_once(lambda _d: shot_screen(0), 2.0)


if __name__ == '__main__':
    os.makedirs(SHOTS, exist_ok=True)
    Clock.schedule_once(start, 2.6)
    app.run()