# -*- coding: utf-8 -*-
"""
RaiseHand на Flet 1.x.

В Flet 1.1 у Page больше нет .views и .go.
Навигация: page.controls + page.navigate (если есть).
"""
from __future__ import annotations

import os
import sys
import traceback

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import flet as ft

from core import database, logs
from flet_app.app_state import STATE
from flet_app import theme
from flet_app.screens import welcome, login, register, home, chat


def main(page: ft.Page):
    page.title = "RaiseHand"
    page.bgcolor = theme.BG
    page.padding = 0
    # Только мобильный UI: фиксированное окно телефона, без ресайза
    theme.lock_phone_window(page)
    theme.setup_fonts(page)
    try:
        page.theme_mode = ft.ThemeMode.LIGHT
    except Exception:
        pass
    try:
        page.theme = theme.page_theme()
    except Exception:
        pass

    try:
        database.init_db()
        logs.setup()
        logs.info("Flet RaiseHand start")
    except Exception as exc:
        page.controls.append(ft.Text(f"DB init: {exc}"))
        page.update()

    current = {"route": "/welcome"}

    def _show_dialog_control(ctrl: ft.Control) -> None:
        """Flet 1.1: show_dialog / pop_dialog (нет page.open/close и snack_bar)."""
        try:
            page.show_dialog(ctrl)
            return
        except Exception:
            pass
        try:
            # запасной путь для старых клиентов
            if hasattr(page, "overlay"):
                page.overlay.append(ctrl)
            setattr(ctrl, "open", True)
            page.update()
        except Exception:
            pass

    def _close_dialog(ctrl=None) -> None:
        try:
            page.pop_dialog()
            return
        except Exception:
            pass
        try:
            if ctrl is not None:
                setattr(ctrl, "open", False)
            page.update()
        except Exception:
            pass

    def snack(message: str):
        bar = ft.SnackBar(content=ft.Text(message))
        try:
            _show_dialog_control(bar)
        except Exception:
            pass

    def dialog(title: str, message: str):
        def close(_=None):
            _close_dialog(dlg)

        dlg = ft.AlertDialog(
            title=ft.Text(title),
            content=ft.Text(message),
            actions=[ft.TextButton("OK", on_click=close)],
        )
        try:
            _show_dialog_control(dlg)
        except Exception:
            snack(f"{title}: {message}")

    def body_for(route: str) -> ft.Control:
        route = route or "/welcome"
        builders = {
            "/": welcome.build_welcome,
            "/welcome": welcome.build_welcome,
            "/login": login.build_login,
            "/reg/name": register.build_reg_name,
            "/reg/password": register.build_reg_password,
            "/reg/school": register.build_reg_school,
            "/reg/work": register.build_reg_work,
            "/reg/proof": register.build_reg_proof,
            "/reg/contact": register.build_reg_contact,
            "/reg/done": register.build_reg_done,
            "/home": home.build_home,
            "/chat": chat.build_chat,
            "/verify": home.build_home,
            "/teacher_proof": home.build_home,
        }
        build = builders.get(route, welcome.build_welcome)
        body = build(page)

        # Всегда «телефон»: контент ровно PHONE_WIDTH
        return ft.Container(
            content=body,
            width=theme.PHONE_WIDTH,
            bgcolor=theme.BG,
            expand=True,
            alignment=ft.Alignment.TOP_CENTER,
        )

    def show_route(route: str, *, animate: bool = True):
        route = route or "/welcome"
        current["route"] = route
        try:
            page.route = route
        except Exception:
            pass

        try:
            content = body_for(route)
        except Exception as exc:
            content = ft.Column(
                controls=[
                    ft.Text("Ошибка экрана", size=22, weight=ft.FontWeight.BOLD),
                    ft.Text(str(exc), selectable=True),
                    ft.Text(traceback.format_exc(), size=11, selectable=True),
                    ft.TextButton("На welcome", on_click=lambda _: go("/welcome")),
                ],
                scroll=ft.ScrollMode.AUTO,
                expand=True,
            )

        # Только fade: затухание → появление, без slide
        if animate:
            wrap = ft.Container(
                content=content,
                expand=True,
                opacity=0,
                animate_opacity=ft.Animation(220, ft.AnimationCurve.EASE_OUT),
            )
        else:
            wrap = content

        page.controls.clear()
        page.controls.append(wrap)
        page.update()

        if animate:
            async def _play():
                import asyncio
                await asyncio.sleep(0.03)
                wrap.opacity = 1
                try:
                    wrap.update()
                except Exception:
                    pass
            try:
                page.run_task(_play)
            except Exception:
                wrap.opacity = 1
                try:
                    page.update()
                except Exception:
                    pass

    def go(route: str):
        route = route or "/welcome"
        # Не вызываем page.navigate: в Flet 1.x он сбрасывает неизвестные
        # маршруты (/reg/school и т.п.) на welcome.
        show_route(route, animate=True)

    STATE.bind(go, snack, dialog)

    def on_route_change(e=None):
        route = getattr(page, "route", None) or current["route"]
        if route != current["route"]:
            show_route(route)

    try:
        page.on_route_change = on_route_change
    except Exception:
        pass

    start = STATE.restore_session()
    go(start)


if __name__ == "__main__":
    # Flet 1.x: ft.run; старые сборки — ft.app
    if hasattr(ft, "run"):
        ft.run(main)
    elif hasattr(ft, "app"):
        ft.app(target=main)
    else:
        raise SystemExit("Flet: нет ни ft.run, ни ft.app")
