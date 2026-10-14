# -*- coding: utf-8 -*-
"""Аудит шрифта: какой шрифт видит каждый текст в приложении.

Задача — весь текст по загруженному SF Pro. Проверяем не настройки, а
то, что реально попадает в текстуры:

  1. что зарегистрировано в LabelBase (и куда указывает «Roboto»);
  2. каким font_name рисуют все Label, Button и TextInput на экранах;
  3. совпадает ли текст, отрисованный под именем Roboto, с SF Pro —
     если да, то явного font_name на кнопках не нужно.

Запуск:  .venv312\\Scripts\\python.exe -X utf8 _font_audit.py
"""
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
os.chdir(BASE)
os.environ['RH_DB'] = os.path.join(BASE, '_shots', 'probe.db')

from main import MessengerApp                    # noqa: E402
from kivy.clock import Clock                     # noqa: E402
from kivy.core.text import Label as CoreLabel     # noqa: E402
from kivy.core.text import LabelBase              # noqa: E402
from kivy.uix.button import Button                # noqa: E402
from kivy.uix.label import Label                  # noqa: E402
from kivy.uix.textinput import TextInput          # noqa: E402

from _probe_account import ensure_account        # noqa: E402

app = MessengerApp()
LOG = os.path.join(BASE, '_shots', 'font_audit.log')
SCREENS = ['home', 'settings', 'logs', 'welcome', 'login',
           'register_student', 'register_teacher', 'verify', 'teacher_proof',
           'chat']


def log(text):
    print(text, flush=True)
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(text + '\n')


def start(dt):
    me = ensure_account()
    app.current_user = me
    app.go('home')
    Clock.schedule_once(begin, 2.0)


def begin(dt):
    log('=== 1. что зарегистрировано ===')
    for name in ('SFPro', 'Roboto'):
        fns = LabelBase._fonts.get(name)
        if not fns:
            log('  %-7s НЕ ЗАРЕГЕСТРИРОВАН' % name)
            continue
        # Порядок в LabelBase._fonts: regular, italic, bold, bolditalic.
        for slot, slot_name in enumerate(('regular', 'italic', 'bold',
                                          'bolditalic')):
            value = fns[slot] if slot < len(fns) else None
            log('  %-7s %-11s %s' % (name, slot_name,
                                      os.path.basename(value or '-')))

    log('')
    log('=== 2. Roboto и SFPro дают одинаковый текст? ===')
    sample = 'Привет, RaiseHand'
    sizes = {}
    for name in ('Roboto', 'SFPro'):
        label = CoreLabel(text=sample, font_size=17, font_name=name)
        label.refresh()
        sizes[name] = label.texture.size
        log('  %-7s ширина=%s высота=%s' % (name, label.texture.width,
                                            label.texture.height))
    log('  совпадает: %s' % (sizes.get('Roboto') == sizes.get('SFPro')))

    log('')
    log('=== 3. какой шрифт у текста на экранах ===')
    run(0)


def run(index):
    if index >= len(SCREENS):
        finish()
        return
    name = SCREENS[index]
    app.go(name)
    Clock.schedule_once(lambda _d: scan(index, name), 1.0)


def scan(index, screen_name):
    screen = app.manager.get_screen(screen_name)
    used = {}
    for widget in screen.walk():
        if not isinstance(widget, (Label, Button, TextInput)):
            continue
        if not getattr(widget, 'text', ''):
            continue
        kind = type(widget).__name__
        used.setdefault(kind, set()).add(widget.font_name or '(пусто)')
    if not used:
        log('  %-20s текста нет' % screen_name)
    for kind in sorted(used):
        log('  %-20s %-14s %s' % (screen_name, kind,
                                   ', '.join(sorted(used[kind]))))
    run(index + 1)


def finish():
    log('')
    log('готово')
    app.stop()


if __name__ == '__main__':
    os.makedirs(os.path.join(BASE, '_shots'), exist_ok=True)
    open(LOG, 'w', encoding='utf-8').close()
    Clock.schedule_once(start, 2.6)
    app.run()