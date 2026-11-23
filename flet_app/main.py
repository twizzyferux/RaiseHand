# -*- coding: utf-8 -*-
"""
RaiseHand на Flet 1.x.
"""
from __future__ import annotations

import os
import sys
import traceback
import threading

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import flet as ft

from core import database, logs, prefs, push
from core.config import get_app_platform

from flet_app.app_state import STATE
from flet_app import theme
from flet_app.screens import (
    welcome,
    login,
    register,
    home,
    chat,
    questions,
    settings_pages,
    contact_profile,
    report,
    new_chat,
)


def main(page: ft.Page):
    page.title = "RaiseHand"
    page.padding = 0
    # Десктоп: окно-телефон; iOS/Android: полный экран + SafeArea
    theme.lock_phone_window(page)
    theme.sync_viewport(page)
    theme.setup_fonts(page)
    try:
        theme.apply_mode(page, prefs.theme_mode())
    except Exception:
        try:
            page.theme_mode = ft.ThemeMode.LIGHT
            page.bgcolor = theme.BG
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
        try:
            logs.error("DB init failed: %s", exc)
        except Exception:
            pass
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
            "/new_chat": new_chat.build_new_chat,
            "/new_group": new_chat.build_new_group,
            "/questions": questions.build_questions,
            "/verify": home.build_home,
            "/teacher_proof": home.build_home,
        }
        builders.update(settings_pages.register_routes())
        builders.update(contact_profile.register_routes())
        builders.update(report.register_routes())
        build = builders.get(route)
        if build is None and route.startswith("/contact/"):
            cid = route[len("/contact/") :].strip()
            build = lambda page, _cid=cid: contact_profile.build_contact_profile(page, _cid)
        if build is None:
            build = welcome.build_welcome
        body = build(page)

        # SafeArea: Dynamic Island / статус-бар
        return theme.safe_shell(
            ft.Container(
                content=body,
                bgcolor=theme.BG,
                expand=True,
                alignment=ft.Alignment.TOP_CENTER,
                clip_behavior=ft.ClipBehavior.HARD_EDGE,
            )
        )

    def show_route(route: str, *, animate: bool = True):
        route = route or "/welcome"
        prev = current.get("route") or ""
        current["route"] = route
        try:
            page.route = route
        except Exception:
            pass

        theme.sync_viewport(page)

        # смена цвета/темы в оформлении — без повторного slide
        quiet_settings = bool(STATE.draft.get("_settings_no_anim"))

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

        to_sheet = (
            route.startswith("/contact")
            or route.startswith("/settings/")
            or route == "/report"
        )
        from_sheet = (
            (
                (prev or "").startswith("/contact")
                or (prev or "").startswith("/settings/")
                or prev == "/report"
            )
            and not to_sheet
        )
        to_chat = route in ("/chat", "/questions")
        from_chat = (prev in ("/chat", "/questions")) and not to_chat and not to_sheet
        to_auth = route.startswith("/reg/") or route == "/login"
        from_auth = (prev or "").startswith("/reg/") or prev in ("/login", "/welcome")
        # уход с чата/вопросов: на всякий случай закрыть клавиатуру (iOS sticky keyboard)
        if from_chat:
            try:
                theme.dismiss_keyboard(page)
            except Exception:
                pass
        # один BG у шагов регистрации — нужен Stack-crossfade, иначе fade «пустой»
        use_crossfade = bool(animate and to_auth and from_auth and page.controls)

        def _anim_wrap(**kwargs) -> ft.Container:
            return ft.Container(
                content=content,
                expand=True,
                bgcolor=theme.BG,
                clip_behavior=ft.ClipBehavior.HARD_EDGE,
                **kwargs,
            )

        old = page.controls[0] if page.controls else None

        if animate and to_chat:
            wrap = _anim_wrap(
                opacity=0,
                offset=ft.Offset(0.10, 0),
                animate_opacity=ft.Animation(280, ft.AnimationCurve.EASE_OUT_CUBIC),
                animate_offset=ft.Animation(340, ft.AnimationCurve.EASE_OUT_CUBIC),
            )
        elif animate and from_chat:
            wrap = _anim_wrap(
                opacity=0,
                offset=ft.Offset(-0.06, 0),
                animate_opacity=ft.Animation(240, ft.AnimationCurve.EASE_OUT),
                animate_offset=ft.Animation(300, ft.AnimationCurve.EASE_OUT_CUBIC),
            )
        elif animate and to_auth:
            # регистрация / вход — fade (+ лёгкий подъём, иначе на одном BG не видно)
            wrap = _anim_wrap(
                opacity=0,
                offset=ft.Offset(0, 0.03),
                animate_opacity=ft.Animation(360, ft.AnimationCurve.EASE_OUT),
                animate_offset=ft.Animation(360, ft.AnimationCurve.EASE_OUT),
            )
        elif animate and to_sheet and quiet_settings:
            wrap = _anim_wrap(opacity=1)
        elif animate and to_sheet:
            wrap = _anim_wrap(
                opacity=0,
                offset=ft.Offset(0, 0.04),
                animate_opacity=ft.Animation(260, ft.AnimationCurve.EASE_OUT),
                animate_offset=ft.Animation(280, ft.AnimationCurve.EASE_OUT),
            )
        elif animate and from_sheet:
            wrap = _anim_wrap(
                opacity=0,
                offset=ft.Offset(-0.03, 0),
                animate_opacity=ft.Animation(220, ft.AnimationCurve.EASE_OUT),
                animate_offset=ft.Animation(240, ft.AnimationCurve.EASE_OUT),
            )
        elif animate:
            wrap = _anim_wrap(
                opacity=0,
                animate_opacity=ft.Animation(220, ft.AnimationCurve.EASE_OUT),
            )
        else:
            wrap = content if isinstance(content, ft.Container) else _anim_wrap()

        try:
            page.bgcolor = theme.BG
            win = getattr(page, "window", None)
            if win is not None:
                win.bgcolor = theme.BG
        except Exception:
            pass

        def _reveal(ctrl: ft.Control) -> None:
            try:
                ctrl.opacity = 1
            except Exception:
                pass
            try:
                if hasattr(ctrl, "offset"):
                    ctrl.offset = ft.Offset(0, 0)
            except Exception:
                pass
            try:
                if hasattr(ctrl, "scale"):
                    ctrl.scale = 1
            except Exception:
                pass

        if use_crossfade and old is not None:
            try:
                old.animate_opacity = ft.Animation(300, ft.AnimationCurve.EASE_OUT)
                old.opacity = 1
            except Exception:
                pass
            # новый сверху, старый снизу — оба с opacity-анимацией
            stage = ft.Stack(expand=True, controls=[old, wrap])
            page.controls.clear()
            page.controls.append(stage)
            page.update()

            async def _crossfade():
                import asyncio

                await asyncio.sleep(0.04)
                try:
                    old.opacity = 0
                except Exception:
                    pass
                _reveal(wrap)
                try:
                    page.update()
                except Exception:
                    try:
                        wrap.update()
                    except Exception:
                        pass
                await asyncio.sleep(0.38)
                try:
                    if current.get("route") != route:
                        return
                    page.controls.clear()
                    page.controls.append(wrap)
                    page.update()
                except Exception:
                    pass

            try:
                page.run_task(_crossfade)
            except Exception:
                _reveal(wrap)
                page.controls.clear()
                page.controls.append(wrap)
                page.update()
            return

        page.controls.clear()
        page.controls.append(wrap)
        page.update()

        if animate:
            async def _play():
                import asyncio

                await asyncio.sleep(0.04)
                _reveal(wrap)
                try:
                    page.update()
                except Exception:
                    try:
                        wrap.update()
                    except Exception:
                        pass

            try:
                page.run_task(_play)
            except Exception:
                _reveal(wrap)
                try:
                    page.update()
                except Exception:
                    pass

    def go(route: str):
        route = route or "/welcome"
        show_route(route, animate=True)

    STATE.bind(go, snack, dialog)
    push.bind_snack(snack)

    def on_route_change(e=None):
        route = getattr(page, "route", None) or current["route"]
        if route != current["route"]:
            show_route(route)

    try:
        page.on_route_change = on_route_change
    except Exception:
        pass

    def on_resize(_e=None):
        # Desktop: снова зафиксировать окно-телефон; mobile: подтянуть реальный экран
        try:
            if theme.is_mobile_runtime():
                theme.sync_viewport(page)
            else:
                theme.lock_phone_window(page)
        except Exception:
            theme.sync_viewport(page)

    try:
        page.on_resize = on_resize
    except Exception:
        pass

    def _net(online: bool):
        try:
            from core import net_status as _net_mod

            _net_mod.set_online(online)
        except Exception:
            pass
        try:
            page.pubsub.send_all({"type": "net_status", "online": bool(online)})
        except Exception:
            pass

    try:
        page.on_disconnect = lambda e: _net(False)
    except Exception:
        pass
    try:
        page.on_connect = lambda e: _net(True)
    except Exception:
        pass

    # Реальная сеть (airplane mode и т.п.) — Flet on_disconnect этого не ловит
    try:
        from core import net_status

        net_status.refresh()
        net_status.start_watcher(lambda online: _net(online), interval=3.0)
        _net(net_status.is_online())
    except Exception:
        pass

    start = STATE.restore_session()
    go(start)


def start_discord_bot():
    """Только desktop: на iOS/Android discord.py не собираем и не запускаем."""
    try:
        from discord_bot.bot import bot
        from core.config import get_token
    except Exception as exc:
        print(f"Discord bot import skipped: {exc}")
        return

    token = get_token()
    if not token:
        print("Discord bot: токен не найден — пропуск")
        return

    print("=== ЗАПУСК DISCORD БОТА ===")
    try:
        bot.run(token)
    except Exception as e:
        print(f"Ошибка при запуске бота: {e}")


if __name__ == "__main__":
    platform = get_app_platform()
    if platform not in ("ios", "android"):
        threading.Thread(target=start_discord_bot, daemon=True).start()

    if hasattr(ft, "run"):
        ft.run(main)
    elif hasattr(ft, "app"):
        ft.app(target=main)
    else:
        raise SystemExit("Flet: нет ни ft.run, ни ft.app")