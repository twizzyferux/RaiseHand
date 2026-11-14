# -*- coding: utf-8 -*-
"""Цвета, фиолетовые PNG-кнопки, SF Pro, фиксированный телефон (Flet 1.x)."""
from __future__ import annotations

import os
from typing import Callable, Optional

import flet as ft

BG = "#FFFBF7"
SURFACE = "#F5F5F7"
FIELD_BG = "#EFEFF4"
PRIMARY = "#4B2FE0"
PRIMARY_TEXT = "#FFFFFF"
INK = "#000000"
MUTED = "#474747"
HINT = "#9E9E9E"
LINK = "#4B2FE0"
DOT_ON = "#4B2FE0"
DOT_OFF = "#B7ACEC"
STROKE = "#E5E5EA"

PAGE_PADDING = 24
PHONE_WIDTH = 390
PHONE_HEIGHT = 844
MAX_CONTENT_WIDTH = PHONE_WIDTH

FONT_FAMILY = "SFPro"

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def asset(*parts: str) -> str:
    return os.path.join(_ROOT, *parts)


# Спрайты кнопок с тенью из макета (проект/проект экран/…)
SPRITE_PRIMARY = asset("assets", "images", "buttons", "btn_next.png")          # «Далее»
SPRITE_PRIMARY_DOWN = asset("assets", "images", "buttons", "btn_next.png")
SPRITE_SECONDARY = asset("assets", "images", "buttons", "btn_teacher.png")     # «Я учитель»
SPRITE_SECONDARY_DOWN = asset("assets", "images", "buttons", "btn_teacher.png")
SPRITE_STUDENT = asset("assets", "images", "buttons", "btn_student.png")       # «Я ученик»
SPRITE_STUDENT_DOWN = asset("assets", "images", "buttons", "btn_student.png")
SPRITE_LOGO = asset("assets", "images", "raisehand", "logo.png")
SPRITE_WORDMARK = asset("assets", "images", "raisehand", "wordmark.png")

FONT_REGULAR = asset("assets", "fonts", "SF-Pro-Text-Regular.otf")
FONT_SEMIBOLD = asset("assets", "fonts", "SF-Pro-Text-Semibold.otf")
FONT_DISPLAY = asset("assets", "fonts", "SF-Pro-Display-Semibold.otf")


def _image_exists(path: str) -> bool:
    return bool(path) and os.path.isfile(path)


def setup_fonts(page: ft.Page) -> None:
    """Регистрирует SF Pro и делает его шрифтом по умолчанию."""
    fonts = {}
    if _image_exists(FONT_REGULAR):
        fonts["SFPro"] = FONT_REGULAR
    if _image_exists(FONT_SEMIBOLD):
        fonts["SFPro-Semibold"] = FONT_SEMIBOLD
    if _image_exists(FONT_DISPLAY):
        fonts["SFPro-Display"] = FONT_DISPLAY
    if fonts:
        try:
            page.fonts = fonts
        except Exception:
            pass
    try:
        kwargs = {"color_scheme_seed": PRIMARY}
        if "SFPro" in fonts:
            kwargs["font_family"] = "SFPro"
        try:
            kwargs["visual_density"] = ft.VisualDensity.COMFORTABLE
        except Exception:
            pass
        page.theme = ft.Theme(**kwargs)
    except Exception:
        try:
            page.theme = ft.Theme(color_scheme_seed=PRIMARY)
        except Exception:
            pass
    try:
        page.theme_mode = ft.ThemeMode.LIGHT
    except Exception:
        pass


def page_theme() -> ft.Theme:
    kwargs = {"color_scheme_seed": PRIMARY}
    try:
        kwargs["font_family"] = FONT_FAMILY
    except Exception:
        pass
    try:
        kwargs["visual_density"] = ft.VisualDensity.COMFORTABLE
    except Exception:
        pass
    try:
        return ft.Theme(**kwargs)
    except Exception:
        return ft.Theme(color_scheme_seed=PRIMARY)


def lock_phone_window(page: ft.Page) -> None:
    """Окно ровно под телефон, без ресайза; фон на весь клиент — без белой полосы."""
    w, h = PHONE_WIDTH, PHONE_HEIGHT
    page.bgcolor = BG
    page.padding = 0
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.vertical_alignment = ft.MainAxisAlignment.START
    win = getattr(page, "window", None)
    if win is not None:
        for name, val in (
            ("width", w),
            ("height", h),
            ("min_width", w),
            ("max_width", w),
            ("min_height", h),
            ("max_height", h),
            ("resizable", False),
            ("maximizable", False),
            ("bgcolor", BG),
        ):
            try:
                setattr(win, name, val)
            except Exception:
                pass
    else:
        for name, val in (
            ("window_width", w),
            ("window_height", h),
            ("window_min_width", w),
            ("window_max_width", w),
            ("window_min_height", h),
            ("window_max_height", h),
            ("window_resizable", False),
        ):
            try:
                setattr(page, name, val)
            except Exception:
                pass


def _press_scale(e):
    try:
        e.control.scale = 0.98 if e.data == "true" else 1.0
        e.control.update()
    except Exception:
        pass


def primary_button(text: str, on_click, *, expand: bool = True) -> ft.Control:
    return ft.Container(
        content=ft.Text(
            text,
            color=PRIMARY_TEXT,
            size=17,
            weight=ft.FontWeight.W_600,
            text_align=ft.TextAlign.CENTER,
            font_family=FONT_FAMILY,
        ),
        bgcolor=PRIMARY,
        border_radius=28,
        height=52,
        alignment=ft.Alignment.CENTER,
        expand=expand,
        on_click=on_click,
        ink=True,
        animate_scale=ft.Animation(120, ft.AnimationCurve.EASE_OUT),
        scale=1,
        on_hover=_press_scale,
    )


def outline_button(text: str, on_click, *, expand: bool = True) -> ft.Control:
    return ft.Container(
        content=ft.Text(
            text,
            color=PRIMARY,
            size=17,
            weight=ft.FontWeight.W_600,
            text_align=ft.TextAlign.CENTER,
            font_family=FONT_FAMILY,
        ),
        bgcolor=BG,
        border=ft.Border.all(2.5, PRIMARY),
        border_radius=28,
        height=52,
        alignment=ft.Alignment.CENTER,
        expand=expand,
        on_click=on_click,
        ink=True,
        animate_scale=ft.Animation(120, ft.AnimationCurve.EASE_OUT),
        scale=1,
        on_hover=_press_scale,
    )


def image_button(
    text: str,
    on_click: Callable,
    *,
    src: str,
    src_down: Optional[str] = None,
    height: float | None = None,
    text_color: str = PRIMARY_TEXT,
    baked_label: bool = False,
) -> ft.Control:
    """Кнопка с тенью: уже и ниже, по центру колонки.

    Ширина ~82% контента (макс. 300), высота по пропорции спрайта
    с потолком 52 — без белых полей сбоку от «натянутой» кнопки.
    """
    if not _image_exists(src):
        if text_color == PRIMARY_TEXT:
            return primary_button(text, on_click, expand=False)
        return outline_button(text, on_click, expand=False)

    content_w = float(PHONE_WIDTH - PAGE_PADDING * 2)
    # компактнее: не на всю ширину
    btn_w = min(content_w * 0.82, 300.0)

    ratio = 168.0 / 840.0
    try:
        from PIL import Image
        with Image.open(src) as im:
            iw, ih = im.size
            if iw > 0:
                ratio = ih / float(iw)
    except Exception:
        pass

    btn_h = float(height) if height is not None else min(btn_w * ratio, 52.0)

    img = ft.Image(
        src=src,
        width=btn_w,
        height=btn_h,
        fit=ft.BoxFit.FILL,
        gapless_playback=True,
    )

    controls: list = [
        ft.Container(content=img, width=btn_w, height=btn_h, left=0, top=0),
    ]
    if text and not baked_label:
        controls.append(
            ft.Container(
                content=ft.Text(
                    text,
                    color=text_color,
                    size=16,
                    weight=ft.FontWeight.W_600,
                    text_align=ft.TextAlign.CENTER,
                    font_family=FONT_FAMILY,
                    width=btn_w,
                ),
                width=btn_w,
                height=btn_h * 0.88,
                left=0,
                top=0,
                alignment=ft.Alignment.CENTER,
            )
        )

    stack = ft.Stack(width=btn_w, height=btn_h, controls=controls)

    def set_src(path: str):
        if path and _image_exists(path):
            img.src = path
            try:
                img.update()
            except Exception:
                pass

    def on_hover(e):
        set_src(src_down if (src_down and e.data == "true") else src)
        _press_scale(e)

    btn = ft.Container(
        content=stack,
        width=btn_w,
        height=btn_h,
        on_click=on_click,
        on_hover=on_hover,
        animate_scale=ft.Animation(120, ft.AnimationCurve.EASE_OUT),
        scale=1,
        expand=False,
        clip_behavior=ft.ClipBehavior.NONE,
    )

    # центрируем в полной ширине контента — без белой полосы с одной стороны
    return ft.Container(
        width=content_w,
        alignment=ft.Alignment.CENTER,
        content=btn,
    )


def primary_image_button(text: str, on_click, *, expand: bool = True) -> ft.Control:
    """«Далее» / primary — спрайт с тенью и подписью из макета."""
    return image_button(
        text,
        on_click,
        src=SPRITE_PRIMARY,
        src_down=SPRITE_PRIMARY_DOWN,
        text_color=PRIMARY_TEXT,
        baked_label=False,
    )


def secondary_image_button(text: str, on_click, *, expand: bool = True) -> ft.Control:
    """«Я учитель» — outline-спрайт с тенью из макета."""
    return image_button(
        text,
        on_click,
        src=SPRITE_SECONDARY,
        src_down=SPRITE_SECONDARY_DOWN,
        text_color=PRIMARY,
        baked_label=False,
    )


def student_image_button(text: str, on_click, *, expand: bool = True) -> ft.Control:
    """«Я ученик» — filled-спрайт с тенью из макета."""
    return image_button(
        text,
        on_click,
        src=SPRITE_STUDENT,
        src_down=SPRITE_STUDENT_DOWN,
        text_color=PRIMARY_TEXT,
        baked_label=False,
    )


def field(label: str, hint: str = "", password: bool = False, value: str = "", on_change=None) -> ft.TextField:
    # Flet 1.x: шрифт через text_style / label_style, не font_family у TextField
    return ft.TextField(
        label=label,
        hint_text=hint,
        value=value,
        password=password,
        can_reveal_password=password,
        border_radius=24,
        filled=True,
        bgcolor=SURFACE,
        border_color="transparent",
        focused_border_color=PRIMARY,
        cursor_color=PRIMARY,
        text_size=16,
        on_change=on_change,
        color=INK,
        text_style=ft.TextStyle(font_family=FONT_FAMILY, size=16, color=INK),
        label_style=ft.TextStyle(color=MUTED, font_family=FONT_FAMILY),
        hint_style=ft.TextStyle(color=HINT, font_family=FONT_FAMILY),
    )


def fade_box(
    control: ft.Control,
    *,
    delay_ms: int = 0,
    width: float | None = None,
) -> ft.Control:
    """width=None → контентная колонка; иначе своя ширина (пузыри на весь экран)."""
    w = float(PHONE_WIDTH - PAGE_PADDING * 2) if width is None else float(width)
    return ft.Container(
        content=control,
        opacity=0,
        offset=ft.Offset(0, 0.05),
        animate_opacity=ft.Animation(360, ft.AnimationCurve.EASE_OUT),
        animate_offset=ft.Animation(360, ft.AnimationCurve.EASE_OUT),
        data={"delay": delay_ms},
        width=w,
        alignment=ft.Alignment.CENTER_LEFT,
    )


async def play_fade_in(boxes: list, page: ft.Page, step_ms: int = 70):
    import asyncio

    for box in boxes:
        delay = 0
        try:
            delay = int((box.data or {}).get("delay") or 0)
        except Exception:
            pass
        if delay:
            await asyncio.sleep(delay / 1000.0)
        try:
            box.opacity = 1
            box.offset = ft.Offset(0, 0)
            box.update()
        except Exception:
            pass
        await asyncio.sleep(step_ms / 1000.0)
