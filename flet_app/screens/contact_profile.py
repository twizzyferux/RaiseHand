# -*- coding: utf-8 -*-
"""Профиль контакта — Telegram-style layout."""
from __future__ import annotations

import flet as ft

from core import gradients
from core.i18n import t
from flet_app import chat_data, liquid_glass, theme
from flet_app.app_state import STATE
from flet_app.profile_ui import (
    actions_row,
    info_card,
    media_cells_from_messages,
    media_tabs_block,
    profile_avatar_from_seed,
    profile_head_block,
    profile_shell,
)


def contact_route(cid: str) -> str:
    return f"/contact/{cid}"


def _back_to_chat(_=None):
    cid = STATE.draft.get("_profile_contact_id") or STATE.draft.get("_open_chat_id")
    if cid:
        STATE.draft["_open_chat_id"] = cid
        STATE.draft["_open_is_group"] = False
    STATE.go("/chat")


def _peer_public_id(contact: chat_data.Contact) -> str:
    cid = str(contact.id or "")
    if cid.startswith("u:"):
        return cid[2:]
    return (contact.seed or "").strip()


def _secondary_card(title: str, body_controls: list[ft.Control]) -> ft.Control:
    card_w = float(theme.PHONE_WIDTH - 32)
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
            spacing=8,
            tight=True,
            controls=[
                ft.Text(
                    title,
                    size=13,
                    weight=ft.FontWeight.W_600,
                    color=theme.MUTED,
                    font_family=theme.FONT_FAMILY,
                ),
                *body_controls,
            ],
        ),
    )


def _edit_name_dialog(page: ft.Page, contact: chat_data.Contact, name_ref: ft.Text | None = None):
    field = ft.TextField(
        value=contact.display_name,
        label=t("profile.contact_name"),
        filled=True,
        bgcolor=theme.FIELD_BG,
        color=theme.INK,
        border=theme.field_border(16, color=theme.STROKE, focused_color=theme.PRIMARY),
        cursor_color=theme.PRIMARY,
        text_style=ft.TextStyle(font_family=theme.FONT_FAMILY, color=theme.INK),
        label_style=ft.TextStyle(color=theme.MUTED, font_family=theme.FONT_FAMILY),
    )

    def close(_=None):
        try:
            page.pop_dialog()
            return
        except Exception:
            pass
        try:
            dlg.open = False
            page.update()
        except Exception:
            pass

    def save(_=None):
        chat_data.set_contact_local_name(contact.id, field.value or "")
        if name_ref is not None:
            name_ref.value = contact.display_name
            try:
                name_ref.update()
            except Exception:
                pass
        close()
        STATE.draft["_profile_reload"] = True
        STATE.go(contact_route(contact.id))

    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Text(t("contact.rename_title"), color=theme.INK, font_family=theme.FONT_FAMILY),
        bgcolor=theme.CARD,
        content=ft.Column(
            tight=True,
            spacing=8,
            controls=[
                field,
                ft.Text(
                    t("contact.rename_hint"),
                    size=12,
                    color=theme.MUTED,
                ),
            ],
        ),
        actions=[
            ft.TextButton(t("common.cancel"), on_click=close),
            ft.TextButton(t("common.save"), on_click=save),
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
            STATE.error(t("common.dialog_open_failed"))


def _shared_chats(contact: chat_data.Contact) -> ft.Control:
    from core import privacy as priv

    pid = _peer_public_id(contact)
    hide_groups = bool(pid and priv.for_user(pid).get("hide_groups"))
    groups = [] if hide_groups else chat_data.shared_groups_for(contact)

    def _open_dm(_e=None, cid=contact.id):
        STATE.draft["_open_chat_id"] = cid
        STATE.draft["_open_is_group"] = False
        STATE.go("/chat")

    rows: list[ft.Control] = [
        ft.Container(
            ink=True,
            on_click=_open_dm,
            padding=ft.Padding.symmetric(vertical=10),
            content=ft.Row(
                spacing=12,
                controls=[
                    profile_avatar_from_seed(
                        contact.seed, contact.first, contact.last, size=40, hide=bool(
                            pid and priv.for_user(pid).get("hide_avatar")
                        ),
                    ),
                    ft.Column(
                        spacing=0,
                        tight=True,
                        expand=True,
                        controls=[
                            ft.Text(
                                t("contact.dm_chat"),
                                size=15,
                                weight=ft.FontWeight.W_600,
                                color=theme.INK,
                            ),
                            ft.Text(contact.status or "", size=12, color=theme.MUTED),
                        ],
                    ),
                    ft.Icon(ft.Icons.CHEVRON_RIGHT, color=theme.MUTED, size=20),
                ],
            ),
        )
    ]

    for g in groups:
        colors = gradients.colors_for(g.seed)
        top = "#%02X%02X%02X" % colors["top"]
        bottom = "#%02X%02X%02X" % colors["bottom"]

        def _open_group(_e=None, gid=g.id):
            STATE.draft["_open_chat_id"] = gid
            STATE.draft["_open_is_group"] = True
            STATE.go("/chat")

        rows.append(
            ft.Container(
                ink=True,
                on_click=_open_group,
                padding=ft.Padding.symmetric(vertical=10),
                content=ft.Row(
                    spacing=12,
                    controls=[
                        ft.Container(
                            width=40,
                            height=40,
                            border_radius=12,
                            gradient=ft.LinearGradient(
                                begin=ft.Alignment(0, -1),
                                end=ft.Alignment(0, 1),
                                colors=[top, bottom],
                            ),
                            alignment=ft.Alignment.CENTER,
                            content=ft.Text(
                                (g.name[:1] or "?").upper(),
                                size=16,
                                weight=ft.FontWeight.W_700,
                                color="#FFFFFF",
                            ),
                        ),
                        ft.Column(
                            spacing=0,
                            tight=True,
                            expand=True,
                            controls=[
                                ft.Text(
                                    g.name,
                                    size=15,
                                    weight=ft.FontWeight.W_600,
                                    color=theme.INK,
                                ),
                                ft.Text(
                                    f"{g.members} уч. · общий чат",
                                    size=12,
                                    color=theme.MUTED,
                                ),
                            ],
                        ),
                        ft.Icon(ft.Icons.CHEVRON_RIGHT, color=theme.MUTED, size=20),
                    ],
                ),
            )
        )

    if hide_groups:
        rows.append(
            ft.Text(
                t("contact.groups_hidden"),
                size=13,
                color=theme.MUTED,
                font_family=theme.FONT_FAMILY,
            )
        )
    return _secondary_card(t("contact.shared_chats"), rows)


def build_contact_profile(page: ft.Page, cid: str = "") -> ft.Control:
    cid = (cid or STATE.draft.get("_profile_contact_id") or "").strip()
    contact = chat_data.get_contact(cid) if cid else None
    if contact is None:
        return ft.Container(
            expand=True,
            bgcolor=theme.BG,
            padding=24,
            content=ft.Column(
                controls=[
                    ft.Text(t("contact.not_found"), size=18, color=theme.INK),
                    ft.TextButton(t("common.back"), on_click=lambda _: STATE.go("/home")),
                ]
            ),
        )

    STATE.draft.pop("_profile_reload", None)
    STATE.draft["_profile_contact_id"] = contact.id

    from core import auth, privacy as priv

    peer_pid = _peer_public_id(contact)
    pset = priv.for_user(peer_pid) if peer_pid else {}
    hide_avatar = bool(peer_pid and pset.get("hide_avatar"))
    status_text = (
        priv.status_for_others(peer_pid, contact.status or "") if peer_pid else (contact.status or "")
    )

    name_text = ft.Text(
        contact.display_name,
        size=24,
        weight=ft.FontWeight.W_700,
        color=theme.INK,
        font_family=theme.FONT_FAMILY,
        text_align=ft.TextAlign.CENTER,
        max_lines=2,
        overflow=ft.TextOverflow.ELLIPSIS,
    )

    def edit_name(_e=None):
        _edit_name_dialog(page, contact, name_text)

    avatar = profile_avatar_from_seed(
        contact.seed,
        contact.first,
        contact.last,
        size=120,
        hide=hide_avatar,
    )

    def open_chat(_e=None):
        STATE.draft["_open_chat_id"] = contact.id
        STATE.draft["_open_is_group"] = False
        STATE.go("/chat")

    muted = chat_data.is_muted(contact.id)

    def toggle_mute(_e=None):
        chat_data.toggle_mute(contact.id)
        STATE.snack(t("contact.notif_on") if muted else t("contact.muted"))
        STATE.go(contact_route(contact.id))

    def search_soon(_e=None):
        STATE.snack(t("contact.search_soon"))

    def open_report(_e=None):
        from flet_app.screens.report import report_route

        pid = peer_pid or contact.seed
        STATE.draft["_report_target_pid"] = pid
        STATE.draft["_report_target_name"] = contact.display_name
        STATE.draft["_report_chat_id"] = str(contact.id)
        STATE.draft["_report_msg_id"] = ""
        STATE.draft["_report_back"] = contact_route(contact.id)
        STATE.go(report_route())

    def more_menu(_e=None):
        open_report()

    mute_label = t("contact.sound") if muted else t("notif.tone_none")
    mute_icon = ft.Icons.NOTIFICATIONS_OFF_OUTLINED if not muted else ft.Icons.NOTIFICATIONS_OUTLINED

    action_items = [
        (ft.Icons.CHAT_BUBBLE_OUTLINED, t("appearance.section_chat"), open_chat),
        (mute_icon, mute_label, toggle_mute),
        (ft.Icons.SEARCH, t("privacy.section_search"), search_soon),
        ("more", t("profile.more"), more_menu),
    ]

    info_rows: list[tuple[str, str, object | None]] = []

    peer_user = auth.find_by_public_id(peer_pid) if peer_pid else None
    if peer_user is not None and (peer_user.contact_value or "").strip():
        if pset.get("hide_phone"):
            info_rows.append((t("contact.phone"), t("contact.hidden"), None))
        else:
            info_rows.append((t("contact.phone"), str(peer_user.contact_value).strip(), None))

    if peer_user is not None and (peer_user.nickname or "").strip():
        info_rows.append((t("contact.username"), f"@{peer_user.nickname.strip()}", None))

    if peer_pid:
        info_rows.append(("ID", peer_pid, None))

    bio = (contact.bio or "").strip() or t("contact.no_bio")
    info_rows.append((t("profile.about"), bio, None))

    media = chat_data.media_messages(contact.id)
    media_block = media_tabs_block(
        media_cells_from_messages(media),
        empty_text=t("contact.no_photos"),
    )

    head = profile_head_block(
        avatar=avatar,
        display_name=name_text,
        status_line=status_text,
        name_on_click=edit_name,
    )

    body = [
        ft.Container(alignment=ft.Alignment.CENTER, content=head),
        ft.Container(alignment=ft.Alignment.CENTER, content=actions_row(action_items)),
        ft.Container(alignment=ft.Alignment.CENTER, content=info_card(info_rows)),
        ft.Container(alignment=ft.Alignment.CENTER, content=media_block),
        ft.Container(alignment=ft.Alignment.CENTER, content=_shared_chats(contact)),
    ]

    return profile_shell(
        page,
        title=t("home.default_profile"),
        on_back=_back_to_chat,
        body_controls=body,
        edge_swipe=True,
    )


def register_routes() -> dict:
    """/contact/{id} и запасной /contact."""

    def _by_draft(page: ft.Page) -> ft.Control:
        return build_contact_profile(page, STATE.draft.get("_profile_contact_id") or "")

    out = {"/contact": _by_draft}
    for c in chat_data.CONTACTS:
        cid = c.id

        def _make(i: str):
            return lambda page, _i=i: build_contact_profile(page, _i)

        out[contact_route(cid)] = _make(cid)
    return out