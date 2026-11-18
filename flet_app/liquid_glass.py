# -*- coding: utf-8 -*-
"""Liquid Glass surfaces on Flet 1.x.

Uses native ``Container.blur`` (Flutter BackdropFilter). Colors via
``Colors.with_opacity`` because Flet expects #AARRGGBB, not CSS #RRGGBBAA.
"""
from __future__ import annotations

from typing import Callable, Optional, Sequence

import flet as ft

from flet_app import mono_icons, theme


def _a(color: str, opacity: float) -> str:
    """Flet colors are #AARRGGBB (alpha first), not CSS #RRGGBBAA."""
    return ft.Colors.with_opacity(opacity, color)


GLASS_TINT = _a("#F4F4F8", 0.66)
GLASS_BORDER = _a("#FFFFFF", 0.80)
GLASS_EDGE = _a("#FFFFFF", 0.90)
GLASS_SHADOW = _a("#1A1A2E", 0.20)
GLASS_PILL_ACTIVE = _a("#FFFFFF", 0.88)
GLASS_PILL_GLOW = _a(theme.PRIMARY, 0.12)
GLASS_CLEAR = _a("#000000", 0.0)
GLASS_BLUR = 28
# Full capsule: radius ≈ half bar height; pad_h clears the end caps so tabs don't clip.
NAV_PAD_V = 5
TAB_H = 48
NAV_RADIUS = (TAB_H + NAV_PAD_V * 2) / 2 + 1  # ~30 — сильное скругление
NAV_PAD_H = 22
ICON = 24
# чуть шире визуально, но без вылезания из слота — иначе края съезжают
PILL_INSET = -3.0
# border left+right is painted inside Container.width
_BORDER_X = 2.0
PILL_SLIDE_MS = 250
TAB_FADE_MS = 250


def _blur(sigma: float = GLASS_BLUR) -> ft.Blur:
    return ft.Blur(sigma_x=sigma, sigma_y=sigma, tile_mode=ft.BlurTileMode.CLAMP)


# --- Buttons: purple / white liquid glass (same recipe as nav capsule) ---
PURPLE_GLASS_TINT = _a(theme.PRIMARY, 0.78)
PURPLE_GLASS_BORDER = _a("#C8B8FF", 0.85)
PURPLE_GLASS_EDGE = _a("#FFFFFF", 0.55)
PURPLE_GLASS_SHADOW = _a(theme.PRIMARY, 0.32)
WHITE_GLASS_TINT = _a("#FFFFFF", 0.82)
# мягкая равномерная обводка — без фиолетовых «полос» по бокам
WHITE_GLASS_BORDER = _a("#E4E0F5", 0.95)
WHITE_GLASS_EDGE = _a("#FFFFFF", 0.98)
WHITE_GLASS_SHADOW = _a("#1A1A2E", 0.14)
BTN_BLUR = 22


def glass_surface_tint() -> str:
    """Навбар / крупные капсулы."""
    if theme.is_dark():
        return _a("#1E1B2A", 0.88)
    return GLASS_TINT


def glass_surface_border() -> str:
    # dark: фиолетово-серый контур, без белых «полос»
    if theme.is_dark():
        return theme.STROKE
    return GLASS_BORDER


def glass_surface_edge() -> str:
    if theme.is_dark():
        return _a(theme.PRIMARY, 0.22)
    return GLASS_EDGE


def glass_surface_shadow() -> str:
    if theme.is_dark():
        return _a("#000000", 0.55)
    return GLASS_SHADOW


def glass_pill_active() -> str:
    if theme.is_dark():
        return _a(theme.PRIMARY, 0.38)
    return GLASS_PILL_ACTIVE


def white_glass_tint() -> str:
    """Карточки настроек / композер / шапка."""
    if theme.is_dark():
        return _a("#221F30", 0.92)
    return WHITE_GLASS_TINT


def white_glass_border() -> str:
    if theme.is_dark():
        return theme.STROKE
    return WHITE_GLASS_BORDER


def white_glass_edge() -> str:
    if theme.is_dark():
        return _a(theme.PRIMARY, 0.18)
    return WHITE_GLASS_EDGE


def accent_glass_tint() -> str:
    """Кнопки акцента (плюс, «Далее», отправка) — текущий цвет темы, мягче."""
    return _a(theme.PRIMARY, 0.62 if theme.is_dark() else 0.78)


def accent_glass_border() -> str:
    if theme.is_dark():
        return _a(theme.PRIMARY, 0.42)
    return _a("#FFFFFF", 0.55)


def accent_glass_shadow() -> str:
    return _a(theme.PRIMARY, 0.18 if theme.is_dark() else 0.22)


def white_glass_shadow() -> str:
    if theme.is_dark():
        return _a("#000000", 0.40)
    return WHITE_GLASS_SHADOW


def purple_glass_border() -> str:
    return accent_glass_border()


def glass_button(
    text: str,
    on_click,
    *,
    variant: str = "purple",
    width: Optional[float] = None,
    height: float = 52,
    expand: bool = False,
    font_size: float = 17,
    content: Optional[ft.Control] = None,
    trailing: Optional[ft.Control] = None,
) -> ft.Control:
    """Pill liquid-glass button. ``variant``: ``purple`` | ``white``."""
    radius = height / 2
    is_purple = variant != "white"
    tint = accent_glass_tint() if is_purple else white_glass_tint()
    border_c = purple_glass_border() if is_purple else white_glass_border()
    edge = _a("#FFFFFF", 0.45) if is_purple else white_glass_edge()
    shadow_c = accent_glass_shadow() if is_purple else white_glass_shadow()
    # white-variant в dark: светлый текст, не фиолетовый на тёмном стекле
    if is_purple:
        text_color = theme.PRIMARY_TEXT
    else:
        text_color = theme.INK if theme.is_dark() else theme.PRIMARY

    label = ft.Text(
        text,
        color=text_color,
        size=font_size,
        weight=ft.FontWeight.W_600,
        text_align=ft.TextAlign.CENTER,
        font_family=theme.FONT_FAMILY,
    )
    if content is not None:
        inner: ft.Control = content
    elif trailing is not None:
        inner = ft.Row(
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            tight=True,
            spacing=8,
            controls=[label, trailing],
        )
    else:
        inner = label

    if is_purple and not theme.is_dark():
        border = ft.Border(
            top=ft.BorderSide(1.6, edge),
            left=ft.BorderSide(1.0, border_c),
            right=ft.BorderSide(1.0, border_c),
            bottom=ft.BorderSide(1.0, _a(border_c, 0.35)),
        )
    else:
        # dark / white: ровный контур без белых бликов
        border = ft.Border.all(1.1, border_c)

    body = ft.Container(
        content=inner,
        width=width,
        height=height,
        expand=expand if width is None else None,
        border_radius=radius,
        bgcolor=tint,
        blur=_blur(BTN_BLUR),
        border=border,
        alignment=ft.Alignment.CENTER,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        on_click=on_click,
        ink=False,
        animate_scale=ft.Animation(120, ft.AnimationCurve.EASE_OUT),
        scale=1,
        on_hover=theme._press_scale,
    )

    return ft.Container(
        content=body,
        width=width,
        expand=expand if width is None else None,
        border_radius=radius,
        clip_behavior=ft.ClipBehavior.NONE,
        alignment=ft.Alignment.CENTER,
        shadow=ft.BoxShadow(
            blur_radius=28,
            spread_radius=0,
            color=shadow_c,
            offset=ft.Offset(0, 10),
        ),
    )


def purple_glass_button(text: str, on_click, **kwargs) -> ft.Control:
    return glass_button(text, on_click, variant="purple", **kwargs)


def white_glass_button(text: str, on_click, **kwargs) -> ft.Control:
    return glass_button(text, on_click, variant="white", **kwargs)


def next_glass_button(text: str, on_click, **kwargs) -> ft.Control:
    """«Далее» — фиолетовый glass + стрелка вправо."""
    arrow = ft.Icon(
        ft.Icons.ARROW_FORWARD_ROUNDED
        if hasattr(ft.Icons, "ARROW_FORWARD_ROUNDED")
        else ft.Icons.ARROW_FORWARD,
        size=20,
        color=theme.PRIMARY_TEXT,
    )
    kwargs.pop("trailing", None)
    return purple_glass_button(text, on_click, trailing=arrow, **kwargs)


def glass_circle_button(
    on_click,
    *,
    content: ft.Control,
    size: float = 44,
    variant: str = "white",
) -> ft.Control:
    """Круглая liquid-glass кнопка (attach / send / FAB)."""
    radius = size / 2
    is_purple = variant != "white"
    tint = accent_glass_tint() if is_purple else white_glass_tint()
    if is_purple:
        border_c = purple_glass_border()
    else:
        border_c = white_glass_border()
    shadow_c = accent_glass_shadow() if is_purple else white_glass_shadow()

    body = ft.Container(
        width=size,
        height=size,
        border_radius=radius,
        bgcolor=tint,
        blur=_blur(BTN_BLUR),
        border=ft.Border.all(1.0, border_c),
        alignment=ft.Alignment.CENTER,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        on_click=on_click,
        ink=False,
        animate_scale=ft.Animation(120, ft.AnimationCurve.EASE_OUT),
        scale=1,
        on_hover=theme._press_scale,
        content=content,
    )
    return ft.Container(
        width=size,
        height=size,
        border_radius=radius,
        clip_behavior=ft.ClipBehavior.NONE,
        alignment=ft.Alignment.CENTER,
        shadow=ft.BoxShadow(
            blur_radius=22,
            spread_radius=0,
            color=shadow_c,
            offset=ft.Offset(0, 8),
        ),
        content=body,
    )


def purple_glass_fab(on_click, *, size: float = 48, icon: str = "+") -> ft.Control:
    """Круглый FAB: ровный круг, плюс по центру (Icon, не Text)."""
    plus = ft.Icon(
        ft.Icons.ADD,
        size=int(size * 0.52),
        color=theme.PRIMARY_TEXT,
    )
    # icon arg kept for API compat; always use centered Material add
    _ = icon
    return glass_circle_button(on_click, content=plus, size=size, variant="purple")


def glass_capsule(
    content: ft.Control,
    *,
    radius: float = NAV_RADIUS,
    blur: float = GLASS_BLUR,
    tint: Optional[str] = None,
    border_color: Optional[str] = None,
    padding: Optional[ft.Padding] = None,
    shadow: bool = True,
    highlight: bool = True,
    width: Optional[float] = None,
    height: Optional[float] = None,
) -> ft.Control:
    """Floating liquid-glass capsule: blur + tint + specular rim + soft depth."""
    if tint is None:
        tint = glass_surface_tint()
    if border_color is None:
        border_color = glass_surface_border()
    # dark: без яркого верхнего блика (белые «полосы»)
    if theme.is_dark() or not highlight:
        border = ft.Border.all(1.0, border_color)
    else:
        edge = glass_surface_edge()
        border = ft.Border(
            top=ft.BorderSide(1.6, edge),
            left=ft.BorderSide(1.0, border_color),
            right=ft.BorderSide(1.0, border_color),
            bottom=ft.BorderSide(1.0, _a("#FFFFFF", 0.40)),
        )

    body = ft.Container(
        content=content,
        padding=padding,
        width=width,
        height=height,
        border_radius=radius,
        bgcolor=tint,
        blur=_blur(blur),
        border=border,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
    )

    if not shadow:
        return body

    return ft.Container(
        content=body,
        width=width,
        border_radius=radius,
        clip_behavior=ft.ClipBehavior.NONE,
        shadow=ft.BoxShadow(
            blur_radius=36 if not theme.is_dark() else 28,
            spread_radius=0,
            color=glass_surface_shadow(),
            offset=ft.Offset(0, 12 if not theme.is_dark() else 10),
        ),
    )


class SlidingLiquidNav:
    """iOS-style liquid glass bar: one pill that slides between tabs."""

    def __init__(
        self,
        tabs: Sequence[tuple[str, str]],
        *,
        active: str,
        on_tab: Callable[[str], None],
        icon_builder: Callable[[str, bool], ft.Control],
        bar_width: float,
    ):
        self.keys = [k for k, _ in tabs]
        self.labels = {k: lab for k, lab in tabs}
        self.on_tab = on_tab
        self.icon_builder = icon_builder
        self.active = active if active in self.keys else self.keys[0]
        self.n = len(self.keys)
        self.gap = 0.0
        self.bar_width = float(bar_width)
        # content box inside border+padding; keep clear of rounded corners
        self.inner_w = max(0.0, self.bar_width - NAV_PAD_H * 2 - _BORDER_X)
        self.tab_w = self.inner_w / self.n
        self.pill_w = max(24.0, self.tab_w - PILL_INSET * 2)
        self.pill_h = TAB_H - 2

        self._icons: dict[str, ft.Control] = {}
        self._labels: dict[str, ft.Text] = {}
        self.pill = self._make_pill()
        hits = self._make_hits()
        stack = ft.Stack(
            width=self.inner_w,
            height=TAB_H,
            clip_behavior=ft.ClipBehavior.NONE,
            controls=[self.pill, hits],
        )
        self.control = glass_capsule(
            stack,
            radius=NAV_RADIUS,
            blur=GLASS_BLUR,
            tint=glass_surface_tint(),
            border_color=glass_surface_border(),
            padding=ft.Padding.symmetric(horizontal=NAV_PAD_H, vertical=NAV_PAD_V),
            width=self.bar_width,
            highlight=True,
            shadow=True,
        )

    def _pill_left(self, key: str) -> float:
        i = self.keys.index(key)
        # строго по центру равного слота — Поиск/Настройки без смещения
        return i * self.tab_w + (self.tab_w - self.pill_w) / 2

    def _make_pill(self) -> ft.Container:
        return ft.Container(
            width=self.pill_w,
            height=self.pill_h,
            left=self._pill_left(self.active),
            top=(TAB_H - self.pill_h) / 2,
            border_radius=self.pill_h / 2,
            bgcolor=glass_pill_active(),
            border=ft.Border.all(
                1,
                (_a(theme.PRIMARY, 0.35) if theme.is_dark() else glass_surface_edge()),
            ),
            animate_position=ft.Animation(
                PILL_SLIDE_MS, ft.AnimationCurve.EASE_IN_OUT_CUBIC
            ),
            shadow=ft.BoxShadow(
                blur_radius=14,
                spread_radius=0,
                color=_a(theme.PRIMARY, 0.22),
                offset=ft.Offset(0, 4),
            ),
        )

    def _make_hits(self) -> ft.Control:
        cells: list[ft.Control] = []
        for key in self.keys:
            is_on = key == self.active
            icon = self.icon_builder(key, is_on)
            self._icons[key] = icon
            label = ft.Text(
                self.labels[key],
                size=10,
                color=mono_icons.nav_label_color(is_on),
                weight=ft.FontWeight.W_700 if is_on else ft.FontWeight.W_500,
                font_family=theme.FONT_FAMILY,
                max_lines=1,
                text_align=ft.TextAlign.CENTER,
                overflow=ft.TextOverflow.ELLIPSIS if hasattr(ft, "TextOverflow") else None,
            )
            self._labels[key] = label
            cells.append(
                ft.Container(
                    width=self.tab_w,
                    height=TAB_H,
                    alignment=ft.Alignment.CENTER,
                    ink=False,
                    on_click=lambda e, k=key: self._click(k),
                    content=ft.Column(
                        spacing=1,
                        tight=True,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        alignment=ft.MainAxisAlignment.CENTER,
                        controls=[icon, label],
                    ),
                )
            )
        return ft.Container(
            left=0,
            top=0,
            width=self.inner_w,
            height=TAB_H,
            content=ft.Row(
                spacing=0,
                tight=True,
                controls=cells,
            ),
        )

    def _click(self, key: str) -> None:
        if key == self.active:
            return
        # Parent decides; calls set_active() when switch is accepted.
        self.on_tab(key)

    def set_active(self, key: str) -> None:
        if key not in self.keys:
            return
        self.active = key
        self.pill.left = self._pill_left(key)
        for k in self.keys:
            on = k == key
            lab = self._labels[k]
            lab.color = mono_icons.nav_label_color(on)
            lab.weight = ft.FontWeight.W_700 if on else ft.FontWeight.W_500
            new_icon = self.icon_builder(k, on)
            old = self._icons[k]
            try:
                if isinstance(old, ft.Image) and isinstance(new_icon, ft.Image):
                    old.src = new_icon.src
                    old.opacity = getattr(new_icon, "opacity", None) or 1.0
                    # SVG уже с цветом — не оставляем старый color_blend (пикселизация)
                    if hasattr(old, "color"):
                        old.color = getattr(new_icon, "color", None)
                    if hasattr(old, "color_blend_mode"):
                        old.color_blend_mode = getattr(new_icon, "color_blend_mode", None)
                elif isinstance(old, ft.Icon) and isinstance(new_icon, ft.Icon):
                    old.name = getattr(new_icon, "name", None) or getattr(new_icon, "icon", None)
                    old.color = new_icon.color
                else:
                    self._icons[k] = new_icon
            except Exception:
                self._icons[k] = new_icon
        try:
            self.pill.update()
            for lab in self._labels.values():
                lab.update()
            for ic in self._icons.values():
                try:
                    ic.update()
                except Exception:
                    pass
        except Exception:
            pass


def liquid_nav_bar(
    tabs: Sequence[tuple[str, str]],
    *,
    active: str,
    on_tab: Callable[[str], None],
    icon_builder: Callable[[str, bool], ft.Control],
    bar_width: float,
) -> tuple[ft.Control, SlidingLiquidNav]:
    nav = SlidingLiquidNav(
        tabs,
        active=active,
        on_tab=on_tab,
        icon_builder=icon_builder,
        bar_width=bar_width,
    )
    return nav.control, nav
