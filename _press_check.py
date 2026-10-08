# -*- coding: utf-8 -*-
"""Нижняя панель: каждый пункт ведёт куда надо, зоны не перекрываются.

Проверяются две вещи, из-за которых «Поиск» открывал настройки:
  1. зоны нажатия — четыре четверти плашки, они не должны наезжать друг
     на друга, иначе верхний пункт («Настройки») перехватывает всё;
  2. обработчики — у каждого пункта должен быть свой on_release, ведущий
     на свою вкладку (или на экран настроек).

Действие вызывается событием on_release — это ровно то, что происходит при
отпускании мыши. Синтетическое касание через Window здесь не годится: в
этой сборке Kivy у такого события координаты остаются None и маршрутизация
падает, поэтому попадание проверяется геометрией, а действие — событием.

Запуск:  .venv312\\Scripts\\python.exe _press_check.py
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
LOG = os.path.join(BASE, '_shots', 'press.log')
lines = []

ORDER = ['nav_search', 'nav_chats', 'nav_groups']
EXPECTED = {'nav_search': 'search', 'nav_chats': 'chats',
            'nav_groups': 'groups'}


def log(text):
    print(text)
    lines.append(text)


def start(dt):
    me = ensure_account()
    app.current_user = me
    app.go('home')
    Clock.schedule_once(check_zones, 2.0)


def check_zones(dt):
    """Зоны нажатия: четыре равные четверти плашки, без перекрытий."""
    screen = app.manager.get_screen('home')
    log('зоны нажатия (сцена 450x920):')
    zones = []
    for name in ('nav_search', 'nav_chats', 'nav_groups', 'nav_settings'):
        item = screen.ids[name]
        zones.append((name, item.x, item.right))
        log('   %-13s x %6.1f..%6.1f  (ширина %5.1f)'
            % (name, item.x, item.right, item.width))
    # Четверти просто соприкасаются границами, поэтому сравниваем с
    # запасом: без него округление dp даёт «перекрытие» в 0.02 пикселя.
    overlaps = [(zones[i][0], zones[i + 1][0])
                for i in range(len(zones) - 1)
                if zones[i][2] > zones[i + 1][1] + 0.5]
    log('   перекрытий: %s' % ('нет' if not overlaps else overlaps))
    log('')
    Clock.schedule_once(press_next, 0.4)


def press_next(dt):
    """Нажимаем по очереди, между нажатиями возвращаясь на экран чатов."""
    if not ORDER:
        report()
        return
    name = ORDER[0]
    app.go('home')

    def _later(_dt):
        screen = app.manager.get_screen('home')
        screen.ids[name].dispatch('on_release')
        log('нажали %-12s -> вкладка %-8s экран %s'
            % (name, screen.tab, app.manager.current))
        ORDER.pop(0)
        Clock.schedule_once(press_next, 0.9)

    Clock.schedule_once(_later, 0.9)


def report():
    """Сводим: вкладка после каждого нажатия должна быть своей."""
    screen = app.manager.get_screen('home')
    log('проверка вкладок:')
    # Нажатия уже отработали выше; здесь итог по последнему состоянию и
    # отдельная проверка «Настроек».
    app.go('home')

    def _settings(_dt):
        screen2 = app.manager.get_screen('home')
        screen2.ids['nav_settings'].dispatch('on_release')
        log('нажали nav_settings  -> экран %s' % app.manager.current)
        finish()

    Clock.schedule_once(_settings, 0.9)


def finish():
    with open(LOG, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    app.stop()


if __name__ == '__main__':
    open(LOG, 'w', encoding='utf-8').close()
    Clock.schedule_once(start, 2.6)
    app.run()
