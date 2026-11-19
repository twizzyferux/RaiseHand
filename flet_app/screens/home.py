# -*- coding: utf-8 -*-
"""Экран «Чаты»: список из chat_data, розовые бейджи, превью последнего."""
from __future__ import annotations

from typing import Any

import flet as ft

from core import auth, gradients, logs, prefs
from core import chat as chat_mod
from flet_app import chat_data
from flet_app import liquid_glass
from flet_app import mono_icons
from flet_app import search_history
from flet_app.app_state import STATE
from flet_app import theme


_SETTINGS_LABELS = {
    "profile": "Мой профиль",
    "favorites": "Избранное",
    "appearance": "Оформление",
    "notifications": "Уведомления и звуки",
    "privacy": "Конфиденциальность",
    "blacklist": "Чёрный список",
    "data": "Данные и память",
    "language": "Язык",
    "password": "Пароль",
    "tips": "Возможности",
    "help": "Помощь",
    "faq": "Вопросы",
    "logs": "Логи приложения",
    "logout": "Выйти",
    "avatar": "Изменить фото",
}


def _settings_sprite_path(key: str) -> str:
    """Спрайт из assets/images/settings/{light|dark}/{key}.png."""
    mode = "dark" if prefs.theme_mode() == "dark" else "light"
    path = theme.asset("assets", "images", "settings", mode, f"{key}.png")
    if theme._image_exists(path):
        return path
    # fallback на light
    alt = theme.asset("assets", "images", "settings", "light", f"{key}.png")
    return alt


def _settings_icon(key: str, *, size: float = 36) -> ft.Control:
    path = _settings_sprite_path(key)
    if theme._image_exists(path):
        return ft.Image(
            src=path,
            width=size,
            height=size,
            fit=ft.BoxFit.CONTAIN,
        )
    return ft.Container(
        width=size,
        height=size,
        border_radius=10,
        bgcolor=theme.PRIMARY,
        alignment=ft.Alignment.CENTER,
        content=ft.Icon(ft.Icons.CIRCLE, size=18, color="#FFFFFF"),
    )


def _settings_row(
    *,
    key: str,
    title: str = "",
    on_click=None,
    show_divider: bool = True,
) -> ft.Control:
    label = title or _SETTINGS_LABELS.get(key, key)
    row = ft.Container(
        padding=ft.Padding.symmetric(horizontal=14, vertical=12),
        ink=True,
        on_click=on_click,
        content=ft.Row(
            spacing=14,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                _settings_icon(key, size=36),
                ft.Text(
                    label,
                    size=16,
                    weight=ft.FontWeight.W_500,
                    color=theme.INK,
                    font_family=theme.FONT_FAMILY,
                    expand=True,
                ),
            ],
        ),
    )
    if not show_divider:
        return row
    return ft.Column(
        spacing=0,
        tight=True,
        controls=[
            row,
            ft.Container(
                margin=ft.Margin.only(left=64),
                height=1,
                bgcolor=theme.DIVIDER,
            ),
        ],
    )


def _settings_group(rows: list[ft.Control]) -> ft.Control:
    return liquid_glass.glass_capsule(
        ft.Column(spacing=0, tight=True, controls=rows),
        radius=28,
        blur=liquid_glass.BTN_BLUR,
        tint=liquid_glass.white_glass_tint(),
        border_color=liquid_glass.white_glass_border(),
        padding=ft.Padding.symmetric(vertical=6),
        shadow=True,
        highlight=True,
    )


def _settings_view(page: ft.Page) -> ft.Control:
    """Настройки по макету: профиль + группы пунктов."""
    user = STATE.user
    first = (user.first_name if user else "") or "И"
    last = (user.last_name if user else "") or ""
    name = (user.full_name if user else "") or (user.display_name if user else "Профиль") or "Профиль"
    nick = (user.nickname if user and user.nickname else "") or ""
    handle = f"@{nick}" if nick else ""
    contact = ""
    if user and user.contact_value:
        contact = str(user.contact_value)
    public_id = (user.public_id if user else "—") or "—"
    seed = (user.public_id if user else name).lower()

    colors = gradients.colors_for(seed)
    top = "#%02X%02X%02X" % colors["top"]
    bottom = "#%02X%02X%02X" % colors["bottom"]
    initials = gradients.initials_for(first, last)

    def open_settings_page(key: str):
        def _(_e=None):
            STATE.draft["_home_tab"] = "settings"
            from flet_app.screens.settings_pages import settings_route

            STATE.go(settings_route(key))
        return _

    def open_favorites(_e=None):
        fav = chat_data.ensure_favorites()
        STATE.draft["_home_tab"] = "chats"
        STATE.draft["_open_chat_id"] = fav.id
        STATE.draft["_open_is_group"] = False
        STATE.go("/chat")

    def do_logout(_e=None):
        from core import session

        session.clear()
        STATE.user = None
        STATE.reset_draft()
        logs.event("LOGOUT")
        STATE.go("/welcome")

    avatar_path = (getattr(user, "avatar_path", None) or "").strip() if user else ""
    if avatar_path and theme._image_exists(avatar_path):
        avatar_face: ft.Control = ft.Container(
            width=72,
            height=72,
            border_radius=36,
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
            content=ft.Image(
                src=avatar_path, width=72, height=72, fit=ft.BoxFit.COVER
            ),
        )
    else:
        avatar_face = ft.Container(
            width=72,
            height=72,
            border_radius=36,
            gradient=ft.LinearGradient(
                begin=ft.Alignment(0, -1),
                end=ft.Alignment(0, 1),
                colors=[top, bottom],
            ),
            alignment=ft.Alignment.CENTER,
            content=ft.Text(
                initials,
                size=26,
                weight=ft.FontWeight.W_700,
                color="#FFFFFF",
                font_family=theme.FONT_FAMILY,
            ),
        )

    avatar = ft.Container(
        ink=True,
        on_click=open_settings_page("avatar"),
        content=ft.Stack(
            width=72,
            height=72,
            controls=[
                avatar_face,
                ft.Container(
                    right=0,
                    bottom=0,
                    width=22,
                    height=22,
                    border_radius=11,
                    bgcolor=theme.PRIMARY,
                    border=ft.Border.all(2, theme.BG),
                    alignment=ft.Alignment.CENTER,
                    content=ft.Icon(ft.Icons.ADD, size=14, color="#FFFFFF"),
                ),
            ],
        ),
    )

    name_row = ft.Row(
        spacing=6,
        tight=True,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            ft.Text(
                name,
                size=20,
                weight=ft.FontWeight.W_700,
                color=theme.INK,
                font_family=theme.FONT_FAMILY,
                max_lines=1,
                overflow=ft.TextOverflow.ELLIPSIS,
            ),
            ft.Icon(ft.Icons.CHEVRON_RIGHT, size=20, color=theme.MUTED),
        ],
    )

    meta_lines: list[ft.Control] = [name_row]
    if handle:
        meta_lines.append(
            ft.Text(handle, size=14, color=theme.MUTED, font_family=theme.FONT_FAMILY)
        )
    if contact:
        meta_lines.append(
            ft.Text(contact, size=14, color=theme.MUTED, font_family=theme.FONT_FAMILY)
        )
    meta_lines.append(
        ft.Text(
            f"ID: {public_id}",
            size=14,
            color=theme.MUTED,
            font_family=theme.FONT_FAMILY,
        )
    )

    profile = ft.Container(
        padding=ft.Padding.only(left=16, right=16, top=8, bottom=18),
        content=ft.Row(
            spacing=14,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                avatar,
                ft.Container(
                    expand=True,
                    ink=True,
                    on_click=open_settings_page("profile"),
                    content=ft.Column(
                        spacing=2, tight=True, expand=True, controls=meta_lines
                    ),
                ),
            ],
        ),
    )

    g1 = _settings_group(
        [
            _settings_row(key="profile", on_click=open_settings_page("profile")),
            _settings_row(
                key="favorites",
                on_click=open_favorites,
                show_divider=False,
            ),
        ]
    )
    g2 = _settings_group(
        [
            _settings_row(key="appearance", on_click=open_settings_page("appearance")),
            _settings_row(
                key="notifications", on_click=open_settings_page("notifications")
            ),
            _settings_row(key="privacy", on_click=open_settings_page("privacy")),
            _settings_row(
                key="blacklist",
                on_click=open_settings_page("blacklist"),
                show_divider=False,
            ),
        ]
    )
    g3 = _settings_group(
        [
            _settings_row(key="data", on_click=open_settings_page("data")),
            _settings_row(key="language", on_click=open_settings_page("language")),
            _settings_row(key="password", on_click=open_settings_page("password")),
            _settings_row(key="tips", on_click=open_settings_page("tips")),
            _settings_row(key="help", on_click=open_settings_page("help")),
            _settings_row(key="faq", on_click=open_settings_page("faq")),
            _settings_row(key="logs", on_click=open_settings_page("logs")),
            _settings_row(key="logout", on_click=do_logout, show_divider=False),
        ]
    )

    def _hub_enter(child: ft.Control) -> ft.Container:
        return ft.Container(
            content=child,
            opacity=0,
            offset=ft.Offset(0, 0.02),
            animate_opacity=ft.Animation(260, ft.AnimationCurve.EASE_OUT),
            animate_offset=ft.Animation(280, ft.AnimationCurve.EASE_OUT),
        )

    # один мягкий fade всего хаба — без каскада блоков
    hub_inner = ft.Column(
        spacing=12,
        tight=True,
        controls=[
            profile,
            ft.Container(padding=ft.Padding.symmetric(horizontal=16), content=g1),
            ft.Container(padding=ft.Padding.symmetric(horizontal=16), content=g2),
            ft.Container(padding=ft.Padding.symmetric(horizontal=16), content=g3),
        ],
    )
    hub_wrap = _hub_enter(hub_inner)

    async def _hub_fade():
        import asyncio

        await asyncio.sleep(0.04)
        hub_wrap.opacity = 1
        hub_wrap.offset = ft.Offset(0, 0)
        try:
            hub_wrap.update()
        except Exception:
            pass

    try:
        page.run_task(_hub_fade)
    except Exception:
        hub_wrap.opacity = 1
        hub_wrap.offset = ft.Offset(0, 0)

    return hub_wrap


def _avatar(contact: chat_data.Contact, size: float = 52) -> ft.Control:
    if contact.id == chat_data.FAVORITES_ID:
        return ft.Container(
            width=size,
            height=size,
            border_radius=size / 2,
            bgcolor=theme.PRIMARY,
            alignment=ft.Alignment.CENTER,
            content=ft.Icon(
                ft.Icons.BOOKMARK_ROUNDED,
                size=max(18, int(size * 0.45)),
                color="#FFFFFF",
            ),
        )
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
        bgcolor=theme.BADGE,
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


def _list_ticks(read: bool, size: float = 18) -> ft.Control:
    """Серая = отправлено, фиолетовая = прочитано — mono-спрайты."""
    kind = "read" if read else "sent"
    img = mono_icons.status_image(kind, size=size)
    if img is not None:
        return img
    color = theme.PRIMARY if read else theme.MUTED
    return ft.Icon(
        ft.Icons.DONE_ALL if read else ft.Icons.DONE,
        size=size - 2,
        color=color,
    )


def _trailing(contact: chat_data.Contact) -> ft.Control:
    """Справа: сверху время (+пин/мьют), снизу бейдж или галочки своих сообщений."""
    top: list[ft.Control] = []
    bottom: list[ft.Control] = []

    if getattr(contact, "muted", False):
        top.append(ft.Icon(ft.Icons.VOLUME_OFF_ROUNDED, size=14, color=theme.MUTED))
    if contact.pinned:
        pin = mono_icons.image("pin", size=16, opacity=0.85)
        top.append(pin if pin is not None else ft.Icon(ft.Icons.PUSH_PIN, size=14, color=theme.MUTED))
    if contact.last_time:
        top.append(
            ft.Text(
                contact.last_time,
                size=13,
                color=theme.MUTED,
                font_family=theme.FONT_FAMILY,
            )
        )

    if contact.unread > 0:
        bottom.append(_unread_badge(contact.unread))
    elif contact.last_mine:
        bottom.append(_list_ticks(contact.last_read, size=18))

    controls: list[ft.Control] = []
    if top:
        controls.append(
            ft.Row(
                spacing=4,
                tight=True,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=top,
            )
        )
    if bottom:
        controls.append(
            ft.Row(
                spacing=0,
                tight=True,
                alignment=ft.MainAxisAlignment.END,
                controls=bottom,
            )
        )
    if not controls:
        controls.append(ft.Container(width=1, height=1))

    return ft.Column(
        spacing=4,
        horizontal_alignment=ft.CrossAxisAlignment.END,
        tight=True,
        controls=controls,
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


def _chat_action_row(label: str, on_click, *, danger: bool = False) -> ft.Control:
    return ft.Container(
        ink=True,
        on_click=on_click,
        border_radius=12,
        padding=ft.Padding.symmetric(horizontal=14, vertical=12),
        bgcolor=("#3A1A22" if theme.is_dark() else "#FEE2E8") if danger else theme.FIELD_BG,
        content=ft.Text(
            label,
            size=15,
            weight=ft.FontWeight.W_500,
            color="#E11D48" if danger else theme.INK,
            font_family=theme.FONT_FAMILY,
        ),
    )


def _show_chat_actions(page: ft.Page, contact: chat_data.Contact, on_done) -> None:
    """Меню по зажатию: закрепить, заглушить, прочитано, удалить."""
    is_fav = contact.id == chat_data.FAVORITES_ID

    def _close(_=None):
        try:
            page.pop_dialog()
        except Exception:
            try:
                dlg.open = False
                page.update()
            except Exception:
                pass

    def _run(fn):
        def _(_e=None):
            _close()
            try:
                fn()
            except Exception:
                pass
            if callable(on_done):
                on_done()
        return _

    rows: list[ft.Control] = []
    if not is_fav:
        rows.append(
            _chat_action_row(
                "Открепить" if contact.pinned else "Закрепить",
                _run(lambda: chat_data.toggle_pin(contact.id)),
            )
        )
        rows.append(
            _chat_action_row(
                "Включить звук" if getattr(contact, "muted", False) else "Заглушить",
                _run(lambda: chat_data.toggle_mute(contact.id)),
            )
        )
    rows.append(
        _chat_action_row(
            "Прочитано",
            _run(lambda: chat_data.mark_read(contact.id)),
        )
    )
    if not is_fav:
        rows.append(
            _chat_action_row(
                "Удалить чат",
                _run(lambda: chat_data.delete_chat(contact.id)),
                danger=True,
            )
        )

    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Text(
            contact.display_name,
            color=theme.INK,
            font_family=theme.FONT_FAMILY,
            size=18,
            weight=ft.FontWeight.W_700,
        ),
        bgcolor=theme.CARD,
        content=ft.Column(spacing=8, tight=True, controls=rows),
        actions=[
            ft.TextButton(
                "Отмена",
                on_click=_close,
                style=ft.ButtonStyle(color=theme.MUTED),
            )
        ],
    )

    try:
        page.show_dialog(dlg)
    except Exception:
        try:
            page.overlay.append(dlg)
            dlg.open = True
            page.update()
        except Exception:
            STATE.snack("Не удалось открыть меню")


def _chat_row(contact: chat_data.Contact, on_click, *, on_long=None) -> ft.Control:
    preview_color = theme.INK if contact.unread else theme.MUTED
    preview_weight = ft.FontWeight.W_600 if contact.unread else ft.FontWeight.NORMAL
    preview = contact.preview or "Нет сообщений"

    # ink только на строке — без лишнего отступа снизу (подсветка не уезжает)
    inner = ft.Container(
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
                                    contact.display_name,
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
    if on_long is not None:
        row: ft.Control = ft.GestureDetector(
            content=inner,
            on_long_press_start=lambda e: on_long(contact),
            on_secondary_tap=lambda e: on_long(contact),
        )
    else:
        row = inner
    return ft.Column(
        spacing=0,
        tight=True,
        controls=[
            row,
            ft.Row(
                spacing=0,
                controls=[
                    ft.Container(width=80),
                    ft.Container(expand=True, height=1, bgcolor=theme.DIVIDER),
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
                            group.live_preview or group.preview or "Нет сообщений",
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
                        ft.Text(
                            group.last_time or group.time,
                            size=13,
                            color=theme.MUTED,
                            font_family=theme.FONT_FAMILY,
                        ) if (group.last_time or group.time) else ft.Container(),
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
                    ft.Container(expand=True, height=1, bgcolor=theme.DIVIDER),
                ],
            ),
        ],
    )



def _search_owner_id() -> int:
    return int(STATE.user.id) if STATE.user else 0


def _avatar_from_seed(seed: str, first: str, last: str, size: float = 48) -> ft.Control:
    initials = gradients.initials_for(first, last)
    colors = gradients.colors_for(seed or first or "?")
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


def _search_person_row(
    *,
    title: str,
    subtitle: str,
    seed: str,
    first: str,
    last: str,
    on_click,
    on_remove=None,
) -> ft.Control:
    """Строка результата / истории поиска."""
    trailing: list[ft.Control] = []
    if on_remove is not None:
        trailing.append(
            ft.IconButton(
                icon=ft.Icons.CLOSE,
                icon_size=18,
                icon_color=theme.MUTED,
                tooltip="Убрать",
                on_click=on_remove,
                style=ft.ButtonStyle(padding=4),
            )
        )
    return ft.Container(
        padding=ft.Padding.symmetric(horizontal=16, vertical=8),
        ink=True,
        on_click=on_click,
        content=ft.Row(
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                _avatar_from_seed(seed, first, last, size=48),
                ft.Column(
                    expand=True,
                    spacing=2,
                    tight=True,
                    controls=[
                        ft.Text(
                            title,
                            size=16,
                            weight=ft.FontWeight.W_600,
                            color=theme.INK,
                            font_family=theme.FONT_FAMILY,
                            max_lines=1,
                        ),
                        ft.Text(
                            subtitle,
                            size=13,
                            color=theme.MUTED,
                            font_family=theme.FONT_FAMILY,
                            max_lines=1,
                        ),
                    ],
                ),
                *trailing,
            ],
        ),
    )


def _open_found_account(
    *,
    public_id: str,
    name: str,
    first: str,
    last: str,
    status: str,
    role: str,
    on_open,
) -> None:
    """Запомнить в истории, добавить контакт и открыть чат."""
    from core import blacklist, privacy as priv

    pid = (public_id or "").strip()
    viewer_pid = (STATE.user.public_id if STATE.user else "") or ""
    if viewer_pid and blacklist.is_blocked(viewer_pid, pid):
        STATE.snack("Пользователь в чёрном списке")
        return
    already = chat_data.get_contact(chat_data.contact_id_for_public_id(pid)) is not None
    ok, reason = priv.can_message(
        pid, viewer_public_id=viewer_pid, is_contact=already
    )
    if not ok:
        STATE.snack(reason)
        return

    status_view = priv.status_for_others(pid, status or "в сети")
    owner = _search_owner_id()
    search_history.remember(
        owner,
        public_id=pid,
        name=name,
        first=first,
        last=last,
        status=status_view,
        role=role,
    )
    if STATE.user is not None:
        try:
            chat_mod.add_contact(STATE.user.id, pid)
        except chat_mod.ChatError:
            pass
        except Exception:
            pass
    contact = chat_data.ensure_user_contact(
        public_id=pid,
        name=name,
        first=first,
        last=last,
        status=status_view,
        is_teacher=(role == "teacher"),
        is_admin=(role == "admin"),
    )
    opener = on_open(contact)
    if callable(opener):
        opener()


def _search_view(on_open, on_scroll=None) -> ft.Control:
    """Поиск по ID: live-подсказки + активная история."""
    owner = _search_owner_id()
    gen = {"n": 0}

    section_title = ft.Text(
        "История поиска",
        size=13,
        color=theme.MUTED,
        font_family=theme.FONT_FAMILY,
        weight=ft.FontWeight.W_600,
    )
    clear_btn = ft.TextButton(
        "Очистить",
        style=ft.ButtonStyle(color=theme.PRIMARY, padding=0),
        visible=False,
    )
    results = ft.Column(spacing=0, tight=True, controls=[])
    empty_hint = ft.Container(
        padding=ft.Padding.symmetric(horizontal=16, vertical=20),
        content=ft.Text(
            "Начните вводить ID — аккаунты появятся сразу",
            size=14,
            color=theme.MUTED,
            font_family=theme.FONT_FAMILY,
        ),
    )

    def _render_rows(controls: list[ft.Control], *, title: str, show_clear: bool):
        section_title.value = title
        clear_btn.visible = show_clear
        results.controls = controls
        empty_hint.visible = len(controls) == 0 and title == "История поиска"
        try:
            section_title.update()
            clear_btn.update()
            results.update()
            empty_hint.update()
        except Exception:
            pass

    def _user_subtitle(user: auth.User) -> str:
        bits = [f"ID {user.public_id}"]
        if user.status_text:
            bits.append(user.status_text)
        elif user.is_teacher:
            bits.append("учитель")
        return " · ".join(bits)

    def _pick_user(user: auth.User):
        def _(_e=None):
            from core import privacy as priv

            st = user.status_text or "в сети"
            _open_found_account(
                public_id=user.public_id,
                name=user.display_name,
                first=user.first_name,
                last=user.last_name,
                status=priv.status_for_others(user.public_id, st),
                role=user.role,
                on_open=on_open,
            )
        return _

    def _pick_history(entry: dict[str, Any]):
        def _(_e=None):
            fields = search_history.entry_to_contact_fields(entry)
            pid = fields["public_id"]
            live = auth.find_by_public_id(pid)
            if live is not None:
                _open_found_account(
                    public_id=live.public_id,
                    name=live.display_name,
                    first=live.first_name,
                    last=live.last_name,
                    status=live.status_text or fields["status"] or "в сети",
                    role=live.role,
                    on_open=on_open,
                )
                return
            _open_found_account(
                public_id=pid,
                name=fields["name"],
                first=fields["first"] or fields["name"],
                last=fields["last"],
                status=fields["status"] or "в сети",
                role=fields["role"],
                on_open=on_open,
            )
        return _

    def show_history():
        items = search_history.load(owner)
        rows: list[ft.Control] = []
        for entry in items:
            fields = search_history.entry_to_contact_fields(entry)
            pid = fields["public_id"]

            def _remove(_e=None, public_id=pid):
                search_history.forget(owner, public_id)
                show_history()

            rows.append(
                _search_person_row(
                    title=fields["name"],
                    subtitle=f"ID {pid}"
                    + (f" · {fields['status']}" if fields["status"] else ""),
                    seed=pid.lower(),
                    first=fields["first"] or fields["name"],
                    last=fields["last"],
                    on_click=_pick_history(entry),
                    on_remove=_remove,
                )
            )
        _render_rows(rows, title="История поиска", show_clear=bool(rows))
        if not rows:
            empty_hint.visible = True
            try:
                empty_hint.update()
            except Exception:
                pass

    def run_live_search(query: str):
        gen["n"] += 1
        token = gen["n"]
        q = (query or "").strip()
        if not q:
            show_history()
            return
        exclude = STATE.user.id if STATE.user else None
        try:
            hits = auth.search_users(q, exclude_user_id=exclude, limit=12)
        except Exception:
            hits = []
        if token != gen["n"]:
            return
        from core import blacklist, privacy as priv

        me = (STATE.user.public_id if STATE.user else "") or ""
        filtered = []
        for u in hits:
            if me and blacklist.is_blocked(me, u.public_id):
                continue
            if not priv.visible_in_search(u.public_id):
                continue
            filtered.append(u)
            if len(filtered) >= 8:
                break
        hits = filtered
        rows = [
            _search_person_row(
                title=u.display_name,
                subtitle=_user_subtitle(u),
                seed=u.public_id.lower(),
                first=("?" if priv.for_user(u.public_id).get("hide_avatar") else u.first_name),
                last=("" if priv.for_user(u.public_id).get("hide_avatar") else u.last_name),
                on_click=_pick_user(u),
            )
            for u in hits
        ]
        if not rows:
            rows = [
                ft.Container(
                    padding=ft.Padding.symmetric(horizontal=16, vertical=18),
                    content=ft.Text(
                        "Никого не найдено",
                        size=14,
                        color=theme.MUTED,
                        font_family=theme.FONT_FAMILY,
                    ),
                )
            ]
        empty_hint.visible = False
        try:
            empty_hint.update()
        except Exception:
            pass
        _render_rows(rows, title="Аккаунты", show_clear=False)

    def on_change(_e=None):
        run_live_search(field.value or "")

    def on_submit(_e=None):
        # Enter — открыть точное совпадение или первый live-результат
        q = (field.value or "").strip()
        if not q:
            return
        exclude = STATE.user.id if STATE.user else None
        exact = auth.find_by_public_id(q)
        if exact is not None and (exclude is None or exact.id != exclude):
            _pick_user(exact)()
            return
        hits = auth.search_users(q, exclude_user_id=exclude, limit=1)
        if hits:
            _pick_user(hits[0])()

    def on_clear(_e=None):
        search_history.clear(owner)
        field.value = ""
        try:
            field.update()
        except Exception:
            pass
        show_history()

    clear_btn.on_click = on_clear

    field = ft.TextField(
        hint_text="ID, ник или имя",
        filled=True,
        bgcolor=theme.FIELD_BG,
        border=theme.field_border(24, color="transparent", focused_color=theme.PRIMARY),
        cursor_color=theme.PRIMARY,
        text_size=15,
        color=theme.INK,
        content_padding=ft.Padding.symmetric(horizontal=16, vertical=12),
        text_style=ft.TextStyle(font_family=theme.FONT_FAMILY, size=15, color=theme.INK),
        hint_style=ft.TextStyle(color=theme.HINT, font_family=theme.FONT_FAMILY),
        prefix_icon=ft.Icons.SEARCH if hasattr(ft, "Icons") else None,
        expand=True,
        on_change=on_change,
        on_submit=on_submit,
        autofocus=False,
    )

    # первичная отрисовка истории (без update — ещё не на странице)
    hist_items = search_history.load(owner)
    hist_rows: list[ft.Control] = []
    for entry in hist_items:
        fields = search_history.entry_to_contact_fields(entry)
        pid = fields["public_id"]

        def _remove_init(_e=None, public_id=pid):
            search_history.forget(owner, public_id)
            show_history()

        hist_rows.append(
            _search_person_row(
                title=fields["name"],
                subtitle=f"ID {pid}"
                + (f" · {fields['status']}" if fields["status"] else ""),
                seed=pid.lower(),
                first=fields["first"] or fields["name"],
                last=fields["last"],
                on_click=_pick_history(entry),
                on_remove=_remove_init,
            )
        )
    results.controls = hist_rows
    clear_btn.visible = bool(hist_rows)
    empty_hint.visible = not hist_rows
    section_title.value = "История поиска"

    return ft.Column(
        expand=True,
        spacing=0,
        scroll=ft.ScrollMode.AUTO,
        on_scroll=on_scroll,
        scroll_interval=24,
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
                padding=ft.Padding.only(left=16, right=8, top=8, bottom=4),
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[section_title, clear_btn],
                ),
            ),
            results,
            empty_hint,
            ft.Container(height=118),
        ],
    )


def _nav_icon_control(key: str, active: bool) -> ft.Control:
    return mono_icons.nav_icon(key, active, size=liquid_glass.ICON)


def _home_tab_body(
    active: str,
    *,
    open_chat,
    on_fab,
    page: ft.Page | None = None,
    on_chat_long=None,
    on_chats_changed=None,
) -> ft.Control:
    """Контент вкладки home без нижней панели (панель живёт отдельно)."""
    list_bottom_pad = 118
    fab_size = 48.0
    # место под welcome + «Чаты» + fab; список стартует ниже и «наезжает» на заголовок
    header_h = 100.0

    fab = liquid_glass.purple_glass_fab(on_fab, size=fab_size, icon="+")

    welcome_btn = ft.TextButton(
        "← Welcome",
        on_click=lambda _: STATE.go("/welcome"),
        style=ft.ButtonStyle(color=theme.MUTED, padding=0),
    )

    title_label = ft.Text(
        "",
        size=34,
        weight=ft.FontWeight.BOLD,
        color=theme.INK,
        font_family=theme.FONT_FAMILY,
    )

    header_layer = ft.Container(
        height=header_h,
        padding=ft.Padding.only(left=16, right=16, top=0, bottom=12),
        bgcolor=theme.BG,
        offset=ft.Offset(0, 0),
        animate_offset=None,
        content=ft.Column(
            spacing=0,
            tight=True,
            controls=[
                welcome_btn,
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        title_label,
                        fab if active != "settings" else ft.Container(width=fab_size),
                    ],
                ),
            ],
        ),
    )

    scroll_ui = {
        "last": 0.0,
        "dy": 0.0,
        "revealed": False,  # sticky-показ после полного перекрытия
        "mode": "track",  # track | hidden | sticky
    }

    def _apply_header_offset(frac: float, *, animate: bool):
        frac = max(0.0, min(1.0, float(frac)))
        header_layer.animate_offset = (
            ft.Animation(130, ft.AnimationCurve.EASE_OUT_CUBIC) if animate else None
        )
        header_layer.offset = ft.Offset(0, -frac)
        try:
            header_layer.update()
        except Exception:
            pass

    def on_scroll(e=None):
        try:
            pixels = float(getattr(e, "pixels", 0) or 0)
        except Exception:
            return
        delta = getattr(e, "scroll_delta", None)
        if delta is not None:
            try:
                delta_f = float(delta)
            except Exception:
                delta_f = pixels - scroll_ui["last"]
        else:
            delta_f = pixels - scroll_ui["last"]
        scroll_ui["last"] = pixels

        # Пока заголовок ещё не полностью перекрыт — едет 1:1 со скроллом
        if pixels < header_h:
            scroll_ui["revealed"] = False
            scroll_ui["dy"] = 0.0
            scroll_ui["mode"] = "track"
            _apply_header_offset(pixels / header_h, animate=False)
            return

        # Полностью перекрыт скроллом
        if scroll_ui["mode"] == "track":
            scroll_ui["mode"] = "hidden"
            _apply_header_offset(1.0, animate=False)

        if abs(delta_f) < 0.5:
            return
        scroll_ui["dy"] += delta_f

        # Небольшой скролл вверх — вернуть заголовок поверх списка
        if scroll_ui["dy"] < -4:
            scroll_ui["dy"] = 0.0
            if not scroll_ui["revealed"]:
                scroll_ui["revealed"] = True
                scroll_ui["mode"] = "sticky"
                _apply_header_offset(0.0, animate=True)
            return

        # Снова вниз — убрать sticky
        if scroll_ui["dy"] > 8 and scroll_ui["revealed"]:
            scroll_ui["dy"] = 0.0
            scroll_ui["revealed"] = False
            scroll_ui["mode"] = "hidden"
            _apply_header_offset(1.0, animate=True)

    if active == "groups":
        groups = chat_data.sorted_groups()

        def open_group(g: chat_data.Group):
            def _(_e=None):
                chat_data.mark_group_read(g.id)
                STATE.draft["_open_chat_id"] = g.id
                STATE.draft["_open_is_group"] = True
                STATE.go("/chat")
            return _

        rows = [_group_row(g, open_group(g)) for g in groups]

        def create_class(_=None):
            from core import auth as auth_mod
            try:
                tid = STATE.user.id if STATE.user else 0
                code = auth_mod.create_class_invite(tid, "Новый класс", "")
                STATE.info(f"Код приглашения: {code}\nПередайте его ученикам.", "Класс создан")
            except Exception as exc:
                STATE.error(str(exc))

        rows.insert(
            0,
            ft.Container(
                padding=ft.Padding.symmetric(horizontal=16, vertical=8),
                content=ft.TextButton(
                    "＋ Создать класс (код для учеников)",
                    on_click=create_class,
                    style=ft.ButtonStyle(color=theme.PRIMARY),
                ),
            ),
        )
        title_label.value = "Группы"
        main_list = None
    elif active == "search":
        title_label.value = "Поиск"
        main_list = _search_view(open_chat, on_scroll=on_scroll)
        rows = []
    elif active == "settings":
        # в макете нет крупного «Настройки» — сразу профиль
        title_label.value = ""
        header_layer.visible = False
        settings_body = _settings_view(page) if page is not None else ft.Text("Настройки")
        main_list = ft.Column(
            expand=True,
            spacing=0,
            scroll=ft.ScrollMode.AUTO,
            on_scroll=on_scroll,
            scroll_interval=24,
            controls=[
                settings_body,
                ft.Container(height=list_bottom_pad),
            ],
        )
        rows = []
    else:
        from core import blacklist

        me = (STATE.user.public_id if STATE.user else "") or ""
        contacts = []
        for c in chat_data.sorted_contacts_for_ui():
            pid = blacklist.public_id_from_contact_id(c.id)
            if me and pid and blacklist.is_blocked(me, pid):
                continue
            contacts.append(c)
        def _long(c: chat_data.Contact):
            if page is None:
                return
            if on_chat_long is not None:
                on_chat_long(c)
            else:
                _show_chat_actions(page, c, on_chats_changed)

        rows = [
            _chat_row(c, open_chat(c), on_long=_long if page is not None else None)
            for c in contacts
        ]
        title_label.value = "Чаты"
        main_list = None

    top_pad = 8.0 if active == "settings" else header_h
    if main_list is None:
        try:
            chat_list = ft.ListView(
                expand=True,
                spacing=0,
                padding=ft.Padding.only(top=top_pad, bottom=list_bottom_pad),
                controls=rows,
                on_scroll=on_scroll,
                scroll_interval=24,
                scrollbar_theme=ft.ScrollbarTheme(thickness=0)
                if hasattr(ft, "ScrollbarTheme")
                else None,
            )
        except Exception:
            chat_list = ft.Column(
                spacing=0,
                scroll=ft.ScrollMode.AUTO,
                expand=True,
                on_scroll=on_scroll,
                scroll_interval=24,
                controls=[ft.Container(height=top_pad)]
                + rows
                + [ft.Container(height=list_bottom_pad)],
            )
    else:
        # поиск: сверху запас под оверлей-заголовок
        chat_list = ft.Container(
            expand=True,
            padding=ft.Padding.only(top=top_pad),
            content=main_list,
        )

    return ft.Column(
        expand=True,
        spacing=0,
        controls=[
            # SafeArea в main уже учитывает Dynamic Island
            ft.Stack(
                expand=True,
                controls=[
                    chat_list,
                    ft.Container(
                        content=header_layer,
                        top=0,
                        left=0,
                        right=0,
                    ),
                ],
            ),
        ],
    )


def build_home(page: ft.Page) -> ft.Control:
    # фото для демо-истории Ивана
    photo = theme.asset("assets", "images", "photo_2026-09-30_00-09-10.jpg")
    if theme._image_exists(photo):
        chat_data.attach_demo_photo(photo)

    tab_state = {"active": STATE.draft.get("_home_tab", "chats"), "busy": False}

    def open_chat(contact: chat_data.Contact):
        def _(_e=None):
            from core import blacklist

            me = (STATE.user.public_id if STATE.user else "") or ""
            pid = blacklist.public_id_from_contact_id(contact.id)
            if me and pid and blacklist.is_blocked(me, pid):
                STATE.snack("Пользователь в чёрном списке")
                return
            chat_data.mark_read(contact.id)
            STATE.draft["_open_chat_id"] = contact.id
            STATE.draft["_open_is_group"] = False
            STATE.go("/chat")
        return _

    def on_fab(_):
        try:
            STATE.snack("Новый чат — скоро")
        except Exception:
            pass

    def refresh_chats():
        if tab_state.get("active") != "chats":
            return
        body_host.content = _home_tab_body(
            "chats",
            open_chat=open_chat,
            on_fab=on_fab,
            page=page,
            on_chat_long=on_chat_long,
            on_chats_changed=refresh_chats,
        )
        try:
            body_host.update()
        except Exception:
            pass

    def on_chat_long(contact: chat_data.Contact):
        _show_chat_actions(page, contact, refresh_chats)

    # Контент анимируется сам; панель снаружи Stack и не участвует в fade
    body_host = ft.Container(
        expand=True,
        opacity=1,
        animate_opacity=ft.Animation(
            liquid_glass.TAB_FADE_MS, ft.AnimationCurve.EASE_OUT
        ),
        content=_home_tab_body(
            tab_state["active"],
            open_chat=open_chat,
            on_fab=on_fab,
            page=page,
            on_chat_long=on_chat_long,
            on_chats_changed=refresh_chats,
        ),
    )

    # ширина панели от реального viewport (на iPhone не 390)
    NAV_INSET = 24
    bar_width = max(260.0, float(theme.PHONE_WIDTH) - NAV_INSET * 2)

    nav_holder: dict = {"nav": None}

    def on_tab(key: str):
        if key == tab_state["active"] or tab_state["busy"]:
            return
        tab_state["active"] = key
        STATE.draft["_home_tab"] = key
        nav = nav_holder["nav"]
        if nav is not None:
            nav.set_active(key)

        async def _swap():
            import asyncio

            tab_state["busy"] = True
            try:
                body_host.animate_opacity = ft.Animation(
                    liquid_glass.TAB_FADE_MS, ft.AnimationCurve.EASE_OUT
                )
                body_host.opacity = 0
                body_host.update()
                await asyncio.sleep(liquid_glass.TAB_FADE_MS / 1000 * 0.5)
                body_host.content = _home_tab_body(
                    key,
                    open_chat=open_chat,
                    on_fab=on_fab,
                    page=page,
                    on_chat_long=on_chat_long,
                    on_chats_changed=refresh_chats,
                )
                body_host.opacity = 1
                body_host.update()
            finally:
                tab_state["busy"] = False

        try:
            page.run_task(_swap)
        except Exception:
            body_host.content = _home_tab_body(
                key,
                open_chat=open_chat,
                on_fab=on_fab,
                page=page,
                on_chat_long=on_chat_long,
                on_chats_changed=refresh_chats,
            )
            body_host.opacity = 1
            try:
                body_host.update()
            except Exception:
                pass

    nav_ctrl, nav = liquid_glass.liquid_nav_bar(
        [
            ("search", "Поиск"),
            ("chats", "Чаты"),
            ("groups", "Группы"),
            ("settings", "Настройки"),
        ],
        active=tab_state["active"],
        on_tab=on_tab,
        icon_builder=_nav_icon_control,
        bar_width=bar_width,
    )
    nav_holder["nav"] = nav

    # Панель по центру снизу; SafeArea уже учёл home indicator
    nav_bar = ft.Container(
        left=0,
        right=0,
        bottom=float(theme.NAV_BOTTOM_GAP),
        alignment=ft.Alignment.CENTER,
        content=nav_ctrl,
    )

    return ft.Container(
        bgcolor=theme.BG,
        expand=True,
        content=ft.Stack(
            expand=True,
            clip_behavior=ft.ClipBehavior.NONE if hasattr(ft, "ClipBehavior") else None,
            controls=[body_host, nav_bar],
        ),
    )
