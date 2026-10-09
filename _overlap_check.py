# -*- coding: utf-8 -*-
"""Видит ли экран чатов касания, пока сверху «Настройки».

Подозрение: после перехода старый экран не убирается из дерева, и нижняя
панель чатов продолжает получать касания сквозь экран настроек. Тогда
любое касание внизу экрана переключает вкладку — и при выходе из
настроек включается «та, под которой оказался палец».

Проверяем по фактам:
  * остаётся ли экран home в children менеджера, когда current='settings';
  * доходят ли до пунктов панели нажатия, сделанные поверх настроек;
  * что с состоянием пунктов (вдруг остались нажатыми).

Запуск:  .venv312\\Scripts\\python.exe _overlap_check.py
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
LOG = os.path.join(BASE, '_shots', 'overlap.log')
lines = []
problems = []


def log(text):
    print(text)
    lines.append(text)


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


def tap_at(x, y):
    touch = make_touch(x, y)
    Window.dispatch('on_touch_down', touch)
    Window.dispatch('on_touch_up', touch)


def home():
    return app.manager.get_screen('home')


def tap_widget(widget):
    point = widget.to_window(widget.center_x, widget.center_y)
    tap_at(*point)
    return point


def screen_names():
    return [s.name for s in app.manager.children]


def expect(label, got, want):
    ok = got == want
    if not ok:
        problems.append('%s: ожидали %r, получили %r' % (label, want, got))
    log('   %-46s %-22s %s' % (label, got, 'OK' if ok else 'НЕ ТАК'))
    return ok


def start(dt):
    me = ensure_account()
    app.current_user = me
    app.go('home')
    Clock.schedule_once(step_home, 2.2)


def step_home(dt):
    log('=== на экране чатов ===')
    log('   экраны в дереве менеджера: %s' % screen_names())
    expect('текущий экран', app.manager.current, 'home')

    home().switch_tab('groups')
    Clock.schedule_once(_note_tab, 0.6)


def _note_tab(dt):
    log('   встали на «Группы»: вкладка=%s' % home().tab)
    log('   тапаем «Настройки»')
    tap_widget(home().ids['nav_settings'])
    Clock.schedule_once(step_settings, 1.4)


def step_settings(dt):
    log('')
    log('=== экран настроек открыт ===')
    log('   текущий экран: %s' % app.manager.current)
    log('   экраны в дереве менеджера: %s' % screen_names())
    expect('экран чатов убран из дерева', 'home' in screen_names(), False)

    # Касание там, где на экране чатов была бы нижняя панель.
    # Если старый экран остался в дереве, панель его примет.
    log('   тапаем вниз экрана, где у чатов нижняя панель')
    panel = home().ids['nav_groups']
    point = panel.to_window(panel.center_x, panel.center_y)
    log('   точка панели «Группы»: (%.0f, %.0f)' % point)
    tap_at(*point)
    Clock.schedule_once(_after_probe_tap, 1.0)


def _after_probe_tap(dt):
    log('   вкладка после касания: %s' % home().tab)
    expect('вкладка не сменилась от касания поверх настроек',
           home().tab, 'groups')

    log('   состояние пунктов панели:')
    for name in ('nav_search', 'nav_chats', 'nav_groups', 'nav_settings'):
        item = home().ids[name]
        log('      %-13s state=%-7s disabled=%s'
            % (name, item.state, item.disabled))

    # Теперь выходим кнопкой «Назад» и смотрим, что с вкладкой.
    back = None
    for widget in app.manager.current_screen.walk():
        if getattr(widget, 'text', None) == 'Назад':
            back = widget
            break
    if back is None:
        problems.append('кнопка «Назад» не найдена')
        finish()
        return
    log('   тапаем «Назад»')
    tap_widget(back)
    Clock.schedule_once(_after_back, 1.2)


def _after_back(dt):
    log('')
    log('=== после выхода из настроек ===')
    log('   текущий экран: %s' % app.manager.current)
    log('   экраны в дереве менеджера: %s' % screen_names())
    log('   вкладка: %s' % home().tab)
    expect('вернулись на чаты', app.manager.current, 'home')
    expect('вкладка осталась «Группы»', home().tab, 'groups')

    stuck = [n for n in ('nav_search', 'nav_chats', 'nav_groups', 'nav_settings')
             if home().ids[n].state == 'down']
    expect('ни один пункт не остался нажатым', stuck, [])
    Clock.schedule_once(_settled, 2.0)


def _settled(dt):
    log('   через 2 секунды: экран=%s вкладка=%s'
        % (app.manager.current, home().tab))
    expect('вкладка не сменилась сама', home().tab, 'groups')
    finish()


def finish():
    log('')
    log('ИТОГ: %s' % ('всё чисто' if not problems
                      else 'проблемы: %s' % problems))
    with open(LOG, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    app.stop()


if __name__ == '__main__':
    open(LOG, 'w', encoding='utf-8').close()
    Clock.schedule_once(start, 2.6)
    app.run()
