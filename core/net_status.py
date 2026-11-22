# -*- coding: utf-8 -*-
"""Глобальный статус сети (реальный probe, не только Flet disconnect)."""
from __future__ import annotations

import socket
import threading
import time
from typing import Callable, Optional

_online = True
_lock = threading.Lock()
_stop = threading.Event()
_thread: Optional[threading.Thread] = None
_PROBE_HOSTS = (
    ("1.1.1.1", 443),
    ("8.8.8.8", 53),
)


def is_online() -> bool:
    with _lock:
        return bool(_online)


def set_online(value: bool) -> bool:
    """Обновить флаг. True, если значение изменилось."""
    global _online
    v = bool(value)
    with _lock:
        changed = _online != v
        _online = v
    return changed


def probe(timeout: float = 1.5) -> bool:
    """Быстрая проверка исходящего TCP — ловит airplane mode / нет DNS."""
    for host, port in _PROBE_HOSTS:
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except OSError:
            continue
    return False


def refresh() -> bool:
    """Probe + set. Возвращает актуальное is_online()."""
    ok = probe()
    set_online(ok)
    return ok


def start_watcher(
    on_change: Optional[Callable[[bool], None]] = None,
    *,
    interval: float = 3.0,
) -> None:
    """Фоновый опрос сети. Безопасно вызывать повторно."""
    global _thread
    _stop.clear()

    def _loop():
        prev = None
        while not _stop.is_set():
            ok = probe()
            changed = set_online(ok)
            if prev is None or changed:
                prev = ok
                if on_change is not None:
                    try:
                        on_change(ok)
                    except Exception:
                        pass
            _stop.wait(interval)

    if _thread is not None and _thread.is_alive():
        return
    _thread = threading.Thread(target=_loop, name="net-status", daemon=True)
    _thread.start()


def stop_watcher() -> None:
    _stop.set()
