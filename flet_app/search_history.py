# -*- coding: utf-8 -*-
"""Активная история поиска аккаунтов (по public_id)."""
from __future__ import annotations

import json
import os
from typing import Any, Optional

from core.config import DATA_DIR

MAX_ITEMS = 24


def _path(owner_id: int) -> str:
    return os.path.join(DATA_DIR, f"search_history_{int(owner_id)}.json")


def load(owner_id: int) -> list[dict[str, Any]]:
    path = _path(owner_id)
    if not os.path.isfile(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            return []
        out: list[dict[str, Any]] = []
        for item in data:
            if isinstance(item, dict) and item.get("public_id"):
                out.append(item)
        return out
    except Exception:
        return []


def _save(owner_id: int, items: list[dict[str, Any]]) -> None:
    path = _path(owner_id)
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(items[:MAX_ITEMS], f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def remember(
    owner_id: int,
    *,
    public_id: str,
    name: str,
    first: str = "",
    last: str = "",
    status: str = "",
    role: str = "",
) -> None:
    pid = (public_id or "").strip()
    if not pid:
        return
    items = [i for i in load(owner_id) if str(i.get("public_id")) != pid]
    items.insert(
        0,
        {
            "public_id": pid,
            "name": name or pid,
            "first": first or "",
            "last": last or "",
            "status": status or "",
            "role": role or "",
        },
    )
    _save(owner_id, items)


def forget(owner_id: int, public_id: str) -> None:
    pid = (public_id or "").strip()
    if not pid:
        return
    items = [i for i in load(owner_id) if str(i.get("public_id")) != pid]
    _save(owner_id, items)


def clear(owner_id: int) -> None:
    _save(owner_id, [])


def entry_to_contact_fields(entry: dict[str, Any]) -> dict[str, str]:
    return {
        "public_id": str(entry.get("public_id") or ""),
        "name": str(entry.get("name") or entry.get("public_id") or ""),
        "first": str(entry.get("first") or ""),
        "last": str(entry.get("last") or ""),
        "status": str(entry.get("status") or ""),
        "role": str(entry.get("role") or ""),
    }
