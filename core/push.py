# -*- coding: utf-8 -*-
"""Локальные push/уведомления (когда приложение открыто — snack; иначе попытка OS toast)."""
from __future__ import annotations

import threading
from typing import Callable, Optional

from core import logs, prefs

_snack: Optional[Callable[[str], None]] = None


def bind_snack(fn: Callable[[str], None]) -> None:
    global _snack
    _snack = fn


def notify(title: str, body: str = "") -> None:
    """Показать уведомление, если включено в настройках."""
    if not prefs.push_enabled():
        return
    text = f"{title}: {body}".strip(": ").strip() if body else title
    logs.info("push %s", text)

    if _snack is not None:
        try:
            _snack(text)
            return
        except Exception:
            pass

    def _os_toast():
        try:
            # Windows 10+ toast через powershell (без внешних пакетов)
            import platform
            import subprocess

            if platform.system() != "Windows":
                return
            safe_title = (title or "RaiseHand").replace("'", "")
            safe_body = (body or "").replace("'", "")
            ps = (
                "[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, "
                "ContentType = WindowsRuntime] > $null; "
                "$template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent("
                "[Windows.UI.Notifications.ToastTemplateType]::ToastText02); "
                "$text = $template.GetElementsByTagName('text'); "
                f"$text.Item(0).AppendChild($template.CreateTextNode('{safe_title}')) | Out-Null; "
                f"$text.Item(1).AppendChild($template.CreateTextNode('{safe_body}')) | Out-Null; "
                "$toast = [Windows.UI.Notifications.ToastNotification]::new($template); "
                "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('RaiseHand')"
                ".Show($toast);"
            )
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps],
                check=False,
                capture_output=True,
                timeout=5,
            )
        except Exception as exc:
            logs.warn("toast failed: %s", exc)

    threading.Thread(target=_os_toast, daemon=True).start()
