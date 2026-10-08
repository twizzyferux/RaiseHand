# -*- coding: utf-8 -*-
r"""Скриншоты экрана чатов и проверка вкладок.

Список наполняется по-настоящему: создаём собеседников, пишем сообщения,
закрепляем чат и оставляем непрочитанные — чтобы на экране было всё,
что есть в макете «основной экран чаты».

Запуск:  .venv312\Scripts\python.exe _probe_chats.py   (из корня проекта)
"""
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
os.chdir(BASE)

# Своя база: прогоны создают временных собеседников и не трогают data/
os.environ['RH_DB'] = os.path.join(BASE, '_shots', 'probe.db')

from main import MessengerApp                      # noqa: E402  (Config до окна)
from kivy.clock import Clock                       # noqa: E402
from kivy.core.window import Window                # noqa: E402

from _probe_account import ensure_account          # noqa: E402
from core import auth, chat, database as db       # noqa: E402

LOG = r'_shots\_chats.log'
SHOTS = r'_shots'
app = MessengerApp()
temp_ids = []


def log(*parts):
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(' '.join(str(p) for p in parts) + '\n')


def close_popups():
    """Убрать всплывающие окна: они закрывают экран на снимке."""
    from kivy.core.window import Window as _W
    from kivy.uix.modalview import ModalView
    for child in list(_W.children):
        if isinstance(child, ModalView):
            child.dismiss(animation=False)
            _W.remove_widget(child)


def snap(name):
    """Снимок экрана: гасим окна, ждём кадр и только потом снимаем."""
    close_popups()

    def _take(_dt):
        path = Window.screenshot(name=os.path.join(SHOTS, name + '.png'))
        log('SHOT', os.path.basename(path))
    Clock.schedule_once(_take, 0.45)


# --- наполнение списка ------------------------------------------------------ #

def seed():
    """Два собеседника, сообщения, закрепление и непрочитанные."""
    me = ensure_account()
    people = []
    for first, last, nick in (('Иван', 'Иванов', ''),
                              ('Мария', 'Петрова', '')):
        user = auth.register_student(first, last, 'pass1234', 'pass1234',
                                     nickname=nick)
        temp_ids.append(user.id)
        people.append(user)

    for person in people:
        chat.add_contact(me.id, person.public_id)

    # первый чат: моё сообщение прочитано, чат закреплён
    chat.send_message(people[0].id, me.id, 'Привет! Как дела?')
    chat.send_message(me.id, people[0].id, 'Всё хорошо, спасибо')
    chat.send_message(me.id, people[0].id, 'Hello, Vinograd!')
    db.execute(
        "UPDATE messages SET is_read = 1 WHERE sender_id = ? AND receiver_id = ?",
        (me.id, people[0].id))
    chat.set_pinned(me.id, people[0].id, True)

    # второй: от собеседника два непрочитанных
    chat.send_message(me.id, people[1].id, 'Домашку скинешь?')
    chat.send_message(people[1].id, me.id, 'Дай десять минут')
    chat.send_message(people[1].id, me.id, 'Готово, держи')
    return me, people


# --- сценарий ---------------------------------------------------------------- #

def start(dt):
    try:
        me, people = seed()
        app.current_user = me
        app.go('home')
    except Exception:
        log('ОШИБКА при наполнении:\n' + _trace())
    Clock.schedule_once(first_shot, 2.0)


def first_shot(dt):
    snap('chats_list')
    Clock.schedule_once(report, 0.5)


def report(dt):
    scr = app.manager.get_screen('home')
    scroll = scr.ids['chats_scroll']
    log('вкладка:', scr.tab, '| рядов:', len(scr.chats_box.children))
    log('окно:', round(Window.width), 'x', round(Window.height),
        '| масштаб сцены: %.4f' % (Window.width / 450.0))
    log('скролл: pos y=%.1f height=%.1f scroll_y=%.2f' % (
        scroll.y, scroll.height, scroll.scroll_y))
    log('список: pos=(%.1f, %.1f) size=(%.1f, %.1f)' % (
        scr.chats_box.x, scr.chats_box.y, scr.chats_box.width,
        scr.chats_box.height))
    for index, row in enumerate(scr.chats_box.children):
        log('  ряд %d: pos y=%.1f height=%.1f верх=%.1f имя=%r пин=%s '
            'непрочитанных=%s' % (index, row.y, row.height,
                                  row.y + row.height, row.peer_name,
                                  row.pinned, row.unread))
    scr.switch_tab('search')
    Clock.schedule_once(search_shot, 0.9)


def search_shot(dt):
    snap('chats_search')
    scr = app.manager.get_screen('home')
    scr.switch_tab('groups')
    Clock.schedule_once(groups_shot, 0.9)


def groups_shot(dt):
    snap('chats_groups')
    scr = app.manager.get_screen('home')
    scr.class_code.text = 'a123b4'
    log('код класса a123b4 ->', repr(scr.class_code.text))
    Clock.schedule_once(join, 0.4)


def join(dt):
    scr = app.manager.get_screen('home')
    scr.join_class()
    Clock.schedule_once(after_join, 0.8)


def after_join(dt):
    scr = app.manager.get_screen('home')
    log('после входа в класс поле пустое:', scr.class_code.text == '')
    scr.switch_tab('chats')
    Clock.schedule_once(back, 0.9)


def back(dt):
    snap('chats_back')
    scr = app.manager.get_screen('home')
    if scr.chats_box.children:
        scr.chats_box.children[0].dispatch('on_release')
    Clock.schedule_once(chat_open, 1.4)


def chat_open(dt):
    log('экран после нажатия:', app.manager.current)
    snap('chats_open')
    app.go('home')
    Clock.schedule_once(finish, 0.9)


def finish(dt):
    cleanup()
    log('готово')
    app.stop()


def cleanup():
    for person_id in temp_ids:
        db.execute("DELETE FROM users WHERE id = ?", (person_id,))
    if temp_ids:
        log('временные собеседники удалены')


def _trace():
    import traceback
    return traceback.format_exc()


if __name__ == '__main__':
    os.makedirs(SHOTS, exist_ok=True)
    open(LOG, 'w', encoding='utf-8').close()
    Clock.schedule_once(start, 2.6)
    try:
        app.run()
    except Exception:
        log('ПАДЕНИЕ:\n' + _trace())
        cleanup()