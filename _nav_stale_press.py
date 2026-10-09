# -*- coding: utf-8 -*-
"""Пункт нижней панели, нажатый ДО ухода на другой экран.

Это вторая половина жалобы «после Настроек включается случайная вкладка».

Механизм подозрения: пункт панели — обычная кнопка Kivy, и она
начинает нажатие сразу (on_touch_down), а действие выполняет на
отпускании (on_release). Если экран сменился, пока палец ещё лежит,
отпуск долетает уже на другом экране — и действие срабатывает там, где
его не ждали: пункт «Поиск» включает поиск, «Группы» — группы.

Проверяем начисто: палец лежит на пункте, экран меняют программно,
палец отпускают. Пункт не должен ничего переключать.

Запуск:  .venv312\\Scripts\\python.exe _nav_stale_press.py
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
LOG = os.path.join(BASE, '_shots', 'nav_stale.log')
problems = []


def log(text):
    """Пишем сразу на диск: если проба зависнет, будет видно, где."""
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


def press(widget):
    x, y = widget.to_window(widget.center_x, widget.center_y)
    touch = make_touch(x, y)
    Window.dispatch('on_touch_down', touch)
    return touch


def release(touch):
    Window.dispatch('on_touch_up', touch)


def expect(label, got, want):
    ok = got == want
    if not ok:
        problems.append('%s: ожидали %r, получили %r' % (label, want, got))
    log('   %-44s %-10s %s' % (label, got, 'OK' if ok else 'НЕ ТАК'))


def start(dt):
    me = ensure_account()
    app.current_user = me
    app.go('home')
    Clock.schedule_once(hook, 2.2)


def hook(dt):
    """Следим за каждым срабатыванием пункта панели."""
    for name in ('nav_search', 'nav_chats', 'nav_groups', 'nav_settings'):
        home().ids[name].fbind(
            'on_release', lambda *_a, n=name: log('      >> сработал %s' % n))
    step(0)


def step(index):
    if index >= len(CASES):
        finish()
        return
    ident, leave_to, want_screen, want_tab = CASES[index]
    log('')
    log('--- %s: держим «%s», уходим на «%s» ---'
        % (ident, ident.replace('nav_', ''), leave_to))

    home().switch_tab('chats')
    touch = press(home().ids[ident])
    log('   нажали, экран=%s вкладка=%s' % (app.manager.current, home().tab))

    # Экран меняется, пока палец ещё лежит на пункте.
    app.go(leave_to)
    log('   экран сменили на %s, палец всё ещё лежит' % app.manager.current)

    release(touch)
    log('   отпустили')
    Clock.schedule_once(lambda _d: check(index, want_screen, want_tab), 1.0)


def check(index, want_screen, want_tab):
    ident = CASES[index][0]
    expect('экран после отпускания', app.manager.current, want_screen)
    expect('вкладка после отпускания', home().tab, want_tab)
    step(index + 1)


# Что должно случиться: после отпускания остаёмся там, куда ушли, и
# вкладка прежняя. Пункт, нажатый до ухода, не должен ничего делать.
CASES = [
    ('nav_search', 'settings', 'settings', 'chats'),
    ('nav_chats', 'settings', 'settings', 'chats'),
    ('nav_groups', 'settings', 'settings', 'chats'),
    ('nav_settings', 'settings', 'settings', 'chats'),
    ('nav_search', 'logs', 'logs', 'chats'),
    ('nav_groups', 'logs', 'logs', 'chats'),
]


def finish():
    log('')
    log('ИТОГ: %s' % ('всё чисто' if not problems
                      else 'проблемы: %s' % problems))
    app.stop()


if __name__ == '__main__':
    open(LOG, 'w', encoding='utf-8').close()
    Clock.schedule_once(start, 2.6)
    app.run()
