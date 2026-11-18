# -*- coding: utf-8 -*-
"""Профиль контакта: локальное имя, описание, медиа, сообщения, общие чаты."""
from __future__ import annotations

from typing import Optional

import flet as ft

from core import gradients
from flet_app import chat_data, liquid_glass, mono_icons, theme
from flet_app.app_state import STATE


def contact_route(cid: str) -> str:
    return f"/contact/{cid}"


def _back_to_chat(_=None):
    cid = STATE.draft.get("_profile_contact_id") or STATE.draft.get("_open_chat_id")
    if cid:
        STATE.draft["_open_chat_id"] = cid
        STATE.draft["_open_is_group"] = False
    STATE.go("/chat")


def _card(content: ft.Control, *, padding: Optional[ft.Padding] = None) -> ft.Control:
    # Фиксированная ширина = ListView (PHONE_WIDTH − padding 16+16),
    # иначе короткий текст (пустые фото) сжимает glass в «пилюлю».
    card_w = float(theme.PHONE_WIDTH - 32)
    return ft.Container(
        alignment=ft.Alignment.CENTER_LEFT,
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


def _enter_wrap(child: ft.Control, *, delay_ms: int = 0) -> ft.Container:
    """Секция: мягкий fade (без scale — иначе полосы по бокам)."""
    return ft.Container(
        alignment=ft.Alignment.CENTER_LEFT,
        content=child,
        opacity=0,
        offset=ft.Offset(0, 0.02),
        animate_opacity=ft.Animation(260, ft.AnimationCurve.EASE_OUT),
        animate_offset=ft.Animation(280, ft.AnimationCurve.EASE_OUT),
        data={"delay": delay_ms},
    )


def _section_title(text: str) -> ft.Control:
    return ft.Text(
        text,
        size=13,
        weight=ft.FontWeight.W_600,
        color=theme.MUTED,
        font_family=theme.FONT_FAMILY,
    )


def _peer_public_id(contact: chat_data.Contact) -> str:
    cid = str(contact.id or "")
    if cid.startswith("u:"):
        return cid[2:]
    return (contact.seed or "").strip()


def _avatar(contact: chat_data.Contact, size: float = 88) -> ft.Control:
    from core import privacy as priv

    pid = _peer_public_id(contact)
    if pid and priv.for_user(pid).get("hide_avatar"):
        return ft.Container(
            width=size,
            height=size,
            border_radius=size / 2,
            bgcolor=theme.FIELD_BG,
            alignment=ft.Alignment.CENTER,
            border=ft.Border.all(1, theme.STROKE),
            content=ft.Icon(ft.Icons.PERSON_OUTLINE, size=size * 0.42, color=theme.MUTED),
        )
    colors = gradients.colors_for(contact.seed)
    top = "#%02X%02X%02X" % colors["top"]
    bottom = "#%02X%02X%02X" % colors["bottom"]
    initials = gradients.initials_for(contact.first, contact.last)
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


def _header_bar(title: str) -> ft.Control:
    back = liquid_glass.glass_circle_button(
        _back_to_chat,
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


def _edit_name_dialog(page: ft.Page, contact: chat_data.Contact, name_text: ft.Text):
    field = ft.TextField(
        value=contact.display_name,
        label="Имя контакта",
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
        name_text.value = contact.display_name
        try:
            name_text.update()
        except Exception:
            pass
        close()

    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Text(
            "Изменить имя",
            color=theme.INK,
            font_family=theme.FONT_FAMILY,
        ),
        bgcolor=theme.CARD,
        content=ft.Column(
            tight=True,
            spacing=8,
            controls=[
                field,
                ft.Text(
                    "Имя видно только вам. Описание контакта не меняется.",
                    size=12,
                    color=theme.MUTED,
                ),
            ],
        ),
        actions=[
            ft.TextButton("Отмена", on_click=close),
            ft.TextButton("Сохранить", on_click=save),
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
            STATE.error("Не удалось открыть форму")


def _media_grid(contact: chat_data.Contact) -> ft.Control:
    media = chat_data.media_messages(contact.id)
    if not media:
        return _card(
            ft.Text(
                "Пока нет фото в этом чате",
                size=14,
                color=theme.MUTED,
                font_family=theme.FONT_FAMILY,
            )
        )
    cells: list[ft.Control] = []
    for m in media[:12]:
        src = m.image or ""
        if theme._image_exists(src):
            body: ft.Control = ft.Image(
                src=src, width=104, height=104, fit=ft.BoxFit.COVER
            )
        else:
            body = ft.Container(
                width=104,
                height=104,
                bgcolor=theme.FIELD_BG,
                alignment=ft.Alignment.CENTER,
                content=ft.Icon(ft.Icons.IMAGE_OUTLINED, color=theme.MUTED, size=28),
            )
        cells.append(
            ft.Container(
                width=104,
                height=104,
                border_radius=14,
                clip_behavior=ft.ClipBehavior.HARD_EDGE,
                content=body,
            )
        )
    return _card(
        ft.Column(
            spacing=10,
            tight=True,
            controls=[
                _section_title(f"Фото · {len(media)}"),
                ft.Row(wrap=True, spacing=8, run_spacing=8, controls=cells),
            ],
        )
    )


def _messages_block(contact: chat_data.Contact) -> ft.Control:
    msgs = chat_data.text_messages(contact.id, limit=8)
    if not msgs:
        return _card(
            ft.Text("Нет сообщений", size=14, color=theme.MUTED, font_family=theme.FONT_FAMILY)
        )

    def open_chat(_=None):
        STATE.draft["_open_chat_id"] = contact.id
        STATE.draft["_open_is_group"] = False
        STATE.go("/chat")

    rows: list[ft.Control] = []
    for m in msgs:
        who = "Вы" if m.mine else contact.first
        preview = "Фото" if m.image and not m.text else (m.text or "").replace("\n", " ")
        preview = preview[:56] + ("…" if len(preview) > 56 else "")
        rows.append(
            ft.Container(
                padding=ft.Padding.symmetric(vertical=6),
                content=ft.Row(
                    spacing=8,
                    controls=[
                        ft.Text(
                            who,
                            size=13,
                            weight=ft.FontWeight.W_600,
                            color=theme.PRIMARY if m.mine else theme.INK,
                            width=48,
                        ),
                        ft.Text(
                            preview,
                            size=13,
                            color=theme.INK,
                            expand=True,
                            max_lines=1,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                        ft.Text(m.time, size=12, color=theme.MUTED),
                    ],
                ),
            )
        )

    return _card(
        ft.Column(
            spacing=4,
            tight=True,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        _section_title("Сообщения"),
                        ft.TextButton(
                            "Открыть чат",
                            style=ft.ButtonStyle(color=theme.PRIMARY, padding=0),
                            on_click=open_chat,
                        ),
                    ],
                ),
                *rows,
            ],
        )
    )


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
                    _avatar(contact, size=40),
                    ft.Column(
                        spacing=0,
                        tight=True,
                        expand=True,
                        controls=[
                            ft.Text(
                                "Личный чат",
                                size=15,
                                weight=ft.FontWeight.W_600,
                                color=theme.INK,
                            ),
                            ft.Text(
                                contact.status or "",
                                size=12,
                                color=theme.MUTED,
                            ),
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

    body_controls: list[ft.Control] = [_section_title("Чаты с этим человеком"), *rows]
    if hide_groups:
        body_controls.append(
            ft.Container(
                padding=ft.Padding.symmetric(vertical=8),
                content=ft.Text(
                    "Общие группы скрыты настройками конфиденциальности",
                    size=13,
                    color=theme.MUTED,
                    font_family=theme.FONT_FAMILY,
                ),
            )
        )
    return _card(
        ft.Column(
            spacing=0,
            tight=True,
            controls=body_controls,
        )
    )


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
                    ft.Text("Контакт не найден", size=18, color=theme.INK),
                    ft.TextButton("Назад", on_click=lambda _: STATE.go("/home")),
                ]
            ),
        )

    STATE.draft["_profile_contact_id"] = contact.id
    name_text = ft.Text(
        contact.display_name,
        size=22,
        weight=ft.FontWeight.W_700,
        color=theme.INK,
        font_family=theme.FONT_FAMILY,
        max_lines=2,
        overflow=ft.TextOverflow.ELLIPSIS,
    )

    name_row = ft.Container(
        ink=True,
        on_click=lambda _: _edit_name_dialog(page, contact, name_text),
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

    from core import auth, privacy as priv

    peer_pid = _peer_public_id(contact)
    pset = priv.for_user(peer_pid) if peer_pid else {}
    status_text = priv.status_for_others(peer_pid, contact.status or "") if peer_pid else (contact.status or "")

    phone_line: ft.Control | None = None
    if peer_pid:
        peer_user = auth.find_by_public_id(peer_pid)
        if peer_user is not None and (peer_user.contact_value or "").strip():
            if pset.get("hide_phone"):
                phone_line = ft.Text(
                    "Номер скрыт",
                    size=13,
                    color=theme.MUTED,
                    font_family=theme.FONT_FAMILY,
                )
            else:
                phone_line = ft.Text(
                    str(peer_user.contact_value).strip(),
                    size=13,
                    color=theme.INK,
                    font_family=theme.FONT_FAMILY,
                )

    bio = (contact.bio or "").strip() or "Пользователь ещё не добавил описание"
    head_controls: list[ft.Control] = [
        _avatar(contact, size=96),
        name_row,
        ft.Text(
            status_text,
            size=13,
            color=theme.MUTED,
            font_family=theme.FONT_FAMILY,
        ),
    ]
    if phone_line is not None:
        head_controls.append(phone_line)
    head_controls.append(
        ft.Container(
            padding=ft.Padding.only(top=4),
            content=ft.Column(
                spacing=4,
                tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.START,
                controls=[
                    _section_title("О себе"),
                    ft.Text(
                        bio,
                        size=15,
                        color=theme.INK,
                        font_family=theme.FONT_FAMILY,
                    ),
                ],
            ),
        )
    )
    profile_head = _card(
        ft.Column(
            spacing=12,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            tight=True,
            controls=head_controls,
        ),
        padding=ft.Padding.symmetric(horizontal=20, vertical=20),
    )

    sections = [
        _enter_wrap(profile_head, delay_ms=40),
        _enter_wrap(_media_grid(contact), delay_ms=110),
        _enter_wrap(_messages_block(contact), delay_ms=180),
        _enter_wrap(_shared_chats(contact), delay_ms=250),
    ]

    # ListView на всю ширину — как в настройках: без центрирования «столбиком»
    scroller = ft.ListView(
        expand=True,
        spacing=12,
        padding=ft.Padding.only(left=16, right=16, top=8, bottom=28),
        controls=sections,
    )

    header = _header_bar("Профиль")
    header_wrap = ft.Container(
        content=header,
        opacity=0,
        animate_opacity=ft.Animation(220, ft.AnimationCurve.EASE_OUT),
    )

    root = ft.Container(
        expand=True,
        bgcolor=theme.BG,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        content=ft.Column(
            expand=True,
            spacing=0,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[
                ft.Container(height=36, bgcolor=theme.BG),
                header_wrap,
                scroller,
            ],
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
            await asyncio.sleep(0.035)
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

    return root


def register_routes() -> dict:
    """/contact/{id} и запасной /contact."""

    def _by_draft(page: ft.Page) -> ft.Control:
        return build_contact_profile(page, STATE.draft.get("_profile_contact_id") or "")

    out = {"/contact": _by_draft}
    # заранее известные демо-id + динамический разбор в main
    for c in chat_data.CONTACTS:
        cid = c.id

        def _make(i: str):
            return lambda page, _i=i: build_contact_profile(page, _i)

        out[contact_route(cid)] = _make(cid)
    return out
