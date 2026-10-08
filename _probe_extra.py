# -*- coding: utf-8 -*-
"""Скриншоты экранов, которых нет в _probe.py: настройки и регистрация учителя.

ВНИМАНИЕ: заходит тестовым аккаунтом (логин 4874691 / raisehand2026) и
временно меняет его ник, но в конце возвращает как было.

Запуск:  .venv312\Scripts\python.exe _probe_extra.py   (из корня проекта)
"""
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
os.chdir(BASE)

from main import MessengerApp  # noqa: E402
from kivy.clock import Clock  # noqa: E402
from kivy.core.window import Window  # noqa: E402

LOG = r'_shots\_extra.log'
app = MessengerApp()


def log(*parts):
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(' '.join(str(p) for p in parts) + '\n')


def shot(name):
    path = Window.screenshot(name='_shots/{}.png'.format(name))
    log('SHOT', path)


def open_settings(dt):
    app.go('login')
    scr = app.manager.get_screen('login')
    scr.login_field.text = '4874691'
    scr.password_field.text = 'raisehand2026'
    scr.do_login()
    Clock.schedule_once(after_login, 1.0)


def after_login(dt):
    app.go('settings')
    Clock.schedule_once(show_settings, 0.8)


def show_settings(dt):
    scr = app.manager.get_screen('settings')
    scr.nickname_field.text = 'новый_ник'
    scr.status_field.text = '10Б класс'
    shot('settings')
    log('поле ника доступно учителю/ученику:',
        scr.nickname_field.disabled, '| текст:', repr(scr.nickname_field.text))
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
    shot('register_teacher')
    log('имя учителя:', repr(scr.ids['first_name'].text),
        '| фамилия:', repr(scr.ids['last_name'].text))
    scr2 = app.manager.get_screen('settings'); scr2.nickname_field.text = 'ivan'; scr2.save_profile(); log('ник тестового аккаунта возвращён:', repr(app.current_user.nickname)); log('готово')


open(LOG, 'w', encoding='utf-8').close()
Clock.schedule_once(open_settings, 2.4)
try:
    app.run()
except Exception as exc:
    log('ПАДЕНИЕ:', exc)