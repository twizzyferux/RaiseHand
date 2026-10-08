# -*- coding: utf-8 -*-
"""Тестовый аккаунт для проверочных прогонов (база _shots/probe.db).

Прогоны (_probe_chats.py, _probe_extra.py) создают временных собеседников
в своей базе и удаляют их, поэтому нужен ровно один «свой» аккаунт.
Создаётся при первом прогоне, дальше просто входит.
"""
from core import auth

LOGIN = "probe_user"
PASSWORD = "raisehand2026"
NICK = "probe"


def ensure_account():
    """Аккаунт зондов: найти или создать."""
    try:
        return auth.login(LOGIN, PASSWORD)
    except auth.AuthError:
        pass
    try:
        return auth.login(NICK, PASSWORD)
    except auth.AuthError:
        return auth.register_student("Проверка", "Зонда", PASSWORD, PASSWORD,
                                     nickname=NICK)