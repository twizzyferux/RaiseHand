# -*- coding: utf-8 -*-
"""Генерация уникальных public_id и ников."""

from __future__ import annotations

import random
import re
import secrets
import unicodedata
from typing import Callable, Optional

from core.config import rule
from core.models import RoleCode

# Транслит для ника из кириллицы.
_TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
    "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "h", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sch",
    "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}


def role_id_prefix(role: str) -> str:
    role = (role or "").lower()
    if role == RoleCode.TEACHER.value:
        return str(rule("teacher_id_prefix") or "U")
    if role == RoleCode.ADMIN.value:
        return str(rule("admin_id_prefix") or "A")
    return ""


def id_digits() -> int:
    return int(rule("student_id_digits") or 7)


def generate_public_id(
    role: str,
    *,
    exists: Callable[[str], bool],
    max_attempts: int = 64,
) -> str:
    """Уникальный ID: ученик 7 цифр, учитель U+цифры, админ A+цифры."""
    digits = id_digits()
    prefix = role_id_prefix(role)
    for _ in range(max_attempts):
        number = "".join(str(random.randint(0, 9)) for _ in range(digits))
        candidate = f"{prefix}{number}"
        if not exists(candidate):
            return candidate
    raise RuntimeError("Не удалось сгенерировать уникальный ID")


def _slugify_name(value: str) -> str:
    value = (value or "").strip().lower().replace("ё", "е")
    out = []
    for ch in value:
        if ch in _TRANSLIT:
            out.append(_TRANSLIT[ch])
        elif ("a" <= ch <= "z") or ("0" <= ch <= "9"):
            out.append(ch)
        elif ch in "._-":
            out.append("_")
        elif unicodedata.category(ch).startswith("L"):
            # прочие буквы — пропускаем, чтобы ник оставался ASCII-дружелюбным
            continue
    slug = re.sub(r"_+", "_", "".join(out)).strip("_")
    return slug[:20]


def generate_nickname(
    first_name: str = "",
    last_name: str = "",
    *,
    exists: Callable[[str], bool],
    public_id: str = "",
    max_attempts: int = 48,
) -> str:
    """Уникальный ник: из имени/фамилии + суффикс, иначе user_<id>."""
    base = _slugify_name(first_name) or _slugify_name(last_name)
    if not base:
        digits = re.sub(r"\D", "", public_id) or secrets.token_hex(3)
        base = f"user{digits[-6:]}"

    min_len = int(rule("nickname_min_length") or 3)
    if len(base) < min_len:
        base = (base + "user")[:min_len]

    candidates = [base]
    if last_name:
        combo = _slugify_name(f"{first_name}_{last_name}")
        if combo and combo != base:
            candidates.append(combo)

    for candidate in candidates:
        if not exists(candidate):
            return candidate

    for _ in range(max_attempts):
        suffix = secrets.randbelow(9000) + 1000
        candidate = f"{base}{suffix}"
        if not exists(candidate):
            return candidate

    fallback = f"user_{secrets.token_hex(4)}"
    if not exists(fallback):
        return fallback
    raise RuntimeError("Не удалось сгенерировать уникальный ник")


def normalize_public_id(value: str) -> str:
    value = (value or "").strip()
    if value[:1].lower() in ("u", "a") and value[1:].isdigit():
        return value[:1].upper() + value[1:]
    return value
