# -*- coding: utf-8 -*-
"""Кегли по текстурам, которые реально создаёт Kivy.

Отдельный процесс без окна на этом Kivy падает (нужен GL-контекст), поэтому
измерение идёт внутри обычного прогона приложения.

Подбираем кегль так, чтобы текст совпадал с макетом по ширине И по высоте
букв: макетные размеры сняты по чернилам Face ID.svg (_measure_mock.py).

Запуск:  .venv312\Scripts\python.exe _probe_type.py
"""
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
os.chdir(BASE)
os.environ['RH_DB'] = os.path.join(BASE, '_shots', 'probe.db')

from main import MessengerApp                      # noqa: E402  (Config до окна)
from kivy.clock import Clock                       # noqa: E402
from kivy.core.text import Label as CoreLabel      # noqa: E402
from kivy.metrics import dp                        # noqa: E402

app = MessengerApp()
LOG = os.path.join(BASE, '_shots', 'type.log')

# Строки макета и их размеры в сцене (сняты по чернилам Face ID.svg).
TARGETS = (
    ('заголовок', 'Чаты', 168.0, 48.0, True),
    ('имя', 'Иван Иванов', 137.0, 15.0, True),
    ('превью', 'Hello, Vinograd!', 129.0, 14.0, False),
    ('время', '19:36', 43.0, 12.0, False),
    ('инициалы', 'ИИ', 42.5, 24.4, False),
    ('подпись', 'Поиск', 40.0, 9.0, False),
    ('подпись', 'Чаты', 32.0, 8.0, False),
    ('подпись', 'Группы', 48.0, 12.0, False),
    ('подпись', 'Настройки', 67.0, 13.0, False),
)

_cache = {}


def measure(text, size, bold):
    """Ширина и высота текстуры Kivy."""
    key = (text, round(size, 2), bold)
    if key not in _cache:
        label = CoreLabel(text=text, font_size=size, font_name='SFPro',
                          color=(1, 1, 1, 1), bold=bold, halign='left',
                          anchor_x='left', anchor_y='baseline')
        label.refresh()
        _cache[key] = (label.texture.width, label.texture.height)
    return _cache[key]


def fit(label, text, target_w, bold):
    """Кегль по ширине текстуры.

    Высоту текстуры Kivy подгонять бессмысленно: она включает выносные
    элементы и интерлиньяж, а в макете мерились сами буквы. По вертикали
    положение проверяется по снимку экрана.
    """
    best = None
    for step in range(8 * 4, 100 * 4):
        size = step / 4.0
        w, h = measure(text, size, bold)
        error = abs(w - target_w)
        if best is None or error < best[0]:
            best = (error, size, w, h)
    error, size, w, h = best
    line = ('%-10s %-17s жирный=%-5s макет ширина %5.1f  ->  кегль %5.2f  '
            'даёт %5.1f (текстура %4.1f x %4.1f)'
            % (label, '"%s"' % text, bold, target_w, size, w, w, h))
    print(line)
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(line + '\n')
    return size


def run(dt):
    print('Кегли по ширине текстуры Kivy')
    sizes = {}
    for label, text, w, h, bold in TARGETS:
        sizes[text] = fit(label, text, w, bold)
    print()
    print('высота текстуры при найденных кеглях (нужна для базовой линии):')
    for text, size in (('Иван Иванов', 21.0), ('Hello, Vinograd!', 18.0),
                       ('19:36', 17.0), ('ИИ', 20.0), ('Настройки', 13.0)):
        w, h = measure(text, size, text == 'Иван Иванов')
        line = '   %-17s кегль %4.1f -> текстура %4.1f x %4.1f' % (
            '"%s"' % text, size, w, h)
        print(line)
        with open(LOG, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    app.stop()


if __name__ == '__main__':
    open(LOG, 'w', encoding='utf-8').close()
    Clock.schedule_once(run, 2.0)
    app.run()