# -*- coding: utf-8 -*-
"""Простой rate-limiter в памяти (на процесс).

Ключ — строка (user_id, IP, email…). При желании позже можно заменить
хранилище на Redis, сохранив тот же API.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Deque, Dict, Optional


class RateLimitError(Exception):
    """Слишком много запросов — текст можно показать пользователю."""


@dataclass
class _Bucket:
    hits: Deque[float]
    blocked_until: float = 0.0


_LOCK = threading.Lock()
_BUCKETS: Dict[str, _Bucket] = defaultdict(lambda: _Bucket(hits=deque()))


def reset(key: Optional[str] = None) -> None:
    """Сброс (для тестов)."""
    with _LOCK:
        if key is None:
            _BUCKETS.clear()
        else:
            _BUCKETS.pop(key, None)


def check(
    key: str,
    *,
    limit: int = 5,
    window_sec: float = 60.0,
    block_sec: float = 60.0,
    action: str = "request",
) -> None:
    """Разрешить действие или бросить RateLimitError.

    limit событий за window_sec; при превышении — блок на block_sec.
    """
    now = time.monotonic()
    with _LOCK:
        bucket = _BUCKETS[key]
        if bucket.blocked_until > now:
            wait = int(bucket.blocked_until - now) + 1
            raise RateLimitError(
                f"Слишком много попыток ({action}). Подождите {wait} сек."
            )
        # вычистить старые
        while bucket.hits and bucket.hits[0] <= now - window_sec:
            bucket.hits.popleft()
        if len(bucket.hits) >= limit:
            bucket.blocked_until = now + block_sec
            bucket.hits.clear()
            raise RateLimitError(
                f"Слишком много попыток ({action}). Подождите {int(block_sec)} сек."
            )
        bucket.hits.append(now)


def allow(key: str, **kwargs) -> bool:
    try:
        check(key, **kwargs)
        return True
    except RateLimitError:
        return False
