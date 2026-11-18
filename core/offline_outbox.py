# -*- coding: utf-8 -*-
"""Локальная очередь сообщений при оффлайне / потере связи.

Файл: data/outbox_messages.json
При реконнекте flush() пытается дослать всё по порядку.
"""

from __future__ import annotations

import json
import os
import threading
import time
import uuid
from typing import Any, Callable, Optional

from core.config import DATA_DIR

OUTBOX_PATH = os.path.join(DATA_DIR, "outbox_messages.json")
_LOCK = threading.Lock()


def _load() -> list[dict[str, Any]]:
    try:
        with open(OUTBOX_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _save(items: list[dict[str, Any]]) -> None:
    os.makedirs(os.path.dirname(OUTBOX_PATH), exist_ok=True)
    tmp = OUTBOX_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    os.replace(tmp, OUTBOX_PATH)


def enqueue(
    *,
    chat_id: str,
    text: str = "",
    attachment_path: str = "",
    reply_to_id: Optional[str] = None,
    meta: Optional[dict] = None,
) -> dict[str, Any]:
    item = {
        "id": uuid.uuid4().hex,
        "chat_id": chat_id,
        "text": text or "",
        "attachment_path": attachment_path or "",
        "reply_to_id": reply_to_id,
        "meta": meta or {},
        "created_at": time.time(),
        "attempts": 0,
    }
    with _LOCK:
        items = _load()
        items.append(item)
        _save(items)
    return item


def pending(chat_id: Optional[str] = None) -> list[dict[str, Any]]:
    with _LOCK:
        items = _load()
    if chat_id is None:
        return items
    return [i for i in items if i.get("chat_id") == chat_id]


def remove(item_id: str) -> None:
    with _LOCK:
        items = [i for i in _load() if i.get("id") != item_id]
        _save(items)


def flush(sender: Callable[[dict[str, Any]], None]) -> tuple[int, int]:
    """Дослать очередь. sender(item) — бросает исключение при неудаче.

    Возвращает (ok, failed).
    """
    with _LOCK:
        items = list(_load())

    ok = failed = 0
    remaining: list[dict[str, Any]] = []
    for item in items:
        try:
            sender(item)
            ok += 1
        except Exception:
            item["attempts"] = int(item.get("attempts") or 0) + 1
            remaining.append(item)
            failed += 1

    with _LOCK:
        # сохранить неудавшиеся + новые, появившиеся во время flush
        fresh = [i for i in _load() if i.get("id") not in {x.get("id") for x in items}]
        _save(remaining + fresh)
    return ok, failed
