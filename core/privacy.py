# -*- coding: utf-8 -*-
"""Настройки конфиденциальности пользователя (по public_id)."""
from __future__ import annotations

from typing import Any, Optional

from core import prefs

# Значения who_can_message
MSG_EVERYONE = "everyone"
MSG_CONTACTS = "contacts"
MSG_NOBODY = "nobody"

MSG_LABELS = {
    MSG_EVERYONE: "Все",
    MSG_CONTACTS: "Контакты",
    MSG_NOBODY: "Никто",
}

_DEFAULTS: dict[str, Any] = {
    "hide_phone": False,
    "hide_groups": False,
    "hide_last_seen": False,
    "hide_avatar": False,
    "hide_from_search": False,
    "who_can_message": MSG_EVERYONE,
}


def _store() -> dict[str, Any]:
    raw = prefs.get("privacy_by_user", {}) or {}
    return dict(raw) if isinstance(raw, dict) else {}


def _save_store(data: dict[str, Any]) -> None:
    prefs.set_pref("privacy_by_user", data)


def for_user(public_id: str) -> dict[str, Any]:
    pid = (public_id or "").strip()
    out = dict(_DEFAULTS)
    if not pid:
        return out
    blob = _store().get(pid)
    if isinstance(blob, dict):
        for k, v in blob.items():
            if k in _DEFAULTS:
                out[k] = v
    mode = str(out.get("who_can_message") or MSG_EVERYONE)
    if mode not in MSG_LABELS:
        mode = MSG_EVERYONE
    out["who_can_message"] = mode
    out["hide_phone"] = bool(out.get("hide_phone"))
    out["hide_groups"] = bool(out.get("hide_groups"))
    out["hide_last_seen"] = bool(out.get("hide_last_seen"))
    out["hide_avatar"] = bool(out.get("hide_avatar"))
    out["hide_from_search"] = bool(out.get("hide_from_search"))
    return out


def set_for_user(public_id: str, **kwargs) -> dict[str, Any]:
    pid = (public_id or "").strip()
    if not pid:
        return dict(_DEFAULTS)
    cur = for_user(pid)
    for k, v in kwargs.items():
        if k not in _DEFAULTS:
            continue
        if k == "who_can_message":
            mode = str(v or MSG_EVERYONE)
            cur[k] = mode if mode in MSG_LABELS else MSG_EVERYONE
        else:
            cur[k] = bool(v)
    data = _store()
    data[pid] = {k: cur[k] for k in _DEFAULTS}
    _save_store(data)
    return cur


def visible_in_search(public_id: str) -> bool:
    return not for_user(public_id).get("hide_from_search", False)


def status_for_others(public_id: str, real_status: str) -> str:
    if for_user(public_id).get("hide_last_seen"):
        return "был(а) недавно"
    return real_status or ""


def can_message(
    target_public_id: str,
    *,
    viewer_public_id: str = "",
    is_contact: bool = False,
) -> tuple[bool, str]:
    """Можно ли зрителю писать target. is_contact — уже есть в контактах."""
    pid = (target_public_id or "").strip()
    viewer = (viewer_public_id or "").strip()
    if pid and viewer and pid == viewer:
        return True, ""
    mode = for_user(pid).get("who_can_message", MSG_EVERYONE)
    if mode == MSG_EVERYONE:
        return True, ""
    if mode == MSG_NOBODY:
        return False, "Пользователь запретил новые сообщения"
    if mode == MSG_CONTACTS:
        if is_contact:
            return True, ""
        return False, "Писать могут только его контакты"
    return True, ""
