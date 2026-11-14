# -*- coding: utf-8 -*-
"""Экран «Чаты»: список из chat_data, розовые бейджи, превью последнего."""
from __future__ import annotations

import flet as ft

from core import gradients
from flet_app import chat_data
from flet_app.app_state import STATE
from flet_app import theme


def _nav_icon(name: str, active: bool) -> str:
    color = "violet" if active else "black"
    return theme.asset("assets", "images", "chats", f"nav_{name}_{color}.png")


def _status_icon(kind: str) -> str:
    return theme.asset("assets", "images", "chats", f"status_{kind}.png")


def _avatar(contact: chat_data.Contact, size: float = 52) -> ft.Control:
    initials = gradients.initials_for(contact.first, contact.last)
    colors = gradients.colors_for(contact.seed)
    top = "#%02X%02X%02X" % colors["top"]
    bottom = "#%02X%02X%02X" % colors["bottom"]
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
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        content=ft.Text(
            initials,
            size=max(12, int(size * 0.28)),
            weight=ft.FontWeight.W_600,
            color="#FFFFFF",
            font_family=theme.FONT_FAMILY,
        ),
    )


def _unread_badge(n: int) -> ft.Control:
    """Розовый бейдж для ЛЮБОГО n >= 1 (1, 2, 3, … 99+)."""
    if n < 1:
        return ft.Container(width=0, height=0)
    text = "99+" if n >= 100 else str(int(n))
    single = n < 10
    return ft.Container(
        width=22 if single else None,
        height=22,
        border_radius=11,
        bgcolor="#F0447C",
        padding=ft.Padding.symmetric(horizontal=0 if single else 7, vertical=0),
        alignment=ft.Alignment.CENTER,
        content=ft.Text(
            text,
            size=12,
            weight=ft.FontWeight.W_600,
            color="#FFFFFF",
            font_family=theme.FONT_FAMILY,
            text_align=ft.TextAlign.CENTER,
        ),
    )


def _trailing(contact: chat_data.Contact) -> ft.Control:
    parts: list[ft.Control] = []
    icon_size = 18

    if contact.pinned and theme._image_exists(_status_icon("pin")):
        parts.append(
            ft.Image(src=_status_icon("pin"), width=icon_size, height=icon_size, fit=ft.BoxFit.CONTAIN)
        )

    if contact.unread > 0:
        parts.append(_unread_badge(contact.unread))
    elif contact.last_mine:
        # галочки: sent / read
        kind = "read" if contact.last_read else "sent"
        path = _status_icon(kind)
        if theme._image_exists(path):
            parts.append(ft.Image(src=path, width=icon_size + 2, height=icon_size + 2, fit=ft.BoxFit.CONTAIN))
        elif contact.last_time:
            parts.append(
                ft.Text(contact.last_time, size=13, color=theme.MUTED, font_family=theme.FONT_FAMILY)
            )
    elif contact.last_time:
        parts.append(
            ft.Text(contact.last_time, size=13, color=theme.MUTED, font_family=theme.FONT_FAMILY)
        )

    if not parts:
        parts.append(ft.Container(width=1, height=1))

    return ft.Column(
        spacing=4,
        horizontal_alignment=ft.CrossAxisAlignment.END,
        tight=True,
        controls=parts,
    )



def _role_badge(kind: str) -> ft.Control:
    """Бейдж роли: учитель — зелёный, админ — фиолетовый, бан — красный."""
    styles = {
        "teacher": ("#E5F6E8", "#1B7A3A", "Учитель"),
        "admin": ("#EDE7FF", "#5B3FF0", "Админ"),
        "banned": ("#FDE8E8", "#C24141", "Бан"),
    }
    bg, fg, label = styles.get(kind, styles["teacher"])
    return ft.Container(
        padding=ft.Padding.symmetric(horizontal=8, vertical=2),
        border_radius=6,
        bgcolor=bg,
        content=ft.Text(
            label,
            size=11,
            weight=ft.FontWeight.W_600,
            color=fg,
            font_family=theme.FONT_FAMILY,
        ),
    )


def _badges_for(contact) -> list:
    out = []
    if getattr(contact, "is_banned", False):
        out.append(_role_badge("banned"))
    if getattr(contact, "is_admin", False):
        out.append(_role_badge("admin"))
    if getattr(contact, "is_teacher", False):
        out.append(_role_badge("teacher"))
    return out or [ft.Container(width=0)]


def _chat_row(contact: chat_data.Contact, on_click) -> ft.Control:
    preview_color = theme.INK if contact.unread else theme.MUTED
    preview_weight = ft.FontWeight.W_600 if contact.unread else ft.FontWeight.NORMAL
    preview = contact.preview or "Нет сообщений"

    # ink только на строке — без лишнего отступа снизу (подсветка не уезжает)
    row = ft.Container(
        padding=ft.Padding.symmetric(horizontal=16, vertical=12),
        ink=True,
        on_click=on_click,
        content=ft.Row(
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                _avatar(contact, size=52),
                ft.Column(
                    expand=True,
                    spacing=3,
                    tight=True,
                    controls=[
                        ft.Row(
                            spacing=6,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                ft.Text(
                                    contact.name,
                                    size=16,
                                    weight=ft.FontWeight.W_600,
                                    color=theme.INK,
                                    font_family=theme.FONT_FAMILY,
                                    max_lines=1,
                                ),
                                *_badges_for(contact),
                            ],
                        ),
                        ft.Text(
                            preview,
                            size=14,
                            color=preview_color,
                            weight=preview_weight,
                            font_family=theme.FONT_FAMILY,
                            max_lines=1,
                        ),
                    ],
                ),
                _trailing(contact),
            ],
        ),
    )
    return ft.Column(
        spacing=0,
        tight=True,
        controls=[
            row,
            ft.Row(
                spacing=0,
                controls=[
                    ft.Container(width=80),
                    ft.Container(expand=True, height=1, bgcolor="#E0E0E0"),
                ],
            ),
        ],
    )



def _group_avatar(group: chat_data.Group, size: float = 52) -> ft.Control:
    """Аватар группы: две буквы или число участников."""
    label = str(group.members) if group.members < 100 else "99+"
    colors = gradients.colors_for(group.seed)
    top = "#%02X%02X%02X" % colors["top"]
    bottom = "#%02X%02X%02X" % colors["bottom"]
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
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        content=ft.Text(
            label,
            size=max(11, int(size * 0.26)),
            weight=ft.FontWeight.W_700,
            color="#FFFFFF",
            font_family=theme.FONT_FAMILY,
        ),
    )


def _group_row(group: chat_data.Group, on_click) -> ft.Control:
    preview_color = theme.INK if group.unread else theme.MUTED
    preview_weight = ft.FontWeight.W_600 if group.unread else ft.FontWeight.NORMAL

    row = ft.Container(
        padding=ft.Padding.symmetric(horizontal=16, vertical=12),
        ink=True,
        on_click=on_click,
        content=ft.Row(
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                _group_avatar(group, size=52),
                ft.Column(
                    expand=True,
                    spacing=3,
                    tight=True,
                    controls=[
                        ft.Text(
                            group.name,
                            size=16,
                            weight=ft.FontWeight.W_600,
                            color=theme.INK,
                            font_family=theme.FONT_FAMILY,
                            max_lines=1,
                        ),
                        ft.Text(
                            group.preview or "Нет сообщений",
                            size=14,
                            color=preview_color,
                            weight=preview_weight,
                            font_family=theme.FONT_FAMILY,
                            max_lines=1,
                        ),
                    ],
                ),
                ft.Column(
                    spacing=4,
                    horizontal_alignment=ft.CrossAxisAlignment.END,
                    tight=True,
                    controls=[
                        ft.Text(group.time, size=13, color=theme.MUTED, font_family=theme.FONT_FAMILY) if group.time else ft.Container(),
                        _unread_badge(group.unread) if group.unread > 0 else ft.Container(width=1, height=1),
                        ft.Text(f"{group.members} уч.", size=11, color=theme.MUTED, font_family=theme.FONT_FAMILY),
                    ],
                ),
            ],
        ),
    )
    return ft.Column(
        spacing=0,
        tight=True,
        controls=[
            row,
            ft.Row(
                spacing=0,
                controls=[
                    ft.Container(width=80),
                    ft.Container(expand=True, height=1, bgcolor="#E0E0E0"),
                ],
            ),
        ],
    )



def _search_history_row(contact: chat_data.Contact, on_click) -> ft.Control:
    """Строка истории поиска: аватар, имя, статус «был в сети»."""
    return ft.Container(
        padding=ft.Padding.symmetric(horizontal=16, vertical=10),
        ink=True,
        on_click=on_click,
        content=ft.Row(
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                _avatar(contact, size=48),
                ft.Column(
                    expand=True,
                    spacing=2,
                    tight=True,
                    controls=[
                        ft.Text(
                            contact.name,
                            size=16,
                            weight=ft.FontWeight.W_600,
                            color=theme.INK,
                            font_family=theme.FONT_FAMILY,
                            max_lines=1,
                        ),
                        ft.Text(
                            contact.status or "был(а) в сети",
                            size=13,
                            color=theme.MUTED,
                            font_family=theme.FONT_FAMILY,
                            max_lines=1,
                        ),
                    ],
                ),
            ],
        ),
    )


def _search_view(on_open) -> ft.Control:
    """Экран поиска: поле + история участников."""
    field = ft.TextField(
        hint_text="Поиск",
        border_radius=24,
        filled=True,
        bgcolor="#F0F0F5",
        border_color="transparent",
        focused_border_color=theme.PRIMARY,
        cursor_color=theme.PRIMARY,
        text_size=15,
        color=theme.INK,
        content_padding=ft.Padding.symmetric(horizontal=16, vertical=12),
        text_style=ft.TextStyle(font_family=theme.FONT_FAMILY, size=15, color=theme.INK),
        hint_style=ft.TextStyle(color=theme.HINT, font_family=theme.FONT_FAMILY),
        prefix_icon=ft.Icons.SEARCH if hasattr(ft, "Icons") else None,
        expand=True,
    )
    # история — несколько контактов как «недавние»
    history = chat_data.sorted_contacts()[:6]
    rows = [_search_history_row(c, on_open(c)) for c in history]
    return ft.Column(
        expand=True,
        spacing=0,
        controls=[
            ft.Container(
                padding=ft.Padding.symmetric(horizontal=16, vertical=8),
                content=ft.Row(
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[field],
                ),
            ),
            ft.Container(
                padding=ft.Padding.only(left=16, top=12, bottom=6),
                content=ft.Text(
                    "История поиска",
                    size=13,
                    color=theme.MUTED,
                    font_family=theme.FONT_FAMILY,
                    weight=ft.FontWeight.W_600,
                ),
            ),
            ft.Column(spacing=0, controls=rows),
        ],
    )


def _bottom_nav(active: str, on_tab) -> ft.Control:
    """Плавающая панель как в Figma: soft drop shadows + inner + blur."""
    tabs = [
        ("search", "Поиск"),
        ("chats", "Чаты"),
        ("groups", "Группы"),
        ("settings", "Настройки"),
    ]
    # активный — без жёсткой заливки, только цвет иконки/текста (как на макете)
    TAB_H = 44
    ICON = 28

    def tab(key: str, label: str) -> ft.Control:
        is_on = key == active
        icon_path = _nav_icon(key, is_on)
        if theme._image_exists(icon_path):
            icon = ft.Image(src=icon_path, width=ICON, height=ICON, fit=ft.BoxFit.CONTAIN)
        else:
            icon = ft.Text("•", size=18, color=theme.PRIMARY if is_on else "#1C1C1E")

        label_ctrl = ft.Text(
            label,
            size=12,
            color=theme.PRIMARY if is_on else "#3A3A3C",
            weight=ft.FontWeight.W_600 if is_on else ft.FontWeight.W_500,
            font_family=theme.FONT_FAMILY,
            max_lines=1,
            text_align=ft.TextAlign.CENTER,
        )
        return ft.Container(
            expand=True,
            height=TAB_H,
            ink=False,
            on_click=lambda e, k=key: on_tab(k),
            alignment=ft.Alignment.CENTER,
            animate_opacity=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
            opacity=1,
            content=ft.Column(
                spacing=2,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                tight=True,
                alignment=ft.MainAxisAlignment.CENTER,
                controls=[icon, label_ctrl],
            ),
        )

    # Одна сильная тень — список теней в Flet часто игнорируется
    container = ft.Container(
        bgcolor="#FFFFFF",
        border_radius=40,
        padding=ft.Padding.symmetric(horizontal=10, vertical=4),
        border=ft.Border.all(1, "#D0D0D5"),
        shadow=ft.BoxShadow(
            blur_radius=50,
            spread_radius=4,
            color="#00000066",
            offset=ft.Offset(0, 14),
        ),
        # не обрезать тень
        clip_behavior=ft.ClipBehavior.NONE if hasattr(ft, "ClipBehavior") else None,
        content=ft.Row(
            spacing=0,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[tab(k, lab) for k, lab in tabs],
        ),
    )
    return container


def build_home(page: ft.Page) -> ft.Control:
    # фото для демо-истории Ивана
    photo = theme.asset("assets", "images", "photo_2026-09-30_00-09-10.jpg")
    if theme._image_exists(photo):
        chat_data.attach_demo_photo(photo)

    tab_state = {"active": STATE.draft.get("_home_tab", "chats")}

    def open_chat(contact: chat_data.Contact):
        def _(_e=None):
            # интерактив: открыли чат → сброс розового бейджа
            chat_data.mark_read(contact.id)
            STATE.draft["_open_chat_id"] = contact.id
            STATE.go("/chat")
        return _

    def on_tab(key: str):
        tab_state["active"] = key
        STATE.draft["_home_tab"] = key
        if key in ("settings",):
            labels = {"settings": "Настройки — скоро"}
            try:
                STATE.snack(labels.get(key, ""))
            except Exception:
                pass
        try:
            STATE.go("/home")
        except Exception:
            pass

    def on_fab(_):
        try:
            STATE.snack("Новый чат — скоро")
        except Exception:
            pass

    active = tab_state["active"]
    list_bottom_pad = 100

    if active == "groups":
        groups = chat_data.sorted_groups()
        def open_group(g):
            def _(_e=None):
                try:
                    STATE.snack(f"Группа: {g.name}")
                except Exception:
                    pass
            return _
        rows = [_group_row(g, open_group(g)) for g in groups]
        # учитель создаёт класс и получает код
        def create_class(_=None):
            from core import auth as auth_mod
            try:
                tid = STATE.user.id if STATE.user else 0
                code = auth_mod.create_class_invite(tid, "Новый класс", "")
                STATE.info(f"Код приглашения: {code}\nПередайте его ученикам.", "Класс создан")
            except Exception as exc:
                STATE.error(str(exc))
        rows.insert(0, ft.Container(
            padding=ft.Padding.symmetric(horizontal=16, vertical=8),
            content=ft.TextButton(
                "＋ Создать класс (код для учеников)",
                on_click=create_class,
                style=ft.ButtonStyle(color=theme.PRIMARY),
            ),
        ))
        title_text = "Группы"
        main_list = None
    elif active == "search":
        title_text = "Поиск"
        main_list = _search_view(open_chat)
        rows = []
    else:
        contacts = chat_data.sorted_contacts()
        rows = [_chat_row(c, open_chat(c)) for c in contacts]
        title_text = "Чаты"
        main_list = None

    if main_list is None:
        try:
            chat_list = ft.ListView(
                expand=True,
                spacing=0,
                padding=ft.Padding.only(bottom=list_bottom_pad),
                controls=rows,
                scrollbar_theme=ft.ScrollbarTheme(thickness=0) if hasattr(ft, "ScrollbarTheme") else None,
            )
        except Exception:
            chat_list = ft.Column(
                spacing=0,
                scroll=ft.ScrollMode.AUTO,
                expand=True,
                controls=rows + [ft.Container(height=list_bottom_pad)],
            )
    else:
        chat_list = main_list

    fab_size = 48
    fab = ft.Container(
        width=fab_size,
        height=fab_size,
        border_radius=fab_size / 2,
        bgcolor=theme.PRIMARY,
        alignment=ft.Alignment.CENTER,
        on_click=on_fab,
        clip_behavior=ft.ClipBehavior.NONE if hasattr(ft, "ClipBehavior") else None,
        # такая же тень, как у панели (без цветного свечения)
        shadow=ft.BoxShadow(
            blur_radius=50,
            spread_radius=4,
            color="#00000066",
            offset=ft.Offset(0, 14),
        ),
        content=ft.Container(
            width=fab_size,
            height=fab_size,
            alignment=ft.Alignment.CENTER,
            padding=ft.Padding.only(bottom=2),
            content=ft.Text("+", size=28, color="#FFFFFF", weight=ft.FontWeight.W_600, text_align=ft.TextAlign.CENTER),
        ),
    )

    def go_welcome(_=None):
        STATE.go("/welcome")

    welcome_btn = ft.TextButton(
        "← Welcome",
        on_click=go_welcome,
        style=ft.ButtonStyle(color=theme.MUTED, padding=0),
    )

    header = ft.Container(
        padding=ft.Padding.symmetric(horizontal=16),
        content=ft.Column(
            spacing=0,
            tight=True,
            controls=[
                welcome_btn,
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Text(title_text, size=34, weight=ft.FontWeight.BOLD, color=theme.INK, font_family=theme.FONT_FAMILY),
                        fab,
                    ],
                ),
            ],
        ),
    )

    # Список на весь экран; панель в Stack только по высоте контента
    # (expand-overlay перехватывал клики — так нельзя)
    main_col = ft.Column(
        expand=True,
        spacing=0,
        controls=[
            ft.Container(height=36),
            header,
            ft.Container(height=12),
            chat_list,
        ],
    )

    nav_bar = ft.Container(
        left=8,
        right=8,
        bottom=20,
        # margin даёт место под тень, чтобы Stack её не обрезал
        margin=ft.Margin.all(12) if hasattr(ft, "Margin") else None,
        content=_bottom_nav(tab_state["active"], on_tab),
    )

    return ft.Container(
        bgcolor=theme.BG,
        expand=True,
        width=theme.PHONE_WIDTH,
        content=ft.Stack(
            expand=True,
            clip_behavior=ft.ClipBehavior.NONE if hasattr(ft, "ClipBehavior") else None,
            controls=[main_col, nav_bar],
        ),
    )
