# -*- coding: utf-8 -*-
"""Отдельные экраны пунктов настроек — сюда добавляем функции."""
from __future__ import annotations

import os
from typing import Callable

import flet as ft

from core import auth, branding, gradients, logs, prefs
from flet_app import chat_data, liquid_glass, mono_icons, theme
from flet_app.app_state import STATE

# ключ → заголовок экрана
SETTINGS_PAGES: dict[str, str] = {
    "profile": "Мой профиль",
    "avatar": "Аватар",
    "favorites": "Избранное",
    "appearance": "Оформление",
    "bubbles": "Пузыри сообщений",
    "app_icon": "Иконка приложения",
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
}

# вложенные экраны → родитель (назад на один уровень, не сразу в хаб)
SETTINGS_PARENT: dict[str, str] = {
    "bubbles": "appearance",
    "app_icon": "appearance",
}


def settings_route(key: str) -> str:
    return f"/settings/{key}"


def _back_to_settings(_=None):
    STATE.draft["_home_tab"] = "settings"
    STATE.go("/home")


def _back_from(key: str):
    """Назад: во вложенных — к родителю, иначе в список настроек."""

    def _(_e=None):
        parent = SETTINGS_PARENT.get(key)
        STATE.draft["_home_tab"] = "settings"
        if parent:
            STATE.go(settings_route(parent))
        else:
            STATE.go("/home")

    return _


def _sprite(key: str) -> str:
    mode = "dark" if prefs.theme_mode() == "dark" else "light"
    path = theme.asset("assets", "images", "settings", mode, f"{key}.png")
    if theme._image_exists(path):
        return path
    return theme.asset("assets", "images", "settings", "light", f"{key}.png")


def _header(title: str, *, on_back=None) -> ft.Control:
    back = liquid_glass.glass_circle_button(
        on_back or _back_to_settings,
        content=mono_icons.ui_icon("back", size=22),
        size=44,
        variant="white",
    )
    return ft.Container(
        padding=ft.Padding.symmetric(horizontal=12, vertical=8),
        content=ft.Row(
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                back,
                ft.Text(
                    title,
                    size=20,
                    weight=ft.FontWeight.W_700,
                    color=theme.INK,
                    font_family=theme.FONT_FAMILY,
                    expand=True,
                    max_lines=1,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
            ],
        ),
    )


def _enter(child: ft.Control, *, visible: bool = False) -> ft.Container:
    """Мягкий fade + едва заметный подъём. Без scale."""
    return ft.Container(
        alignment=ft.Alignment.CENTER_LEFT,
        content=child,
        opacity=1 if visible else 0,
        offset=ft.Offset(0, 0) if visible else ft.Offset(0, 0.02),
        animate_opacity=ft.Animation(260, ft.AnimationCurve.EASE_OUT),
        animate_offset=ft.Animation(280, ft.AnimationCurve.EASE_OUT),
    )


def _shell(page: ft.Page, key: str, body: ft.Control) -> ft.Control:
    """Полная ширина + скролл у края; контент с padding внутри."""
    # тихий refresh (смена цвета/темы) — без повторного «шоу»
    quiet = bool(STATE.draft.pop("_settings_no_anim", False))

    title = SETTINGS_PAGES.get(key, key)
    header = _header(title, on_back=_back_from(key))
    header_wrap = ft.Container(
        content=header,
        opacity=1 if quiet else 0,
        animate_opacity=ft.Animation(220, ft.AnimationCurve.EASE_OUT),
    )

    # один общий fade контента вместо каскада карточек
    if isinstance(body, ft.Column) and body.controls:
        scroll_inner: ft.Control = ft.Column(
            spacing=12,
            tight=True,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=list(body.controls),
        )
    else:
        scroll_inner = body
    body_wrap = _enter(scroll_inner, visible=quiet)

    # ListView на всю ширину — скроллбар у правого края окна, не поверх карточек с padding
    scroller = ft.ListView(
        expand=True,
        spacing=0,
        padding=ft.Padding.only(left=16, right=16, top=8, bottom=28),
        controls=[body_wrap],
    )

    root = ft.Container(
        expand=True,
        bgcolor=theme.BG,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        content=ft.Column(
            expand=True,
            spacing=0,
            controls=[
                # SafeArea в main уже отодвигает от Dynamic Island
                header_wrap,
                scroller,
            ],
        ),
    )

    if quiet:
        return root

    async def _fade_in():
        import asyncio

        await asyncio.sleep(0.03)
        header_wrap.opacity = 1
        body_wrap.opacity = 1
        body_wrap.offset = ft.Offset(0, 0)
        try:
            header_wrap.update()
            body_wrap.update()
        except Exception:
            pass

    try:
        page.run_task(_fade_in)
    except Exception:
        header_wrap.opacity = 1
        body_wrap.opacity = 1
        body_wrap.offset = ft.Offset(0, 0)

    return root


def _placeholder(key: str, hint: str = "") -> ft.Control:
    icon_path = _sprite(key)
    controls: list[ft.Control] = []
    if theme._image_exists(icon_path):
        controls.append(
            ft.Image(src=icon_path, width=56, height=56, fit=ft.BoxFit.CONTAIN)
        )
    controls.extend(
        [
            ft.Text(
                SETTINGS_PAGES.get(key, key),
                size=18,
                weight=ft.FontWeight.W_600,
                color=theme.INK,
                font_family=theme.FONT_FAMILY,
            ),
            ft.Text(
                hint or "Здесь появятся настройки этого раздела.",
                size=14,
                color=theme.MUTED,
                font_family=theme.FONT_FAMILY,
            ),
        ]
    )
    return ft.Column(spacing=12, tight=True, controls=controls)


def _card(content: ft.Control, *, padding: ft.Padding | None = None) -> ft.Control:
    # ширина = ListView (PHONE_WIDTH − padding 16+16), иначе короткие карточки «пилюлей»
    card_w = float(theme.PHONE_WIDTH - 32)
    return ft.Container(
        alignment=ft.Alignment.CENTER,
        width=card_w,
        content=liquid_glass.glass_capsule(
            content,
            radius=22,
            blur=liquid_glass.BTN_BLUR,
            tint=liquid_glass.white_glass_tint(),
            border_color=liquid_glass.white_glass_border(),
            padding=padding or ft.Padding.all(16),
            shadow=True,
            highlight=True,
            width=card_w,
        ),
    )


def _switch_row(label: str, sw: ft.Switch, *, hint: str = "") -> ft.Control:
    left: list[ft.Control] = [
        ft.Text(label, size=16, color=theme.INK, font_family=theme.FONT_FAMILY),
    ]
    if hint:
        left.append(
            ft.Text(
                hint,
                size=12,
                color=theme.MUTED,
                font_family=theme.FONT_FAMILY,
            )
        )
    return ft.Row(
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            ft.Column(spacing=2, tight=True, expand=True, controls=left),
            sw,
        ],
    )


def _divider() -> ft.Control:
    return ft.Container(height=1, bgcolor=theme.DIVIDER)


# --- экраны с уже рабочей логикой ---

def _field(
    label: str,
    value: str = "",
    *,
    hint: str = "",
    multiline: bool = False,
    password: bool = False,
) -> ft.TextField:
    return ft.TextField(
        label=label,
        value=value or "",
        hint_text=hint or None,
        password=password,
        multiline=multiline,
        min_lines=3 if multiline else 1,
        max_lines=5 if multiline else 1,
        filled=True,
        bgcolor=theme.FIELD_BG,
        color=theme.INK,
        border=theme.field_border(16, color=theme.STROKE, focused_color=theme.PRIMARY),
        cursor_color=theme.PRIMARY,
        text_style=ft.TextStyle(font_family=theme.FONT_FAMILY, color=theme.INK),
        hint_style=ft.TextStyle(color=theme.HINT, font_family=theme.FONT_FAMILY),
        label_style=ft.TextStyle(color=theme.MUTED, font_family=theme.FONT_FAMILY),
    )


def _section_label(text: str) -> ft.Control:
    return ft.Text(
        text,
        size=13,
        weight=ft.FontWeight.W_600,
        color=theme.MUTED,
        font_family=theme.FONT_FAMILY,
    )


def _profile_avatar(user: auth.User, size: float = 96) -> ft.Control:
    path = (getattr(user, "avatar_path", None) or "").strip()
    if path and theme._image_exists(path):
        return ft.Container(
            width=size,
            height=size,
            border_radius=size / 2,
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
            content=ft.Image(src=path, width=size, height=size, fit=ft.BoxFit.COVER),
        )
    seed = (user.public_id or user.display_name or "me").lower()
    colors = gradients.colors_for(seed)
    top = "#%02X%02X%02X" % colors["top"]
    bottom = "#%02X%02X%02X" % colors["bottom"]
    initials = gradients.initials_for(user.first_name or "?", user.last_name or "")
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


def _show_dlg(page: ft.Page, dlg: ft.AlertDialog) -> None:
    """Flet 1.x: show_dialog / overlay — page.open часто нет."""
    try:
        page.show_dialog(dlg)
        return
    except Exception:
        pass
    try:
        page.overlay.append(dlg)
        dlg.open = True
        page.update()
    except Exception as exc:
        logs.error("show dialog: %s", exc)
        STATE.error("Не удалось открыть форму", "Профиль")


def _close_dlg(page: ft.Page, dlg: ft.AlertDialog | None = None) -> None:
    try:
        page.pop_dialog()
        return
    except Exception:
        pass
    try:
        if dlg is not None:
            dlg.open = False
        page.update()
    except Exception:
        pass


def _edit_dialog(
    page: ft.Page,
    *,
    title: str,
    fields: list[ft.TextField],
    on_save,
):
    def close(_=None):
        _close_dlg(page, dlg)

    def save(_=None):
        try:
            on_save()
            close()
        except auth.AuthError as exc:
            STATE.error(str(exc), title)
        except Exception as exc:
            logs.error("profile field save: %s", exc)
            STATE.error(str(exc), title)

    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Text(title, color=theme.INK, font_family=theme.FONT_FAMILY),
        bgcolor=theme.CARD,
        content=ft.Column(tight=True, spacing=10, controls=fields),
        actions=[
            ft.TextButton(
                "Отмена",
                on_click=close,
                style=ft.ButtonStyle(color=theme.MUTED),
            ),
            ft.TextButton(
                "Сохранить",
                on_click=save,
                style=ft.ButtonStyle(color=theme.PRIMARY),
            ),
        ],
    )
    _show_dlg(page, dlg)


def _settings_row_item(
    *,
    title: str,
    value: str,
    on_click,
) -> ft.Control:
    return ft.Container(
        ink=True,
        on_click=on_click,
        padding=ft.Padding.symmetric(vertical=14, horizontal=4),
        border_radius=12,
        content=ft.Row(
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Column(
                    spacing=2,
                    tight=True,
                    expand=True,
                    controls=[
                        ft.Text(
                            title,
                            size=13,
                            color=theme.MUTED,
                            font_family=theme.FONT_FAMILY,
                        ),
                        ft.Text(
                            value or "не указано",
                            size=15,
                            weight=ft.FontWeight.W_500,
                            color=theme.INK,
                            font_family=theme.FONT_FAMILY,
                            max_lines=2,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                    ],
                ),
                ft.Icon(ft.Icons.CHEVRON_RIGHT, color=theme.MUTED, size=20),
            ],
        ),
    )


def _page_profile(page: ft.Page) -> ft.Control:
    """Свой профиль — тот же вид, что у чужого: карточка + строки настроек."""
    user = STATE.user
    if user is None:
        return _placeholder("profile", "Войдите, чтобы видеть профиль.")

    name_text = ft.Text(
        user.full_name or "Без имени",
        size=22,
        weight=ft.FontWeight.W_700,
        color=theme.INK,
        font_family=theme.FONT_FAMILY,
        max_lines=2,
        overflow=ft.TextOverflow.ELLIPSIS,
    )
    nick_line = ft.Text(
        f"@{user.nickname}" if user.nickname else "без ника",
        size=13,
        color=theme.MUTED,
        font_family=theme.FONT_FAMILY,
    )
    bio_body = ft.Text(
        (user.status_text or "").strip() or "Добавьте описание профиля",
        size=15,
        color=theme.INK,
        font_family=theme.FONT_FAMILY,
    )

    def reload():
        STATE.draft["_settings_no_anim"] = True
        STATE.go(settings_route("profile"))

    def apply_user(updated: auth.User):
        STATE.user = updated
        STATE.snack("Профиль обновлён")
        reload()

    def edit_name(_e=None):
        u = STATE.user
        if u is None:
            return
        first_tf = _field("Имя", u.first_name or "")
        last_tf = _field("Фамилия", u.last_name or "")

        def _save():
            apply_user(
                auth.update_profile(
                    u.id,
                    first_name=(first_tf.value or "").strip(),
                    last_name=(last_tf.value or "").strip(),
                )
            )

        _edit_dialog(page, title="Имя", fields=[first_tf, last_tf], on_save=_save)

    def edit_nick(_e=None):
        u = STATE.user
        if u is None:
            return
        nick_tf = _field(
            "Ник",
            u.nickname or "",
            hint="только латиница: name_01",
        )

        def _save():
            raw = (nick_tf.value or "").strip().lstrip("@")
            apply_user(auth.update_profile(u.id, nickname=raw))

        _edit_dialog(page, title="Никнейм", fields=[nick_tf], on_save=_save)

    def edit_phone(_e=None):
        u = STATE.user
        if u is None:
            return
        phone_tf = _field("Телефон или email", u.contact_value or "", hint="+7… или email")

        def _save():
            apply_user(
                auth.update_profile(
                    u.id, contact_value=(phone_tf.value or "").strip()
                )
            )

        _edit_dialog(page, title="Контакт", fields=[phone_tf], on_save=_save)

    def edit_bio(_e=None):
        u = STATE.user
        if u is None:
            return
        bio_tf = _field(
            "О себе",
            u.status_text or "",
            hint="Короткое описание",
            multiline=True,
        )

        def _save():
            apply_user(
                auth.update_profile(u.id, status_text=(bio_tf.value or "").strip())
            )

        _edit_dialog(page, title="Описание", fields=[bio_tf], on_save=_save)

    name_row = ft.Container(
        ink=True,
        on_click=edit_name,
        padding=ft.Padding.symmetric(horizontal=8, vertical=4),
        border_radius=10,
        content=ft.Row(
            spacing=8,
            tight=True,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                name_text,
                mono_icons.ui_icon("edit", size=18),
            ],
        ),
    )

    nick_tap = ft.Container(
        ink=True,
        on_click=edit_nick,
        padding=ft.Padding.symmetric(horizontal=8, vertical=2),
        border_radius=8,
        content=nick_line,
    )

    bio_block = ft.Container(
        ink=True,
        on_click=edit_bio,
        padding=ft.Padding.symmetric(vertical=4),
        border_radius=10,
        content=ft.Column(
            spacing=4,
            tight=True,
            horizontal_alignment=ft.CrossAxisAlignment.START,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        _section_label("О себе"),
                        mono_icons.ui_icon("edit", size=18),
                    ],
                ),
                bio_body,
            ],
        ),
    )

    head = _card(
        ft.Column(
            spacing=12,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            tight=True,
            controls=[
                _profile_avatar(user, 96),
                name_row,
                nick_tap,
                ft.Text(
                    f"ID: {user.public_id}",
                    size=13,
                    color=theme.MUTED,
                    font_family=theme.FONT_FAMILY,
                    selectable=True,
                ),
                ft.Container(padding=ft.Padding.only(top=4), content=bio_block),
            ],
        ),
        padding=ft.Padding.symmetric(horizontal=20, vertical=20),
    )

    details = _card(
        ft.Column(
            spacing=0,
            tight=True,
            controls=[
                _section_label("Данные профиля"),
                _settings_row_item(
                    title="Имя",
                    value=user.full_name or "",
                    on_click=edit_name,
                ),
                ft.Container(height=1, bgcolor=theme.DIVIDER),
                _settings_row_item(
                    title="Никнейм",
                    value=f"@{user.nickname}" if user.nickname else "",
                    on_click=edit_nick,
                ),
                ft.Container(height=1, bgcolor=theme.DIVIDER),
                _settings_row_item(
                    title="Телефон / email",
                    value=user.contact_value or "",
                    on_click=edit_phone,
                ),
                ft.Container(height=1, bgcolor=theme.DIVIDER),
                _settings_row_item(
                    title="Описание",
                    value=(user.status_text or "").strip(),
                    on_click=edit_bio,
                ),
            ],
        )
    )

    return ft.Column(
        spacing=12,
        tight=True,
        controls=[head, details, ft.Container(height=8)],
    )


def _color_chip(key: str, selected: bool, on_tap, *, size: float = 44.0) -> ft.Control:
    tok = branding.theme_tokens(key, "dark" if theme.is_dark() else "light")
    fill = tok.get("fill") or theme.PRIMARY
    ring = theme.BG if selected else "transparent"
    return ft.Container(
        width=size,
        height=size,
        border_radius=size / 2,
        bgcolor=fill,
        border=ft.Border.all(3, ring),
        shadow=ft.BoxShadow(
            blur_radius=12 if selected else 6,
            color=theme.PRIMARY_SOFT if selected else "#00000022",
            offset=ft.Offset(0, 2),
        ),
        on_click=on_tap,
        ink=False,
        tooltip=branding.THEME_LABELS.get(key, key),
    )


def _chips_row(chips: list[ft.Control], *, spacing: float = 12) -> ft.Control:
    """Один горизонтальный ряд кружков по центру."""
    return ft.Row(
        spacing=spacing,
        wrap=False,
        scroll=ft.ScrollMode.AUTO if hasattr(ft, "ScrollMode") else None,
        alignment=ft.MainAxisAlignment.CENTER,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=chips,
    )


def _page_appearance(page: ft.Page) -> ft.Control:
    theme_sw = ft.Switch(value=prefs.theme_mode() == "dark", active_color=theme.PRIMARY)
    accent = prefs.accent_theme()

    def _quiet_reload(route_key: str = "appearance"):
        STATE.draft["_settings_no_anim"] = True
        STATE.go(settings_route(route_key))

    def on_theme(e):
        mode = "dark" if theme_sw.value else "light"
        prefs.set_theme_mode(mode)
        theme.apply_mode(page, mode)
        logs.info("prefs theme=%s", mode)
        _quiet_reload("appearance")

    theme_sw.on_change = on_theme

    chips: list[ft.Control] = []
    for key in branding.THEME_KEYS:

        def _pick(_e=None, k=key):
            prefs.set_accent_theme(k)
            # по умолчанию пузыри следуют акценту, если не задавали отдельно
            prefs.set_bubble_theme(k)
            theme.apply_mode(page, prefs.theme_mode())
            STATE.snack(f"Цвет: {branding.THEME_LABELS.get(k, k)}")
            _quiet_reload("appearance")

        chips.append(_color_chip(key, key == accent, _pick))

    return ft.Column(
        spacing=12,
        tight=True,
        controls=[
            _card(
                ft.Column(
                    spacing=14,
                    tight=True,
                    controls=[
                        _switch_row("Тёмная тема", theme_sw),
                        _section_label("Предпочтительный цвет"),
                        _chips_row(chips),
                        ft.Text(
                            "Меняет кнопки, акценты и общий тон приложения.",
                            size=12,
                            color=theme.MUTED,
                        ),
                    ],
                )
            ),
            _card(
                ft.Column(
                    spacing=0,
                    tight=True,
                    controls=[
                        _settings_row_item(
                            title="Пузыри сообщений",
                            value="Цвет ваших сообщений в чатах",
                            on_click=lambda _: STATE.go(settings_route("bubbles")),
                        ),
                        ft.Container(height=1, bgcolor=theme.DIVIDER),
                        _settings_row_item(
                            title="Иконка приложения",
                            value="Иконка на рабочем столе / в панели",
                            on_click=lambda _: STATE.go(settings_route("app_icon")),
                        ),
                    ],
                )
            ),
        ],
    )


def _page_bubbles(page: ft.Page) -> ft.Control:
    """Превью пузыря по центру; панель цвета — на всю ширину."""
    current = prefs.bubble_theme()
    preview_bubble = {"c": None}
    preview_text = {"c": None}
    # ширина контента настроек (ListView padding 16+16)
    full_w = float(theme.PHONE_WIDTH) - 32.0

    def _rebuild_preview(key: str):
        tok = branding.theme_tokens(key, "dark" if theme.is_dark() else "light")
        fill = tok.get("fill") or theme.PRIMARY
        onfill = tok.get("onfill") or "#FFFFFF"
        if preview_bubble["c"] is not None:
            preview_bubble["c"].bgcolor = fill
            preview_text["c"].color = onfill
            try:
                preview_bubble["c"].update()
                preview_text["c"].update()
            except Exception:
                pass

    bubble_label = ft.Text(
        "Привет! Это пример вашего сообщения",
        size=15,
        color="#FFFFFF",
        font_family=theme.FONT_FAMILY,
    )
    preview_text["c"] = bubble_label
    bubble = ft.Container(
        bgcolor=theme.BUBBLE_OUT,
        border_radius=ft.BorderRadius(
            top_left=20, top_right=20, bottom_left=6, bottom_right=20
        ),
        padding=ft.Padding.symmetric(horizontal=14, vertical=10),
        content=bubble_label,
        shadow=ft.BoxShadow(blur_radius=16, color="#00000033", offset=ft.Offset(0, 6)),
    )
    preview_bubble["c"] = bubble

    # превью сразу в цветах выбранной темы пузырей
    _rebuild_preview(current)

    half = ft.Container(
        width=full_w,
        height=300,
        bgcolor=theme.SURFACE,
        border_radius=24,
        alignment=ft.Alignment.CENTER,
        content=ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=16,
            controls=[
                ft.Text("Исходящее", size=13, color=theme.MUTED),
                bubble,
                ft.Container(
                    bgcolor=theme.BUBBLE_IN,
                    border_radius=ft.BorderRadius(
                        top_left=20, top_right=20, bottom_left=20, bottom_right=6
                    ),
                    padding=ft.Padding.symmetric(horizontal=14, vertical=10),
                    content=ft.Text(
                        "А это входящее",
                        size=15,
                        color=theme.INK,
                        font_family=theme.FONT_FAMILY,
                    ),
                ),
            ],
        ),
    )

    chips: list[ft.Control] = []
    for key in branding.THEME_KEYS:

        def _pick(_e=None, k=key):
            prefs.set_bubble_theme(k)
            theme.apply_mode(page, prefs.theme_mode())
            _rebuild_preview(k)
            STATE.snack(f"Пузыри: {branding.THEME_LABELS.get(k, k)}")
            STATE.draft["_settings_no_anim"] = True
            STATE.go(settings_route("bubbles"))

        chips.append(_color_chip(key, key == current, _pick, size=48))

    colors_panel = ft.Container(
        width=full_w,
        content=_card(
            ft.Column(
                spacing=14,
                tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Text(
                        "Цвет пузырей",
                        size=13,
                        weight=ft.FontWeight.W_600,
                        color=theme.MUTED,
                        font_family=theme.FONT_FAMILY,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    _chips_row(chips, spacing=14),
                ],
            ),
            padding=ft.Padding.symmetric(horizontal=16, vertical=18),
        ),
    )

    return ft.Column(
        spacing=14,
        tight=True,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[half, colors_panel],
    )


def _page_app_icon(page: ft.Page) -> ft.Control:
    current = prefs.app_icon_key()
    # light/dark спрайты уже из branding
    icons = branding.list_app_icons(dark=theme.is_dark())
    # превью крупнее; спрайты уже со скруглёнными углами (RGBA)
    icon_size = 76.0
    corner = 17.0
    cells: list[ft.Control] = []
    for key, label, path in icons:

        def _pick(_e=None, k=key, p=path):
            prefs.set_app_icon_key(k)
            theme.apply_window_icon(page)
            STATE.snack(f"Иконка: {branding.THEME_LABELS.get(k, k)}")
            STATE.draft["_settings_no_anim"] = True
            STATE.go(settings_route("app_icon"))

        selected = key == current
        cells.append(
            ft.Container(
                ink=True,
                on_click=_pick,
                padding=ft.Padding.symmetric(horizontal=4),
                content=ft.Column(
                    spacing=8,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    tight=True,
                    controls=[
                        ft.Container(
                            width=icon_size,
                            height=icon_size,
                            border_radius=corner,
                            border=ft.Border.all(
                                2.5, theme.PRIMARY if selected else "transparent"
                            ),
                            clip_behavior=ft.ClipBehavior.HARD_EDGE,
                            shadow=ft.BoxShadow(
                                blur_radius=12,
                                color="#00000028",
                                offset=ft.Offset(0, 4),
                            ),
                            content=ft.Image(
                                src=path,
                                width=icon_size,
                                height=icon_size,
                                fit=ft.BoxFit.COVER,
                            ),
                        ),
                        ft.Text(
                            label,
                            size=10,
                            color=theme.PRIMARY if selected else theme.MUTED,
                            text_align=ft.TextAlign.CENTER,
                            max_lines=1,
                            overflow=ft.TextOverflow.ELLIPSIS,
                            width=80,
                        ),
                    ],
                ),
            )
        )

    return _card(
        ft.Column(
            spacing=12,
            tight=True,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Text(
                    "Иконка приложения",
                    size=13,
                    weight=ft.FontWeight.W_600,
                    color=theme.MUTED,
                    font_family=theme.FONT_FAMILY,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Text(
                    "Выберите цвет иконки для светлой и тёмной темы. "
                    "На телефоне обновится на рабочем столе.",
                    size=12,
                    color=theme.MUTED,
                    text_align=ft.TextAlign.CENTER,
                ),
                _chips_row(cells, spacing=8),
            ],
        )
    )


def _page_favorites(page: ft.Page) -> ft.Control:
    fav = chat_data.ensure_favorites()
    STATE.draft["_open_chat_id"] = fav.id
    STATE.draft["_open_is_group"] = False
    STATE.go("/chat")
    return ft.Container()


def _page_avatar(page: ft.Page) -> ft.Control:
    user = STATE.user
    if user is None:
        return _placeholder("avatar", "Войдите, чтобы сменить аватар.")

    status = ft.Text(
        "Нажмите «Выбрать фото» — аватар сохранится в профиле.",
        size=13,
        color=theme.MUTED,
        text_align=ft.TextAlign.CENTER,
    )
    avatar_host = ft.Container(content=_profile_avatar(user, 112))

    def _apply_path(path: str):
        if not path or STATE.user is None:
            return
        try:
            updated = auth.update_profile(STATE.user.id, avatar_path=path)
            STATE.user = updated
            avatar_host.content = _profile_avatar(updated, 112)
            status.value = "Аватар обновлён"
            status.color = theme.PRIMARY
            try:
                avatar_host.update()
                status.update()
            except Exception:
                pass
            STATE.snack("Аватар сохранён")
            STATE.go(settings_route("avatar"))
        except Exception as exc:
            STATE.error(str(exc), "Аватар")

    def pick(_=None):
        async def _pick():
            try:
                picker = ft.FilePicker()
                try:
                    page.services.append(picker)
                except Exception:
                    try:
                        page.overlay.append(picker)
                        page.update()
                    except Exception:
                        pass
                files = await picker.pick_files(
                    dialog_title="Фото профиля",
                    allow_multiple=False,
                    allowed_extensions=["png", "jpg", "jpeg", "webp"],
                    file_type=ft.FilePickerFileType.CUSTOM,
                )
                if not files:
                    return
                path = getattr(files[0], "path", None) or ""
                if path:
                    _apply_path(path)
            except Exception:
                # fallback: системный диалог Windows
                try:
                    import tkinter as tk
                    from tkinter import filedialog

                    root = tk.Tk()
                    root.withdraw()
                    root.attributes("-topmost", True)
                    path = filedialog.askopenfilename(
                        title="Фото профиля",
                        filetypes=[
                            ("Изображения", "*.png *.jpg *.jpeg *.webp"),
                            ("Все файлы", "*.*"),
                        ],
                    )
                    root.destroy()
                    if path:
                        _apply_path(path)
                except Exception as exc:
                    STATE.error(str(exc), "Аватар")

        try:
            page.run_task(_pick)
        except Exception as exc:
            STATE.error(str(exc), "Аватар")

    return ft.Column(
        spacing=12,
        tight=True,
        controls=[
            _card(
                ft.Column(
                    spacing=14,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        avatar_host,
                        status,
                        liquid_glass.purple_glass_button(
                            "Выбрать фото", pick, expand=True
                        ),
                    ],
                ),
                padding=ft.Padding.symmetric(horizontal=20, vertical=24),
            )
        ],
    )


def _page_notifications(page: ft.Page) -> ft.Control:
    from core import sounds

    push_sw = ft.Switch(value=prefs.push_enabled(), active_color=theme.PRIMARY)
    private_sw = ft.Switch(value=prefs.notif_private(), active_color=theme.PRIMARY)
    groups_sw = ft.Switch(value=prefs.notif_groups(), active_color=theme.PRIMARY)
    preview_sw = ft.Switch(value=prefs.notif_preview(), active_color=theme.PRIMARY)

    sound_sw = ft.Switch(value=prefs.sounds_enabled(), active_color=theme.PRIMARY)
    incoming_sw = ft.Switch(value=prefs.sound_incoming(), active_color=theme.PRIMARY)
    outgoing_sw = ft.Switch(value=prefs.sound_outgoing(), active_color=theme.PRIMARY)

    vol = prefs.sound_volume()
    if vol <= 0.45:
        vol_key = "low"
    elif vol >= 0.9:
        vol_key = "high"
    else:
        vol_key = "mid"
    vol_state = {"key": vol_key}

    def on_push(_e=None):
        prefs.set_push_enabled(bool(push_sw.value))
        logs.info("prefs push=%s", push_sw.value)

    def on_private(_e=None):
        prefs.set_notif_private(bool(private_sw.value))

    def on_groups(_e=None):
        prefs.set_notif_groups(bool(groups_sw.value))

    def on_preview(_e=None):
        prefs.set_notif_preview(bool(preview_sw.value))

    def on_sound(_e=None):
        prefs.set_sounds_enabled(bool(sound_sw.value))
        logs.info("prefs sounds=%s", sound_sw.value)

    def on_incoming(_e=None):
        prefs.set_sound_incoming(bool(incoming_sw.value))

    def on_outgoing(_e=None):
        prefs.set_sound_outgoing(bool(outgoing_sw.value))

    push_sw.on_change = on_push
    private_sw.on_change = on_private
    groups_sw.on_change = on_groups
    preview_sw.on_change = on_preview
    sound_sw.on_change = on_sound
    incoming_sw.on_change = on_incoming
    outgoing_sw.on_change = on_outgoing

    vol_labels = {
        "low": ("Тихо", 0.35),
        "mid": ("Нормально", 0.7),
        "high": ("Громко", 1.0),
    }

    def _vol_chip(key: str) -> ft.Control:
        label, value = vol_labels[key]
        selected = vol_state["key"] == key

        def _pick(_e=None, k=key, v=value):
            vol_state["key"] = k
            prefs.set_sound_volume(v)
            STATE.draft["_settings_no_anim"] = True
            STATE.go(settings_route("notifications"))

        return ft.Container(
            ink=True,
            on_click=_pick,
            border_radius=14,
            bgcolor=theme.PRIMARY_SOFT if selected else theme.FIELD_BG,
            padding=ft.Padding.symmetric(horizontal=14, vertical=10),
            border=ft.Border.all(
                1.5, theme.PRIMARY if selected else theme.STROKE
            ),
            content=ft.Text(
                label,
                size=13,
                weight=ft.FontWeight.W_600 if selected else ft.FontWeight.W_500,
                color=theme.PRIMARY if selected else theme.INK,
                font_family=theme.FONT_FAMILY,
            ),
        )

    def _test_sound(_e=None):
        sounds.play_ding(force=True)
        STATE.snack("Звук входящего")

    notif_card = _card(
        ft.Column(
            spacing=12,
            tight=True,
            controls=[
                _switch_row(
                    "Push-уведомления",
                    push_sw,
                    hint="Показывать уведомления о новых сообщениях",
                ),
                _divider(),
                _switch_row(
                    "Личные чаты",
                    private_sw,
                    hint="Уведомления из личных переписок",
                ),
                _switch_row(
                    "Группы",
                    groups_sw,
                    hint="Уведомления из групповых чатов",
                ),
                _switch_row(
                    "Текст сообщения",
                    preview_sw,
                    hint="Показывать текст в уведомлении",
                ),
            ],
        )
    )

    sound_card = _card(
        ft.Column(
            spacing=12,
            tight=True,
            controls=[
                _switch_row(
                    "Звуки",
                    sound_sw,
                    hint="Общий переключатель звуков в приложении",
                ),
                _divider(),
                _switch_row(
                    "Входящие",
                    incoming_sw,
                    hint="Звук при новом сообщении",
                ),
                _switch_row(
                    "Исходящие",
                    outgoing_sw,
                    hint="Короткий звук при отправке",
                ),
                ft.Text(
                    "Громкость",
                    size=13,
                    weight=ft.FontWeight.W_600,
                    color=theme.MUTED,
                    font_family=theme.FONT_FAMILY,
                ),
                ft.Row(
                    spacing=8,
                    wrap=True,
                    controls=[_vol_chip("low"), _vol_chip("mid"), _vol_chip("high")],
                ),
                ft.Container(
                    ink=True,
                    on_click=_test_sound,
                    border_radius=14,
                    bgcolor=theme.FIELD_BG,
                    padding=ft.Padding.symmetric(horizontal=14, vertical=12),
                    content=ft.Row(
                        spacing=10,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Icon(
                                ft.Icons.VOLUME_UP_ROUNDED,
                                size=18,
                                color=theme.PRIMARY,
                            ),
                            ft.Text(
                                "Прослушать звук входящего",
                                size=14,
                                color=theme.INK,
                                font_family=theme.FONT_FAMILY,
                            ),
                        ],
                    ),
                ),
            ],
        )
    )

    return ft.Column(
        spacing=14,
        tight=True,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        controls=[
            _section_label("Уведомления"),
            notif_card,
            _section_label("Звуки"),
            sound_card,
        ],
    )


def _page_password(page: ft.Page) -> ft.Control:
    if STATE.user is None:
        return _placeholder("password", "Войдите, чтобы сменить пароль.")
    p1 = ft.TextField(
        label="Новый пароль",
        password=True,
        can_reveal_password=True,
        bgcolor=theme.FIELD_BG,
        color=theme.INK,
        border=theme.field_border(16, color=theme.STROKE, focused_color=theme.PRIMARY),
    )
    p2 = ft.TextField(
        label="Повтор",
        password=True,
        can_reveal_password=True,
        bgcolor=theme.FIELD_BG,
        color=theme.INK,
        border=theme.field_border(16, color=theme.STROKE, focused_color=theme.PRIMARY),
    )

    def save(_=None):
        try:
            auth.change_password(STATE.user.id, p1.value or "", p2.value or "")
            STATE.snack("Пароль обновлён")
            logs.event("PASSWORD_CHANGE", user=STATE.user.public_id)
            p1.value = ""
            p2.value = ""
            p1.update()
            p2.update()
        except Exception as exc:
            STATE.error(str(exc), "Пароль")

    return _card(
        ft.Column(
            spacing=12,
            tight=True,
            controls=[
                p1,
                p2,
                ft.FilledButton("Сохранить", icon=ft.Icons.SAVE, on_click=save),
            ],
        )
    )


def _page_privacy(page: ft.Page) -> ft.Control:
    from core import privacy as priv

    user = STATE.user
    if user is None:
        return _placeholder("privacy", "Войдите, чтобы настроить конфиденциальность.")

    pid = user.public_id
    cur = priv.for_user(pid)

    def _sw(key: str, label: str, hint: str) -> ft.Control:
        sw = ft.Switch(value=bool(cur.get(key)), active_color=theme.PRIMARY)

        def _on(_e=None, k=key, control=sw):
            priv.set_for_user(pid, **{k: bool(control.value)})
            logs.info("privacy %s %s=%s", pid, k, control.value)

        sw.on_change = _on
        return _switch_row(label, sw, hint=hint)

    msg_mode = {"v": cur.get("who_can_message") or priv.MSG_EVERYONE}

    def _msg_chip(mode: str) -> ft.Control:
        selected = msg_mode["v"] == mode
        label = priv.MSG_LABELS.get(mode, mode)

        def _pick(_e=None, m=mode):
            msg_mode["v"] = m
            priv.set_for_user(pid, who_can_message=m)
            STATE.draft["_settings_no_anim"] = True
            STATE.go(settings_route("privacy"))

        return ft.Container(
            ink=True,
            on_click=_pick,
            border_radius=14,
            bgcolor=theme.PRIMARY_SOFT if selected else theme.FIELD_BG,
            padding=ft.Padding.symmetric(horizontal=14, vertical=10),
            border=ft.Border.all(1.5, theme.PRIMARY if selected else theme.STROKE),
            content=ft.Text(
                label,
                size=13,
                weight=ft.FontWeight.W_600 if selected else ft.FontWeight.W_500,
                color=theme.PRIMARY if selected else theme.INK,
                font_family=theme.FONT_FAMILY,
            ),
        )

    visibility = _card(
        ft.Column(
            spacing=12,
            tight=True,
            controls=[
                _sw(
                    "hide_phone",
                    "Скрыть номер / email",
                    "Другие не увидят ваш контакт в профиле",
                ),
                _divider(),
                _sw(
                    "hide_last_seen",
                    "Скрыть время в сети",
                    "Вместо точного статуса — «был(а) недавно»",
                ),
                _divider(),
                _sw(
                    "hide_avatar",
                    "Скрыть аватар",
                    "Вместо фото — нейтральная заглушка",
                ),
                _divider(),
                _sw(
                    "hide_groups",
                    "Скрыть общие группы",
                    "Не показывать, в каких группах вы вместе",
                ),
            ],
        )
    )

    discovery = _card(
        ft.Column(
            spacing=12,
            tight=True,
            controls=[
                _sw(
                    "hide_from_search",
                    "Скрыть себя в поиске",
                    "Вас нельзя найти по имени, нику или ID",
                ),
            ],
        )
    )

    messaging = _card(
        ft.Column(
            spacing=12,
            tight=True,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[
                ft.Text(
                    "Кто может писать",
                    size=16,
                    color=theme.INK,
                    font_family=theme.FONT_FAMILY,
                ),
                ft.Text(
                    "Ограничение новых личных сообщений",
                    size=12,
                    color=theme.MUTED,
                    font_family=theme.FONT_FAMILY,
                ),
                ft.Row(
                    spacing=8,
                    wrap=True,
                    alignment=ft.MainAxisAlignment.CENTER,
                    controls=[
                        _msg_chip(priv.MSG_EVERYONE),
                        _msg_chip(priv.MSG_CONTACTS),
                        _msg_chip(priv.MSG_NOBODY),
                    ],
                ),
            ],
        )
    )

    return ft.Column(
        spacing=14,
        tight=True,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        controls=[
            _section_label("Профиль"),
            visibility,
            _section_label("Поиск"),
            discovery,
            _section_label("Сообщения"),
            messaging,
        ],
    )


def _page_blacklist(page: ft.Page) -> ft.Control:
    from core import blacklist as bl

    user = STATE.user
    if user is None:
        return _placeholder("blacklist", "Войдите, чтобы видеть чёрный список.")

    owner = user.public_id
    items = bl.list_blocked(owner)

    if not items:
        return _card(
            ft.Column(
                spacing=8,
                tight=True,
                controls=[
                    ft.Text(
                        "Список пуст",
                        size=16,
                        weight=ft.FontWeight.W_600,
                        color=theme.INK,
                        font_family=theme.FONT_FAMILY,
                    ),
                    ft.Text(
                        "Сюда попадают пользователи после блокировки "
                        "или жалобы с добавлением в чёрный список. "
                        "Они не видны в поиске и к ним нельзя написать.",
                        size=13,
                        color=theme.MUTED,
                        font_family=theme.FONT_FAMILY,
                    ),
                ],
            )
        )

    rows: list[ft.Control] = []
    for i, entry in enumerate(items):
        pid = entry["public_id"]
        name = entry["name"] or pid

        def _unblock(_e=None, target=pid, title=name):
            bl.unblock(owner, target)
            STATE.snack(f"Разблокирован: {title}")
            STATE.draft["_settings_no_anim"] = True
            STATE.go(settings_route("blacklist"))

        rows.append(
            ft.Container(
                padding=ft.Padding.symmetric(vertical=10),
                content=ft.Row(
                    spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Column(
                            spacing=2,
                            tight=True,
                            expand=True,
                            controls=[
                                ft.Text(
                                    name,
                                    size=15,
                                    weight=ft.FontWeight.W_600,
                                    color=theme.INK,
                                    font_family=theme.FONT_FAMILY,
                                ),
                                ft.Text(
                                    f"ID {pid}",
                                    size=12,
                                    color=theme.MUTED,
                                    font_family=theme.FONT_FAMILY,
                                ),
                            ],
                        ),
                        ft.TextButton(
                            "Разблок.",
                            on_click=_unblock,
                            style=ft.ButtonStyle(color=theme.PRIMARY),
                        ),
                    ],
                ),
            )
        )
        if i < len(items) - 1:
            rows.append(_divider())

    return ft.Column(
        spacing=14,
        tight=True,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        controls=[
            _section_label("Заблокированные"),
            _card(ft.Column(spacing=0, tight=True, controls=rows)),
            ft.Text(
                "Заблокированные не появляются в поиске и не могут начать переписку с вами в этом приложении.",
                size=12,
                color=theme.MUTED,
                font_family=theme.FONT_FAMILY,
            ),
        ],
    )


def _page_logs(page: ft.Page) -> ft.Control:
    text = logs.tail(200)
    return _card(
        ft.Text(
            text or "Лог пуст",
            size=11,
            color=theme.MUTED,
            selectable=True,
            font_family=theme.FONT_FAMILY,
        )
    )


def _page_language(page: ft.Page) -> ft.Control:
    return _card(
        ft.Column(
            spacing=10,
            tight=True,
            controls=[
                ft.Text("Язык интерфейса", size=16, weight=ft.FontWeight.W_600),
                ft.Text("Русский (по умолчанию)", size=14, color=theme.MUTED),
                ft.Text(
                    "Другие языки добавим позже.",
                    size=13,
                    color=theme.MUTED,
                ),
            ],
        )
    )


_BUILDERS: dict[str, Callable[[ft.Page], ft.Control]] = {
    "profile": _page_profile,
    "avatar": _page_avatar,
    "favorites": _page_favorites,
    "appearance": _page_appearance,
    "bubbles": _page_bubbles,
    "app_icon": _page_app_icon,
    "notifications": _page_notifications,
    "password": _page_password,
    "privacy": _page_privacy,
    "blacklist": _page_blacklist,
    "logs": _page_logs,
    "language": _page_language,
}


def build(page: ft.Page, key: str) -> ft.Control:
    """Собрать экран пункта настроек. Заготовки — в _placeholder."""
    key = (key or "").strip() or "profile"
    if key not in SETTINGS_PAGES:
        key = "profile"
    STATE.draft["_settings_page"] = key
    builder = _BUILDERS.get(key)
    if builder is not None:
        body = builder(page)
    else:
        body = _placeholder(key)
    return _shell(page, key, body)


def register_routes() -> dict[str, Callable]:
    """Карта route → builder для main.py."""
    out: dict[str, Callable] = {}
    for key in SETTINGS_PAGES:

        def _make(k: str):
            return lambda page, _k=k: build(page, _k)

        out[settings_route(key)] = _make(key)
    return out
