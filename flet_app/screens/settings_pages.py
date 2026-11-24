# -*- coding: utf-8 -*-
"""Отдельные экраны пунктов настроек — сюда добавляем функции."""
from __future__ import annotations

import os
from typing import Callable

import flet as ft

from core import auth, branding, gradients, logs, prefs
from core.config import DATA_DIR, UPLOADS_DIR
from core.i18n import t
from flet_app import chat_data, liquid_glass, mono_icons, search_history, theme
from flet_app.profile_ui import (
    actions_row,
    info_card,
    media_tabs_block,
    profile_avatar_from_seed,
    profile_head_block,
)
from flet_app.app_state import STATE

SETTINGS_PAGE_KEYS: tuple[str, ...] = (
    "profile",
    "avatar",
    "favorites",
    "appearance",
    "bubbles",
    "app_icon",
    "notifications",
    "privacy",
    "blacklist",
    "data",
    "language",
    "password",
    "tips",
    "help",
    "faq",
    "logs",
)


def settings_page_title(key: str) -> str:
    """Заголовок экрана настроек — строка вычисляется при отрисовке."""
    return t(f"settings.{key}")

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


def _header(title: str, *, on_back=None, trailing: ft.Control | None = None) -> ft.Control:
    back = liquid_glass.glass_circle_button(
        on_back or _back_to_settings,
        content=mono_icons.ui_icon("back", size=22),
        size=44,
        variant="white",
    )
    row_controls: list[ft.Control] = [
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
    ]
    if trailing is not None:
        row_controls.append(trailing)
    return ft.Container(
        padding=ft.Padding.symmetric(horizontal=12, vertical=8),
        content=ft.Row(
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=row_controls,
        ),
    )


def _enter(child: ft.Control, *, visible: bool = False) -> ft.Container:
    """Появление экрана настроек."""
    return theme.live_panel(child, visible=visible)


def _shell(page: ft.Page, key: str, body: ft.Control) -> ft.Control:
    """Полная ширина + скролл у края; контент с padding внутри."""
    # тихий refresh (смена цвета/темы) — без повторного «шоу»
    quiet = bool(STATE.draft.pop("_settings_no_anim", False))

    title = settings_page_title(key) if key in SETTINGS_PAGE_KEYS else key
    header_trailing: ft.Control | None = None
    if key == "profile":
        edit_cb = STATE.draft.pop("_profile_header_edit", None)
        if edit_cb is not None:
            header_trailing = liquid_glass.glass_circle_button(
                edit_cb,
                content=mono_icons.ui_icon("edit", size=22),
                size=44,
                variant="white",
            )
    header = _header(title, on_back=_back_from(key), trailing=header_trailing)
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
                settings_page_title(key) if key in SETTINGS_PAGE_KEYS else key,
                size=18,
                weight=ft.FontWeight.W_600,
                color=theme.INK,
                font_family=theme.FONT_FAMILY,
            ),
            ft.Text(
                hint or t("settings.section_placeholder"),
                size=14,
                color=theme.MUTED,
                font_family=theme.FONT_FAMILY,
            ),
        ]
    )
    return ft.Column(spacing=12, tight=True, controls=controls)


def _card(content: ft.Control, *, padding: ft.Padding | None = None) -> ft.Control:
    # ширина = ListView (PHONE_WIDTH − padding 16+16), иначе короткие карточки «пилюлей»
    # Плотная CARD без glass-blur — без серых полос между строками
    card_w = float(theme.PHONE_WIDTH - 32)
    return ft.Container(
        alignment=ft.Alignment.CENTER,
        width=card_w,
        content=ft.Container(
            content=content,
            width=card_w,
            padding=padding or ft.Padding.all(16),
            border_radius=22,
            bgcolor=theme.CARD,
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
            shadow=ft.BoxShadow(
                blur_radius=12,
                spread_radius=0,
                color=liquid_glass.white_glass_shadow(),
                offset=ft.Offset(0, 3),
            ),
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
                size=14,
                color=theme.INK,
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
    # Без серых линий в карточках — только небольшой зазор
    return ft.Container(height=8)


def _on_phone() -> bool:
    """Телефонный порт — без desktop-only пунктов."""
    try:
        return theme.is_mobile_runtime()
    except Exception:
        return True


def _choice_chips(
    options: list[tuple[str, str]],
    *,
    selected: str,
    on_pick,
) -> ft.Control:
    """Чипы выбора без remount экрана (не прыгает скролл наверх)."""
    state = {"v": selected}
    boxes: dict[str, ft.Container] = {}
    labels: dict[str, ft.Text] = {}

    def _paint():
        for key, box in boxes.items():
            on = key == state["v"]
            box.bgcolor = theme.PRIMARY_SOFT if on else theme.FIELD_BG
            box.border = ft.Border.all(1.5, theme.PRIMARY) if on else None
            lab = labels[key]
            lab.color = theme.PRIMARY if on else theme.INK
            lab.weight = ft.FontWeight.W_600 if on else ft.FontWeight.W_500
            try:
                box.update()
                lab.update()
            except Exception:
                pass

    controls: list[ft.Control] = []
    for key, title in options:
        lab = ft.Text(
            title,
            size=16,
            weight=ft.FontWeight.W_600 if key == selected else ft.FontWeight.W_500,
            color=theme.PRIMARY if key == selected else theme.INK,
            font_family=theme.FONT_FAMILY,
        )
        labels[key] = lab

        def _click(_e=None, k=key):
            if state["v"] == k:
                return
            state["v"] = k
            try:
                on_pick(k)
            except Exception:
                pass
            _paint()

        box = ft.Container(
            border_radius=16,
            bgcolor=theme.PRIMARY_SOFT if key == selected else theme.FIELD_BG,
            padding=ft.Padding.symmetric(horizontal=18, vertical=12),
            border=ft.Border.all(2, theme.PRIMARY) if key == selected else None,
            content=lab,
        )
        boxes[key] = box
        controls.append(theme.pressable(box, _click, scale_to=theme.PRESS_SCALE))

    return ft.Row(spacing=8, wrap=True, controls=controls)


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
        border=theme.field_border(16, color="transparent", focused_color=theme.PRIMARY),
        cursor_color=theme.PRIMARY,
        text_style=ft.TextStyle(font_family=theme.FONT_FAMILY, color=theme.INK),
        hint_style=ft.TextStyle(color=theme.HINT, font_family=theme.FONT_FAMILY),
        label_style=ft.TextStyle(color=theme.MUTED, font_family=theme.FONT_FAMILY),
    )


def _section_label(text: str) -> ft.Control:
    return ft.Text(
        text,
        size=16,
        weight=ft.FontWeight.W_700,
        color=theme.INK,
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
        STATE.error(t("common.dialog_open_failed"), t("common.profile_title"))


_INACTIVE_LABELS = {
    3: "3 месяца",
    6: "6 месяцев",
    12: "1 год",
    18: "1,5 года",
    24: "2 года",
}


def _fresh_user() -> auth.User | None:
    user = STATE.user
    if user is None:
        return None
    try:
        fresh = auth.get_user_by_id(user.id)
    except Exception:
        fresh = None
    if fresh is not None:
        STATE.user = fresh
        return fresh
    return user


def _terms_status_text(user: auth.User) -> str:
    if user.terms_accepted and user.terms_version:
        when = (user.terms_accepted_at or "").strip()
        when = when[:16].replace("T", " ") if when else ""
        if when:
            return f"Правила приняты · версия {user.terms_version} · {when}"
        return f"Правила приняты · версия {user.terms_version}"
    return "Согласие с правилами ещё не записано в профиль"


def _confirm_delete_account(page: ft.Page) -> None:
    user = _fresh_user()
    if user is None:
        STATE.snack("Сначала войдите в аккаунт")
        return

    word = ft.TextField(
        hint_text="УДАЛИТЬ",
        bgcolor=theme.FIELD_BG,
        border=theme.field_border(16, color="transparent", focused_color=theme.PRIMARY),
        color=theme.INK,
        text_style=ft.TextStyle(font_family=theme.FONT_FAMILY, size=16, color=theme.INK),
        hint_style=ft.TextStyle(font_family=theme.FONT_FAMILY, size=16, color=theme.HINT),
        cursor_color=theme.PRIMARY,
        autofocus=True,
    )

    def close(_=None):
        _close_dlg(page, dlg)

    def do_delete(_=None):
        if (word.value or "").strip() != "УДАЛИТЬ":
            STATE.snack("Чтобы удалить аккаунт, введите УДАЛИТЬ")
            return
        uid = user.id
        try:
            auth.delete_account(uid)
        except Exception as exc:
            logs.error("delete account: %s", exc)
            STATE.error("Не удалось удалить аккаунт")
            return
        try:
            from core import session

            session.clear()
        except Exception:
            pass
        STATE.user = None
        STATE.reset_draft()
        close()
        STATE.go("/welcome")

    dlg = ft.AlertDialog(
        modal=True,
        bgcolor=theme.CARD,
        title=ft.Text(
            "Удалить аккаунт?",
            size=20,
            weight=ft.FontWeight.W_700,
            color=theme.INK,
            font_family=theme.FONT_FAMILY,
        ),
        content=ft.Column(
            tight=True,
            spacing=12,
            width=max(220.0, float(theme.content_width()) - 88),
            controls=[
                ft.Text(
                    "Профиль, чаты и фото на этом устройстве исчезнут. Вернуть их будет нельзя.",
                    size=15,
                    color=theme.INK,
                    font_family=theme.FONT_FAMILY,
                ),
                ft.Text(
                    "Введите УДАЛИТЬ, чтобы подтвердить.",
                    size=14,
                    color=theme.MUTED,
                    font_family=theme.FONT_FAMILY,
                ),
                word,
            ],
        ),
        actions=[
            theme.action_button("Отмена", close, width=130),
            theme.pressable(
                ft.Container(
                    width=150,
                    height=48,
                    border_radius=16,
                    bgcolor="#C4475A",
                    alignment=ft.Alignment.CENTER,
                    content=ft.Text(
                        "Удалить",
                        size=16,
                        weight=ft.FontWeight.W_700,
                        color="#FFFBFF",
                        font_family=theme.FONT_FAMILY,
                    ),
                ),
                do_delete,
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.CENTER,
    )
    _show_dlg(page, dlg)


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
            theme.action_button(t("common.cancel"), close, width=140),
            theme.action_button(t("common.save"), save, primary=True, width=140),
        ],
    )
    _show_dlg(page, dlg)


def _settings_row_item(
    *,
    title: str,
    value: str,
    on_click,
) -> ft.Control:
    body = ft.Container(
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
                            size=16,
                            weight=ft.FontWeight.W_600,
                            color=theme.INK,
                            font_family=theme.FONT_FAMILY,
                        ),
                        ft.Text(
                            value or t("common.not_set"),
                            size=16,
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
    return theme.pressable(body, on_click, scale_to=theme.PRESS_SCALE, expand=True)


def _page_profile(page: ft.Page) -> ft.Control:
    """Свой профиль — Telegram-style (тело для settings _shell)."""
    user = _fresh_user()
    if user is None:
        return _placeholder("profile", t("profile.login_required"))

    def reload():
        STATE.draft["_settings_no_anim"] = True
        STATE.go(settings_route("profile"))

    def apply_user(updated: auth.User):
        STATE.user = updated
        STATE.snack(t("profile.updated"))
        reload()

    def edit_name(_e=None):
        u = STATE.user
        if u is None:
            return
        first_tf = _field(t("profile.first_name"), u.first_name or "")
        last_tf = _field(t("profile.last_name"), u.last_name or "")

        def _save():
            apply_user(
                auth.update_profile(
                    u.id,
                    first_name=(first_tf.value or "").strip(),
                    last_name=(last_tf.value or "").strip(),
                )
            )

        _edit_dialog(page, title=t("profile.first_name"), fields=[first_tf, last_tf], on_save=_save)

    STATE.draft["_profile_header_edit"] = edit_name

    def edit_nick(_e=None):
        u = STATE.user
        if u is None:
            return
        nick_tf = _field(
            t("profile.nick"),
            u.nickname or "",
            hint=t("profile.nick_hint"),
        )

        def _save():
            raw = (nick_tf.value or "").strip().lstrip("@")
            apply_user(auth.update_profile(u.id, nickname=raw))

        _edit_dialog(page, title=t("profile.nickname"), fields=[nick_tf], on_save=_save)

    def edit_phone(_e=None):
        u = STATE.user
        if u is None:
            return
        phone_tf = _field(t("profile.phone_email"), u.contact_value or "", hint=t("profile.phone_hint"))

        def _save():
            apply_user(
                auth.update_profile(
                    u.id, contact_value=(phone_tf.value or "").strip()
                )
            )

        _edit_dialog(page, title=t("profile.contact"), fields=[phone_tf], on_save=_save)

    def edit_bio(_e=None):
        u = STATE.user
        if u is None:
            return
        bio_tf = _field(
            t("profile.about"),
            u.status_text or "",
            hint=t("profile.about_hint"),
            multiline=True,
        )

        def _save():
            apply_user(
                auth.update_profile(u.id, status_text=(bio_tf.value or "").strip())
            )

        _edit_dialog(page, title=t("profile.description"), fields=[bio_tf], on_save=_save)

    def more_soon(_e=None):
        STATE.snack(t("profile.more_soon"))

    seed = (user.public_id or user.display_name or "me").lower()
    avatar = profile_avatar_from_seed(
        seed,
        user.first_name or "?",
        user.last_name or "",
        size=120,
        image_path=getattr(user, "avatar_path", None),
    )

    status_line = t("profile.status_you")
    if (user.status_text or "").strip():
        status_line = t(
            "profile.status_you_with",
            status=(user.status_text or "").strip()[:48],
        )

    head = profile_head_block(
        avatar=avatar,
        display_name=user.full_name or t("profile.no_name"),
        status_line=status_line,
        name_on_click=edit_name,
    )

    profile_actions = actions_row(
        [
            ("edit", t("profile.edit"), edit_name),
            (ft.Icons.ACCOUNT_CIRCLE_OUTLINED, t("avatar.title"), lambda _: STATE.go(settings_route("avatar"))),
            (ft.Icons.LOCK_OUTLINE, t("profile.privacy_short"), lambda _: STATE.go(settings_route("privacy"))),
            ("more", t("profile.more"), more_soon),
        ]
    )

    info_rows = [
        (t("profile.first_name"), user.full_name or "", edit_name),
        (
            t("profile.nickname"),
            f"@{user.nickname}" if user.nickname else t("common.not_set"),
            edit_nick,
        ),
        (t("profile.phone_row"), user.contact_value or "", edit_phone),
        (
            t("profile.about"),
            (user.status_text or "").strip() or t("common.not_set"),
            edit_bio,
        ),
        ("ID", user.public_id or "", None),
    ]

    media_block = media_tabs_block([], empty_text=t("profile.media_empty"))

    return ft.Column(
        spacing=16,
        tight=True,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            head,
            profile_actions,
            info_card(info_rows),
            ft.Text(
                _terms_status_text(user),
                size=14,
                color=theme.MUTED,
                font_family=theme.FONT_FAMILY,
                text_align=ft.TextAlign.CENTER,
            ),
            media_block,
            ft.Container(height=8),
        ],
    )


def _color_chip(key: str, selected: bool, on_tap, *, size: float = 52.0) -> ft.Control:
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

    accent_state = {"v": accent}
    accent_chips: dict[str, ft.Container] = {}

    def _paint_accent():
        for k, chip in accent_chips.items():
            on = k == accent_state["v"]
            chip.border = ft.Border.all(3, theme.BG if on else "transparent")
            chip.shadow = ft.BoxShadow(
                blur_radius=12 if on else 6,
                color=theme.PRIMARY_SOFT if on else "#00000022",
                offset=ft.Offset(0, 2),
            )
            try:
                chip.update()
            except Exception:
                pass

    chips: list[ft.Control] = []
    for key in branding.THEME_KEYS:

        def _pick(_e=None, k=key):
            accent_state["v"] = k
            prefs.set_accent_theme(k)
            # по умолчанию пузыри следуют акценту, если не задавали отдельно
            prefs.set_bubble_theme(k)
            theme.apply_mode(page, prefs.theme_mode())
            _paint_accent()
            STATE.snack(t("appearance.snack_color", name=branding.THEME_LABELS.get(k, k)))

        chip = _color_chip(key, key == accent, _pick)
        accent_chips[key] = chip
        chips.append(chip)

    font_lbl = ft.Text(
        t("appearance.font_scale", scale=f"{prefs.font_scale():.2f}"),
        size=16,
        weight=ft.FontWeight.W_600,
        color=theme.INK,
        font_family=theme.FONT_FAMILY,
    )
    font_slider = ft.Slider(
        min=0.85,
        max=1.25,
        divisions=8,
        value=prefs.font_scale(),
        active_color=theme.PRIMARY,
        on_change=lambda e: None,
    )

    def on_font(e):
        prefs.set_font_scale(float(e.control.value))
        font_lbl.value = t("appearance.font_scale", scale=f"{prefs.font_scale():.2f}")
        try:
            font_lbl.update()
        except Exception:
            pass

    font_slider.on_change = on_font

    dim_lbl = ft.Text(
        t("appearance.chat_dim", pct=int(prefs.chat_bg_dim() * 100)),
        size=16,
        weight=ft.FontWeight.W_600,
        color=theme.INK,
        font_family=theme.FONT_FAMILY,
    )
    dim_slider = ft.Slider(
        min=0.0,
        max=0.4,
        divisions=8,
        value=prefs.chat_bg_dim(),
        active_color=theme.PRIMARY,
    )

    def on_dim(e):
        prefs.set_chat_bg_dim(float(e.control.value))
        dim_lbl.value = t("appearance.chat_dim", pct=int(prefs.chat_bg_dim() * 100))
        try:
            dim_lbl.update()
        except Exception:
            pass

    dim_slider.on_change = on_dim

    fps_chips = _choice_chips(
        [("60", "60"), ("120", "120")],
        selected=str(prefs.frame_rate()),
        on_pick=lambda key: prefs.set_frame_rate(int(key)),
    )
    reduce_sw = ft.Switch(value=prefs.reduce_motion(), active_color=theme.PRIMARY)
    time_sw = ft.Switch(value=prefs.show_message_time(), active_color=theme.PRIMARY)

    reduce_sw.on_change = lambda _e: prefs.set_reduce_motion(bool(reduce_sw.value))
    time_sw.on_change = lambda _e: prefs.set_show_message_time(bool(time_sw.value))

    corner_chips = _choice_chips(
        [("sharp", t("appearance.corners_sharp")), ("round", t("appearance.corners_round")), ("super", t("appearance.corners_super"))],
        selected=prefs.bubble_corners(),
        on_pick=lambda k: prefs.set_bubble_corners(k),
    )

    look_links: list[ft.Control] = [
        _settings_row_item(
            title=t("appearance.bubbles_row"),
            value=t("appearance.bubbles_hint"),
            on_click=lambda _: STATE.go(settings_route("bubbles")),
        ),
    ]
    # Иконка окна — только desktop; на телефоне системная иконка из IPA
    if not _on_phone():
        look_links.append(ft.Container(height=6))
        look_links.append(
            _settings_row_item(
                title=t("appearance.app_icon_row"),
                value=t("appearance.app_icon_hint"),
                on_click=lambda _: STATE.go(settings_route("app_icon")),
            )
        )

    return ft.Column(
        spacing=12,
        tight=True,
        controls=[
            _card(
                ft.Column(
                    spacing=14,
                    tight=True,
                    controls=[
                        _switch_row(t("appearance.dark_theme"), theme_sw),
                        _section_label(t("appearance.preferred_color")),
                        _chips_row(chips),
                        ft.Text(
                            t("appearance.color_hint"),
                            size=14,
                            color=theme.INK,
                            font_family=theme.FONT_FAMILY,
                        ),
                    ],
                )
            ),
            _card(
                ft.Column(
                    spacing=0,
                    tight=True,
                    controls=look_links,
                )
            ),
            _section_label(t("appearance.text_animation")),
            _card(
                ft.Column(
                    spacing=12,
                    tight=True,
                    controls=[
                        font_lbl,
                        font_slider,
                        _divider(),
                        _switch_row(
                            t("appearance.reduce_motion"),
                            reduce_sw,
                            hint=t("appearance.reduce_motion_hint"),
                        ),
                        _divider(),
                        ft.Text(
                            t("appearance.frame_rate"),
                            size=16,
                            weight=ft.FontWeight.W_600,
                            color=theme.INK,
                            font_family=theme.FONT_FAMILY,
                        ),
                        fps_chips,
                        ft.Text(
                            t("appearance.frame_rate_hint"),
                            size=14,
                            color=theme.INK,
                            font_family=theme.FONT_FAMILY,
                        ),
                    ],
                )
            ),
            _section_label(t("appearance.section_chat")),
            _card(
                ft.Column(
                    spacing=12,
                    tight=True,
                    controls=[
                        ft.Text(
                            t("appearance.bubble_corners"),
                            size=16,
                            weight=ft.FontWeight.W_600,
                            color=theme.INK,
                            font_family=theme.FONT_FAMILY,
                        ),
                        corner_chips,
                        _divider(),
                        _switch_row(
                            t("appearance.message_time"),
                            time_sw,
                            hint=t("appearance.message_time_hint"),
                        ),
                        dim_lbl,
                        dim_slider,
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
        t("appearance.preview_outgoing"),
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
                ft.Text(
                    t("appearance.preview_out_label"),
                    size=15,
                    color=theme.INK,
                    font_family=theme.FONT_FAMILY,
                ),
                bubble,
                ft.Container(
                    bgcolor=theme.BUBBLE_IN,
                    border_radius=ft.BorderRadius(
                        top_left=20, top_right=20, bottom_left=20, bottom_right=6
                    ),
                    padding=ft.Padding.symmetric(horizontal=14, vertical=10),
                    content=ft.Text(
                        t("appearance.preview_incoming"),
                        size=15,
                        color=theme.INK,
                        font_family=theme.FONT_FAMILY,
                    ),
                ),
            ],
        ),
    )

    bubble_state = {"v": current}
    bubble_chips: dict[str, ft.Container] = {}

    def _paint_bubble_chips():
        for k, chip in bubble_chips.items():
            on = k == bubble_state["v"]
            chip.border = ft.Border.all(3, theme.BG if on else "transparent")
            chip.shadow = ft.BoxShadow(
                blur_radius=12 if on else 6,
                color=theme.PRIMARY_SOFT if on else "#00000022",
                offset=ft.Offset(0, 2),
            )
            try:
                chip.update()
            except Exception:
                pass

    chips: list[ft.Control] = []
    for key in branding.THEME_KEYS:

        def _pick(_e=None, k=key):
            bubble_state["v"] = k
            prefs.set_bubble_theme(k)
            theme.apply_mode(page, prefs.theme_mode())
            _rebuild_preview(k)
            _paint_bubble_chips()
            STATE.snack(t("appearance.snack_bubbles", name=branding.THEME_LABELS.get(k, k)))

        chip = _color_chip(key, key == current, _pick, size=48)
        bubble_chips[key] = chip
        chips.append(chip)

    colors_panel = ft.Container(
        width=full_w,
        content=_card(
            ft.Column(
                spacing=14,
                tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Text(
                        t("appearance.bubble_color"),
                        size=16,
                        weight=ft.FontWeight.W_600,
                        color=theme.INK,
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
    if _on_phone():
        return _placeholder(
            "app_icon",
            t("appearance.app_icon_desc"),
        )
    current = prefs.app_icon_key()
    # light/dark спрайты уже из branding
    icons = branding.list_app_icons(dark=theme.is_dark())
    # превью крупнее; спрайты уже со скруглёнными углами (RGBA)
    icon_size = 76.0
    corner = 17.0
    state = {"v": current}
    frames: dict[str, ft.Container] = {}
    labels: dict[str, ft.Text] = {}

    def _paint():
        for k, fr in frames.items():
            on = k == state["v"]
            fr.border = ft.Border.all(2.5, theme.PRIMARY if on else "transparent")
            lab = labels[k]
            lab.color = theme.PRIMARY if on else theme.INK
            try:
                fr.update()
                lab.update()
            except Exception:
                pass

    cells: list[ft.Control] = []
    for key, label, path in icons:

        def _pick(_e=None, k=key):
            state["v"] = k
            prefs.set_app_icon_key(k)
            theme.apply_window_icon(page)
            _paint()
            STATE.snack(t("appearance.snack_icon", name=branding.THEME_LABELS.get(k, k)))

        selected = key == current
        frame = ft.Container(
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
        )
        lab = ft.Text(
            label,
            size=14,
            weight=ft.FontWeight.W_600,
            color=theme.PRIMARY if selected else theme.INK,
            font_family=theme.FONT_FAMILY,
            text_align=ft.TextAlign.CENTER,
            max_lines=1,
            overflow=ft.TextOverflow.ELLIPSIS,
            width=88,
        )
        frames[key] = frame
        labels[key] = lab
        cells.append(
            ft.Container(
                ink=True,
                on_click=_pick,
                padding=ft.Padding.symmetric(horizontal=4),
                content=ft.Column(
                    spacing=8,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    tight=True,
                    controls=[frame, lab],
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
                    t("appearance.app_icon_title"),
                    size=16,
                    weight=ft.FontWeight.W_600,
                    color=theme.INK,
                    font_family=theme.FONT_FAMILY,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Text(
                    t("appearance.app_icon_desc"),
                    size=14,
                    color=theme.INK,
                    font_family=theme.FONT_FAMILY,
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
        return _placeholder("avatar", t("avatar.login_required"))

    status = ft.Text(
        t("avatar.pick_hint"),
        size=15,
        color=theme.INK,
        font_family=theme.FONT_FAMILY,
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
            status.value = t("avatar.updated")
            status.color = theme.PRIMARY
            try:
                avatar_host.update()
                status.update()
            except Exception:
                pass
            STATE.snack(t("avatar.saved"))
            STATE.go(settings_route("avatar"))
        except Exception as exc:
            STATE.error(str(exc), t("avatar.title"))

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
                    dialog_title=t("avatar.dialog_title"),
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
                        title=t("avatar.dialog_title"),
                        filetypes=[
                            (t("avatar.file_images"), "*.png *.jpg *.jpeg *.webp"),
                            (t("avatar.file_all"), "*.*"),
                        ],
                    )
                    root.destroy()
                    if path:
                        _apply_path(path)
                except Exception as exc:
                    STATE.error(str(exc), t("avatar.title"))

        try:
            page.run_task(_pick)
        except Exception as exc:
            STATE.error(str(exc), t("avatar.title"))

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
                            t("avatar.pick_photo"), pick, expand=True
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
    questions_sw = ft.Switch(value=prefs.notif_questions(), active_color=theme.PRIMARY)
    mentions_sw = ft.Switch(
        value=prefs.notif_mentions_only_groups(), active_color=theme.PRIMARY
    )
    quiet_sw = ft.Switch(value=prefs.notif_quiet_hours(), active_color=theme.PRIMARY)

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

    def on_questions(_e=None):
        prefs.set_notif_questions(bool(questions_sw.value))

    def on_mentions(_e=None):
        prefs.set_notif_mentions_only_groups(bool(mentions_sw.value))

    def on_quiet(_e=None):
        prefs.set_notif_quiet_hours(bool(quiet_sw.value))

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
    questions_sw.on_change = on_questions
    mentions_sw.on_change = on_mentions
    quiet_sw.on_change = on_quiet
    sound_sw.on_change = on_sound
    incoming_sw.on_change = on_incoming
    outgoing_sw.on_change = on_outgoing

    vol_map = {"low": 0.35, "mid": 0.7, "high": 1.0}

    def _on_vol(k: str):
        vol_state["key"] = k
        prefs.set_sound_volume(vol_map.get(k, 0.7))

    vol_chips = _choice_chips(
        [("low", t("notif.vol_low")), ("mid", t("notif.vol_mid")), ("high", t("notif.vol_high"))],
        selected=vol_state["key"],
        on_pick=_on_vol,
    )

    def _test_sound(_e=None):
        if prefs.notif_sound_name() == "none":
            STATE.snack(t("notif.sound_off"))
            return
        sounds.play_ding(force=True)
        STATE.snack(t("notif.sound_incoming"))

    def _on_notif_sound(k: str):
        prefs.set_notif_sound_name(k)

    sound_chips = _choice_chips(
        [("default", t("notif.tone_default")), ("soft", t("notif.tone_soft")), ("none", t("notif.tone_none"))],
        selected=prefs.notif_sound_name(),
        on_pick=_on_notif_sound,
    )

    qh_start = _field(
        t("notif.qh_start"), prefs.quiet_hours_start(), hint=t("notif.qh_hint")
    )
    qh_end = _field(t("notif.qh_end"), prefs.quiet_hours_end(), hint=t("notif.qh_hint"))

    def _save_quiet_times(_e=None):
        prefs.set_quiet_hours_start(qh_start.value or "22:00")
        prefs.set_quiet_hours_end(qh_end.value or "08:00")
        STATE.snack(t("notif.qh_saved"))

    qh_start.on_blur = _save_quiet_times
    qh_end.on_blur = _save_quiet_times

    notif_card = _card(
        ft.Column(
            spacing=12,
            tight=True,
            controls=[
                _switch_row(
                    t("notif.push"),
                    push_sw,
                    hint=t("notif.push_hint"),
                ),
                _divider(),
                _switch_row(
                    t("notif.dm"),
                    private_sw,
                    hint=t("notif.dm_hint"),
                ),
                _switch_row(
                    t("notif.groups"),
                    groups_sw,
                    hint=t("notif.groups_hint"),
                ),
                _switch_row(
                    t("notif.show_text"),
                    preview_sw,
                    hint=t("notif.show_text_hint"),
                ),
                _divider(),
                _switch_row(
                    t("notif.questions"),
                    questions_sw,
                    hint=t("notif.questions_hint"),
                ),
                _switch_row(
                    t("notif.mentions_only"),
                    mentions_sw,
                    hint=t("notif.mentions_hint"),
                ),
            ],
        )
    )

    quiet_card = _card(
        ft.Column(
            spacing=12,
            tight=True,
            controls=[
                _switch_row(
                    t("notif.quiet_hours"),
                    quiet_sw,
                    hint=t("notif.quiet_hours_hint"),
                ),
                qh_start,
                qh_end,
                ft.Text(
                    t("notif.quiet_resume"),
                    size=14,
                    color=theme.INK,
                    font_family=theme.FONT_FAMILY,
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
                    t("notif.sounds_master"),
                    sound_sw,
                    hint=t("notif.sounds_hint"),
                ),
                _divider(),
                _switch_row(
                    t("notif.incoming"),
                    incoming_sw,
                    hint=t("notif.incoming_hint"),
                ),
                _switch_row(
                    t("notif.outgoing"),
                    outgoing_sw,
                    hint=t("notif.outgoing_hint"),
                ),
                ft.Text(
                    t("notif.volume"),
                    size=16,
                    weight=ft.FontWeight.W_600,
                    color=theme.INK,
                    font_family=theme.FONT_FAMILY,
                ),
                vol_chips,
                ft.Text(
                    t("notif.sound_pick"),
                    size=16,
                    weight=ft.FontWeight.W_600,
                    color=theme.INK,
                    font_family=theme.FONT_FAMILY,
                ),
                sound_chips,
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
                                t("notif.preview_incoming"),
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
            _section_label(t("notif.section_notifications")),
            notif_card,
            quiet_card,
            _section_label(t("notif.section_sounds")),
            sound_card,
        ],
    )


def _page_password(page: ft.Page) -> ft.Control:
    if STATE.user is None:
        return _placeholder("password", t("password.login_required"))
    def _pwd_field(label: str) -> ft.TextField:
        return ft.TextField(
            label=label,
            password=True,
            can_reveal_password=True,
            filled=True,
            bgcolor=theme.FIELD_BG,
            color=theme.INK,
            cursor_color=theme.PRIMARY,
            border=theme.field_border(28, color="transparent", focused_color=theme.PRIMARY, width=1.5),
            text_style=ft.TextStyle(font_family=theme.FONT_FAMILY, size=16, color=theme.INK),
            label_style=ft.TextStyle(font_family=theme.FONT_FAMILY, size=15, color=theme.MUTED),
            height=56,
            content_padding=ft.Padding.symmetric(horizontal=20, vertical=14),
        )

    p1 = _pwd_field(t("password.new"))
    p2 = _pwd_field(t("password.repeat"))

    def save(_=None):
        try:
            auth.change_password(STATE.user.id, p1.value or "", p2.value or "")
            logs.event("PASSWORD_CHANGE", user=STATE.user.public_id)
            p1.value = ""
            p2.value = ""
            p1.update()
            p2.update()
        except Exception as exc:
            STATE.error(str(exc), t("password.title"))

    return ft.Column(
        spacing=14,
        tight=True,
        controls=[
            p1,
            p2,
            theme.primary_button(t("common.save"), save),
        ],
    )


def _page_privacy(page: ft.Page) -> ft.Control:
    from core import privacy as priv

    user = _fresh_user()
    if user is None:
        return _placeholder("privacy", t("privacy.login_required"))

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

    def _on_msg_mode(m: str) -> None:
        msg_mode["v"] = m
        priv.set_for_user(pid, who_can_message=m)

    msg_chips = _choice_chips(
        [
            (priv.MSG_EVERYONE, priv.MSG_LABELS.get(priv.MSG_EVERYONE, priv.MSG_EVERYONE)),
            (priv.MSG_CONTACTS, priv.MSG_LABELS.get(priv.MSG_CONTACTS, priv.MSG_CONTACTS)),
            (priv.MSG_NOBODY, priv.MSG_LABELS.get(priv.MSG_NOBODY, priv.MSG_NOBODY)),
        ],
        selected=msg_mode["v"],
        on_pick=_on_msg_mode,
    )

    visibility = _card(
        ft.Column(
            spacing=12,
            tight=True,
            controls=[
                _sw(
                    "hide_phone",
                    t("privacy.hide_contact"),
                    t("privacy.hide_contact_hint"),
                ),
                _divider(),
                _sw(
                    "hide_last_seen",
                    t("privacy.hide_online"),
                    t("privacy.hide_online_hint"),
                ),
                _divider(),
                _sw(
                    "hide_avatar",
                    t("privacy.hide_avatar"),
                    t("privacy.hide_avatar_hint"),
                ),
                _divider(),
                _sw(
                    "hide_groups",
                    t("privacy.hide_groups"),
                    t("privacy.hide_groups_hint"),
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
                    t("privacy.hide_search"),
                    t("privacy.hide_search_hint"),
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
                    t("privacy.who_can_write"),
                    size=16,
                    color=theme.INK,
                    font_family=theme.FONT_FAMILY,
                ),
                ft.Text(
                    t("privacy.dm_limit"),
                    size=14,
                    color=theme.INK,
                    font_family=theme.FONT_FAMILY,
                ),
                msg_chips,
            ],
        )
    )

    receipts_sw = ft.Switch(
        value=prefs.show_read_receipts_send(), active_color=theme.PRIMARY
    )
    typing_sw = ft.Switch(value=prefs.show_typing(), active_color=theme.PRIMARY)

    def on_receipts(_e=None):
        prefs.set_show_read_receipts_send(bool(receipts_sw.value))

    def on_typing(_e=None):
        prefs.set_show_typing(bool(typing_sw.value))

    receipts_sw.on_change = on_receipts
    typing_sw.on_change = on_typing

    signals = _card(
        ft.Column(
            spacing=12,
            tight=True,
            controls=[
                _switch_row(
                    t("privacy.read_receipts"),
                    receipts_sw,
                    hint=t("privacy.read_receipts_hint"),
                ),
                _divider(),
                _switch_row(
                    t("privacy.typing"),
                    typing_sw,
                    hint=t("privacy.typing_hint"),
                ),
            ],
        )
    )

    months_now = int(user.inactive_delete_months or 12)
    if months_now not in auth.INACTIVE_MONTH_CHOICES:
        months_now = 12

    def _pick_months(raw: str) -> None:
        try:
            updated = auth.set_inactive_delete_months(user.id, int(raw))
        except Exception as exc:
            STATE.error(str(exc))
            return
        STATE.user = updated

    idle_chips = _choice_chips(
        [(str(n), _INACTIVE_LABELS[n]) for n in auth.INACTIVE_MONTH_CHOICES],
        selected=str(months_now),
        on_pick=_pick_months,
    )

    def _accept_terms(_e=None):
        from flet_app.screens.legal import TERMS_VERSION

        try:
            updated = auth.record_terms(user.id, TERMS_VERSION)
        except Exception as exc:
            STATE.error(str(exc))
            return
        STATE.user = updated
        STATE.snack("Согласие с правилами записано в профиль")
        STATE.draft["_settings_no_anim"] = True
        STATE.go(settings_route("privacy"))

    account_card = _card(
        ft.Column(
            spacing=12,
            tight=True,
            controls=[
                ft.Text(
                    _terms_status_text(user),
                    size=15,
                    color=theme.INK,
                    font_family=theme.FONT_FAMILY,
                ),
                theme.pressable(
                    ft.Container(
                        height=48,
                        border_radius=16,
                        bgcolor=theme.FIELD_BG,
                        alignment=ft.Alignment.CENTER,
                        content=ft.Text(
                            "Открыть правила",
                            size=16,
                            weight=ft.FontWeight.W_700,
                            color=theme.INK,
                            font_family=theme.FONT_FAMILY,
                        ),
                    ),
                    lambda _: (
                        STATE.draft.__setitem__("_legal_back", settings_route("privacy")),
                        STATE.go("/legal"),
                    ),
                ),
                theme.action_button("Записать согласие", _accept_terms, primary=True, width=220)
                if not user.terms_accepted
                else ft.Container(height=0),
                ft.Text(
                    "Удалять аккаунт, если не заходить",
                    size=16,
                    weight=ft.FontWeight.W_600,
                    color=theme.INK,
                    font_family=theme.FONT_FAMILY,
                ),
                ft.Text(
                    "От 3 месяцев до 2 лет. Если не открывать приложение дольше, аккаунт удалится при следующем запуске.",
                    size=14,
                    color=theme.MUTED,
                    font_family=theme.FONT_FAMILY,
                ),
                idle_chips,
                theme.pressable(
                    ft.Container(
                        height=48,
                        border_radius=16,
                        bgcolor="#C4475A",
                        alignment=ft.Alignment.CENTER,
                        content=ft.Text(
                            "Удалить аккаунт",
                            size=16,
                            weight=ft.FontWeight.W_700,
                            color="#FFFBFF",
                            font_family=theme.FONT_FAMILY,
                        ),
                    ),
                    lambda _: _confirm_delete_account(page),
                ),
            ],
        )
    )

    return ft.Column(
        spacing=14,
        tight=True,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        controls=[
            _section_label(t("home.default_profile")),
            visibility,
            _section_label(t("privacy.section_search")),
            discovery,
            _section_label(t("privacy.section_messages")),
            messaging,
            _section_label(t("privacy.section_activity")),
            signals,
            _section_label("Аккаунт"),
            account_card,
        ],
    )


def _page_blacklist(page: ft.Page) -> ft.Control:
    from core import blacklist as bl

    user = STATE.user
    if user is None:
        return _placeholder("blacklist", t("blacklist.login_required"))

    owner = user.public_id
    items = bl.list_blocked(owner)

    if not items:
        return _card(
            ft.Column(
                spacing=8,
                tight=True,
                controls=[
                    ft.Text(
                        t("blacklist.empty"),
                        size=16,
                        weight=ft.FontWeight.W_600,
                        color=theme.INK,
                        font_family=theme.FONT_FAMILY,
                    ),
                    ft.Text(
                        t("blacklist.empty_hint"),
                        size=15,
                        color=theme.INK,
                        font_family=theme.FONT_FAMILY,
                    ),
                ],
            )
        )

    list_col = ft.Column(spacing=0, tight=True, controls=[])
    empty_hint = ft.Text(
        t("blacklist.empty"),
        size=16,
        weight=ft.FontWeight.W_600,
        color=theme.INK,
        font_family=theme.FONT_FAMILY,
        visible=False,
    )

    def _rebuild_rows() -> None:
        list_col.controls.clear()
        cur = bl.list_blocked(owner)
        if not cur:
            empty_hint.visible = True
            try:
                empty_hint.update()
                list_col.update()
            except Exception:
                pass
            return
        empty_hint.visible = False
        for i, entry in enumerate(cur):
            pid = entry["public_id"]
            name = entry["name"] or pid

            def _unblock(_e=None, target=pid, title=name):
                bl.unblock(owner, target)
                STATE.snack(t("common.unblocked", name=title))
                _rebuild_rows()

            list_col.controls.append(
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
                                        size=14,
                                        color=theme.INK,
                                        font_family=theme.FONT_FAMILY,
                                    ),
                                ],
                            ),
                            theme.action_button(
                                t("common.unblock"),
                                _unblock,
                                primary=True,
                                width=132,
                                height=40,
                            ),
                        ],
                    ),
                )
            )
            if i < len(cur) - 1:
                list_col.controls.append(_divider())
        try:
            empty_hint.update()
            list_col.update()
        except Exception:
            pass

    _rebuild_rows()

    return ft.Column(
        spacing=14,
        tight=True,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        controls=[
            _section_label(t("blacklist.section")),
            empty_hint,
            _card(list_col),
            ft.Text(
                t("blacklist.footer"),
                size=14,
                color=theme.INK,
                font_family=theme.FONT_FAMILY,
            ),
        ],
    )


def _page_logs(page: ft.Page) -> ft.Control:
    text = logs.tail(200)
    return _card(
        ft.Text(
            text or t("logs.empty"),
            size=11,
            color=theme.MUTED,
            selectable=True,
            font_family=theme.FONT_FAMILY,
        )
    )


_LANG_CODES: tuple[str, ...] = (
    "ru",
    "en",
    "kk",
    "be",
    "uk",
    "de",
    "fr",
    "es",
    "zh",
    "tr",
)


def _page_language(page: ft.Page) -> ft.Control:
    current = prefs.language()

    rows: list[ft.Control] = []
    for code in _LANG_CODES:
        native = t(f"lang.{code}")
        english = t(f"lang.{code}_hint")
        selected = code == current

        def _pick(_e=None, c=code):
            prefs.set_language(c)
            logs.info("prefs language=%s", c)
            name = t(f"lang.{c}")
            STATE.snack(t("lang.changed", name=name))
            STATE.draft["_home_tab"] = "settings"
            STATE.draft["_open_settings_after_lang"] = "language"
            STATE.go("/home")

        rows.append(
            ft.Container(
                ink=False,
                on_click=_pick,
                padding=ft.Padding.symmetric(vertical=12, horizontal=8),
                border_radius=14,
                bgcolor=theme.PRIMARY_SOFT if selected else None,
                content=ft.Stack(
                    controls=[
                        ft.Container(
                            alignment=ft.Alignment.CENTER,
                            content=ft.Column(
                                spacing=2,
                                tight=True,
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                controls=[
                                    ft.Text(
                                        native,
                                        size=16,
                                        weight=ft.FontWeight.W_600
                                        if selected
                                        else ft.FontWeight.W_500,
                                        color=theme.PRIMARY if selected else theme.INK,
                                        font_family=theme.FONT_FAMILY,
                                        text_align=ft.TextAlign.CENTER,
                                    ),
                                    ft.Text(
                                        english,
                                        size=14,
                                        color=theme.INK,
                                        font_family=theme.FONT_FAMILY,
                                        text_align=ft.TextAlign.CENTER,
                                    ),
                                ],
                            ),
                        ),
                        ft.Container(
                            right=4,
                            top=0,
                            bottom=0,
                            alignment=ft.Alignment.CENTER_RIGHT,
                            content=ft.Icon(
                                ft.Icons.CHECK_ROUNDED,
                                size=20,
                                color=theme.PRIMARY if selected else "#00000000",
                            ),
                        ),
                    ],
                ),
            )
        )

    return _card(
        ft.Column(
            spacing=6,
            tight=True,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Text(
                    t("lang.title"),
                    size=16,
                    weight=ft.FontWeight.W_600,
                    color=theme.INK,
                    font_family=theme.FONT_FAMILY,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Text(
                    t("lang.subtitle"),
                    size=15,
                    color=theme.INK,
                    font_family=theme.FONT_FAMILY,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Container(height=4),
                *rows,
            ],
        )
    )


def _fmt_bytes(n: int) -> str:
    if n < 1024:
        return t("common.bytes_b", n=n)
    if n < 1024 * 1024:
        return t("common.bytes_kb", n=f"{n / 1024:.1f}")
    return t("common.bytes_mb", n=f"{n / (1024 * 1024):.1f}")


def _dir_size_bytes(root: str) -> int:
    total = 0
    if not os.path.isdir(root):
        return 0
    for dirpath, _dirnames, filenames in os.walk(root):
        for fn in filenames:
            try:
                total += os.path.getsize(os.path.join(dirpath, fn))
            except OSError:
                pass
    return total


def _clear_image_cache() -> int:
    """Удалить файлы в каталогах кэша изображений; вернуть число удалённых."""
    removed = 0
    roots = [
        os.path.join(DATA_DIR, "avatars"),
        os.path.join(DATA_DIR, "cache"),
        os.path.join(DATA_DIR, "gallery"),
        UPLOADS_DIR,
    ]
    for root in roots:
        if not os.path.isdir(root):
            continue
        for dirpath, _dirnames, filenames in os.walk(root):
            for fn in filenames:
                path = os.path.join(dirpath, fn)
                try:
                    os.remove(path)
                    removed += 1
                except OSError:
                    pass
    return removed


def _action_row(label: str, *, on_click) -> ft.Control:
    row = ft.Container(
        border_radius=14,
        bgcolor=theme.FIELD_BG,
        padding=ft.Padding.symmetric(horizontal=14, vertical=12),
        content=ft.Row(
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Text(
                    label,
                    size=14,
                    color=theme.INK,
                    font_family=theme.FONT_FAMILY,
                    expand=True,
                ),
                ft.Icon(ft.Icons.CHEVRON_RIGHT, size=18, color=theme.MUTED),
            ],
        ),
    )
    return theme.pressable(row, on_click, scale_to=theme.PRESS_SCALE, expand=True)


def _page_data(page: ft.Page) -> ft.Control:
    cache_dirs = [
        os.path.join(DATA_DIR, "avatars"),
        os.path.join(DATA_DIR, "cache"),
        UPLOADS_DIR,
    ]
    cache_bytes = sum(_dir_size_bytes(p) for p in cache_dirs)
    size_lbl = ft.Text(
        t("data.cache_estimate", size=_fmt_bytes(cache_bytes)),
        size=15,
        weight=ft.FontWeight.W_600,
        color=theme.INK,
        font_family=theme.FONT_FAMILY,
    )

    def clear_cache(_e=None):
        n = _clear_image_cache()
        cache_bytes_new = sum(_dir_size_bytes(p) for p in cache_dirs)
        size_lbl.value = t("data.cache_estimate", size=_fmt_bytes(cache_bytes_new))
        STATE.snack(t("data.files_removed", n=n))
        try:
            size_lbl.update()
        except Exception:
            pass

    def clear_hist(_e=None):
        user = STATE.user
        if user is None:
            STATE.snack(t("data.login_clear_hist"))
            return
        search_history.clear(user.id)
        STATE.snack(t("data.search_hist_cleared"))

    def clear_drafts(_e=None):
        keys = [k for k in list(STATE.draft.keys()) if "draft" in k.lower() or k.startswith("_composer")]
        if not keys:
            STATE.snack(t("data.no_drafts"))
            return
        for k in keys:
            STATE.draft.pop(k, None)
        STATE.snack(t("data.drafts_cleared"))

    wifi_sw = ft.Switch(
        value=prefs.media_auto_download_wifi(), active_color=theme.PRIMARY
    )
    mobile_sw = ft.Switch(
        value=prefs.media_auto_download_mobile(), active_color=theme.PRIMARY
    )
    gallery_sw = ft.Switch(value=prefs.save_to_gallery(), active_color=theme.PRIMARY)
    logout_sw = ft.Switch(
        value=prefs.data_clear_on_logout(), active_color=theme.PRIMARY
    )
    cache_sw = ft.Switch(value=prefs.data_cache_images(), active_color=theme.PRIMARY)
    link_sw = ft.Switch(value=prefs.link_previews(), active_color=theme.PRIMARY)

    wifi_sw.on_change = lambda _e: prefs.set_media_auto_download_wifi(bool(wifi_sw.value))
    mobile_sw.on_change = lambda _e: prefs.set_media_auto_download_mobile(
        bool(mobile_sw.value)
    )
    gallery_sw.on_change = lambda _e: prefs.set_save_to_gallery(bool(gallery_sw.value))
    logout_sw.on_change = lambda _e: prefs.set_data_clear_on_logout(bool(logout_sw.value))
    cache_sw.on_change = lambda _e: prefs.set_data_cache_images(bool(cache_sw.value))
    link_sw.on_change = lambda _e: prefs.set_link_previews(bool(link_sw.value))

    storage_card = _card(
        ft.Column(
            spacing=10,
            tight=True,
            controls=[
                size_lbl,
                ft.Text(
                    t("data.cache_desc"),
                    size=14,
                    color=theme.INK,
                    font_family=theme.FONT_FAMILY,
                ),
                _action_row(t("data.clear_cache"), on_click=clear_cache),
                _action_row(t("data.clear_search"), on_click=clear_hist),
                _action_row(t("data.clear_drafts"), on_click=clear_drafts),
            ],
        )
    )

    media_card = _card(
        ft.Column(
            spacing=12,
            tight=True,
            controls=[
                _switch_row(
                    t("data.wifi_auto"),
                    wifi_sw,
                    hint=t("data.wifi_auto_hint"),
                ),
                _divider(),
                _switch_row(
                    t("data.mobile_auto"),
                    mobile_sw,
                    hint=t("data.mobile_auto_hint"),
                ),
                _divider(),
                _switch_row(
                    t("data.cache_images"),
                    cache_sw,
                    hint=t("data.cache_images_hint"),
                ),
                _divider(),
                _switch_row(
                    t("data.save_gallery"),
                    gallery_sw,
                    hint=t("data.save_gallery_hint"),
                ),
            ],
        )
    )

    other_card = _card(
        ft.Column(
            spacing=12,
            tight=True,
            controls=[
                _switch_row(
                    t("data.clear_on_logout"),
                    logout_sw,
                    hint=t("data.clear_on_logout_hint"),
                ),
                _divider(),
                _switch_row(
                    t("data.link_previews"),
                    link_sw,
                    hint=t("data.link_previews_hint"),
                ),
            ],
        )
    )

    swipe_sw = ft.Switch(value=prefs.swipe_to_reply(), active_color=theme.PRIMARY)
    like_sw = ft.Switch(
        value=prefs.double_tap_like_react(), active_color=theme.PRIMARY
    )
    swipe_sw.on_change = lambda _e: prefs.set_swipe_to_reply(bool(swipe_sw.value))
    like_sw.on_change = lambda _e: prefs.set_double_tap_like_react(bool(like_sw.value))

    chat_controls: list[ft.Control] = [
        _switch_row(
            t("data.swipe_reply"),
            swipe_sw,
            hint=t("data.swipe_reply_hint"),
        ),
        _divider(),
        _switch_row(
            t("data.double_tap_like"),
            like_sw,
            hint=t("data.double_tap_hint"),
        ),
    ]
    # Enter / Ctrl+Enter — клавиатурные опции ПК; на телефоне Enter не шлёт
    if not _on_phone():
        enter_sw = ft.Switch(
            value=prefs.chat_enter_to_send(), active_color=theme.PRIMARY
        )
        ctrl_enter_sw = ft.Switch(
            value=prefs.chat_send_by_ctrl_enter(), active_color=theme.PRIMARY
        )
        enter_sw.on_change = lambda _e: prefs.set_chat_enter_to_send(bool(enter_sw.value))
        ctrl_enter_sw.on_change = lambda _e: prefs.set_chat_send_by_ctrl_enter(
            bool(ctrl_enter_sw.value)
        )
        chat_controls = [
            _switch_row(
                t("data.enter_sends"),
                enter_sw,
                hint=t("data.enter_sends_hint"),
            ),
            _divider(),
            _switch_row(
                t("data.ctrl_enter"),
                ctrl_enter_sw,
                hint=t("data.ctrl_enter_hint"),
            ),
            _divider(),
            *chat_controls,
        ]

    chat_card = _card(
        ft.Column(
            spacing=12,
            tight=True,
            controls=chat_controls,
        )
    )

    return ft.Column(
        spacing=14,
        tight=True,
        controls=[
            _section_label(t("data.section_storage")),
            storage_card,
            _section_label(t("data.section_media")),
            media_card,
            _section_label(t("data.section_chat")),
            chat_card,
            _section_label(t("data.section_other")),
            other_card,
        ],
    )


def _tip_card(title: str, body: str) -> ft.Control:
    return _card(
        ft.Column(
            spacing=8,
            tight=True,
            controls=[
                ft.Text(
                    title,
                    size=16,
                    weight=ft.FontWeight.W_600,
                    color=theme.INK,
                    font_family=theme.FONT_FAMILY,
                ),
                ft.Text(
                    body,
                    size=14,
                    color=theme.MUTED,
                    font_family=theme.FONT_FAMILY,
                ),
            ],
        )
    )


def _page_tips(_page: ft.Page) -> ft.Control:
    tips = [
        (t("tips.back_title"), t("tips.back_body")),
        (t("tips.questions_title"), t("tips.questions_body")),
        (t("tips.fav_title"), t("tips.fav_body")),
        (t("tips.privacy_title"), t("tips.privacy_body")),
        (t("tips.offline_title"), t("tips.offline_body")),
        (t("tips.lang_title"), t("tips.lang_body")),
        (t("tips.theme_title"), t("tips.theme_body")),
    ]
    return ft.Column(
        spacing=12,
        tight=True,
        controls=[_tip_card(title, body) for title, body in tips],
    )


def _page_help(page: ft.Page) -> ft.Control:
    support_email = "help@raisehand.app"

    def _copy(text: str, msg: str):
        def _inner(_e=None):
            try:
                page.set_clipboard(text)
            except Exception:
                pass
            STATE.snack(msg)

        return _inner

    def _open_report(_e=None):
        if STATE.user is None:
            STATE.snack(t("help.report_login"))
            return
        STATE.snack(t("help.report_hint"))

    return ft.Column(
        spacing=14,
        tight=True,
        controls=[
            _card(
                ft.Column(
                    spacing=10,
                    tight=True,
                    controls=[
                        ft.Text(
                            t("help.support_title"),
                            size=16,
                            weight=ft.FontWeight.W_600,
                            color=theme.INK,
                            font_family=theme.FONT_FAMILY,
                        ),
                        ft.Text(
                            t("help.about"),
                            size=14,
                            color=theme.MUTED,
                            font_family=theme.FONT_FAMILY,
                        ),
                        _action_row(
                            t("help.write_email", email=support_email),
                            on_click=_copy(support_email, t("help.email_copied")),
                        ),
                    ],
                )
            ),
            _card(
                ft.Column(
                    spacing=10,
                    tight=True,
                    controls=[
                        ft.Text(
                            t("help.actions_title"),
                            size=16,
                            weight=ft.FontWeight.W_600,
                            color=theme.INK,
                            font_family=theme.FONT_FAMILY,
                        ),
                        _action_row(
                            t("help.class_code_q"),
                            on_click=_copy(
                                t("help.class_code_a"),
                                t("help.class_code_copied"),
                            ),
                        ),
                        _action_row(
                            t("help.report_user"),
                            on_click=_open_report,
                        ),
                        _action_row(
                            t("help.privacy_policy"),
                            on_click=lambda _: (
                                STATE.draft.__setitem__("_legal_back", settings_route("help")),
                                STATE.go("/legal"),
                            ),
                        ),
                        _action_row(
                            "Удалить аккаунт",
                            on_click=lambda _: _confirm_delete_account(page),
                        ),
                    ],
                )
            ),
        ],
    )


def _page_faq(_page: ft.Page) -> ft.Control:
    pairs = [(t(f"faq.q{i}"), t(f"faq.a{i}")) for i in range(1, 11)]
    open_state: dict[int, bool] = {}

    rows: list[ft.Control] = []
    for i, (q, a) in enumerate(pairs):
        ans = ft.Text(
            a,
            size=15,
            color=theme.INK,
            font_family=theme.FONT_FAMILY,
            visible=bool(open_state.get(i, False)),
        )

        def _toggle(_e=None, idx=i, answer=ans):
            open_state[idx] = not open_state.get(idx, False)
            answer.visible = open_state[idx]
            try:
                answer.update()
            except Exception:
                STATE.draft["_settings_no_anim"] = True
                STATE.go(settings_route("faq"))

        rows.append(
            ft.Container(
                ink=True,
                on_click=_toggle,
                padding=ft.Padding.symmetric(vertical=12, horizontal=4),
                border_radius=12,
                content=ft.Column(
                    spacing=6,
                    tight=True,
                    controls=[
                        ft.Row(
                            spacing=8,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                ft.Text(
                                    q,
                                    size=15,
                                    weight=ft.FontWeight.W_600,
                                    color=theme.INK,
                                    font_family=theme.FONT_FAMILY,
                                    expand=True,
                                ),
                                ft.Icon(
                                    ft.Icons.EXPAND_MORE,
                                    size=22,
                                    color=theme.MUTED,
                                ),
                            ],
                        ),
                        ans,
                    ],
                ),
            )
        )
        if i < len(pairs) - 1:
            rows.append(_divider())

    return _card(ft.Column(spacing=4, tight=True, controls=rows))


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
    "data": _page_data,
    "tips": _page_tips,
    "help": _page_help,
    "faq": _page_faq,
}


def build(page: ft.Page, key: str) -> ft.Control:
    """Собрать экран пункта настроек. Заготовки — в _placeholder."""
    key = (key or "").strip() or "profile"
    if key not in SETTINGS_PAGE_KEYS:
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
    for key in SETTINGS_PAGE_KEYS:

        def _make(k: str):
            return lambda page, _k=k: build(page, _k)

        out[settings_route(key)] = _make(key)
    return out
