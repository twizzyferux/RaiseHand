# -*- coding: utf-8 -*-
"""Экран входа."""
from __future__ import annotations

import flet as ft

from core import auth, session
from core.i18n import t
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
        filled=True,
        bgcolor=theme.FIELD_BG,
        border=theme.field_border(28, color="transparent", focused_color=theme.PRIMARY, width=1.5),
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
    login_tf = _pill_field(t("common.login_id"), hint=t("common.login_id_hint"), value=remembered)
    pass_tf = _pill_field(t("auth.password"), password=True)
    remember = ft.Checkbox(
        label=t("common.remember_me"),
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
            STATE.error(str(exc) or t("common.login_failed"))
            return

        pass_tf.value = ""
        try:
            pass_tf.update()
        except Exception:
            pass
        try:
            auth.touch_last_active(user.id)
        except Exception:
            pass
        STATE.user = user

        if remember.value:
            session.save(user.id, user.public_id, role=user.role, public_id=user.public_id)
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

    back = theme.pressable(
        ft.Container(
            padding=ft.Padding.symmetric(horizontal=4, vertical=8),
            content=ft.Text(
                t("common.back"),
                size=16,
                weight=ft.FontWeight.W_700,
                color=theme.PRIMARY,
                font_family=theme.FONT_FAMILY,
            ),
        ),
        lambda _: STATE.go("/welcome"),
    )
    content_w = float(theme.content_width())
    head = theme.fade_box(
        ft.Column(
            spacing=0,
            tight=True,
            controls=[
                ft.Container(content=back, alignment=ft.Alignment.CENTER_LEFT, height=44),
                ft.Container(height=8),
                ft.Text(
                    t("auth.login"),
                    size=34,
                    weight=ft.FontWeight.BOLD,
                    color=theme.INK,
                    font_family=theme.FONT_FAMILY,
                ),
            ],
        ),
        delay_ms=0,
        width=content_w,
    )
    form = theme.fade_box(
        ft.Column(
            spacing=0,
            tight=True,
            controls=[
                ft.Container(height=24),
                login_tf,
                ft.Container(height=12),
                pass_tf,
                ft.Container(height=8),
                remember,
            ],
        ),
        delay_ms=50,
        width=content_w,
    )
    foot = theme.fade_box(
        ft.Column(
            spacing=0,
            tight=True,
            controls=[
                ft.Container(
                    alignment=ft.Alignment.CENTER,
                    content=theme.primary_image_button(t("auth.sign_in"), do_login),
                ),
                ft.Container(height=8),
            ],
        ),
        delay_ms=110,
        width=content_w,
    )

    async def _play_in():
        await theme.play_fade_in([head, form, foot], page, step_ms=45)

    try:
        page.run_task(_play_in)
    except Exception:
        for box in (head, form, foot):
            try:
                box.opacity = 1
                box.offset = ft.Offset(0, 0)
            except Exception:
                pass

    return ft.Container(
        bgcolor=theme.BG,
        expand=True,
        padding=ft.Padding.only(
            left=theme.PAGE_PADDING,
            right=theme.PAGE_PADDING,
            top=8,
            bottom=float(theme.bottom_inset()),
        ),
        content=ft.Column(
            expand=True,
            controls=[head, form, ft.Container(expand=True), foot],
        ),
    )
