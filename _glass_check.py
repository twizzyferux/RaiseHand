# -*- coding: utf-8 -*-
"""Проверка стекла по правилам скилла liquid glass.

Снимаем три состояния, которые и должны быть видны глазами:
  1. обычное стекло и подсветка под пальцем на панели (интерактив);
  2. то же стекло с включённым «Меньше прозрачности»;
  3. экран настроек с переключателем.

Запуск:  .venv312\\Scripts\\python.exe -X utf8 _glass_check.py
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
LOG = os.path.join(BASE, '_shots', 'glass_check.log')


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


def snap(name, delay=0.4):
    def take(_dt):
        path = Window.screenshot(name=os.path.join(BASE, '_shots',
                                                   'glass_%s.png' % name))
        log('сняли %s' % os.path.basename(path))
    Clock.schedule_once(take, delay)


def start(dt):
    me = ensure_account()
    app.current_user = me
    app.go('home')
    Clock.schedule_once(press_panel, 2.4)


def press_panel(dt):
    """Держим палец на «Группах» и снимаем — видно подсветку стекла."""
    item = app.manager.get_screen('home').ids['nav_groups']
    x, y = item.to_window(item.center_x, item.center_y)
    touch = make_touch(x, y)
    Window.dispatch('on_touch_down', touch)
    log('палец на «Группах»')
    snap('press', 0.05)

    def release(_dt):
        Window.dispatch('on_touch_up', touch)
        Clock.schedule_once(step_solid, 1.0)
    Clock.schedule_once(release, 0.8)


def step_solid(_dt):
    """Включаем «Меньше прозрачности» и смотрим результат."""
    from core.config import SETTINGS, save_settings
    from ui.glass_widget import apply_accessibility

    SETTINGS.setdefault('glass', {})['reduced_transparency'] = True
    save_settings()
    home = app.manager.get_screen('home')
    apply_accessibility([home.ids['navbar'], home.ids['fab']])
    log('«Меньше прозрачности» включена')
    snap('solid', 0.6)
    Clock.schedule_once(step_settings, 1.2)


def step_settings(_dt):
    from core.config import SETTINGS, save_settings
    SETTINGS.setdefault('glass', {})['reduced_transparency'] = False
    save_settings()
    home = app.manager.get_screen('home')
    from ui.glass_widget import apply_accessibility
    apply_accessibility([home.ids['navbar'], home.ids['fab']])
    app.go('settings')
    Clock.schedule_once(lambda _d: (snap('settings', 0.5), finish()), 1.4)


def finish():
    log('готово')
    app.stop()


if __name__ == '__main__':
    open(LOG, 'w', encoding='utf-8').close()
    Clock.schedule_once(start, 2.6)
    app.run()