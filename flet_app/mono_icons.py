# -*- coding: utf-8 -*-
"""Иконки RaiseHand из папки проект (kit-спрайты + mono fallback).

Nav — SVG. UI (edit/attach/send/eye…) — PNG из
``assets/images/kit/{accent}-{light|dark}/``, вырезанные из
``проект/raisehand-icon-kit/sprites``.
"""
from __future__ import annotations

from typing import Optional

import flet as ft

from flet_app import theme

_NAV_KEYS = {
    "search": "search",
    "chats": "chats",
    "groups": "groups",
    "settings": "settings",
}

_NAV_FALLBACK_ICON = {
    "search": ft.Icons.SEARCH,
    "chats": ft.Icons.CHAT_BUBBLE_OUTLINE,
    "groups": ft.Icons.GROUPS_OUTLINED,
    "settings": ft.Icons.SETTINGS_OUTLINED,
}

# Material — только если спрайта нет
_UI_FALLBACK = {
    "edit": ft.Icons.EDIT_ROUNDED,
    "attach": ft.Icons.ATTACH_FILE,
    "send": ft.Icons.SEND_ROUNDED,
    "eye": ft.Icons.VISIBILITY_OUTLINED,
    "eye-off": ft.Icons.VISIBILITY_OFF_OUTLINED,
    "back": ft.Icons.CHEVRON_LEFT,
    "plus": ft.Icons.ADD,
    "pin": ft.Icons.PUSH_PIN,
    "copy": ft.Icons.CONTENT_COPY,
    "delete": ft.Icons.DELETE_OUTLINE,
    "reply": ft.Icons.REPLY,
    "flag": ft.Icons.FLAG_OUTLINED,
    "more": ft.Icons.MORE_HORIZ,
    "close": ft.Icons.CLOSE,
}


def _tone() -> str:
    return "white" if theme.is_dark() else "black"


def _accent() -> str:
    try:
        from core import prefs

        return prefs.accent_theme()
    except Exception:
        return "violet"


def _mode() -> str:
    return "dark" if theme.is_dark() else "light"


def kit_folder() -> str:
    """``assets/images/kit/violet-dark`` и т.п. — из проект/raisehand-icon-kit."""
    return theme.asset("assets", "images", "kit", f"{_accent()}-{_mode()}")


def kit_path(name: str, *, variant: str = "") -> str:
    """
    name: edit | attach | send | eye …
    variant: '' | 'idle' | 'onaccent'
    """
    key = f"icon-{name}"
    if variant:
        key = f"icon-{name}-{variant}"
    return theme.asset("assets", "images", "kit", f"{_accent()}-{_mode()}", f"{key}.png")


def nav_label_color(active: bool) -> str:
    """Активная вкладка — акцент темы, остальные — приглушённые."""
    if active:
        return theme.PRIMARY
    return theme.NAV_IDLE


def nav_svg_path(key: str, active: bool) -> str:
    """Вектор из assets/images/nav_svg — idle фиолетовый, active светлый/brand."""
    name = _NAV_KEYS.get(key, key)
    if active:
        folder = "active_dark" if theme.is_dark() else "active_light"
    else:
        folder = "idle"
    return theme.asset("assets", "images", "nav_svg", folder, f"{name}.svg")


def line(name: str, *, tone: Optional[str] = None) -> str:
    t = tone or _tone()
    return theme.asset("assets", "images", "mono", t, f"{name}.png")


def status(kind: str, *, on_bubble: bool = False, tone: Optional[str] = None) -> str:
    if on_bubble:
        for cand in (
            f"{kind}_onviolet.png",
            f"{kind}_white.png",
            f"{kind}.png",
        ):
            p = theme.asset("assets", "images", "mono", "status", cand)
            if theme._image_exists(p):
                return p
    t = tone or _tone()
    for cand in (f"{kind}_{t}.png", f"{kind}.png"):
        p = theme.asset("assets", "images", "mono", "status", cand)
        if theme._image_exists(p):
            return p
    return theme.asset("assets", "images", "mono", "status", f"{kind}_{t}.png")


def ui_path(name: str, *, variant: str = "") -> str:
    """Сначала kit из проект, потом legacy assets/images/ui."""
    path = kit_path(name, variant=variant)
    if theme._image_exists(path):
        return path
    # fallback: общий ui-набор
    suffix = f"-{variant}" if variant else ""
    legacy = theme.asset("assets", "images", "ui", f"icon-{name}{suffix}.png")
    if theme._image_exists(legacy):
        return legacy
    return path


def image(
    name: str,
    *,
    size: float = 24,
    opacity: float = 1.0,
    tone: Optional[str] = None,
    color: Optional[str] = None,
) -> Optional[ft.Control]:
    # предпочтительно kit; mono line — запасной
    for candidate in (
        ui_path(name),
        line(name, tone=tone),
    ):
        if theme._image_exists(candidate):
            kwargs: dict = {
                "src": candidate,
                "width": size,
                "height": size,
                "fit": ft.BoxFit.CONTAIN,
                "opacity": opacity,
            }
            if color:
                kwargs["color"] = color
                try:
                    kwargs["color_blend_mode"] = ft.BlendMode.SRC_IN
                except Exception:
                    pass
            return ft.Image(**kwargs)
    return None


def ui_icon(
    name: str,
    *,
    size: float = 22,
    variant: str = "",
    fallback_color: Optional[str] = None,
) -> ft.Control:
    """Спрайт из проект/kit; иначе Material."""
    path = ui_path(name, variant=variant)
    if theme._image_exists(path):
        return ft.Image(src=path, width=size, height=size, fit=ft.BoxFit.CONTAIN)
    # idle/onaccent → базовый
    if variant:
        base = ui_path(name, variant="")
        if theme._image_exists(base):
            return ft.Image(src=base, width=size, height=size, fit=ft.BoxFit.CONTAIN)
    color = fallback_color or (theme.INK if theme.is_dark() else theme.PRIMARY)
    return ft.Icon(
        _UI_FALLBACK.get(name, ft.Icons.CIRCLE),
        size=size,
        color=color,
    )


def nav_icon(key: str, active: bool, *, size: float = 24) -> ft.Control:
    """Nav: SVG, перекрашенный в акцент темы (активная) или приглушённый."""
    path = nav_svg_path(key, active)
    tint = theme.PRIMARY if active else theme.NAV_IDLE
    if theme._image_exists(path):
        kwargs: dict = {
            "src": path,
            "width": size,
            "height": size,
            "fit": ft.BoxFit.CONTAIN,
            "color": tint,
        }
        try:
            kwargs["color_blend_mode"] = ft.BlendMode.SRC_IN
        except Exception:
            pass
        return ft.Image(**kwargs)
    return ft.Icon(
        _NAV_FALLBACK_ICON.get(key, ft.Icons.CIRCLE),
        size=size,
        color=tint,
    )


def status_image(
    kind: str,
    *,
    size: float = 16,
    on_bubble: bool = False,
) -> Optional[ft.Control]:
    path = status(kind, on_bubble=on_bubble)
    if not theme._image_exists(path):
        return None
    return ft.Image(src=path, width=size, height=size, fit=ft.BoxFit.CONTAIN)
