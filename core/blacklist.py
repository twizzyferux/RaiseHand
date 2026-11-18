# -*- coding: utf-8 -*-
"""Чёрный список: owner_public_id → заблокированные public_id."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from core import prefs

_PREF_KEY = "blacklist_by_owner"


def _store() -> dict[str, Any]:
    raw = prefs.get(_PREF_KEY, {}) or {}
    return dict(raw) if isinstance(raw, dict) else {}


def _save(data: dict[str, Any]) -> None:
    prefs.set_pref(_PREF_KEY, data)


def _owner_map(owner_public_id: str) -> dict[str, Any]:
    oid = (owner_public_id or "").strip()
    if not oid:
        return {}
    blob = _store().get(oid)
    return dict(blob) if isinstance(blob, dict) else {}


def is_blocked(owner_public_id: str, target_public_id: str) -> bool:
    oid = (owner_public_id or "").strip()
    tid = (target_public_id or "").strip()
    if not oid or not tid or oid == tid:
        return False
    return tid in _owner_map(oid)


def block(
    owner_public_id: str,
    target_public_id: str,
    *,
    name: str = "",
) -> bool:
    """Добавить в ЧС. True если добавлен (или уже был)."""
    oid = (owner_public_id or "").strip()
    tid = (target_public_id or "").strip()
    if not oid or not tid or oid == tid:
        return False
    data = _store()
    bucket = dict(data.get(oid) or {}) if isinstance(data.get(oid), dict) else {}
    prev = bucket.get(tid) if isinstance(bucket.get(tid), dict) else {}
    bucket[tid] = {
        "name": (name or (prev or {}).get("name") or tid).strip(),
        "blocked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    data[oid] = bucket
    _save(data)
    return True


def unblock(owner_public_id: str, target_public_id: str) -> bool:
    oid = (owner_public_id or "").strip()
    tid = (target_public_id or "").strip()
    if not oid or not tid:
        return False
    data = _store()
    bucket = dict(data.get(oid) or {}) if isinstance(data.get(oid), dict) else {}
    if tid not in bucket:
        return False
    bucket.pop(tid, None)
    if bucket:
        data[oid] = bucket
    else:
        data.pop(oid, None)
    _save(data)
    return True


def list_blocked(owner_public_id: str) -> list[dict[str, str]]:
    """Список {public_id, name, blocked_at}."""
    bucket = _owner_map(owner_public_id)
    out: list[dict[str, str]] = []
    for tid, meta in bucket.items():
        if not isinstance(meta, dict):
            meta = {}
        out.append(
            {
                "public_id": str(tid),
                "name": str(meta.get("name") or tid),
                "blocked_at": str(meta.get("blocked_at") or ""),
            }
        )
    out.sort(key=lambda x: (x.get("name") or "").lower())
    return out


def public_id_from_contact_id(contact_id: str) -> Optional[str]:
    cid = str(contact_id or "")
    if cid.startswith("u:"):
        return cid[2:].strip() or None
    return None
