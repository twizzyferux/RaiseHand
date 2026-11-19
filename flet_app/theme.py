# -*- coding: utf-8 -*-
"""Цвета, фиолетовые PNG-кнопки, SF Pro, фиксированный телефон (Flet 1.x)."""
from __future__ import annotations

import os
from typing import Callable, Optional

import flet as ft
import sys

PRIMARY = "#6A5AC8"
PRIMARY_TEXT = "#FFFBFF"
LINK = "#6A5AC8"
DOT_ON = "#6A5AC8"
DOT_OFF = "#C4BED8"
BADGE = "#C46B8A"

# Светлая / тёмная — мягче, без «вырвиглаз»
_LIGHT = {
    "BG": "#F4F2EE",
    "SURFACE": "#EBE8E3",
    "CARD": "#FBF9F6",
    "FIELD_BG": "#E6E2DC",
    "INK": "#3A3644",
    "MUTED": "#7A7486",
    "HINT": "#A39EAE",
    "STROKE": "#E0DCD6",
    "BUBBLE_IN": "#E8E4DE",
    "BUBBLE_OUT": "#6A5AC8",
    "TIME_IN": "#8A8496",
    "TIME_OUT": "#F3EEF8",
    "DIVIDER": "#E4E0DA",
    "DATE_CHIP": "#E6E2DC",
    "MENU_SCRIM": "#2A243844",
    "NAV_IDLE": "#6E6878",
    "PRIMARY_SOFT": "#E8E4F4",
}
# Тёмная: тёплый уголь, приглушённый текст, не неоновый акцент
_DARK = {
    "BG": "#141318",
    "SURFACE": "#1C1B22",
    "CARD": "#24232C",
    "FIELD_BG": "#2A2832",
    "INK": "#D2CEDC",
    "MUTED": "#8A8498",
    "HINT": "#6A6576",
    "STROKE": "#34323C",
    "BUBBLE_IN": "#2C2A36",
    "BUBBLE_OUT": "#7A6BC4",
    "TIME_IN": "#8A8496",
    "TIME_OUT": "#E4DFF0",
    "DIVIDER": "#2E2C36",
    "DATE_CHIP": "#26242E",
    "MENU_SCRIM": "#0A0910CC",
    "NAV_IDLE": "#8A8496",
    "PRIMARY_SOFT": "#2A2640",
}

BG = _LIGHT["BG"]
SURFACE = _LIGHT["SURFACE"]
CARD = _LIGHT["CARD"]
FIELD_BG = _LIGHT["FIELD_BG"]
INK = _LIGHT["INK"]
MUTED = _LIGHT["MUTED"]
HINT = _LIGHT["HINT"]
STROKE = _LIGHT["STROKE"]
BUBBLE_IN = _LIGHT["BUBBLE_IN"]
BUBBLE_OUT = _LIGHT["BUBBLE_OUT"]
TIME_IN = _LIGHT["TIME_IN"]
TIME_OUT = _LIGHT["TIME_OUT"]
DIVIDER = _LIGHT["DIVIDER"]
DATE_CHIP = _LIGHT["DATE_CHIP"]
MENU_SCRIM = _LIGHT["MENU_SCRIM"]
NAV_IDLE = _LIGHT["NAV_IDLE"]
PRIMARY_SOFT = _LIGHT["PRIMARY_SOFT"]
_MODE = "light"

PAGE_PADDING = 24
PHONE_WIDTH = 390
PHONE_HEIGHT = 844
MAX_CONTENT_WIDTH = PHONE_WIDTH
# Минимальные отступы поверх системных (когда SafeArea даёт 0 — на десктопе)
SAFE_MIN_TOP = 8
SAFE_MIN_BOTTOM = 8
NAV_BOTTOM_GAP = 18

FONT_FAMILY = "SFPro"

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def is_dark() -> bool:
    return _MODE == "dark"


def is_mobile_runtime() -> bool:
    """Реальный телефон (iOS/Android), не десктоп-симулятор окна."""
    env = (os.environ.get("FLET_PLATFORM") or "").lower()
    if env in ("ios", "android"):
        return True
    plat = (sys.platform or "").lower()
    if "iphone" in plat or "ios" in plat or "android" in plat:
        return True
    try:
        from core.config import get_app_platform

        return get_app_platform() in ("ios", "android")
    except Exception:
        return False


def sync_viewport(page: Optional[ft.Page] = None) -> None:
    """Подтянуть PHONE_WIDTH/HEIGHT под реальный экран (особенно iPhone)."""
    global PHONE_WIDTH, PHONE_HEIGHT, MAX_CONTENT_WIDTH
    if page is None:
        return
    try:
        w = float(getattr(page, "width", 0) or 0)
        h = float(getattr(page, "height", 0) or 0)
    except Exception:
        return
    if w >= 280:
        PHONE_WIDTH = w
        MAX_CONTENT_WIDTH = w
    if h >= 480:
        PHONE_HEIGHT = h


def content_width() -> float:
    return max(240.0, float(PHONE_WIDTH) - float(PAGE_PADDING) * 2)


def safe_shell(
    content: ft.Control,
    *,
    top: bool = True,
    bottom: bool = True,
    left: bool = True,
    right: bool = True,
    maintain_bottom: bool = True,
) -> ft.Control:
    """Обертка SafeArea: Dynamic Island / статус-бар / home indicator."""
    try:
        return ft.SafeArea(
            content=content,
            expand=True,
            avoid_intrusions_top=top,
            avoid_intrusions_bottom=bottom,
            avoid_intrusions_left=left,
            avoid_intrusions_right=right,
            maintain_bottom_view_padding=maintain_bottom,
            minimum_padding=ft.Padding.only(
                top=SAFE_MIN_TOP if top else 0,
                bottom=SAFE_MIN_BOTTOM if bottom else 0,
                left=0,
                right=0,
            ),
        )
    except Exception:
        # Старый Flet / отсутствие SafeArea — ручной запасной отступ
        pad_top = 47 if (is_mobile_runtime() and top) else SAFE_MIN_TOP
        pad_bottom = 28 if (is_mobile_runtime() and bottom) else SAFE_MIN_BOTTOM
        return ft.Container(
            content=content,
            expand=True,
            padding=ft.Padding.only(
                top=pad_top if top else 0,
                bottom=pad_bottom if bottom else 0,
            ),
        )


def _hex_rgb(value: str) -> tuple[int, int, int]:
    s = (value or "").strip().lstrip("#")
    if len(s) == 8:
        s = s[2:]
    if len(s) != 6:
        return 106, 90, 200
    return int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)


def soften(value: str, amount: float | None = None) -> str:
    """Приглушить насыщенность: смешать с тёплым серым."""
    if amount is None:
        amount = 0.34 if not is_dark() else 0.28
    amount = max(0.0, min(0.7, float(amount)))
    r, g, b = _hex_rgb(value)
    gray = (168, 160, 176) if not is_dark() else (92, 86, 108)
    r = int(r * (1 - amount) + gray[0] * amount)
    g = int(g * (1 - amount) + gray[1] * amount)
    b = int(b * (1 - amount) + gray[2] * amount)
    return "#%02X%02X%02X" % (r, g, b)


def apply_mode(page: Optional[ft.Page] = None, mode: Optional[str] = None) -> str:
    """Переключить светлую/тёмную палитру + акцент/пузыри из branding. Возвращает 'light'|'dark'."""
    global BG, SURFACE, CARD, FIELD_BG, INK, MUTED, HINT, STROKE
    global BUBBLE_IN, BUBBLE_OUT, TIME_IN, TIME_OUT, DIVIDER
    global DATE_CHIP, MENU_SCRIM, NAV_IDLE, PRIMARY_SOFT, _MODE
    global PRIMARY, LINK, DOT_ON, PRIMARY_TEXT, BADGE
    if mode is None:
        try:
            from core import prefs

            mode = prefs.theme_mode()
        except Exception:
            mode = "light"
    mode = "dark" if str(mode).lower() == "dark" else "light"
    pal = _DARK if mode == "dark" else _LIGHT
    _MODE = mode
    BG = pal["BG"]
    SURFACE = pal["SURFACE"]
    CARD = pal["CARD"]
    FIELD_BG = pal["FIELD_BG"]
    INK = pal["INK"]
    MUTED = pal["MUTED"]
    HINT = pal["HINT"]
    STROKE = pal["STROKE"]
    BUBBLE_IN = pal["BUBBLE_IN"]
    BUBBLE_OUT = pal["BUBBLE_OUT"]
    TIME_IN = pal["TIME_IN"]
    TIME_OUT = pal["TIME_OUT"]
    DIVIDER = pal["DIVIDER"]
    DATE_CHIP = pal["DATE_CHIP"]
    MENU_SCRIM = pal["MENU_SCRIM"]
    NAV_IDLE = pal["NAV_IDLE"]
    PRIMARY_SOFT = pal["PRIMARY_SOFT"]

    # акцент и пузыри из токенов RaiseHand
    try:
        from core import branding, prefs

        accent_key = prefs.accent_theme()
        bubble_key = prefs.bubble_theme()
        tok = branding.theme_tokens(accent_key, mode)
        bub = branding.theme_tokens(bubble_key, mode)
        if tok.get("fill"):
            soft_fill = soften(tok["fill"])
            PRIMARY = soft_fill
            LINK = soft_fill
            DOT_ON = soft_fill
        if tok.get("soft"):
            PRIMARY_SOFT = tok["soft"]
        if tok.get("bubble_in"):
            BUBBLE_IN = tok["bubble_in"]
        # исходящие — приглушённый fill выбранной bubble-темы
        if bub.get("fill"):
            BUBBLE_OUT = soften(bub["fill"], 0.22 if mode == "light" else 0.18)
        if tok.get("badge"):
            BADGE = soften(tok["badge"], 0.3)
        if tok.get("onfill"):
            PRIMARY_TEXT = "#FFFBFF"
    except Exception:
        pass
    if page is not None:
        try:
            page.theme_mode = ft.ThemeMode.DARK if mode == "dark" else ft.ThemeMode.LIGHT
        except Exception:
            pass
        try:
            page.theme = page_theme()
        except Exception:
            pass
        sync_window_bg(page)
        try:
            apply_window_icon(page)
        except Exception:
            pass
        try:
            page.update()
        except Exception:
            pass
    return mode


def apply_window_icon(page: Optional[ft.Page] = None) -> None:
    """Поставить иконку окна из prefs (десктоп)."""
    if page is None:
        return
    try:
        from core import branding, prefs

        path = branding.app_icon_path(prefs.app_icon_key(), dark=is_dark())
        if not _image_exists(path):
            return
        win = getattr(page, "window", None)
        if win is not None and hasattr(win, "icon"):
            win.icon = path
        elif hasattr(page, "window_icon"):
            page.window_icon = path
    except Exception:
        pass


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
    kwargs: dict = {"color_scheme_seed": PRIMARY}
    try:
        kwargs["font_family"] = FONT_FAMILY
    except Exception:
        pass
    try:
        kwargs["visual_density"] = ft.VisualDensity.COMFORTABLE
    except Exception:
        pass
    # Явная схема — чтобы тёмная не выглядела как авто-инверсия Material
    try:
        if is_dark():
            kwargs["color_scheme"] = ft.ColorScheme(
                primary=PRIMARY,
                on_primary=PRIMARY_TEXT,
                secondary="#9B8CFF",
                surface=CARD,
                on_surface=INK,
                background=BG,
                on_background=INK,
                outline=STROKE,
            )
        else:
            kwargs["color_scheme"] = ft.ColorScheme(
                primary=PRIMARY,
                on_primary=PRIMARY_TEXT,
                surface=SURFACE,
                on_surface=INK,
                background=BG,
                on_background=INK,
            )
    except Exception:
        pass
    # скролл у края окна, без серой «полосы»-трека
    try:
        kwargs["scrollbar_theme"] = ft.ScrollbarTheme(
            thickness=3,
            radius=8,
            main_axis_margin=0,
            cross_axis_margin=0,
            thumb_visibility=False,
            track_visibility=False,
            thumb_color=ft.Colors.with_opacity(0.35, PRIMARY if is_dark() else "#1A1528"),
            track_color=BG,
            track_border_color=BG,
        )
    except Exception:
        pass
    try:
        return ft.Theme(**kwargs)
    except Exception:
        return ft.Theme(color_scheme_seed=PRIMARY)


def lock_phone_window(page: ft.Page) -> None:
    """Десктоп: фиксированное «телефонное» окно. iOS/Android: на весь экран + SafeArea."""
    page.bgcolor = BG
    page.padding = 0
    page.horizontal_alignment = ft.CrossAxisAlignment.STRETCH
    page.vertical_alignment = ft.MainAxisAlignment.START
    sync_viewport(page)

    if is_mobile_runtime():
        # На телефоне не фиксируем 390×844 — иначе ломаются отступы и масштаб
        win = getattr(page, "window", None)
        if win is not None:
            try:
                win.bgcolor = BG
            except Exception:
                pass
        return

    w, h = PHONE_WIDTH, PHONE_HEIGHT
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
        for name, val in (
            ("title_bar_hidden", False),
            ("frameless", False),
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


def sync_window_bg(page: Optional[ft.Page] = None) -> None:
    """Подтянуть page/window bgcolor под текущую тему (без полос)."""
    if page is None:
        return
    try:
        page.bgcolor = BG
    except Exception:
        pass
    win = getattr(page, "window", None)
    if win is not None:
        try:
            win.bgcolor = BG
        except Exception:
            pass


def _press_scale(e):
    try:
        e.control.scale = 0.98 if e.data == "true" else 1.0
        e.control.update()
    except Exception:
        pass


def _btn_width() -> float:
    return min(float(PHONE_WIDTH - PAGE_PADDING * 2) * 0.82, 300.0)


def primary_button(text: str, on_click, *, expand: bool = True) -> ft.Control:
    from flet_app import liquid_glass as lg

    return lg.purple_glass_button(
        text, on_click, width=None if expand else _btn_width(), height=52, expand=expand
    )


def outline_button(text: str, on_click, *, expand: bool = True) -> ft.Control:
    from flet_app import liquid_glass as lg

    return lg.white_glass_button(
        text, on_click, width=None if expand else _btn_width(), height=52, expand=expand
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
    """«Далее» / primary — фиолетовый liquid glass (+ стрелка для «Далее»)."""
    from flet_app import liquid_glass as lg

    w = _btn_width()
    label = (text or "").strip().lower()
    if label in ("далее", "next"):
        return lg.next_glass_button(text, on_click, width=w, height=52)
    return lg.purple_glass_button(text, on_click, width=w, height=52)


def secondary_image_button(text: str, on_click, *, expand: bool = True) -> ft.Control:
    """«Я учитель» — белый liquid glass."""
    from flet_app import liquid_glass as lg

    return lg.white_glass_button(text, on_click, width=_btn_width(), height=52)


def student_image_button(text: str, on_click, *, expand: bool = True) -> ft.Control:
    """«Я ученик» — фиолетовый liquid glass."""
    from flet_app import liquid_glass as lg

    return lg.purple_glass_button(text, on_click, width=_btn_width(), height=52)


def field_border(
    radius: float,
    *,
    color: str = "transparent",
    focused_color: str = PRIMARY,
    width: float = 1.0,
) -> dict:
    """Flet 1.x: вместо deprecated border_radius / border_color / focused_border_color."""
    return {
        ft.ControlState.DEFAULT: ft.OutlineInputBorder(
            border_radius=radius,
            side=ft.BorderSide(color=color, width=0 if color in ("transparent", "") else width),
        ),
        ft.ControlState.FOCUSED: ft.OutlineInputBorder(
            border_radius=radius,
            side=ft.BorderSide(color=focused_color, width=width),
        ),
    }


def field(label: str, hint: str = "", password: bool = False, value: str = "", on_change=None) -> ft.TextField:
    # Flet 1.x: шрифт через text_style / label_style, не font_family у TextField
    return ft.TextField(
        label=label,
        hint_text=hint,
        value=value,
        password=password,
        can_reveal_password=password,
        filled=True,
        bgcolor=SURFACE,
        border=field_border(24, color="transparent", focused_color=PRIMARY),
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
