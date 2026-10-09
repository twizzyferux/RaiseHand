# -*- coding: utf-8 -*-
"""Гонка анимации панели вкладок — проверка гипотезы «рандомности».

ЧТО ПРОВЕРЯЕМ
-------------
В ui/screens.py, _paint_tabs переключение вкладки затемняет панели
анимацией: anim.fade_to(pane, 'opacity', ..., duration=0.2). Анимация
живёт по часам Kivy и сама пишет opacity каждый кадр.

При возврате на экран чатов on_pre_enter вызывает _paint_tabs(..., animate=False)
и ставит прозрачность НАПРЯМУЮ. Но анимацию, которая ещё не доиграла,
это НЕ отменяет — и она доводит старое значение до конца.

Итог: панель, которую уже свернули, снова становится видимой. Человек
видит не ту вкладку. А «рандомно» — потому что исход зависит от того,
успел ли анимация доиграть за время перехода в настройки и обратно:
0.2 с анимации против 0.24 с перехода — рядом, и исход плавает.

Проверяем без переходов, чтобы увидеть саму гонку:
  1. включить анимацию переключения на «Поиск»;
  2. тут же переключиться на «Чаты» БЕЗ анимации (как при возврате);
  3. подождать и посмотреть, что осталось.

Запуск:  .venv312\\Scripts\\python.exe _pane_race_check.py
"""
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
os.chdir(BASE)
os.environ['RH_DB'] = os.path.join(BASE, '_shots', 'probe.db')

from main import MessengerApp                    # noqa: E402
from kivy.clock import Clock                     # noqa: E402

from _probe_account import ensure_account        # noqa: E402

app = MessengerApp()
LOG = os.path.join(BASE, '_shots', 'pane_race.log')
problems = []


def log(text):
    print(text, flush=True)
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(text + '\n')


def home():
    return app.manager.get_screen('home')


def opacities():
    return {name: round(home()._pane(name).opacity, 2)
            for name in ('search', 'chats', 'groups')}


def lit_panes():
    return [n for n, v in opacities().items() if v > 0.5]


def check(label, want):
    values = opacities()
    lit = lit_panes()
    log('   %-34s прозрачности=%s видимые=%s'
        % (label, values, lit))
    if values != want:
        problems.append('%s: прозрачности %s вместо %s (видимые %s)'
                        % (label, values, want, lit))


def start(dt):
    me = ensure_account()
    app.current_user = me
    app.go('home')
    Clock.schedule_once(begin, 2.2)


def begin(dt):
    log('старт: вкладка=%s прозрачности=%s'
        % (home().tab, opacities()))

    # Шаг 1: включаем анимацию перехода на «Поиск».
    log('')
    log('--- 1. переключаемся на «Поиск» (с анимацией) ---')
    home().switch_tab('search')
    log('   сразу после: прозрачности=%s' % opacities())

    # Шаг 2: тут же переключаемся на «Чаты» без анимации — ровно то,
    # что делает on_pre_enter при возврате из настроек.
    log('')
    log('--- 2. переключаемся на «Чаты» без анимации (как при возврате) ---')
    home()._paint_tabs('chats', animate=False)
    log('   сразу после: прозрачности=%s' % opacities())

    # Шаг 3: даём анимации доиграть.
    Clock.schedule_once(settled, 0.8)


def settled(dt):
    log('')
    log('--- 3. через 0.8 с (анимация должна была доиграть) ---')
    check('после возврата на «Чаты»', {'search': 0.0, 'chats': 1.0,
                                       'groups': 0.0})
    if home().tab != 'chats':
        problems.append('в поле tab «%s» вместо «chats»' % home().tab)
    finish()


def finish():
    log('')
    if problems:
        log('ИТОГ: гонка подтверждена, расхождений — %d' % len(problems))
        for item in problems:
            log('   - %s' % item)
    else:
        log('ИТОГ: гонки нет — прозрачности встали как надо')
    app.stop()


if __name__ == '__main__':
    open(LOG, 'w', encoding='utf-8').close()
    Clock.schedule_once(start, 2.6)
    app.run()
