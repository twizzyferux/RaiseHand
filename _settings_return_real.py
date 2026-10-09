# -*- coding: utf-8 -*-
"""Сценарий жалобы целиком, после правки гонки анимации.

Что делаем: жмём вкладку и, не дожидаясь, уходим в «Настройки», потом
возвращаемся «Назад» — и смотрим, что видит человек. Именно этот порядок
раньше оставлял чужую панель открытой.

Проверяем на всех вкладках и на разном времени между нажатиями: исход
зависел от того, успел ли отработать затухание 0.2 с, поэтому одна
удачная проверка ничего не доказывает — нужно много повторов.

Запуск:  .venv312\\Scripts\\python.exe _settings_return_real.py
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
LOG = os.path.join(BASE, '_shots', 'settings_return_real.log')
problems = []


def log(text):
    print(text, flush=True)
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(text + '\n')


def make_touch(x, y):
    from kivy.input.motionevent import MotionEvent

    class Tap(MotionEvent):
        def depack(self, args):
            self.is_touch = True
            px, py = float(args[0]), float(args[1])
            self.sx, self.sy = px, py
            self.x, self.y = px, py
            self.px, self.py = px, py
            self.ox, self.oy = px, py
            self.osx, self.osy = px, py
            self.psx, self.psy = px, py
            self.x0, self.y0 = px, py
            self.dx = self.dy = 0.0
            self.profile = ['pos']

    touch = Tap('tap', 1, [x, y])
    touch.pos = (x, y)
    return touch


def home():
    return app.manager.get_screen('home')


def tap(widget):
    x, y = widget.to_window(widget.center_x, widget.center_y)
    touch = make_touch(x, y)
    Window.dispatch('on_touch_down', touch)
    Window.dispatch('on_touch_up', touch)


def find_text(text):
    for widget in app.manager.current_screen.walk():
        if getattr(widget, 'text', None) == text:
            return widget
    return None


def view():
    lit = [n for n in ('search', 'chats', 'groups')
           if home()._pane(n).opacity > 0.5]
    active = [k for k, n in (('search', 'nav_search'),
                             ('chats', 'nav_chats'),
                             ('groups', 'nav_groups'))
              if home().ids[n].active]
    return lit, active, home().tab


def check(label, want_tab):
    lit, active, tab = view()
    log('   %-30s видно=%-8s подсвечен=%-8s tab=%s'
        % (label, ','.join(lit) or '-', ','.join(active) or '-', tab))
    if tab != want_tab:
        problems.append('%s: tab=%r вместо %r' % (label, tab, want_tab))
    if lit != [want_tab]:
        problems.append('%s: видно %s вместо [%s]'
                        % (label, lit, want_tab))
    if active != [want_tab]:
        problems.append('%s: подсвечено %s вместо [%s]'
                        % (label, active, want_tab))


def roundtrip(index):
    """Вкладка -> сразу Настройки -> Назад.

    В ROUNDS хранятся и id пункта панели (что нажимать), и название
    вкладки (что ожидаем увидеть) — это разные строки, путать их нельзя.
    """
    label, target, want_tab, gap = ROUNDS[index]

    def begin():
        home().switch_tab('chats')
        tap(home().ids[target])
        Clock.schedule_once(go_settings, gap)

    def go_settings(_dt):
        tap(home().ids['nav_settings'])
        Clock.schedule_once(go_back, 0.7)

    def go_back(_dt):
        back = find_text('Назад')
        if back is None:
            problems.append('%s: «Назад» не найден' % label)
            next_round(index)
            return
        tap(back)
        Clock.schedule_once(lambda _d: after(index, want_tab), 0.8)

    log('')
    log('--- %s ---' % label)
    begin()


def after(index, want_tab):
    check(label_of(index) + ': сразу', want_tab)
    # Ещё раз чуть позже: анимация могла дописать своё с задержкой.
    Clock.schedule_once(lambda _d: later(index, want_tab), 1.2)


def later(index, want_tab):
    check(label_of(index) + ': через 1.2 с', want_tab)
    next_round(index + 1)


def label_of(index):
    return ROUNDS[index][0]


def next_round(index):
    if index + 1 >= len(ROUNDS):
        finish()
        return
    roundtrip(index + 1)


def start(dt):
    me = ensure_account()
    app.current_user = me
    app.go('home')
    Clock.schedule_once(lambda _d: roundtrip(0), 2.2)


def finish():
    log('')
    if problems:
        log('ИТОГ: расхождений — %d' % len(problems))
        for item in problems:
            log('   - %s' % item)
    else:
        log('ИТОГ: после возврата всегда та же вкладка, что и до ухода')
    app.stop()


# Разные паузы между нажатием вкладки и уходом в настройки: затухание
# панели длится 0.2 с, поэтому 0.0..0.35 с — это как раз тот диапазон,
# где исход раньше плавал.
ROUNDS = [
    ('Поиск -> Настройки -> Назад (мгновенно)', 'nav_search', 'search', 0.0),
    ('Группы -> Настройки -> Назад (0.1 с)', 'nav_groups', 'groups', 0.1),
    ('Поиск -> Настройки -> Назад (0.15 с)', 'nav_search', 'search', 0.15),
    ('Группы -> Настройки -> Назад (0.2 с)', 'nav_groups', 'groups', 0.2),
    ('Поиск -> Настройки -> Назад (0.25 с)', 'nav_search', 'search', 0.25),
    ('Группы -> Настройки -> Назад (0.3 с)', 'nav_groups', 'groups', 0.3),
    ('Поиск -> Настройки -> Назад (0.35 с)', 'nav_search', 'search', 0.35),
    ('Группы -> Настройки -> Назад (мгновенно)', 'nav_groups', 'groups', 0.0),
]


if __name__ == '__main__':
    open(LOG, 'w', encoding='utf-8').close()
    Clock.schedule_once(start, 2.6)
    app.run()
