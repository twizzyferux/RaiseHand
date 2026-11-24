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
    # чат и ввод
    "chat_enter_to_send": True,
    "chat_send_by_ctrl_enter": False,
    # медиа и данные
    "media_auto_download_wifi": True,
    "media_auto_download_mobile": False,
    "save_to_gallery": True,
    "data_cache_images": True,
    "data_clear_on_logout": False,
    "link_previews": True,
    # внешний вид
    "reduce_motion": False,
    "frame_rate": 120,  # 60 | 120
    "haptic_feedback": True,
    "font_scale": 1.0,
    "bubble_corners": "round",  # sharp|round|super
    "chat_bg_dim": 0.0,
    "show_message_time": True,
    # конфиденциальность (локальные сигналы)
    "show_read_receipts_send": True,
    "show_typing": True,
    # уведомления (доп.)
    "notif_questions": True,
    "notif_mentions_only_groups": False,
    "notif_sound_name": "default",  # default|soft|none
    "notif_quiet_hours": False,
    "quiet_hours_start": "22:00",
    "quiet_hours_end": "08:00",
    # жесты и чат
    "double_tap_like_react": True,
    "swipe_to_reply": True,
    "spellcheck": True,
    "keep_screen_on_chat": False,
}


_cache: dict[str, Any] | None = None


def _load() -> dict[str, Any]:
    """Загрузить prefs с диска один раз; дальше — in-memory кэш."""
    global _cache
    if _cache is not None:
        return _cache
    if not os.path.isfile(_PATH):
        _cache = dict(_DEFAULTS)
        return _cache
    try:
        with open(_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            _cache = dict(_DEFAULTS)
            return _cache
        out = dict(_DEFAULTS)
        out.update(data)
        _cache = out
        return _cache
    except Exception:
        _cache = dict(_DEFAULTS)
        return _cache


def _save(data: dict[str, Any]) -> None:
    global _cache
    _cache = data
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
    if key == "language":
        try:
            from core import i18n as _i18n

            _i18n.invalidate_cache()
        except Exception:
            pass


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


def _bool_val(key: str, default: bool = True) -> bool:
    return bool(get(key, default))


def _set_bool_val(key: str, on: bool) -> None:
    set_pref(key, bool(on))


def _float_clamp(key: str, default: float, lo: float, hi: float) -> float:
    try:
        v = float(get(key, default) or default)
    except (TypeError, ValueError):
        v = default
    return max(lo, min(hi, v))


def _set_float_clamp(key: str, value: float, lo: float, hi: float) -> None:
    try:
        v = float(value)
    except (TypeError, ValueError):
        v = lo
    set_pref(key, max(lo, min(hi, v)))


_BUBBLE_CORNERS = ("sharp", "round", "super")
_NOTIF_SOUNDS = ("default", "soft", "none")


def _choice_key(key: str, valid: tuple[str, ...], default: str) -> str:
    raw = str(get(key, default) or default).strip().lower()
    return raw if raw in valid else default


def _set_choice(key: str, value: str, valid: tuple[str, ...], default: str) -> None:
    raw = str(value or default).strip().lower()
    set_pref(key, raw if raw in valid else default)


def chat_enter_to_send() -> bool:
    return _bool_val("chat_enter_to_send", True)


def set_chat_enter_to_send(on: bool) -> None:
    _set_bool_val("chat_enter_to_send", on)


def chat_send_by_ctrl_enter() -> bool:
    return _bool_val("chat_send_by_ctrl_enter", False)


def set_chat_send_by_ctrl_enter(on: bool) -> None:
    _set_bool_val("chat_send_by_ctrl_enter", on)


def media_auto_download_wifi() -> bool:
    return _bool_val("media_auto_download_wifi", True)


def set_media_auto_download_wifi(on: bool) -> None:
    _set_bool_val("media_auto_download_wifi", on)


def media_auto_download_mobile() -> bool:
    return _bool_val("media_auto_download_mobile", False)


def set_media_auto_download_mobile(on: bool) -> None:
    _set_bool_val("media_auto_download_mobile", on)


def save_to_gallery() -> bool:
    return _bool_val("save_to_gallery", True)


def set_save_to_gallery(on: bool) -> None:
    _set_bool_val("save_to_gallery", on)


def data_cache_images() -> bool:
    return _bool_val("data_cache_images", True)


def set_data_cache_images(on: bool) -> None:
    _set_bool_val("data_cache_images", on)


def data_clear_on_logout() -> bool:
    return _bool_val("data_clear_on_logout", False)


def set_data_clear_on_logout(on: bool) -> None:
    _set_bool_val("data_clear_on_logout", on)


def link_previews() -> bool:
    return _bool_val("link_previews", True)


def set_link_previews(on: bool) -> None:
    _set_bool_val("link_previews", on)


def reduce_motion() -> bool:
    return _bool_val("reduce_motion", False)


def set_reduce_motion(on: bool) -> None:
    _set_bool_val("reduce_motion", on)


def frame_rate() -> int:
    """60 или 120 кадров. Всё остальное считается как 60."""
    try:
        rate = int(get("frame_rate", 120) or 120)
    except (TypeError, ValueError):
        rate = 120
    return 120 if rate >= 120 else 60


def set_frame_rate(rate: int) -> None:
    set_pref("frame_rate", 120 if int(rate) >= 120 else 60)


def scroll_interval_ms() -> int:
    """Интервал событий прокрутки: 120 Гц → 8 мс, 60 Гц → 16 мс."""
    return 8 if frame_rate() >= 120 else 16


def haptic_feedback() -> bool:
    return _bool_val("haptic_feedback", True)


def set_haptic_feedback(on: bool) -> None:
    _set_bool_val("haptic_feedback", on)


def font_scale() -> float:
    return _float_clamp("font_scale", 1.0, 0.85, 1.25)


def set_font_scale(scale: float) -> None:
    _set_float_clamp("font_scale", scale, 0.85, 1.25)


def bubble_corners() -> str:
    return _choice_key("bubble_corners", _BUBBLE_CORNERS, "round")


def set_bubble_corners(style: str) -> None:
    _set_choice("bubble_corners", style, _BUBBLE_CORNERS, "round")


def chat_bg_dim() -> float:
    return _float_clamp("chat_bg_dim", 0.0, 0.0, 0.4)


def set_chat_bg_dim(dim: float) -> None:
    _set_float_clamp("chat_bg_dim", dim, 0.0, 0.4)


def show_message_time() -> bool:
    return _bool_val("show_message_time", True)


def set_show_message_time(on: bool) -> None:
    _set_bool_val("show_message_time", on)


def show_read_receipts_send() -> bool:
    return _bool_val("show_read_receipts_send", True)


def set_show_read_receipts_send(on: bool) -> None:
    _set_bool_val("show_read_receipts_send", on)


def show_typing() -> bool:
    return _bool_val("show_typing", True)


def set_show_typing(on: bool) -> None:
    _set_bool_val("show_typing", on)


def notif_questions() -> bool:
    return _bool_val("notif_questions", True)


def set_notif_questions(on: bool) -> None:
    _set_bool_val("notif_questions", on)


def notif_mentions_only_groups() -> bool:
    return _bool_val("notif_mentions_only_groups", False)


def set_notif_mentions_only_groups(on: bool) -> None:
    _set_bool_val("notif_mentions_only_groups", on)


def notif_sound_name() -> str:
    return _choice_key("notif_sound_name", _NOTIF_SOUNDS, "default")


def set_notif_sound_name(name: str) -> None:
    _set_choice("notif_sound_name", name, _NOTIF_SOUNDS, "default")


def notif_quiet_hours() -> bool:
    return _bool_val("notif_quiet_hours", False)


def set_notif_quiet_hours(on: bool) -> None:
    _set_bool_val("notif_quiet_hours", on)


def quiet_hours_start() -> str:
    return str(get("quiet_hours_start", "22:00") or "22:00")


def set_quiet_hours_start(value: str) -> None:
    set_pref("quiet_hours_start", (value or "22:00").strip() or "22:00")


def quiet_hours_end() -> str:
    return str(get("quiet_hours_end", "08:00") or "08:00")


def set_quiet_hours_end(value: str) -> None:
    set_pref("quiet_hours_end", (value or "08:00").strip() or "08:00")


def double_tap_like_react() -> bool:
    return _bool_val("double_tap_like_react", True)


def set_double_tap_like_react(on: bool) -> None:
    _set_bool_val("double_tap_like_react", on)


def swipe_to_reply() -> bool:
    return _bool_val("swipe_to_reply", True)


def set_swipe_to_reply(on: bool) -> None:
    _set_bool_val("swipe_to_reply", on)


def spellcheck() -> bool:
    return _bool_val("spellcheck", True)


def set_spellcheck(on: bool) -> None:
    _set_bool_val("spellcheck", on)


def keep_screen_on_chat() -> bool:
    return _bool_val("keep_screen_on_chat", False)


def set_keep_screen_on_chat(on: bool) -> None:
    _set_bool_val("keep_screen_on_chat", on)


def _parse_hhmm(raw: str) -> int | None:
    """Минуты с полуночи или None."""
    text = (raw or "").strip()
    if not text:
        return None
    parts = text.replace(".", ":").split(":")
    if len(parts) < 2:
        return None
    try:
        h = int(parts[0])
        m = int(parts[1])
    except ValueError:
        return None
    if h < 0 or h > 23 or m < 0 or m > 59:
        return None
    return h * 60 + m


def in_quiet_hours() -> bool:
    """Тихие часы активны сейчас (локальное время)."""
    if not notif_quiet_hours():
        return False
    start = _parse_hhmm(quiet_hours_start())
    end = _parse_hhmm(quiet_hours_end())
    if start is None or end is None:
        return False
    from datetime import datetime

    now = datetime.now()
    cur = now.hour * 60 + now.minute
    if start <= end:
        return start <= cur < end
    # через полночь, напр. 22:00 — 08:00
    return cur >= start or cur < end
