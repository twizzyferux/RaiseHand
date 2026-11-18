# -*- coding: utf-8 -*-
"""Постоянный вход: JWT-сессия, чтобы не вводить пароль каждый раз.

Сессия лежит в data/session.json рядом с базой.
Пароль не хранится — только JWT с user_id / role / public_id.
"""
from __future__ import annotations

import json
import os
import platform
import socket
from datetime import datetime
from typing import Any, Optional

from core.config import DATA_DIR
from core.security import TokenError, create_access_token, decode_access_token, token_user_id

SESSION_PATH = os.path.join(DATA_DIR, "session.json")


def _device() -> str:
    try:
        return socket.gethostname()
    except Exception:
        return "device"


def save(
    user_id: int,
    login_value: str = "",
    *,
    role: str = "",
    public_id: str = "",
    token: Optional[str] = None,
) -> str:
    """Запомнить, кто вошёл. Возвращает JWT."""
    if not public_id and login_value:
        public_id = login_value
    access_token = token or create_access_token(
        user_id, role=role, public_id=public_id, extra={"login": login_value},
    )
    data = {
        "user_id": int(user_id),
        "login": login_value,
        "role": role,
        "public_id": public_id,
        "token": access_token,
        "device": _device(),
        "os": platform.system(),
        "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    try:
        with open(SESSION_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
    return access_token


def load() -> dict:
    """Прочитанная сессия или пустой словарь."""
    try:
        with open(SESSION_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def user_id() -> Optional[int]:
    data = load()
    token = data.get("token")
    if token:
        try:
            return token_user_id(token)
        except TokenError:
            # Просроченный JWT: если в файле ещё есть user_id — не ломаем старый UX,
            # но считаем сессию «мягко» невалидной для API-слоя.
            return None
    raw = data.get("user_id")
    try:
        return int(raw) if raw is not None else None
    except (TypeError, ValueError):
        return None


def get_token() -> Optional[str]:
    token = load().get("token")
    return str(token) if token else None


def payload() -> dict[str, Any]:
    """Полезная нагрузка JWT или {}."""
    token = get_token()
    if not token:
        return {}
    try:
        return decode_access_token(token)
    except TokenError:
        return {}


def clear() -> None:
    """Забыть сессию (кнопка «Выйти»)."""
    try:
        if os.path.exists(SESSION_PATH):
            os.remove(SESSION_PATH)
    except Exception:
        pass
