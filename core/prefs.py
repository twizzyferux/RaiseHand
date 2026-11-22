# -*- coding: utf-8 -*-
"""Локальные настройки устройства: звук, тема."""
from __future__ import annotations

import json
import os
from typing import Any

from core.config import DATA_DIR

_PATH = os.path.join(DATA_DIR, "prefs.json")
_DEFAULTS = {
    "sounds_enabled": True,
    "theme_mode": "light",  # light | dark
    "push_enabled": True,
    "notif_private": True,
    "notif_groups": True,
    "notif_preview": True,
    "sound_incoming": True,
    "sound_outgoing": False,
    "sound_volume": 0.7,  # 0.15 … 1.0
    "contact_aliases": {},  # contact_id → локальное имя
    "accent_theme": "violet",  # violet|pink|blue|coral|green|orange
    "bubble_theme": "violet",  # цвет исходящих пузырей
    "app_icon": "violet",  # ключ иконки приложения
    "language": "ru",  # ru|en|kk|be|uk|de|fr|es|zh|tr
    "privacy_by_user": {},  # public_id → настройки конфиденциальности
    "blacklist_by_owner": {},  # owner_public_id → { target_pid → meta }
}


def _load() -> dict[str, Any]:
    if not os.path.isfile(_PATH):
        return dict(_DEFAULTS)
    try:
        with open(_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return dict(_DEFAULTS)
        out = dict(_DEFAULTS)
        out.update(data)
        return out
    except Exception:
        return dict(_DEFAULTS)


def _save(data: dict[str, Any]) -> None:
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def get(key: str, default=None):
    data = _load()
    return data.get(key, _DEFAULTS.get(key, default))


def set_pref(key: str, value) -> None:
    data = _load()
    data[key] = value
    _save(data)


def sounds_enabled() -> bool:
    return bool(get("sounds_enabled", True))


def set_sounds_enabled(on: bool) -> None:
    set_pref("sounds_enabled", bool(on))


def theme_mode() -> str:
    mode = str(get("theme_mode", "light") or "light").lower()
    return "dark" if mode == "dark" else "light"


def set_theme_mode(mode: str) -> None:
    set_pref("theme_mode", "dark" if str(mode).lower() == "dark" else "light")


def push_enabled() -> bool:
    return bool(get("push_enabled", True))


def set_push_enabled(on: bool) -> None:
    set_pref("push_enabled", bool(on))


def notif_private() -> bool:
    return bool(get("notif_private", True))


def set_notif_private(on: bool) -> None:
    set_pref("notif_private", bool(on))


def notif_groups() -> bool:
    return bool(get("notif_groups", True))


def set_notif_groups(on: bool) -> None:
    set_pref("notif_groups", bool(on))


def notif_preview() -> bool:
    return bool(get("notif_preview", True))


def set_notif_preview(on: bool) -> None:
    set_pref("notif_preview", bool(on))


def notif_allowed(*, is_group: bool = False) -> bool:
    """Можно ли показывать уведомление для этого типа чата."""
    if not push_enabled():
        return False
    return notif_groups() if is_group else notif_private()


def sound_incoming() -> bool:
    return bool(get("sound_incoming", True))


def set_sound_incoming(on: bool) -> None:
    set_pref("sound_incoming", bool(on))


def sound_outgoing() -> bool:
    return bool(get("sound_outgoing", False))


def set_sound_outgoing(on: bool) -> None:
    set_pref("sound_outgoing", bool(on))


def sound_volume() -> float:
    try:
        vol = float(get("sound_volume", 0.7) or 0.7)
    except (TypeError, ValueError):
        vol = 0.7
    return max(0.15, min(1.0, vol))


def set_sound_volume(vol: float) -> None:
    try:
        v = float(vol)
    except (TypeError, ValueError):
        v = 0.7
    set_pref("sound_volume", max(0.15, min(1.0, v)))


def contact_aliases() -> dict:
    raw = get("contact_aliases", {}) or {}
    return dict(raw) if isinstance(raw, dict) else {}


def get_contact_alias(contact_id: str) -> str:
    return str(contact_aliases().get(str(contact_id), "") or "")


def set_contact_alias(contact_id: str, alias: str) -> None:
    data = contact_aliases()
    key = str(contact_id)
    alias = (alias or "").strip()
    if alias:
        data[key] = alias
    else:
        data.pop(key, None)
    set_pref("contact_aliases", data)


_VALID_THEMES = ("violet", "pink", "blue", "coral", "green", "orange")


def _theme_key(raw: str, default: str = "violet") -> str:
    key = str(raw or default).strip().lower()
    return key if key in _VALID_THEMES else default


def accent_theme() -> str:
    return _theme_key(get("accent_theme", "violet"))


def set_accent_theme(key: str) -> None:
    set_pref("accent_theme", _theme_key(key))


def bubble_theme() -> str:
    return _theme_key(get("bubble_theme", accent_theme()))


def set_bubble_theme(key: str) -> None:
    set_pref("bubble_theme", _theme_key(key))


def app_icon_key() -> str:
    return _theme_key(get("app_icon", "violet"))


def set_app_icon_key(key: str) -> None:
    set_pref("app_icon", _theme_key(key))


_VALID_LANGS = ("ru", "en", "kk", "be", "uk", "de", "fr", "es", "zh", "tr")


def language() -> str:
    raw = str(get("language", "ru") or "ru").strip().lower()
    return raw if raw in _VALID_LANGS else "ru"


def set_language(code: str) -> None:
    key = str(code or "ru").strip().lower()
    set_pref("language", key if key in _VALID_LANGS else "ru")
