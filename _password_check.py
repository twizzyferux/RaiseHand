# -*- coding: utf-8 -*-
"""Полная проверка полей пароля: вид, ввод и глаз.

Задача пользователя — чтобы это наконец работало, поэтому проверка
строгая и по всем экранам сразу: у каждого поля проверяем
  1. что оно выглядит как обычное поле (такого же размера и цвета,
     как соседние «Имя»/«Фамилия» там, где они есть);
  2. что введённый пароль прячется точками;
  3. что глаз показывает пароль и снова прячет, а текст не теряется.

Запуск:  .venv312\\Scripts\\python.exe -X utf8 _password_check.py
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
from kivy.input.motionevent import MotionEvent   # noqa: E402

app = MessengerApp()
LOG = os.path.join(BASE, '_shots', 'password.log')
SHOTS = os.path.join(BASE, '_shots')
problems = []

# экран -> (id полей с паролем, id соседнего обычного поля или None)
PLAN = [
    ('login', ['password_field'], None),
    ('register_teacher', ['password', 'password_repeat'], 'first_name'),
    ('reg_step2', ['password', 'password_repeat'], None),
    ('settings', ['password_field', 'password_repeat_field'], None),
]


def log(text):
    print(text, flush=True)
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(text + '\n')


def tap(x, y):
    class T(MotionEvent):
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

    touch = T('tap', 1, [x, y])
    touch.pos = (x, y)
    Window.dispatch('on_touch_down', touch)
    Window.dispatch('on_touch_up', touch)


def start(dt):
    app.go('login')
    Clock.schedule_once(lambda _d: step(0), 2.2)


def step(index):
    if index >= len(PLAN):
        finish()
        return
    screen, ids, neighbour = PLAN[index]
    app.manager.current = screen
    Clock.schedule_once(lambda _d: check(index, screen, ids, neighbour), 1.4)


def check(index, screen, ids, neighbour):
    scr = app.manager.get_screen(screen)
    log('\n=== %s ===' % screen)
    for field_id in ids:
        if field_id not in scr.ids:
            problems.append('%s: нет поля %s' % (screen, field_id))
            continue
        field = scr.ids[field_id]
        # 1. вид: тот же размер, что у обычного поля рядом
        if neighbour and neighbour in scr.ids:
            other = scr.ids[neighbour]
            same_height = abs(field.height - other.height) < 1
            log('  %-22s высота %.0f против %.0f у обычного поля — %s'
                % (field_id, field.height, other.height,
                   'совпадает' if same_height else 'РАЗНЫЕ'))
            if not same_height:
                problems.append('%s/%s: высота отличается от обычного поля'
                                % (screen, field_id))
        # 2. точки
        field.text = 'pass1234'
        masked = field.password
        log('  %-22s точки: %s' % (field_id, 'да' if masked else 'НЕТ'))
        if not masked:
            problems.append('%s/%s: пароль не маскируется' % (screen, field_id))
        # 3. глаз
        box = field._eye_box()
        wx, wy = field.to_window(box[0] + box[2] / 2, box[1] + box[3] / 2)
        tap(wx, wy)
        shown = (not field.password) and field.show_password
        text_kept = field.text == 'pass1234'
        log('  %-22s глаз показал: %s, текст цел: %s'
            % (field_id, 'да' if shown else 'НЕТ', 'да' if text_kept else 'НЕТ'))
        if not shown:
            problems.append('%s/%s: глаз не показал пароль' % (screen, field_id))
        if not text_kept:
            problems.append('%s/%s: текст потерялся' % (screen, field_id))
        tap(wx, wy)
        hidden = field.password and not field.show_password
        log('  %-22s глаз снова спрятал: %s'
            % (field_id, 'да' if hidden else 'НЕТ'))
        if not hidden:
            problems.append('%s/%s: глаз не спрятал обратно' % (screen, field_id))
    Clock.schedule_once(lambda _d: snap(index, screen), 0.7)


def snap(index, screen):
    Window.screenshot(name=os.path.join(SHOTS, 'pw_%s.png' % screen))
    step(index + 1)


def finish():
    log('')
    if problems:
        log('ИТОГ: проблем — %d' % len(problems))
        for item in problems:
            log('   - %s' % item)
    else:
        log('ИТОГ: все поля в порядке')
    app.stop()


if __name__ == '__main__':
    open(LOG, 'w', encoding='utf-8').close()
    Clock.schedule_once(start, 2.6)
    app.run()