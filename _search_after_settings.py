# -*- coding: utf-8 -*-
"""Поиск -> Настройки -> Назад -> Поиск: баг с последовательностью.

Жалоба:
  1. при нажатии «Настроек» нижняя панель на секунду раздваивается;
  2. после выхода из настроек нажатие «Поиска» не срабатывает — и
     срабатывает только если до этого нажать «Поиск», сходить в
     настройки и вернуться.

Раньше пробы шли в основном «вкладка -> Настройки -> Назад» и проверяли
вкладку сразу после возврата. Эта последовательность — со ПСЕДУЮЩИМ
нажатием после возврата — не проверялась, поэтому баг и жил.

Проверяем по шагам и логируем, куда уходит каждое касание: если
«Поиск» не сработал, смотрим, кто перехватил касание раньше него.

Запуск:  .venv312\\Scripts\\python.exe _search_after_settings.py
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
LOG = os.path.join(BASE, '_shots', 'search_after_settings.log')
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
    return (x, y)


def who_is_at(x, y):
    """Кто лежит в точке окна, сверху вниз."""
    chain = []

    def walk(widget):
        try:
            if not widget.collide_point(x, y):
                return
        except Exception:                        # noqa: BLE001
            return
        name = type(widget).__name__
        ident = getattr(widget, 'id', None)
        chain.append('%s(%s)' % (name, ident) if ident else name)
        for child in reversed(list(widget.children)):
            walk(child)

    for widget in reversed(list(Window.children)):
        walk(widget)
    return chain


def find_text(text):
    for widget in app.manager.current_screen.walk():
        if getattr(widget, 'text', None) == text:
            return widget
    return None


def hook():
    """Каждое срабатывание пункта панели — в журнал."""
    for name in ('nav_search', 'nav_chats', 'nav_groups', 'nav_settings'):
        home().ids[name].fbind(
            'on_release', lambda *_a, n=name: log('      >> on_release %s' % n))


def state(label):
    log('   %-26s экран=%-9s вкладка=%s' % (label, app.manager.current,
                                            home().tab))


def start(dt):
    me = ensure_account()
    app.current_user = me
    app.go('home')
    Clock.schedule_once(begin, 2.2)


def begin(dt):
    hook()
    log('старт: экран=%s вкладка=%s' % (app.manager.current, home().tab))
    step1()


def step1():
    """Шаг 1: нажимаем «Поиск»."""
    log('')
    log('--- 1. нажимаем «Поиск» ---')
    tap(home().ids['nav_search'])
    Clock.schedule_once(step1_done, 1.0)


def step1_done(dt):
    state('после «Поиска»')
    expect('вкладка «Поиск»', home().tab, 'search')
    step2()


def step2():
    """Шаг 2: нажимаем «Настройки»."""
    log('')
    log('--- 2. нажимаем «Настройки» ---')
    tap(home().ids['nav_settings'])
    Clock.schedule_once(step2_done, 1.6)


def step2_done(dt):
    state('после «Настроек»')
    expect('экран настроек', app.manager.current, 'settings')
    step3()


def step3():
    """Шаг 3: выходим кнопкой «Назад»."""
    log('')
    log('--- 3. выходим «Назад» ---')
    back = find_text('Назад')
    if back is None:
        problems.append('кнопка «Назад» не найдена')
        finish()
        return
    tap(back)
    Clock.schedule_once(step3_done, 1.6)


def step3_done(dt):
    state('после «Назад»')
    expect('вернулись на чаты', app.manager.current, 'home')
    step4()


def step4():
    """Шаг 4: снова жмём «Поиск» — здесь, по жалобе, и ломается."""
    log('')
    log('--- 4. снова нажимаем «Поиск» ---')
    search = home().ids['nav_search']
    point = search.to_window(search.center_x, search.center_y)
    log('   «Поиск» в окне: (%.0f, %.0f)' % point)
    log('   что лежит в этой точке: %s' % ' <- '.join(who_is_at(*point)))
    log('   совпадает ли с нашим пунктом: %s'
        % (search.collide_point(*point),))
    log('   нажат=%s disabled=%s' % (search._pressed, search.disabled))
    tap(search)
    Clock.schedule_once(step4_done, 1.2)


def step4_done(dt):
    state('после повторного «Поиска»')
    expect('вкладка снова «Поиск»', home().tab, 'search')
    if home().tab != 'search':
        search = home().ids['nav_search']
        point = search.to_window(search.center_x, search.center_y)
        log('   кто перехватил: %s' % ' <- '.join(who_is_at(*point)))
    finish()


def expect(label, got, want):
    ok = got == want
    if not ok:
        problems.append('%s: ожидали %r, получили %r' % (label, want, got))
    log('   %-26s %-10s %s' % (label, got, 'OK' if ok else 'НЕ ТАК'))


def finish():
    log('')
    if problems:
        log('ИТОГ: баг воспроизведён — %d' % len(problems))
        for item in problems:
            log('   - %s' % item)
    else:
        log('ИТОГ: баг не воспроизводится')
    app.stop()


if __name__ == '__main__':
    os.makedirs(os.path.join(BASE, '_shots'), exist_ok=True)
    open(LOG, 'w', encoding='utf-8').close()
    Clock.schedule_once(start, 2.6)
    app.run()