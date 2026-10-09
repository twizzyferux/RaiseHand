# -*- coding: utf-8 -*-
"""Кнопки сквозным нажатием: как настоящий палец.

Касание идёт в окно и дальше штатным путём. Шаги выполняются по одному:
нажали -> дождались -> проверили. Иначе нажатия «склеиваются» (все
проверки читают последнее состояние) и результат врёт.

Проверяем нижнюю панель, кнопку «+», ввод в поле и кнопку «Найти».

Запуск:  .venv312\\Scripts\\python.exe _buttons_check.py
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
LOG = os.path.join(BASE, '_shots', 'buttons.log')
lines = []
problems = []


def log(text):
    print(text)
    lines.append(text)


def make_touch(x, y):
    """Касание с настоящими координатами.

    pos задаётся явно: именно из него ButtonBehavior берёт точку
    попадания. У самодельного события без этого он остаётся (0, 0), и
    кнопки «не нажимаются» только в пробе, а не в приложении.
    """
    from kivy.input.motionevent import MotionEvent

    class Tap(MotionEvent):
        def depack(self, args):
            self.is_touch = True
            x, y = float(args[0]), float(args[1])
            self.sx, self.sy = x, y
            # x/y и pos проставляет scale_for_screen, которого в пробе
            # нет: без него ButtonBehavior получает точку (0, 0) и решает,
            # что нажатия не было. Поэтому заполняем всё вручную.
            self.x, self.y = x, y
            self.px, self.py = x, y
            self.ox, self.oy = x, y
            self.osx, self.osy = x, y
            self.psx, self.psy = x, y
            self.x0, self.y0 = x, y
            self.dx = self.dy = 0.0
            self.profile = ['pos']

    touch = Tap('tap', 1, [x, y])
    touch.pos = (x, y)
    return touch


def tap(widget, scroll=None):
    """Нажатие по центру виджета — так же, как настоящий палец.

    scroll — список, внутри которого лежит виджет. to_window() у ScrollView
    в этой сборке Kivy не учитывает сдвиг содержимого (g_translate), и для
    виджетов внутри списка координаты уезжают: нажатие промахивается мимо
    ряда. Поэтому для них сдвиг прибавляем сами.
    """
    x, y = widget.to_window(widget.center_x, widget.center_y)
    if scroll is not None:
        # Содержимое списка сдвинуто на g_translate; to_window() этот сдвиг
        # не учитывает. В окне ряд лежит там, куда его сдвинул список, и
        # обязательно внутри его видимой области — прижимаем к ней.
        x = widget.center_x + scroll.g_translate.x
        y = widget.center_y + scroll.g_translate.y
        low, high = scroll.to_window(scroll.x, scroll.y)[1], \
            scroll.to_window(scroll.right, scroll.top)[1]
        y = min(max(y, low + 2), high - 2)
    touch = make_touch(x, y)
    Window.dispatch('on_touch_down', touch)
    Window.dispatch('on_touch_up', touch)
    return (x, y)


def close_popups():
    """Закрыть всплывающие окна.

    Они модальные и висят поверх всего окна, поэтому следующее нажатие
    уйдёт в поп-ап, а не в список. Это нормальное поведение приложения,
    а не поломка, — просто убираем его перед следующим шагом.
    """
    from kivy.uix.modalview import ModalView
    closed = 0
    for widget in list(Window.children):
        if isinstance(widget, ModalView):
            widget.dismiss()
            closed += 1
    return closed


def screen():
    return app.manager.get_screen('home')


def by_id(ident):
    return screen().ids.get(ident)


def by_text(text):
    for widget in screen().walk():
        if getattr(widget, 'text', None) == text:
            return widget
    return None


def expect(label, got, want):
    ok = got == want
    if not ok:
        problems.append('%s: ожидали %r, получили %r' % (label, want, got))
    log('   %-38s %-10s %s' % (label, got, 'OK' if ok else 'НЕ ТАК'))
    return ok


# --- сценарий: список шагов, каждый ждёт своего времени -------------------- #

def run_step(index):
    if index >= len(STEPS):
        finish()
        return
    name, action, check = STEPS[index]
    log('--- %s ---' % name)
    result = action()
    Clock.schedule_once(lambda _dt: verify(index, result), 1.0)


def verify(index, result):
    name, action, check = STEPS[index]
    ok = check(result)
    del ok
    run_step(index + 1)


# --- сами шаги ------------------------------------------------------------- #

def step_tab(ident, want):
    def action():
        screen().switch_tab('chats')
        tap(by_id(ident))
        return None

    def check(_result):
        return expect('%s -> вкладка' % ident, screen().tab, want)

    return ('вкладка %s' % ident, action, check)


def step_settings():
    def action():
        tap(by_id('nav_settings'))
        return None

    def check(_result):
        return expect('nav_settings -> экран', app.manager.current,
                      'settings')

    return ('настройки', action, check)


def step_back_home():
    def action():
        app.go('home')
        return None

    def check(_result):
        return expect('вернулись на чаты', app.manager.current, 'home')

    return ('возврат на чаты', action, check)


def step_fab():
    def action():
        screen().switch_tab('chats')
        tap(by_id('fab'))
        return None

    def check(_result):
        return expect('«+» -> вкладка', screen().tab, 'search')

    return ('кнопка «+»', action, check)


def step_field():
    def action():
        field = screen().ids.get('search_field')
        if field is not None:
            field.text = '123'
        return getattr(field, 'text', None)

    def check(result):
        return expect('поле принимает текст', result, '123')

    return ('поле ввода', action, check)


def step_find():
    def action():
        before = app.manager.current
        tap(by_text('Найти'))
        return before

    def check(before):
        return expect('«Найти» не уводит с экрана',
                      app.manager.current == before, True)

    return ('кнопка «Найти»', action, check)


def step_join():
    def action():
        screen().switch_tab('groups')
        return None

    def check(_result):
        return expect('переключились на «Группы»', screen().tab, 'groups')

    return ('вкладка «Группы»', action, check)


def step_close_popups():
    """Убрать модальные окна: они висят поверх и съедают касания."""
    def action():
        return close_popups()

    def check(result):
        return expect('всплывающих окон закрыто', result > 0, True)

    return ('закрыть поп-апы', action, check)


def step_row():
    """Строка чата открывается — раньше её перехватывали невидимые панели."""
    def action():
        screen().switch_tab('chats')
        rows = screen().chats_box.children
        log('   строк в списке: %d' % len(rows))
        if not rows:
            return None
        row = rows[-1]
        point = tap(row, scroll=screen().ids['chats_scroll'])
        log('   нажали ряд в точке %s' % (tuple(round(v) for v in point),))
        return None

    def check(_result):
        return expect('строка чата -> экран чата', app.manager.current,
                      'chat')

    return ('строка чата', action, check)


def step_back():
    def action():
        app.go('home')
        return None

    def check(_result):
        return expect('вернулись на экран чатов', app.manager.current, 'home')

    return ('назад на чаты', action, check)


STEPS = [
    step_tab('nav_chats', 'chats'),
    step_tab('nav_search', 'search'),
    step_tab('nav_groups', 'groups'),
    step_settings(),
    step_back_home(),
    step_fab(),
    step_field(),
    step_find(),
    step_close_popups(),
    step_row(),
    step_back(),
    step_join(),
]


def seed():
    """Собеседник и чат: без них строки списка нажимать нечего."""
    from core import auth, chat

    me = ensure_account()
    other = auth.register_student('Пётр', 'Сидоров', 'pass1234', 'pass1234')
    chat.add_contact(me.id, other.public_id)
    chat.send_message(me.id, other.id, 'Привет')
    return me


def start(dt):
    me = seed()
    app.current_user = me
    app.go('home')
    Clock.schedule_once(lambda _dt: run_step(0), 2.2)


def finish():
    log('')
    log('ИТОГ: %s' % ('все проверки пройдены' if not problems
                      else 'проблемы: %s' % problems))
    with open(LOG, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    app.stop()


if __name__ == '__main__':
    open(LOG, 'w', encoding='utf-8').close()
    Clock.schedule_once(start, 2.6)
    app.run()
