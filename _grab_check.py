# -*- coding: utf-8 -*-
"""Работает ли вообще touch.grab() в этой сборке Kivy.

От него зависит ButtonBehavior: он отпускает кнопку только при
`touch.grab_current is self`. Если захват не регистрируется, ни одна
кнопка на Button/PressButton не сработает — а это ровно жалоба
«кнопки не работают». Проверяем в отрыве от приложения.

Запуск:  .venv312\\Scripts\\python.exe _grab_check.py
"""
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

from kivy.config import Config                    # noqa: E402
Config.set('graphics', 'width', '400')
Config.set('graphics', 'height', '300')

from kivy.app import App                          # noqa: E402
from kivy.clock import Clock                      # noqa: E402
from kivy.input.motionevent import MotionEvent    # noqa: E402
from kivy.metrics import dp                       # noqa: E402
from kivy.uix.button import Button                # noqa: E402

LOG = os.path.join(BASE, '_shots', 'grab.log')
lines = []


def log(text):
    print(text)
    lines.append(text)


def make_touch(x, y):
    class Tap(MotionEvent):
        def depack(self, args):
            self.is_touch = True
            px, py = float(args[0]), float(args[1])
            self.sx, self.sy = px, py
            self.x, self.y = px, py
            self.px, self.py = px, py
            self.ox, self.oy = px, py
            self.x0, self.y0 = px, py
            self.profile = ['pos']

    touch = Tap('tap', 1, [x, y])
    touch.pos = (x, y)
    return touch


class Root(Button):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.size_hint = (None, None)
        self.size = (dp(200), dp(80))
        self.pos = (dp(100), dp(100))
        self.text = 'кнопка'
        self.fired = []

        self.bind(on_release=lambda *_: self.fired.append('release'))
        self.bind(on_press=lambda *_: self.fired.append('press'))


class Test(App):
    def build(self):
        Clock.schedule_once(self.check, 1.0)
        return Root()

    def check(self, *_):
        button = self.root
        from kivy.core.window import Window
        x, y = button.to_window(button.center_x, button.center_y)
        log('кнопка: pos=%s size=%s' % (tuple(round(v) for v in button.pos),
                                        tuple(round(v) for v in button.size)))
        log('точка в окне: (%.1f, %.1f)' % (x, y))
        log('')

        # 1. голый захват
        touch = make_touch(x, y)
        result = touch.grab(button)
        log('1) touch.grab(button) вернул: %s' % result)
        log('   grab_state   = %s' % touch.grab_state)
        log('   grab_list    = %s' % (touch.grab_list,))
        log('   grab_current = %r' % (touch.grab_current,))
        log('')

        # 2. то же через штатную маршрутизацию окна
        touch2 = make_touch(x, y)
        Window.dispatch('on_touch_down', touch2)
        log('2) после Window.dispatch(on_touch_down):')
        log('   grab_state   = %s' % touch2.grab_state)
        log('   grab_current = %r' % (touch2.grab_current,))
        log('   состояние кнопки: %r' % button.state)
        Window.dispatch('on_touch_up', touch2)
        log('   после отпускания состояние: %r' % button.state)
        log('   сработало: %s' % button.fired)
        log('')

        # 3. захват настоящим событием мыши Kivy, если оно есть
        try:
            from kivy.input.providers.mouse import MouseMotionEvent
            real = MouseMotionEvent('mouse', 1, {'sx': x, 'sy': y})
            log('3) MouseMotionEvent: x=%s y=%s' % (real.x, real.y))
            Window.dispatch('on_touch_down', real)
            log('   grab_state=%s grab_current=%r'
                % (real.grab_state, real.grab_current))
            Window.dispatch('on_touch_up', real)
            log('   сработало: %s' % button.fired)
        except Exception as error:                # noqa: BLE001
            log('3) MouseMotionEvent недоступен: %s' % error)

        with open(LOG, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines) + '\n')
        self.stop()


if __name__ == '__main__':
    os.makedirs(os.path.join(BASE, '_shots'), exist_ok=True)
    Test().run()
