# -*- coding: utf-8 -*-
"""Хеширование паролей (bcrypt; passlib совместим по формату $2b$) и JWT-сессии.

Новые пароли — bcrypt.
Старые PBKDF2-SHA256 (password_hash + password_salt) продолжают проверяться,
чтобы не ломать уже созданные аккаунты.
"""

from __future__ import annotations

import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import bcrypt
import jwt

from core.config import SETTINGS, rule

PBKDF2_ITERATIONS = 200_000
JWT_ALGORITHM = "HS256"
BCRYPT_ROUNDS = 12


class TokenError(Exception):
    """Токен невалиден или просрочен."""


def _jwt_secret() -> str:
    secret = (
        os.environ.get("RH_JWT_SECRET")
        or os.environ.get("JWT_SECRET")
        or SETTINGS.get("jwt", {}).get("secret")
    )
    if secret:
        return str(secret)
    # Учебный fallback: стабильный, но не для продакшена.
    return "raisehand-dev-jwt-secret-change-me"


def _jwt_ttl_hours() -> int:
    jwt_cfg = SETTINGS.get("jwt") or {}
    if "ttl_hours" in jwt_cfg:
        return int(jwt_cfg["ttl_hours"])
    return 24 * 30  # месяц по умолчанию


def _truncate_password(password: str) -> str:
    raw = password.encode("utf-8")
    if len(raw) <= 72:
        return password
    return raw[:72].decode("utf-8", errors="ignore")


def hash_password(password: str) -> tuple[str, str]:
    """Вернуть (hash, salt). Для bcrypt salt внутри hash, второй элемент — ''."""
    raw = _truncate_password(password).encode("utf-8")
    digest = bcrypt.hashpw(raw, bcrypt.gensalt(rounds=BCRYPT_ROUNDS))
    return digest.decode("ascii"), ""


def hash_password_pbkdf2(password: str, salt: Optional[bytes] = None) -> tuple[str, str]:
    """Старый формат — только для миграционных проверок."""
    if salt is None:
        salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )
    return digest.hex(), salt.hex()


def verify_password(password: str, password_hash: str, salt_hex: str = "") -> bool:
    if not password_hash:
        return False
    # Новый формат: bcrypt ($2a$ / $2b$ / $2y$) — тот же, что у passlib.
    if password_hash.startswith("$2"):
        try:
            raw = _truncate_password(password).encode("utf-8")
            return bcrypt.checkpw(raw, password_hash.encode("ascii"))
        except (ValueError, TypeError):
            return False
    # Старый PBKDF2
    if not salt_hex:
        return False
    try:
        digest, _ = hash_password_pbkdf2(password, bytes.fromhex(salt_hex))
        return secrets.compare_digest(digest, password_hash)
    except (ValueError, TypeError):
        return False


def needs_rehash(password_hash: str) -> bool:
    """True, если после входа стоит переписать хеш в bcrypt."""
    return not (password_hash or "").startswith("$2")

def create_access_token(
    user_id: int,
    *,
    role: str = "",
    public_id: str = "",
    extra: Optional[dict[str, Any]] = None,
    ttl_hours: Optional[int] = None,
) -> str:
    now = datetime.now(timezone.utc)
    hours = _jwt_ttl_hours() if ttl_hours is None else ttl_hours
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "role": role,
        "pid": public_id,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=hours)).timestamp()),
        "jti": secrets.token_urlsafe(12),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, _jwt_secret(), algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, _jwt_secret(), algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise TokenError("Сессия истекла — войдите снова") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenError("Недействительная сессия") from exc


def token_user_id(token: str) -> int:
    payload = decode_access_token(token)
    try:
        return int(payload["sub"])
    except (KeyError, TypeError, ValueError) as exc:
        raise TokenError("Недействительная сессия") from exc


def min_password_length() -> int:
    return int(rule("min_password_length") or 6)
