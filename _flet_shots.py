# -*- coding: utf-8 -*-
"""Снимает скриншоты экранов Flet-приложения в _flet_shots/."""
from __future__ import annotations

import asyncio
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import flet as ft

from flet_app.main import main as app_main
from flet_app.app_state import STATE

OUT = os.path.join(ROOT, "_flet_shots")
os.makedirs(OUT, exist_ok=True)

ROUTES = [
    ("01_welcome", "/welcome"),
    ("02_login", "/login"),
    ("03_reg_name", "/reg/name"),
    ("04_reg_password", "/reg/password"),
    ("05_reg_school", "/reg/school"),
    ("06_reg_contact", "/reg/contact"),
    ("07_reg_done", "/reg/done"),
    ("08_home", "/home"),
]


async def shoot(page: ft.Page):
    await asyncio.sleep(2.5)
    for name, route in ROUTES:
        try:
            STATE.go(route)
        except Exception as exc:
            print("go err", route, exc)
        await asyncio.sleep(1.3)
        try:
            data = await page.take_screenshot(pixel_ratio=2)
            path = os.path.join(OUT, f"{name}.png")
            with open(path, "wb") as f:
                f.write(data)
            print("saved", path)
        except Exception as exc:
            print("shot err", name, exc)
    await asyncio.sleep(0.3)
    try:
        await page.window.close()
    except Exception:
        pass


def target(page: ft.Page):
    try:
        page.enable_screenshots = True
    except Exception:
        pass
    try:
        page.run_task(shoot, page)
    except Exception as exc:
        print("run_task err", exc)
    app_main(page)


if __name__ == "__main__":
    ft.run(target)
