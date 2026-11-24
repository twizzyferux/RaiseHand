# -*- coding: utf-8 -*-
"""Telegram-style profile layout helpers (RaiseHand theme)."""
from __future__ import annotations

from typing import Any, Callable, Optional, Union

import flet as ft

from core import gradients
from core.i18n import t
from flet_app import liquid_glass, mono_icons, theme

IconLike = Union[str, ft.Icons, ft.Control]
RowSpec = tuple[str, str, Optional[Callable]]
ActionSpec = tuple[IconLike, str, Optional[Callable]]


def _card_width() -> float:
    return float(theme.PHONE_WIDTH - 32)


def profile_avatar_from_seed(
    seed: str,
    first: str,
    last: str,
    size: float = 120,
    *,
    hide: bool = False,
    image_path: str | None = None,
) -> ft.Control:
    if hide:
        return ft.Container(
            width=size,
            height=size,
            border_radius=size / 2,
            bgcolor=theme.FIELD_BG,
            alignment=ft.Alignment.CENTER,
            border=None,
            content=ft.Icon(ft.Icons.PERSON_OUTLINE, size=size * 0.42, color=theme.MUTED),
        )
    path = (image_path or "").strip()
    if path and theme._image_exists(path):
        return ft.Container(
            width=size,
            height=size,
            border_radius=size / 2,
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
            content=ft.Image(src=path, width=size, height=size, fit=ft.BoxFit.COVER),
        )
    colors = gradients.colors_for(seed or "user")
    top = "#%02X%02X%02X" % colors["top"]
    bottom = "#%02X%02X%02X" % colors["bottom"]
    initials = gradients.initials_for(first, last)
    return ft.Container(
        width=size,
        height=size,
        border_radius=size / 2,
        gradient=ft.LinearGradient(
            begin=ft.Alignment(0, -1),
            end=ft.Alignment(0, 1),
            colors=[top, bottom],
        ),
        alignment=ft.Alignment.CENTER,
        content=ft.Text(
            initials,
            size=int(size * 0.32),
            weight=ft.FontWeight.W_700,
            color="#FFFFFF",
            font_family=theme.FONT_FAMILY,
        ),
    )


def _icon_content(icon: IconLike, *, size: float = 22) -> ft.Control:
    if isinstance(icon, ft.Control):
        return icon
    if isinstance(icon, str):
        return mono_icons.ui_icon(icon, size=size)
    return ft.Icon(icon, size=size, color=theme.INK)


def action_button(
    icon_control_or_Icons: IconLike,
    label: str,
    on_click: Optional[Callable] = None,
) -> ft.Control:
    circle = ft.Container(
        width=56,
        height=56,
        border_radius=28,
        bgcolor=theme.CARD,
        alignment=ft.Alignment.CENTER,
        border=None,
        shadow=ft.BoxShadow(
            blur_radius=8,
            color=liquid_glass.white_glass_shadow(),
            offset=ft.Offset(0, 2),
        ),
        content=_icon_content(icon_control_or_Icons, size=22),
        on_click=on_click if on_click else None,
        ink=bool(on_click),
    )
    return ft.Column(
        spacing=6,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        tight=True,
        controls=[
            circle,
            ft.Text(
                label,
                size=11,
                color=theme.MUTED,
                font_family=theme.FONT_FAMILY,
                text_align=ft.TextAlign.CENTER,
                max_lines=2,
                overflow=ft.TextOverflow.ELLIPSIS,
            ),
        ],
    )


def actions_row(items: list[ActionSpec]) -> ft.Control:
    buttons = [
        action_button(icon, lbl, fn) for icon, lbl, fn in items
    ]
    return ft.Row(
        alignment=ft.MainAxisAlignment.SPACE_EVENLY,
        vertical_alignment=ft.CrossAxisAlignment.START,
        wrap=True,
        spacing=8,
        run_spacing=12,
        controls=buttons,
    )


def _info_row(label: str, value: str, on_click: Optional[Callable]) -> ft.Control:
    value_ctrl = ft.Text(
        value or "—",
        size=17,
        weight=ft.FontWeight.W_500,
        color=theme.INK,
        font_family=theme.FONT_FAMILY,
        max_lines=4,
        overflow=ft.TextOverflow.ELLIPSIS,
        selectable=not on_click,
    )
    col = ft.Column(
        spacing=4,
        tight=True,
        expand=True,
        controls=[
            ft.Text(
                label,
                size=13,
                color=theme.MUTED,
                font_family=theme.FONT_FAMILY,
            ),
            value_ctrl,
        ],
    )
    row = ft.Row(
        spacing=8,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            col,
            ft.Icon(ft.Icons.CHEVRON_RIGHT, color=theme.MUTED, size=20)
            if on_click
            else ft.Container(width=0),
        ],
    )
    if on_click:
        return ft.Container(ink=True, on_click=on_click, padding=ft.Padding.symmetric(vertical=12), content=row)
    return ft.Container(padding=ft.Padding.symmetric(vertical=12), content=row)


def info_card(rows: list[RowSpec]) -> ft.Control:
    card_w = _card_width()
    inner: list[ft.Control] = []
    for i, (label, value, on_click) in enumerate(rows):
        if i > 0:
            inner.append(ft.Container(height=1, bgcolor=theme.DIVIDER, opacity=0.35))
        inner.append(_info_row(label, value, on_click))
    return ft.Container(
        width=card_w,
        padding=ft.Padding.symmetric(horizontal=16, vertical=4),
        border_radius=20,
        bgcolor=theme.CARD,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        shadow=ft.BoxShadow(
            blur_radius=12,
            color=liquid_glass.white_glass_shadow(),
            offset=ft.Offset(0, 3),
        ),
        content=ft.Column(spacing=0, tight=True, controls=inner),
    )


def _seg_tab(label: str, selected: bool, on_tap: Callable) -> ft.Control:
    return ft.Container(
        expand=True,
        padding=ft.Padding.symmetric(vertical=8),
        border_radius=10,
        bgcolor=theme.PRIMARY_SOFT if selected else "transparent",
        alignment=ft.Alignment.CENTER,
        on_click=on_tap,
        ink=False,
        content=ft.Text(
            label,
            size=14,
            weight=ft.FontWeight.W_600 if selected else ft.FontWeight.W_500,
            color=theme.PRIMARY if selected else theme.MUTED,
            font_family=theme.FONT_FAMILY,
        ),
    )


def media_tabs_block(
    media_controls: list[ft.Control],
    *,
    empty_text: str = t("profile.no_media"),
    links_controls: list[ft.Control] | None = None,
    links_empty_text: str = t("profile.no_links"),
) -> ft.Control:
    links_controls = links_controls if links_controls is not None else []

    state: dict[str, Any] = {"tab": "media"}
    media_host = ft.Container()
    tabs_host = ft.Container()
    links_host = ft.Container()

    def _grid_or_empty(cells: list[ft.Control], empty: str) -> ft.Control:
        if not cells:
            return ft.Container(
                padding=ft.Padding.symmetric(vertical=24),
                alignment=ft.Alignment.CENTER,
                content=ft.Text(
                    empty,
                    size=14,
                    color=theme.MUTED,
                    font_family=theme.FONT_FAMILY,
                    text_align=ft.TextAlign.CENTER,
                ),
            )
        return ft.Row(wrap=True, spacing=4, run_spacing=4, controls=cells)

    def _render_body():
        if state["tab"] == "media":
            media_host.content = _grid_or_empty(media_controls, empty_text)
        else:
            links_host.content = _grid_or_empty(links_controls, links_empty_text)
        stack = media_host if state["tab"] == "media" else links_host
        return stack

    def _set_tab(tab: str):
        def _(_e=None):
            state["tab"] = tab
            tabs_host.content = _tabs_row()
            body.content = _render_body()
            try:
                body.update()
                tabs_host.update()
            except Exception:
                pass

        return _

    def _tabs_row() -> ft.Control:
        return ft.Container(
            padding=ft.Padding.all(4),
            border_radius=12,
            bgcolor=theme.FIELD_BG,
            content=ft.Row(
                spacing=4,
                controls=[
                    _seg_tab(t("profile.media_tab"), state["tab"] == "media", _set_tab("media")),
                    _seg_tab(t("profile.links_tab"), state["tab"] == "links", _set_tab("links")),
                ],
            ),
        )

    body = ft.Container(content=_render_body())
    tabs_host.content = _tabs_row()

    card_w = _card_width()
    return ft.Container(
        width=card_w,
        padding=ft.Padding.all(16),
        border_radius=20,
        bgcolor=theme.CARD,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        shadow=ft.BoxShadow(
            blur_radius=12,
            color=liquid_glass.white_glass_shadow(),
            offset=ft.Offset(0, 3),
        ),
        content=ft.Column(
            spacing=12,
            tight=True,
            controls=[tabs_host, body],
        ),
    )


def profile_head_block(
    *,
    avatar: ft.Control,
    display_name: ft.Control | str,
    status_line: str = "",
    name_on_click: Optional[Callable] = None,
) -> ft.Control:
    if isinstance(display_name, str):
        name_ctrl: ft.Control = ft.Text(
            display_name,
            size=24,
            weight=ft.FontWeight.W_700,
            color=theme.INK,
            font_family=theme.FONT_FAMILY,
            text_align=ft.TextAlign.CENTER,
            max_lines=2,
            overflow=ft.TextOverflow.ELLIPSIS,
        )
    else:
        name_ctrl = display_name

    name_wrap = name_ctrl
    if name_on_click:
        name_wrap = ft.Container(
            ink=True,
            on_click=name_on_click,
            content=ft.Row(
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=6,
                tight=True,
                controls=[name_ctrl, mono_icons.ui_icon("edit", size=16)],
            ),
        )

    controls: list[ft.Control] = [
        avatar,
        name_wrap,
    ]
    if status_line:
        controls.append(
            ft.Text(
                status_line,
                size=14,
                color=theme.MUTED,
                font_family=theme.FONT_FAMILY,
                text_align=ft.TextAlign.CENTER,
            )
        )
    return ft.Column(
        spacing=10,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        tight=True,
        controls=controls,
    )


def profile_shell(
    page: ft.Page,
    *,
    title: str,
    on_back: Callable,
    trailing: Optional[ft.Control] = None,
    body_controls: list[ft.Control],
    edge_swipe: bool = True,
) -> ft.Control:
    back = liquid_glass.glass_circle_button(
        on_back,
        content=mono_icons.ui_icon("back", size=22),
        size=44,
        variant="white",
    )
    header_controls: list[ft.Control] = [back]
    if title:
        header_controls.append(
            ft.Text(
                title,
                size=20,
                weight=ft.FontWeight.W_700,
                color=theme.INK,
                font_family=theme.FONT_FAMILY,
                expand=True,
                max_lines=1,
                overflow=ft.TextOverflow.ELLIPSIS,
            )
        )
    else:
        header_controls.append(ft.Container(expand=True))
    if trailing is not None:
        header_controls.append(trailing)

    header = ft.Container(
        padding=ft.Padding.symmetric(horizontal=12, vertical=8),
        content=ft.Row(
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=header_controls,
        ),
    )
    header_wrap = ft.Container(
        content=header,
        opacity=0,
        animate_opacity=ft.Animation(220, ft.AnimationCurve.EASE_OUT),
    )

    sections = [
        ft.Container(
            alignment=ft.Alignment.CENTER,
            content=c,
            opacity=0,
            offset=ft.Offset(0, 0.02),
            animate_opacity=ft.Animation(260, ft.AnimationCurve.EASE_OUT),
            animate_offset=ft.Animation(280, ft.AnimationCurve.EASE_OUT),
            data={"delay": 40 + i * 50},
        )
        for i, c in enumerate(body_controls)
    ]

    scroller = ft.ListView(
        expand=True,
        spacing=16,
        padding=ft.Padding.only(left=16, right=16, top=4, bottom=28),
        controls=sections,
    )

    root = ft.Container(
        expand=True,
        bgcolor=theme.BG,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        content=ft.Column(
            expand=True,
            spacing=0,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[header_wrap, scroller],
        ),
    )

    async def _fade_in():
        import asyncio

        await asyncio.sleep(0.03)
        header_wrap.opacity = 1
        try:
            header_wrap.update()
        except Exception:
            pass
        for box in sections:
            delay = int((box.data or {}).get("delay", 0))
            if delay:
                await asyncio.sleep(delay / 1000.0)
            box.opacity = 1
            box.offset = ft.Offset(0, 0)
            try:
                box.update()
            except Exception:
                pass

    try:
        page.run_task(_fade_in)
    except Exception:
        header_wrap.opacity = 1
        for box in sections:
            box.opacity = 1
            box.offset = ft.Offset(0, 0)

    if edge_swipe:
        return theme.edge_swipe_back(root, on_back=on_back)
    return root


def media_cells_from_messages(media, *, cell: float = 104) -> list[ft.Control]:
    cells: list[ft.Control] = []
    for m in media[:24]:
        src = m.image or ""
        if theme._image_exists(src):
            body: ft.Control = ft.Image(src=src, width=cell, height=cell, fit=ft.BoxFit.COVER)
        else:
            body = ft.Container(
                width=cell,
                height=cell,
                bgcolor=theme.FIELD_BG,
                alignment=ft.Alignment.CENTER,
                content=ft.Icon(ft.Icons.IMAGE_OUTLINED, color=theme.MUTED, size=28),
            )
        cells.append(
            ft.Container(
                width=cell,
                height=cell,
                border_radius=12,
                clip_behavior=ft.ClipBehavior.HARD_EDGE,
                content=body,
            )
        )
    return cells