# -*- coding: utf-8 -*-
"""Что человек видит на экране, а не что записано в поле.

Доселе я сверял home.tab — логическое поле. Но жалоба «включилась
случайная вкладка» — это про картинку: какая панель видима и какой пункт
подсвечен. Эти вещи могут разойтись, если параллельно играет анимация.

Главный подозреваемый: ui/screens.py, _paint_tabs. При переключении
вкладки панели затемняются анимацией (fade_to на opacity, 0.2 с).
Анимация живёт по часам Kivy и продолжает писать opacity, даже если
панель уже переключили. В on_pre_enter при возврате из настроек панели
ставятся напрямую (animate=False) — но БЕЗ отмены анимации. Догоняющая
анимация доводит старое значение до конца и открывает чужую панель.

Отсюда и «рандомно»: результат зависит от того, попали ли мы в 0.2 с
анимации или нет.

Проверяем после каждого шага, что видят глаза:
  * какая панель светлая (opacity выше половины);
  * какой пункт панели подсвечен;
  * совпадает ли это с заголовком и с полем tab.

Запуск:  .venv312\\Scripts\\python.exe _tab_view_check.py
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
LOG = os.path.join(BASE, '_shots', 'tab_view.log')
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


def what_is_visible():
    """Что видит человек: какая панель светлая и какой пункт подсвечен."""
    lit = [name for name in ('search', 'chats', 'groups')
           if home()._pane(name).opacity > 0.5]
    active = []
    for name, key in (('nav_search', 'search'), ('nav_chats', 'chats'),
                      ('nav_groups', 'groups')):
        item = home().ids[name]
        if item.active:
            active.append(key)
    return lit, active, home().tab, home().ids['tab_title'].text


def sweep(label):
    lit, active, tab, title = what_is_visible()
    log('   %-34s панели=%-9s подсвечен=%-9s tab=%-7s «%s»'
        % (label, ','.join(lit) or '-', ','.join(active) or '-', tab, title))

    if len(lit) != 1:
        problems.append('%s: видно %d панелей сразу (%s)'
                        % (label, len(lit), lit))
    if len(active) != 1:
        problems.append('%s: подсвечено %d пунктов (%s)'
                        % (label, len(active), active))
    if lit and active and lit[0] != active[0]:
        problems.append('%s: панель «%s», а подсвечен «%s» — разные'
                        % (label, lit[0], active[0]))
    if lit and tab and lit[0] != tab:
        problems.append('%s: панель «%s», а в поле tab «%s»'
                        % (label, lit[0], tab))
    title_map = {'search': 'Поиск', 'chats': 'Чаты', 'groups': 'Группы'}
    if tab and title != title_map[tab]:
        problems.append('%s: заголовок «%s» не про вкладку «%s»'
                        % (label, title, tab))


# --- сценарии: переключение и уход В РАЗГАР анимации ------------------------ #

NAV = ('nav_search', 'nav_chats', 'nav_groups')


def enter_settings():
    tap(home().ids['nav_settings'])


def leave_settings():
    back = find_text('Назад')
    if back is not None:
        tap(back)


def run(index):
    if index >= len(CASES):
        finish()
        return
    label, setup, jump = CASES[index]
    log('')
    log('--- %s ---' % label)
    home().switch_tab('chats')
    setup()
    jump()
    # Сверяем картинку, когда всё устоялось: и сразу после события,
    # и через 2 секунды — анимации могли доводить старое значение.
    Clock.schedule_once(lambda _d: sweep('%s (сразу)' % label), 0.9)
    Clock.schedule_once(lambda _d: (sweep('%s (через 2 с)' % label),
                                    run(index + 1)), 2.0)


# setup: доводим экран в порядок. jump: ломаем.
def plain_switch(ident):
    def setup():
        home().switch_tab('chats')
    return setup


def switch_and_leave(ident, wait):
    """Переключаем вкладку и уходим в настройки, не дожидаясь анимации."""
    def setup():
        home().switch_tab('chats')
    return setup


CASES = [
    ('переключились и сразу в настройки',
     lambda: home().switch_tab('chats'),
     lambda: _switch_then_settings('nav_search')),
    ('переключились, пауза, потом настройки',
     lambda: home().switch_tab('chats'),
     lambda: _switch_then_settings('nav_groups', wait=0.5)),
    ('в настройки сразу после «Чатов»',
     lambda: None,
     lambda: _to_settings()),
    ('в настройки, выход, и снова вкладка',
     lambda: home().switch_tab('groups'),
     lambda: _roundtrip()),
    ('две вкладки подряд, потом настройки',
     lambda: None,
     lambda: _two_switches()),
]


def _switch_then_settings(ident, wait=0.0):
    def inner():
        tap(home().ids[ident])
        if wait:
            Clock.schedule_once(lambda _d: enter_settings(), wait)
        else:
            enter_settings()
    return inner


def _to_settings():
    enter_settings()


def _roundtrip():
    def open_it(_d):
        leave_settings()
        Clock.schedule_once(lambda _d2: tap(home().ids['nav_search']), 0.05)
    Clock.schedule_once(open_it, 0.9)


def _two_switches():
    def first(_d):
        tap(home().ids['nav_groups'])
        Clock.schedule_once(second, 0.05)
    def second(_d):
        enter_settings()
        Clock.schedule_once(third, 0.9)
    def third(_d):
        leave_settings()
    Clock.schedule_once(first, 0.05)


def start(dt):
    me = ensure_account()
    app.current_user = me
    app.go('home')
    Clock.schedule_once(begin, 2.2)


def begin(dt):
    sweep('исходное состояние')
    run(0)


def finish():
    log('')
    if problems:
        log('ИТОГ: расхождений — %d' % len(problems))
        for item in problems:
            log('   - %s' % item)
    else:
        log('ИТОГ: картинка всегда совпадает с вкладкой')
    app.stop()


if __name__ == '__main__':
    open(LOG, 'w', encoding='utf-8').close()
    Clock.schedule_once(start, 2.6)
    app.run()
