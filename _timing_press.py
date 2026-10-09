# -*- coding: utf-8 -*-
"""Первое нажатие «Поиска» в реальном потоке: с задержками после входа.

Жалоба: пока не сделать «Поиск -> Настройки -> Назад», нажатие «Поиска»
ничего не даёт. Пробы раньше всегда жали «Поиск» через 2+ секунды после
появления экрана и через прямой go('home') без перехода — то есть не в
тех условиях, в которых пользователь.

Здесь:
  1. идём на экран входа, а с него в чаты (настоящий переход 0.24 с);
  2. жмём «Поиск» в разное время: 0.05 с (внутри перехода), 0.3, 1, 3 с;
  3. после каждого нажатия проверяем вкладку, заголовок и прозрачность
     панели «Поиск» — видно ли её вообще.

Запуск:  .venv312\\Scripts\\python.exe _timing_press.py
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
LOG = os.path.join(BASE, '_shots', 'timing.log')
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


def press():
    item = home().ids['nav_search']
    x, y = item.to_window(item.center_x, item.center_y)
    touch = make_touch(x, y)
    Window.dispatch('on_touch_down', touch)
    Window.dispatch('on_touch_up', touch)


def report(label):
    scr = home()
    pane = scr.ids['search_pane']
    title = scr.ids['tab_title'].text
    log('%-26s вкладка=%-8s заголовок=%-9s pane.opacity=%s pane.disabled=%s'
        % (label, scr.tab, title, pane.opacity, pane.disabled))
    if scr.tab != 'search' or pane.opacity < 0.9:
        problems.append('%s: вкладка=%s pane.opacity=%s'
                        % (label, scr.tab, pane.opacity))
    # На всякий случай возвращаем всё в исходное, чтобы следующее
    # нажатие было именно «переключением», а не «уже на месте».
    scr._paint_tabs('chats', animate=False)


def start(dt):
    me = ensure_account()
    app.current_user = me
    # Настоящий путь: сначала экран входа, потом переход в чаты.
    app.go('login')
    Clock.schedule_once(enter_home, 1.0)


def enter_home(dt):
    app.go('home')
    log('ушли в чаты (переход 0.24 с)')
    # Нажатие -> пауза -> результат (и возврат на «Чаты») -> следующее.
    # Иначе нажатия наложились бы друг на друга и результат был бы нечитаем.
    step(0.05, 0.05)
    step(0.90, 0.90)
    step(3.00, 3.00)
    Clock.schedule_once(finish, 4.0)


def step(press_at, report_at):
    Clock.schedule_once(lambda _d: press(), press_at)
    Clock.schedule_once(
        lambda _d, t=report_at: report('нажатие через %.2f с' % t), report_at + 0.6)


def finish(_dt):
    log('')
    if problems:
        log('ИТОГ: нажатия не сработали — %d' % len(problems))
        for item in problems:
            log('   - %s' % item)
    else:
        log('ИТОГ: все нажатия сработали')
    app.stop()


if __name__ == '__main__':
    os.makedirs(os.path.join(BASE, '_shots'), exist_ok=True)
    open(LOG, 'w', encoding='utf-8').close()
    Clock.schedule_once(start, 2.6)
    app.run()
