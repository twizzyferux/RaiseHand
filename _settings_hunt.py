# -*- coding: utf-8 -*-
"""Возврат из настроек: ищем «случайную» вкладку.

Жалоба: тапаем «Настройки», выходим — и включается не та вкладка.
На быстрых нажатиях (палец пришёл и сразу ушёл) воспроизвести не удалось,
поэтому здесь проверяются Sequences, которых не было в первых пробах:

  A. Вход в настройки с КАЖДОЙ вкладки — возвращаемся туда же.
  B. Касание там, где на неактивной вкладке спрятана кнопка «+».
     Кнопка невидима (opacity 0), но она жива: если нажатие проходит,
     она вызывает new_chat() и уводит на «Поиск».
  C. Палец нажат, но отпускание приходит уже на другом экране —
     типичная причина «случайных» действий: отложенное отпускание
     достаёт виджет на экране, который к нему отношения не имеет.
  D. Многократные входы и выходы — проверяем, не накапливается ли
     состояние (залипшие флаги, накопленные подписки).

Каждый шаг печатает состояние: вкладка, активный пункт панели, какая
панель видима, не осталось ли нажатых кнопок.

Запуск:  .venv312\\Scripts\\python.exe _settings_hunt.py
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
LOG = os.path.join(BASE, '_shots', 'settings_hunt.log')
lines = []
problems = []


def log(text):
    print(text)
    lines.append(text)


def make_touch(x, y):
    """Касание с настоящими координатами (см. _buttons_check.py)."""
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


def point_of(widget):
    return widget.to_window(widget.center_x, widget.center_y)


def press(widget):
    """Только нажать — палец пока не отпущен."""
    x, y = point_of(widget)
    touch = make_touch(x, y)
    Window.dispatch('on_touch_down', touch)
    return touch


def release(touch):
    Window.dispatch('on_touch_up', touch)


def tap(widget):
    touch = press(widget)
    release(touch)


def home():
    return app.manager.get_screen('home')


NAV = ('nav_search', 'nav_chats', 'nav_groups', 'nav_settings')


def snapshot():
    """Всё, по чему видно, какая вкладка перед глазами."""
    active = [n.replace('nav_', '') for n in NAV if home().ids[n].active]
    panes = []
    for name in ('search', 'chats', 'groups'):
        pane = home()._pane(name)
        panes.append('%s:%s' % (name[:4],
                                'видна' if pane.opacity > 0.5 else 'скрыта'))
    stuck = [n.replace('nav_', '') for n in NAV
             if home().ids[n].state == 'down']
    if home().ids['fab']._pressed:
        stuck.append('ПЛЮС')
    return ('вкладка=%-7s актив=%-9s %s зажато=%s'
            % (home().tab, ','.join(active) or '-', ' '.join(panes),
               ','.join(stuck) or '-'))


def fail(text):
    problems.append(text)
    log('   !! %s' % text)


def check(label, got, want):
    if got != want:
        fail('%s: ожидали %r, получили %r' % (label, want, got))


def find_text(text):
    for widget in app.manager.current_screen.walk():
        if getattr(widget, 'text', None) == text:
            return widget
    return None


# --- очередь шагов ----------------------------------------------------------- #

def run_next(queue, index):
    if index >= len(queue):
        finish()
        return
    tag, action, check_fn = queue[index]
    log('')
    log('--- %s ---' % tag)
    before = snapshot()
    log('   до:    %s' % before)
    result = action()
    Clock.schedule_once(lambda _d: verify(queue, index, before, result), 1.1)


def verify(queue, index, before, result):
    after = snapshot()
    log('   после: %s' % after)
    tag, action, check_fn = queue[index]
    if check_fn is not None:
        check_fn(before, after, result)
    run_next(queue, index + 1)


# --- сценарии ---------------------------------------------------------------- #

def noop():
    """Шаг без действия — только чтобы зафиксировать состояние."""
    return None


def to_tab(name):
    """Шаг: переключиться на вкладку и сразу сверить результат."""
    def action():
        home().switch_tab(name)
        return name

    def check_fn(_before, _after, _result):
        check('вкладка', home().tab, name)
    return ('встать на «%s»' % name, action, check_fn)


def step_check_tab(want):
    """Шаг без действия: просто сверяем, что вкладка та же."""
    return ('проверка вкладки «%s»' % want, noop,
            lambda _b, _a, _r: (check('вкладка', home().tab, want),
                                check('экран', app.manager.current, 'home')))


def go_settings():
    """Нажать «Настройки» и дождаться перехода."""
    def action():
        tap(home().ids['nav_settings'])
        return None

    def check_fn(before, _after, _result):
        check('экран', app.manager.current, 'settings')
    return ('нажать «Настройки»', action, check_fn)


def back_home():
    """Нажать «Назад» в настройках."""
    def action():
        back = find_text('Назад')
        if back is None:
            fail('кнопка «Назад» не найдена')
            return None
        tap(back)
        return None

    def check_fn(_before, after, _result):
        check('экран', app.manager.current, 'home')
    return ('нажать «Назад»', action, check_fn)


def tap_fab_area(label, expect_tab):
    """Касание в зоне кнопки «+».

    expect_tab — какой вкладка обязана остаться. На «Поиске» и «Группы»
    кнопка спрятана, поэтому вкладка меняться не должна. На «Чатах»
    кнопка видима и нажатие законно уводит на «Поиск».
    """
    def action():
        fab = home().ids['fab']
        log('   кнопка «+»: opacity=%.2f disabled=%s'
            % (fab.opacity, fab.disabled))
        x, y = point_of(fab)
        log('   касание в точке кнопки (%.0f, %.0f)' % (x, y))
        tap_at(x, y)
        return None

    def check_fn(_before, _after, _result):
        check('вкладка', home().tab, expect_tab)
    return (label, action, check_fn)


def tap_at(x, y):
    touch = make_touch(x, y)
    Window.dispatch('on_touch_down', touch)
    Window.dispatch('on_touch_up', touch)


def late_release(widget, label):
    """Нажали, экран сменили, и только теперь отпустили палец."""
    state = {}

    def action():
        touch = press(widget)
        state['touch'] = touch
        state['from'] = snapshot()
        log('   нажали, экран=%s вкладка=%s' % (app.manager.current,
                                                home().tab))
        return touch

    def check_fn(_before, _after, _result):
        touch = state['touch']
        log('   вкладка перед отпусканием: %s' % home().tab)
        release(touch)
        log('   отпустили')
        Clock.schedule_once(lambda _d: done(), 0.9)

    def done():
        log('   после отпускания: %s' % snapshot())
        stuck = [n.replace('nav_', '') for n in NAV
                 if home().ids[n].state == 'down']
        if home().ids['fab']._pressed:
            stuck.append('ПЛЮС')
        if stuck:
            fail('%s: после отпускания зажато %s' % (label, stuck))

    return (label, action, check_fn)


def build_queue():
    queue = []

    # A. Вход в настройки с каждой вкладки.
    for tab in ('chats', 'search', 'groups'):
        queue.append(to_tab(tab))
        queue.append(go_settings())
        queue.append(back_home())
        queue.append(step_check_tab(tab))

    # B. Касание в зоне спрятанной кнопки «+»: вкладка обязана остаться.
    for tab in ('search', 'groups'):
        queue.append(to_tab(tab))
        queue.append(tap_fab_area('B: касание в зоне «+» на «%s»' % tab, tab))

    # B2. На «Чатах» кнопка «+» видима — нажатие законно уводит на «Поиск».
    queue.append(to_tab('chats'))
    queue.append(tap_fab_area('B2: касание в зоне «+» на «Чатах»', 'search'))

    # C. Отпускание, пришедшее на другом экране, разобрано отдельно:
    # _nav_stale_press.py. Здесь оно не воспроизводилось, а в общей
    # очереди ломало её же (отпуск уводил с экрана mid-шаг).

    # D. Многократные входы и выходы: ничего не должно накапливаться.
    queue.append(to_tab('chats'))
    for _ in range(3):
        queue.append(go_settings())
        queue.append(back_home())
    queue.append(step_check_tab('chats'))

    return queue


def start(dt):
    me = ensure_account()
    app.current_user = me
    app.go('home')
    Clock.schedule_once(begin, 2.2)


def begin(dt):
    run_next(build_queue(), 0)


def finish():
    log('')
    if problems:
        log('ИТОГ: найдено проблем — %d' % len(problems))
        for item in problems:
            log('   - %s' % item)
    else:
        log('ИТОГ: ни один сценарий не ломает вкладки')
    with open(LOG, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    app.stop()


if __name__ == '__main__':
    open(LOG, 'w', encoding='utf-8').close()
    Clock.schedule_once(start, 2.6)
    app.run()
