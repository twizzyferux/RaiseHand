# -*- coding: utf-8 -*-
"""Единый визуальный язык RaiseHand: pill-кнопки, pill-поля, аватары, карточки.

Все пользовательские экраны собираются только из этих компонентов.
Цвета и шрифты — из flet_app.theme.
"""
from __future__ import annotations

import os
from typing import Callable, Optional

import flet as ft

from flet_app import theme

# ---------------------------------------------------------------------------
#  Размеры (сверены с макетом 402px -> 390px)
# ---------------------------------------------------------------------------
FORM_WIDTH = 290          # поле
BUTTON_WIDTH = 305        # «Далее» / «Начать общение»
FIELD_HEIGHT = 52
BUTTON_HEIGHT = 52
CARD_WIDTH = 334
CARD_HEIGHT = 56
NAV_HEIGHT = 60
NAV_RADIUS = 30

# фирменный градиент аватара (как в макете: розовый -> фиолетовый)
AVATAR_GRADIENT = ["#FF8FAB", "#A78BFA"]
BADGE_PINK = "#F0447C"


def _font() -> str:
    return theme.FONT_FAMILY


def _img(name: str, size: float, *, violet: bool = True) -> Optional[ft.Control]:
    """PNG-иконка из assets/images/ui (из набора кита)."""
    path = theme.asset("assets", "images", "ui", name + ".png")
    if not theme._image_exists(path):
        return None
    return ft.Image(src=path, width=size, height=size, fit=ft.BoxFit.CONTAIN)


def icon(name: str, size: float = 22) -> Optional[ft.Control]:
    return _img(name, size)


# ---------------------------------------------------------------------------
#  Кнопки
# ---------------------------------------------------------------------------
def _press_scale(e):
    try:
        e.control.scale = 0.98 if e.data == "true" else 1.0
        e.control.update()
    except Exception:
        pass


def _button_shadow() -> ft.BoxShadow:
    return ft.BoxShadow(
        spread_radius=0,
        blur_radius=18,
        color="#4B2FE02E",
        offset=ft.Offset(0, 6),
    )


def pill_button(
    text: str,
    on_click,
    *,
    icon_name: Optional[str] = None,
    icon_size: float = 22,
    width: float = BUTTON_WIDTH,
    height: float = BUTTON_HEIGHT,
    expand: bool = False,
    text_color: str = "#FFFFFF",
    bg: str = theme.PRIMARY,
    border: Optional[ft.Border] = None,
    font_size: float = 17,
) -> ft.Control:
    """Primary pill-кнопка. Иконка слева от текста, как в макете."""
    content: list[ft.Control] = []
    if icon_name:
        ic = _img(icon_name, icon_size)
        if ic is not None:
            content.append(ic)
            content.append(ft.Container(width=10))
    content.append(
        ft.Text(
            text,
            color=text_color,
            size=font_size,
            weight=ft.FontWeight.W_600,
            text_align=ft.TextAlign.CENTER,
            font_family=_font(),
        )
    )

    return ft.Container(
        content=ft.Row(
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            tight=True,
            controls=content,
        ),
        width=width,
        height=height,
        bgcolor=bg,
        border_radius=height / 2,
        border=border,
        alignment=ft.Alignment.CENTER,
        expand=expand,
        on_click=on_click,
        ink=True,
        animate_scale=ft.Animation(120, ft.AnimationCurve.EASE_OUT),
        scale=1,
        on_hover=_press_scale,
        shadow=_button_shadow() if border is None else None,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
    )


def pill_outline_button(
    text: str,
    on_click,
    *,
    icon_name: Optional[str] = None,
    icon_size: float = 22,
    width: float = BUTTON_WIDTH,
    height: float = BUTTON_HEIGHT,
    expand: bool = False,
) -> ft.Control:
    """Вторичная pill-кнопка: белая, с фиолетовой обводкой."""
    return pill_button(
        text,
        on_click,
        icon_name=icon_name,
        icon_size=icon_size,
        width=width,
        height=height,
        expand=expand,
        text_color=theme.PRIMARY,
        bg="#FFFFFF",
        border=ft.Border.all(2.5, theme.PRIMARY),
    )


def link_button(
    text: str,
    on_click,
    *,
    color: str = theme.PRIMARY,
    size: float = 15,
    weight: ft.FontWeight = ft.FontWeight.W_600,
    align: ft.TextAlign = ft.TextAlign.LEFT,
) -> ft.Control:
    return ft.Text(
        text,
        color=color,
        size=size,
        weight=weight,
        font_family=_font(),
        text_align=align,
        on_tap=on_click,
    )


# ---------------------------------------------------------------------------
#  Поля
# ---------------------------------------------------------------------------
def _field_base(
    tf: ft.TextField,
    label: str,
    helper: str,
    width: float,
) -> ft.Control:
    """Поле с подписью сверху и подсказкой снизу (как в макете)."""
    col = ft.Column(
        spacing=6,
        tight=True,
        width=width,
        horizontal_alignment=ft.CrossAxisAlignment.START,
        controls=[
            ft.Text(
                label,
                size=17,
                weight=ft.FontWeight.W_600,
                color=theme.INK,
                font_family=_font(),
            ),
            tf,
        ],
    )
    if helper:
        col.controls.append(
            ft.Text(
                helper,
                size=13,
                color=theme.MUTED,
                font_family=_font(),
                width=width,
            )
        )
    return col


def pill_field(
    label: str,
    *,
    hint: str = "",
    value: str = "",
    helper: str = "",
    width: float = FORM_WIDTH,
    password: bool = False,
    suffix: Optional[ft.Control] = None,
    on_change=None,
    on_suffix_click=None,
    keyboard_type: Optional[ft.KeyboardType] = None,
    max_length: Optional[int] = None,
) -> tuple[ft.Control, ft.TextField]:
    """Pill-поле ввода. Иконка справа — через suffix (не наезжает на текст)."""
    tf = ft.TextField(
        value=value,
        hint_text=hint,
        password=password,
        can_reveal_password=False,
        border_radius=FIELD_HEIGHT / 2,
        filled=True,
        fill_color=theme.FIELD_BG,
        bgcolor=theme.FIELD_BG,
        border=ft.NoInputBorder(),
        focused_border_color=theme.PRIMARY,
        cursor_color=theme.PRIMARY,
        text_size=16,
        color=theme.INK,
        width=width,
        height=FIELD_HEIGHT,
        content_padding=ft.Padding(
            left=20, top=12, right=58 if suffix is not None else 20, bottom=12
        ),
        text_style=ft.TextStyle(font_family=_font(), size=16, color=theme.INK),
        hint_style=ft.TextStyle(color=theme.HINT, font_family=_font()),
        suffix=suffix,
        on_change=on_change,
        keyboard_type=keyboard_type,
        max_length=max_length,
    )
    return _field_base(tf, label, helper, width), tf


def pill_password_field(
    label: str,
    *,
    hint: str = "",
    value: str = "",
    helper: str = "",
    width: float = FORM_WIDTH,
    on_change=None,
) -> tuple[ft.Control, ft.TextField]:
    """Pill-поле пароля: глаз справа внутри поля, текст не перекрывается."""
    state = {"show": False}

    def toggle(_):
        state["show"] = not state["show"]
        tf.password = not state["show"]
        eye.src = theme.asset(
            "assets", "images", "ui",
            "icon-eye.png" if state["show"] else "icon-eye-off.png",
        )
        try:
            tf.update()
            eye.update()
        except Exception:
            pass

    eye = ft.Image(
        src=theme.asset("assets", "images", "ui", "icon-eye.png"),
        width=24,
        height=24,
        fit=ft.BoxFit.CONTAIN,
    )
    suffix = ft.GestureDetector(
        content=ft.Container(content=eye, padding=ft.Padding.all(4)),
        on_tap=toggle,
    )
    tf = ft.TextField(
        value=value,
        hint_text=hint,
        password=True,
        can_reveal_password=False,
        border_radius=FIELD_HEIGHT / 2,
        filled=True,
        fill_color=theme.FIELD_BG,
        bgcolor=theme.FIELD_BG,
        border=ft.NoInputBorder(),
        focused_border_color=theme.PRIMARY,
        cursor_color=theme.PRIMARY,
        text_size=16,
        color=theme.INK,
        width=width,
        height=FIELD_HEIGHT,
        content_padding=ft.Padding(left=20, top=12, right=58, bottom=12),
        text_style=ft.TextStyle(font_family=_font(), size=16, color=theme.INK),
        hint_style=ft.TextStyle(color=theme.HINT, font_family=_font()),
        suffix=suffix,
        on_change=on_change,
    )
    return _field_base(tf, label, helper, width), tf


def clear_suffix(tf: ft.TextField) -> ft.Control:
    """Крестик очистки справа в поле."""
    def clear(_):
        tf.value = ""
        try:
            tf.update()
        except Exception:
            pass

    ic = _img("icon-close", 20)
    if ic is None:
        return ft.Container(width=40)
    return ft.GestureDetector(
        content=ft.Container(content=ic, padding=ft.Padding.all(4)),
        on_tap=clear,
    )


def static_suffix(name: str, size: float = 22) -> ft.Control:
    """Просто иконка справа (поиск, копирование)."""
    ic = _img(name, size)
    if ic is None:
        return ft.Container(width=40)
    return ft.Container(
        content=ic,
        padding=ft.Padding.symmetric(horizontal=8),
        alignment=ft.Alignment.CENTER,
    )


# ---------------------------------------------------------------------------
#  Прогресс
# ---------------------------------------------------------------------------
def progress_bar(value: float, width: float = FORM_WIDTH) -> ft.Control:
    return ft.Container(
        width=width,
        content=ft.ProgressBar(
            value=value,
            color=theme.PRIMARY,
            bgcolor="#E8E8EE",
            bar_height=3,
            border_radius=2,
            width=width,
        ),
    )


# ---------------------------------------------------------------------------
#  Аватар
# ---------------------------------------------------------------------------
def avatar(
    initials: str,
    size: float,
    *,
    seed: str = "user",
    badge: bool = False,
    edit_icon: bool = False,
    font_size: Optional[float] = None,
) -> ft.Control:
    """Круглый градиентный аватар с инициалами. Опционально — бейдж и карандаш."""
    circle = ft.Container(
        width=size,
        height=size,
        border_radius=size / 2,
        gradient=ft.LinearGradient(
            begin=ft.Alignment(0, -1),
            end=ft.Alignment(0, 1),
            colors=AVATAR_GRADIENT,
        ),
        alignment=ft.Alignment.CENTER,
        content=ft.Text(
            initials,
            size=font_size if font_size is not None else int(size * 0.34),
            weight=ft.FontWeight.BOLD,
            color="#FFFFFF",
            font_family=_font(),
        ),
    )
    if not (badge or edit_icon):
        return circle

    controls: list[ft.Control] = [circle]
    if edit_icon:
        pencil = _img("icon-edit", int(size * 0.22))
        if pencil is not None:
            controls.append(
                ft.Container(
                    content=pencil,
                    left=-2,
                    bottom=size * 0.12,
                )
            )
    if badge:
        bs = size * 0.28
        controls.append(
            ft.Container(
                width=bs,
                height=bs,
                border_radius=bs / 2,
                bgcolor=BADGE_PINK,
                border=ft.Border.all(2, "#FFFFFF"),
                alignment=ft.Alignment.CENTER,
                right=-2,
                top=size - bs * 0.7,
                content=ft.Text(
                    "✓",
                    size=int(bs * 0.62),
                    weight=ft.FontWeight.BOLD,
                    color="#FFFFFF",
                    font_family=_font(),
                ),
            )
        )
    return ft.Stack(width=size + 8, height=size + 8, controls=controls)


# ---------------------------------------------------------------------------
#  Карточка «Класс / Школа / Роль»
# ---------------------------------------------------------------------------
def info_card(
    label: str,
    value: str,
    *,
    icon_name: Optional[str] = None,
    width: float = CARD_WIDTH,
    height: float = CARD_HEIGHT,
) -> ft.Control:
    leading: list[ft.Control] = []
    if icon_name:
        ic = _img(icon_name, 22)
        if ic is not None:
            leading.append(ic)
            leading.append(ft.Container(width=10))
    leading.append(
        ft.Text(
            label,
            size=18,
            weight=ft.FontWeight.W_600,
            color=theme.INK,
            font_family=_font(),
        )
    )
    leading.append(ft.Container(width=14))
    leading.append(
        ft.Text(
            value,
            size=18,
            color=theme.MUTED,
            font_family=_font(),
        )
    )
    return ft.Container(
        width=width,
        height=height,
        bgcolor=theme.FIELD_BG,
        border_radius=height / 2,
        padding=ft.Padding.symmetric(horizontal=22),
        content=ft.Row(
            alignment=ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            tight=True,
            controls=leading,
        ),
    )


# ---------------------------------------------------------------------------
#  Обёртки
# ---------------------------------------------------------------------------
def screen_bg(child: ft.Control, *, width: float = theme.PHONE_WIDTH) -> ft.Control:
    return ft.Container(
        content=child,
        bgcolor=theme.BG,
        expand=True,
        width=width,
    )


def centered_form(col: ft.Control, *, width: float = FORM_WIDTH) -> ft.Control:
    """Поле/блок фиксированной ширины по центру экрана."""
    content_w = float(theme.PHONE_WIDTH - theme.PAGE_PADDING * 2)
    return ft.Container(
        width=content_w,
        alignment=ft.Alignment.CENTER,
        content=col,
    )
