# -*- coding: utf-8 -*-
"""Экран входа."""
from __future__ import annotations

import flet as ft

from core import auth, session
from core.config import SETTINGS, save_settings
from flet_app.app_state import STATE
from flet_app import theme


def _pill_field(label: str, hint: str = "", *, value: str = "", password: bool = False) -> ft.TextField:
    """Скруглённое поле как на регистрации."""
    fw = min(float(theme.PHONE_WIDTH - theme.PAGE_PADDING * 2) * 0.92, 340.0)
    return ft.TextField(
        label=label,
        hint_text=hint,
        value=value,
        password=password,
        can_reveal_password=password,
        border_radius=28,
        filled=True,
        bgcolor="#F0F0F5",
        border_color="#F0F0F5",
        focused_border_color=theme.PRIMARY,
        cursor_color=theme.PRIMARY,
        text_size=16,
        color=theme.INK,
        width=fw,
        height=52,
        content_padding=ft.Padding.symmetric(horizontal=20, vertical=14),
        text_style=ft.TextStyle(font_family=theme.FONT_FAMILY, size=16, color=theme.INK),
        label_style=ft.TextStyle(color=theme.MUTED, font_family=theme.FONT_FAMILY),
        hint_style=ft.TextStyle(color=theme.HINT, font_family=theme.FONT_FAMILY),
    )


def build_login(page: ft.Page) -> ft.Control:
    remembered = SETTINGS.get("remember_login", "") or ""
    login_tf = _pill_field("Логин / ID", hint="email или ID", value=remembered)
    pass_tf = _pill_field("Пароль", password=True)
    remember = ft.Checkbox(
        label="Запомнить меня",
        value=bool(session.user_id()),
        active_color=theme.PRIMARY,
    )

    def do_login(_):
        try:
            user = auth.login(login_tf.value or "", pass_tf.value or "")
        except auth.AuthError as exc:
            STATE.error(str(exc))
            return
        except Exception as exc:
            STATE.error(str(exc) or "Не удалось войти")
            return

        pass_tf.value = ""
        try:
            pass_tf.update()
        except Exception:
            pass
        STATE.user = user

        if remember.value:
            session.save(user.id, user.public_id)
            SETTINGS["remember_login"] = login_tf.value or ""
            try:
                save_settings()
            except Exception:
                pass
        else:
            session.clear()

        if not user.contact_verified:
            STATE.go("/verify")
        elif user.is_teacher and not user.teacher_verified:
            STATE.go("/teacher_proof")
        else:
            STATE.go("/home")

    back = ft.TextButton(
        "← Назад",
        on_click=lambda _: STATE.go("/welcome"),
        style=ft.ButtonStyle(color=theme.PRIMARY),
    )

    return ft.Container(
        bgcolor=theme.BG,
        expand=True,
        padding=ft.Padding.symmetric(horizontal=theme.PAGE_PADDING, vertical=16),
        content=ft.Column(
            expand=True,
            controls=[
                ft.Container(content=back, alignment=ft.Alignment.CENTER_LEFT),
                ft.Container(height=12),
                ft.Text("Вход", size=34, weight=ft.FontWeight.BOLD, color=theme.INK, font_family=theme.FONT_FAMILY),
                ft.Container(height=24),
                login_tf,
                ft.Container(height=12),
                pass_tf,
                ft.Container(height=8),
                remember,
                ft.Container(expand=True),
                theme.primary_image_button("Войти", do_login),
                ft.Container(height=12),
            ],
        ),
    )
