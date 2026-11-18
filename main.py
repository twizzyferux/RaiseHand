# -*- coding: utf-8 -*-
"""Точка входа для `flet build` / desktop: модуль `main.py` в корне проекта."""
from __future__ import annotations

from flet_app.main import main

__all__ = ["main"]


if __name__ == "__main__":
    import flet as ft

    from flet_app.main import start_discord_bot
    from core.config import get_app_platform
    import threading

    if get_app_platform() not in ("ios", "android"):
        threading.Thread(target=start_discord_bot, daemon=True).start()

    if hasattr(ft, "run"):
        ft.run(main)
    elif hasattr(ft, "app"):
        ft.app(target=main)
    else:
        raise SystemExit("Flet: нет ни ft.run, ни ft.app")
