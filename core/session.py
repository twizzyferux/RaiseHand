# -*- coding: utf-8 -*-
"""Постоянный вход: сессия, чтобы не вводить пароль каждый раз.

Сессия лежит в data/session.json — это обычный файл рядом с базой,
поэтому работает и на ПК, и на телефоне, и переживает перезапуск.

Что хранится: id пользователя, когда он вошёл и с какого устройства.
Пароль не хранится — только идентификатор, поэтому «войти заново»
означает ровно одно: зайти под тем же аккаунтом на этом устройстве.
"""
import json
import os
import platform
import socket
from datetime import datetime

from core.config import DATA_DIR

SESSION_PATH = os.path.join(DATA_DIR, "session.json")


def _device() -> str:
    try:
        return socket.gethostname()
    except Exception:
        return "device"


def save(user_id: int, login_value: str = "") -> None:
    """Запомнить, кто вошёл."""
    data = {
        "user_id": int(user_id),
        "login": login_value,
        "device": _device(),
        "os": platform.system(),
        "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    try:
        with open(SESSION_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def load() -> dict:
    """Прочитанная сессия или пустой словарь."""
    try:
        with open(SESSION_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def user_id():
    return load().get("user_id")


def clear() -> None:
    """Забыть сессию (кнопка «Выйти»)."""
    try:
        if os.path.exists(SESSION_PATH):
            os.remove(SESSION_PATH)
    except Exception:
        pass