# -*- coding: utf-8 -*-
r"""Скриншоты настроек и регистрации учителя.

Работает на своей базе (_shots/probe.db), чтобы не трогать настоящие
данные: тестовый логин создаётся при первом прогоне.

Запуск:  .venv312\Scripts\python.exe _probe_extra.py   (из корня проекта)
"""
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
os.chdir(BASE)
os.environ['RH_DB'] = os.path.join(BASE, '_shots', 'probe.db')

from main import MessengerApp                      # noqa: E402
from kivy.clock import Clock                       # noqa: E402
from kivy.core.window import Window                # noqa: E402
from kivy.uix.modalview import ModalView           # noqa: E402

from _probe_account import ensure_account          # noqa: E402

LOG = os.path.join('_shots', '_extra.log')
app = MessengerApp()


def log(*parts):
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(' '.join(str(p) for p in parts) + '\n')


def snap(name):
    """Снимок без всплывающих окон: они закрывают экран."""
    for child in list(Window.children):
        if isinstance(child, ModalView):
            child.dismiss(animation=False)
            Window.remove_widget(child)

    def _take(_dt):
        path = Window.screenshot(name=os.path.join('_shots', name + '.png'))
        log('SHOT', os.path.basename(path))
    Clock.schedule_once(_take, 0.45)


def open_settings(dt):
    app.go('settings')
    Clock.schedule_once(show_settings, 0.9)


def show_settings(dt):
    scr = app.manager.get_screen('settings')
    scr.nickname_field.text = 'новый_ник'
    scr.status_field.text = '10Б класс'
    snap('settings')
    log('поле ника доступно:', not scr.nickname_field.disabled)
    scr.save_profile()
    Clock.schedule_once(saved, 0.8)


def saved(dt):
    user = app.current_user
    log('после сохранения ник =', repr(user.nickname),
        '| показываем', repr(user.display_name))
    scr = app.manager.get_screen('settings')
    scr.nickname_field.text = ''
    scr.save_profile()
    Clock.schedule_once(cleared, 0.8)


def cleared(dt):
    user = app.current_user
    log('после очистки ник =', repr(user.nickname),
        '| показываем', repr(user.display_name))
    app.go('register_teacher')
    Clock.schedule_once(teacher, 0.9)


def teacher(dt):
    scr = app.manager.get_screen('register_teacher')
    scr.ids['first_name'].text = 'Мария2'
    scr.ids['last_name'].text = 'Петрова7'
    snap('register_teacher')
    log('имя учителя:', repr(scr.ids['first_name'].text),
        '| фамилия:', repr(scr.ids['last_name'].text))

    # ник тестового аккаунта возвращаем как было
    back = app.manager.get_screen('settings')
    back.nickname_field.text = 'probe'
    back.save_profile()
    Clock.schedule_once(finish, 0.8)


def finish(dt):
    log('готово')
    app.stop()


def start(dt):
    app.current_user = ensure_account()
    open_settings(None)


if __name__ == '__main__':
    open(LOG, 'w', encoding='utf-8').close()
    Clock.schedule_once(start, 2.4)
    try:
        app.run()
    except Exception:
        import traceback
        log('ПАДЕНИЕ:\n' + traceback.format_exc())