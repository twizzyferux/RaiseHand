# -*- coding: utf-8 -*-
"""Тестовый аккаунт для проверочных прогонов (база _shots/probe.db).

Прогоны (_probe_chats.py, _probe_extra.py) создают временных собеседников
в своей базе и удаляют их, поэтому нужен ровно один «свой» аккаунт.
Создаётся при первом прогоне, дальше просто входит.

Пароль НЕ хранится в коде. Он лежит в файле probe_login.txt рядом с
этим модулем, а сам файл в репозиторий не попадает. Причина: репозиторий
стал публичным, и любой текст в коде виден всем. Пароль здесь от
локальной базы, настоящими данными он не является, но и показывать его
незачем - привычка хранить пароли рядом с кодом вредная сама по себе.

Если файла нет, берётся значение из переменной окружения
RH_PROBE_PASSWORD. Если нет и его, пароль выбирается случайный: база
тестовая, главное, чтобы вход сработал.
"""
import os
import secrets

LOGIN = "probe_user"
NICK = "probe"
PASSWORD_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "probe_login.txt")


def _password() -> str:
    """Пароль пробы: из файла, из окружения или случайный."""
    try:
        with open(PASSWORD_FILE, encoding="utf-8") as f:
            got = f.read().strip()
            if got:
                return got
    except OSError:
        pass
    got = os.environ.get("RH_PROBE_PASSWORD", "").strip()
    if got:
        return got
    # Случайный: он нигде не нужен, база тестовая и пересоздаётся
    # вместе с probe.db. Запомнить его нельзя и не нужно.
    return secrets.token_urlsafe(12)


def ensure_account():
    """Аккаунт зондов: найти или создать."""
    from core import auth

    password = _password()
    for login in (LOGIN, NICK):
        try:
            return auth.login(login, password)
        except auth.AuthError:
            pass
    return auth.register_student("Проверка", "Зонда", password, password,
                                 nickname=NICK)