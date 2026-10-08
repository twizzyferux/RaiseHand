# -*- coding: utf-8 -*-
"""Сколько стоит стекло: кадры в секунду со стеклом и без него.

Плагин frostedglass перерисовывает буферы по своему таймеру, и это может
бить по производительности. Меряем честно: окно открыто, экран чатов на
 месте, замер идёт несколько секунд. Затем тот же замер без стекла —
разница и есть цена эффекта.
"""
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
os.chdir(BASE)
os.environ['RH_DB'] = os.path.join(BASE, '_shots', 'probe.db')

from main import MessengerApp                    # noqa: E402
from kivy.clock import Clock                     # noqa: E402

from _probe_account import ensure_account        # noqa: E402

app = MessengerApp()
LOG = os.path.join(BASE, '_shots', 'fps.log')
lines = []
SECONDS = 4.0


def log(text):
    print(text)
    lines.append(text)


def start(dt):
    me = ensure_account()
    app.current_user = me
    app.go('home')
    Clock.schedule_once(begin_glass, 2.0)


def measure(label, done):
    """Считает кадры за SECONDS секунд."""
    state = {'frames': 0}

    def tick(_dt):
        state['frames'] += 1

    def finish(_dt):
        Clock.unschedule(tick)
        log('%-22s %5.1f кадров/с' % (label, state['frames'] / SECONDS))
        done()

    Clock.schedule_interval(tick, 0)
    Clock.schedule_once(finish, SECONDS)


def begin_glass(dt):
    screen = app.manager.get_screen('home')
    log('плагин frostedglass активен: %s'
        % type(screen.ids.get('navbar')).__name__)

    def _after(dt2):
        measure('со стеклом', glass_done)

    Clock.schedule_once(_after, 0.5)


def glass_done():
    screen = app.manager.get_screen('home')
    # Прячем стекло, но оставляем его жить: так же будет, если эффект
    # выключат настройкой, и замер покажет чистую цену кадра.
    for name in ('navbar', 'fab'):
        widget = screen.ids.get(name)
        if widget is not None:
            widget.opacity = 0

    def _after(dt):
        measure('без стекла', finish)

    Clock.schedule_once(_after, 0.8)


def finish():
    with open(LOG, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    app.stop()


if __name__ == '__main__':
    open(LOG, 'w', encoding='utf-8').close()
    Clock.schedule_once(start, 2.6)
    app.run()
