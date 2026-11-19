# -*- coding: utf-8 -*-
"""Экран переписки: pubsub, меню сообщений, файлы, оффлайн, пагинация, звук."""
from __future__ import annotations

import os
from typing import Optional

import flet as ft

from core import gradients, logs, offline_outbox, push, rate_limit, sounds, uploads
from flet_app import chat_data
from flet_app import liquid_glass
from flet_app import mono_icons
from flet_app.app_state import STATE
from flet_app import theme

# Бренд RaiseHand: исходящие primary, входящие мягкий surface
STATUS_MUTED = "#8A8A8E"
PAGE_SIZE = 30
TOPIC_CHAT = "raisehand.chat"

# Контекстное меню RaiseHand (компактное, под сообщением)
MENU_RADIUS = 14
MENU_DANGER = "#E11D48"


def _approx_bubble_width(msg: chat_data.Message) -> float:
    """Ширина пузыря — панель меню делается такой же."""
    max_w = float(theme.PHONE_WIDTH) * 0.72
    if msg.image and theme._image_exists(msg.image) and not msg.deleted:
        return min(208.0, max_w)
    text = msg.text or ""
    if msg.deleted:
        text = "удалено"
    if "\n" in text or len(text) > 36:
        return max_w
    # текст + время в одной строке
    est = 28.0 + max(len(text), 1) * 8.0 + 46.0
    return float(min(max_w, max(128.0, est)))


def _approx_bubble_height(msg: chat_data.Message) -> float:
    if msg.image and theme._image_exists(msg.image) and not msg.deleted:
        return 168.0
    text = msg.text or ""
    if "\n" in text or len(text) > 36:
        lines = text.count("\n") + 1
        wrap = max(lines, len(text) // 32 + 1)
        return float(18 + wrap * 20 + 12)
    return 42.0


def _menu_bg() -> str:
    return liquid_glass.white_glass_tint()


def _menu_item_bg() -> str:
    return theme.PRIMARY_SOFT if theme.is_dark() else "#F5F3FF"


def _sprite(*parts: str) -> str:
    return theme.asset("assets", "images", *parts)


def _status_icon(kind: str) -> str:
    return _sprite("chats", f"status_{kind}.png")


def _avatar_circle(seed: str, first: str, last: str, size: float = 40) -> ft.Control:
    if seed == "favorites":
        return ft.Container(
            width=size,
            height=size,
            border_radius=size / 2,
            bgcolor=theme.PRIMARY,
            alignment=ft.Alignment.CENTER,
            content=ft.Icon(
                ft.Icons.BOOKMARK_ROUNDED,
                size=max(16, int(size * 0.45)),
                color="#FFFFFF",
            ),
        )
    initials = gradients.initials_for(first, last)
    colors = gradients.colors_for(seed)
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
            size=int(size * 0.30),
            weight=ft.FontWeight.W_600,
            color="#FFFFFF",
            font_family=theme.FONT_FAMILY,
        ),
    )


def _date_chip(label: str) -> ft.Control:
    return ft.Container(
        alignment=ft.Alignment.CENTER,
        padding=ft.Padding.symmetric(vertical=12),
        content=ft.Container(
            bgcolor=theme.DATE_CHIP,
            border_radius=14,
            padding=ft.Padding.symmetric(horizontal=14, vertical=5),
            content=ft.Text(label, size=12, color=STATUS_MUTED, font_family=theme.FONT_FAMILY),
        ),
    )


def _bubble_ticks(msg: chat_data.Message) -> Optional[ft.Control]:
    """Галочки на своём сообщении — mono status (onviolet/white)."""
    if not msg.mine or msg.deleted:
        return None
    if msg.pending:
        img = mono_icons.status_image("sending", size=13, on_bubble=True)
        return img or ft.Icon(ft.Icons.SCHEDULE, size=13, color="#FFFFFF99")
        kind = "read" if msg.read else "sent"
    img = mono_icons.status_image(kind, size=14, on_bubble=True)
    if img is not None:
        return img
    if msg.read:
        return ft.Icon(ft.Icons.DONE_ALL, size=14, color="#EDE7FF")
    return ft.Icon(ft.Icons.DONE, size=14, color="#FFFFFFB3")


def _meta(msg: chat_data.Message, time_color: str) -> ft.Control:
    """Время у всех сообщений; галочки — только у исходящих."""
    parts: list[ft.Control] = []
    if msg.edited and not msg.deleted:
        parts.append(
            ft.Text("изменено", size=11, color=time_color, font_family=theme.FONT_FAMILY)
        )
    # время всегда — и у своих, и у входящих
    if msg.time:
        parts.append(
            ft.Text(msg.time, size=12, color=time_color, font_family=theme.FONT_FAMILY)
        )
    ticks = _bubble_ticks(msg)
    if ticks is not None:
        parts.append(ticks)
    return ft.Row(
        spacing=4,
        tight=True,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=parts,
    )


def _corners(mine: bool):
    tl = tr = 16
    if mine:
        bl, brc = 16, 5
    else:
        bl, brc = 5, 16
    try:
        return ft.BorderRadius(top_left=tl, top_right=tr, bottom_left=bl, bottom_right=brc)
    except Exception:
        return 16


def _reply_quote(msg: chat_data.Message, fg: str) -> Optional[ft.Control]:
    if not msg.reply_preview:
        return None
    return ft.Container(
        bgcolor="#00000022",
        border_radius=8,
        padding=ft.Padding.symmetric(horizontal=8, vertical=4),
        content=ft.Text(
            msg.reply_preview,
            size=12,
            color=fg,
            font_family=theme.FONT_FAMILY,
            max_lines=2,
            overflow=ft.TextOverflow.ELLIPSIS,
        ),
    )


def _text_bubble(msg: chat_data.Message, bg: str, fg: str, time_color: str, br) -> ft.Control:
    if msg.deleted:
        body = ft.Text("Сообщение удалено", size=14, italic=True, color=time_color, font_family=theme.FONT_FAMILY)
        return ft.Container(
            bgcolor=bg,
            border_radius=br,
            padding=ft.Padding.symmetric(horizontal=12, vertical=7),
            content=body,
        )

    quote = _reply_quote(msg, fg)
    text = msg.text or ""
    text_ctrl = ft.Text(text, size=15, color=fg, font_family=theme.FONT_FAMILY)
    meta = _meta(msg, time_color)
    long = len(text) > 28 or "\n" in text or text.count(" ") > 4

    column_controls: list[ft.Control] = []
    if quote:
        column_controls.append(quote)
    if long:
        column_controls.extend([
                text_ctrl,
                ft.Container(alignment=ft.Alignment.CENTER_RIGHT, content=meta),
        ])
        inner = ft.Column(spacing=2, tight=True, controls=column_controls)
    else:
        row = ft.Row(
            spacing=8,
            tight=True,
            vertical_alignment=ft.CrossAxisAlignment.END,
            controls=[text_ctrl, meta],
        )
        column_controls.append(row)
        inner = ft.Column(spacing=2, tight=True, controls=column_controls) if quote else row

    return ft.Container(
        bgcolor=bg,
        border_radius=br,
        padding=ft.Padding.symmetric(horizontal=12, vertical=7),
        content=inner,
    )


def _image_bubble(msg: chat_data.Message, bg: str, time_color: str, br) -> ft.Control:
    img_w = 220
    quote = _reply_quote(msg, theme.PRIMARY_TEXT if msg.mine else theme.INK)
    controls: list[ft.Control] = []
    if quote:
        controls.append(quote)
    if msg.deleted:
        controls.append(ft.Text("Сообщение удалено", size=14, italic=True, color=time_color))
    else:
        controls.append(
                ft.Container(
                    width=img_w - 8,
                    height=160,
                    border_radius=10,
                    clip_behavior=ft.ClipBehavior.HARD_EDGE,
                    content=ft.Image(
                        src=msg.image,
                        width=img_w - 8,
                        height=160,
                        fit=ft.BoxFit.COVER,
                        border_radius=10,
                    ),
            )
        )
        if msg.text:
            controls.append(ft.Text(
                msg.text,
                size=14,
                color=theme.PRIMARY_TEXT if msg.mine else theme.INK,
                font_family=theme.FONT_FAMILY,
            ))
    controls.append(
                ft.Container(
                    alignment=ft.Alignment.CENTER_RIGHT,
            padding=ft.Padding.only(right=4, bottom=2),
                    content=_meta(msg, time_color),
        )
    )
    return ft.Container(
        width=img_w,
        bgcolor=bg,
        border_radius=br,
        padding=4,
        content=ft.Column(spacing=2, tight=True, controls=controls),
    )


def _bubble_body(msg: chat_data.Message, *, highlighted: bool = False) -> ft.Control:
    """Сам пузырь без жестов — подсветка на месте в ленте."""
    bg = theme.BUBBLE_OUT if msg.mine else theme.BUBBLE_IN
    fg = theme.PRIMARY_TEXT if msg.mine else theme.INK
    time_color = theme.TIME_OUT if msg.mine else theme.TIME_IN
    br = _corners(msg.mine)
    max_w = float(theme.PHONE_WIDTH) * 0.72

    if msg.image and theme._image_exists(msg.image) and not msg.deleted:
        body = _image_bubble(msg, bg, time_color, br)
    else:
        body = _text_bubble(msg, bg, fg, time_color, br)
        if len(msg.text or "") > 36 or "\n" in (msg.text or ""):
            body = ft.Container(content=body, width=max_w)

    if highlighted:
        body = ft.Container(
            content=body,
            border_radius=br,
            shadow=ft.BoxShadow(
                blur_radius=22,
                spread_radius=1,
                color="#4018A05A" if not theme.is_dark() else "#66A7F3A0",
                offset=ft.Offset(0, 4),
            ),
            border=ft.Border.all(1.5, theme.PRIMARY),
        )
    return body

def _sender_nick_label(msg: chat_data.Message) -> ft.Control:
    nick = msg.sender_nick or msg.sender_first or "Участник"
    colors = gradients.colors_for(msg.sender_seed or nick)
    # цвет ника из градиента аватара
    accent = "#%02X%02X%02X" % colors["top"]
    return ft.Text(
        nick,
        size=12,
        weight=ft.FontWeight.W_600,
        color=accent,
        font_family=theme.FONT_FAMILY,
    )


def _bubble(
    msg: chat_data.Message,
    *,
    gap_top: float,
    actions: dict,
    is_group: bool = False,
    show_sender: bool = True,
    animate_in: bool = False,
    highlighted: bool = False,
    dimmed: bool = False,
) -> ft.Control:
    if msg.date:
        return _date_chip(msg.date)

    align = ft.MainAxisAlignment.END if msg.mine else ft.MainAxisAlignment.START
    body = _bubble_body(msg, highlighted=highlighted)

    def _long(e=None, m=msg):
        opener = actions.get("open_menu")
        if opener:
            opener(m, e)

    def _tap(_e=None):
        # тап по ленте закрывает меню (сообщение не двигаем)
        if actions.get("is_menu_open") and actions["is_menu_open"]():
            closer = actions.get("close_menu")
            if closer:
                closer()

    pressed = ft.GestureDetector(
        content=body,
        on_tap=_tap,
        on_long_press_start=_long,
        on_secondary_tap=_long,  # ПКМ на десктопе
    )

    # Группа: у чужих — маленький аватар слева и ник сверху сообщения
    if is_group and not msg.mine:
        if show_sender:
            avatar = _avatar_circle(
                msg.sender_seed or msg.sender_nick or "u",
                msg.sender_first or (msg.sender_nick[:1] if msg.sender_nick else "?"),
                msg.sender_last or "",
                size=28,
            )
            col = ft.Column(
                spacing=2,
                tight=True,
                controls=[_sender_nick_label(msg), pressed],
            )
        else:
            avatar = ft.Container(width=28, height=28)
            col = pressed
        row = ft.Row(
            spacing=8,
            tight=True,
            vertical_alignment=ft.CrossAxisAlignment.END,
            controls=[avatar, col],
        )
        left_pad, right_pad = 10, 40
    else:
        row = ft.Row(alignment=align, tight=True, controls=[pressed])
        left_pad = 12 if not msg.mine else 48
        right_pad = 12 if msg.mine else 48

    # Появление «из композера»: рост из нижнего угла + подъём + лёгкий tilt
    origin = ft.Alignment(1, 1) if msg.mine else ft.Alignment(-1, 1)
    if animate_in:
        start_scale = ft.Scale(scale=0.46, alignment=origin)
        start_offset = (
            ft.Offset(0.18, 0.62) if msg.mine else ft.Offset(-0.10, 0.42)
        )
        start_rotate = ft.Rotate(
            angle=0.07 if msg.mine else -0.045,
            alignment=origin,
        )
        motion = ft.Container(
            content=row,
            opacity=0,
            scale=start_scale,
            offset=start_offset,
            rotate=start_rotate,
            animate_opacity=ft.Animation(180, ft.AnimationCurve.EASE_OUT),
            animate_scale=ft.Animation(420, ft.AnimationCurve.EASE_OUT_CUBIC),
            animate_offset=ft.Animation(400, ft.AnimationCurve.EASE_OUT_CUBIC),
            animate_rotation=ft.Animation(380, ft.AnimationCurve.EASE_OUT_CUBIC),
        )
    else:
        motion = ft.Container(content=row)

    outer = ft.Container(
        key=msg.id or None,
        padding=ft.Padding.only(
            left=left_pad,
            right=right_pad,
            top=gap_top,
            bottom=2,
        ),
        opacity=0.34 if dimmed else 1,
        animate_opacity=ft.Animation(160, ft.AnimationCurve.EASE_OUT),
        content=motion,
    )
    if animate_in:
        outer.data = {"motion": motion, "origin": origin, "mine": bool(msg.mine)}
    return outer


def _menu_row(
    label: str, on_click, *, danger: bool = False, sprite: str | None = None
) -> ft.Control:
    color = MENU_DANGER if danger else theme.INK
    left: list[ft.Control] = []
    if sprite:
        left.append(mono_icons.ui_icon(sprite, size=15))
    left.append(
        ft.Text(
            label,
            size=13,
            color=color,
            weight=ft.FontWeight.W_500,
            font_family=theme.FONT_FAMILY,
        )
    )
    return ft.Container(
        border_radius=10,
        bgcolor=_menu_item_bg() if not danger else ("#3A1A22" if theme.is_dark() else "#FEE2E8"),
        padding=ft.Padding.symmetric(horizontal=10, vertical=7),
        on_click=on_click,
        content=ft.Row(spacing=8, controls=left),
    )


def _context_menu_card(
    msg: chat_data.Message,
    actions: dict,
    close,
    *,
    width: float,
) -> ft.Control:
    rows: list[ft.Control] = []
    if msg.mine and not msg.deleted:
        rows.append(_menu_row(
            "Редактировать",
            lambda e: (close(), actions["edit"](msg)),
            sprite="edit",
        ))
    rows.append(_menu_row(
        "Копировать",
        lambda e: (close(), actions["copy"](msg)),
        sprite="copy",
    ))
    rows.append(_menu_row(
        "Ответить",
        lambda e: (close(), actions["reply"](msg)),
        sprite="reply",
    ))
    if not msg.deleted:
        rows.append(_menu_row(
            "Удалить",
            lambda e: (close(), actions["delete"](msg)),
            danger=True,
            sprite="delete",
        ))
    if not msg.mine and not msg.deleted and actions.get("report"):
        rows.append(_menu_row(
            "Пожаловаться",
            lambda e: (close(), actions["report"](msg)),
            danger=True,
            sprite="flag",
        ))

    return ft.Container(
        width=width,
        bgcolor=_menu_bg(),
        border_radius=MENU_RADIUS,
        padding=5,
        blur=ft.Blur(12, 12, ft.BlurTileMode.CLAMP),
        shadow=ft.BoxShadow(
            blur_radius=18,
            spread_radius=0,
            color="#1A103830",
            offset=ft.Offset(0, 6),
        ),
        border=ft.Border.all(1, liquid_glass.white_glass_border()),
        content=ft.Column(spacing=3, tight=True, controls=rows),
    )


def _same_sender(a: Optional[chat_data.Message], b: chat_data.Message) -> bool:
    if a is None or a.date or b.date:
        return False
    if a.mine and b.mine:
        return True
    if a.mine != b.mine:
        return False
    return (a.sender_seed or a.sender_nick) == (b.sender_seed or b.sender_nick)


def _build_message_controls(
    messages: list[chat_data.Message],
    actions: dict,
    *,
    is_group: bool = False,
    highlight_id: Optional[str] = None,
) -> list[ft.Control]:
    out: list[ft.Control] = []
    prev: Optional[chat_data.Message] = None
    menu_open = bool(highlight_id)
    for msg in messages:
        if msg.date:
            out.append(_date_chip(msg.date))
            prev = None
            continue
        same = _same_sender(prev, msg)
        if prev is None:
            gap = 6.0
        elif same:
            gap = 2.0
        else:
            gap = 10.0
        show_sender = bool(is_group and not msg.mine and not same)
        is_hi = bool(highlight_id and msg.id == highlight_id)
        out.append(
            _bubble(
                msg,
                gap_top=gap,
                actions=actions,
                is_group=is_group,
                show_sender=show_sender,
                highlighted=is_hi,
                dimmed=bool(menu_open and not is_hi),
            )
        )
        prev = msg
    return out


def _header(
    *,
    title: str,
    seed: str,
    first: str,
    last: str,
    on_back,
    online_label: ft.Text,
    full_title: bool = False,
    on_report=None,
    on_profile=None,
) -> ft.Control:
    back_icon = mono_icons.ui_icon("back", size=22)
    back_btn = liquid_glass.glass_circle_button(
        on_back, content=back_icon, size=44, variant="white"
    )

    short = title if full_title else (title.split()[0] if title else (first or "?"))
    pill_inner = ft.Row(
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
            _avatar_circle(seed, first or short[:1], last, size=40),
                ft.Column(
                    spacing=0,
                    tight=True,
                expand=True,
                    controls=[
                        ft.Text(
                            short,
                            size=16,
                            weight=ft.FontWeight.W_600,
                            color=theme.INK,
                            font_family=theme.FONT_FAMILY,
                        max_lines=1,
                        overflow=ft.TextOverflow.ELLIPSIS,
                    ),
                    online_label,
                    ],
                ),
            ],
    )
    pill = liquid_glass.glass_capsule(
        pill_inner,
        radius=28,
        blur=liquid_glass.BTN_BLUR,
        tint=liquid_glass.white_glass_tint(),
        border_color=liquid_glass.white_glass_border(),
        padding=ft.Padding.only(left=6, right=16, top=6, bottom=6),
        shadow=True,
        highlight=True,
    )
    # expand через обёртку — у capsule фиксированная тень/клип
    # тап по профилю собеседника (не для групп)
    pill_wrap = ft.Container(
        expand=True,
        content=pill,
        ink=bool(on_profile) and not full_title,
        on_click=on_profile if (on_profile and not full_title) else None,
    )

    report_btn = None
    if on_report is not None and not full_title:
        report_btn = ft.IconButton(
            icon=ft.Icons.FLAG_OUTLINED,
            icon_color=theme.PRIMARY,
            tooltip="Пожаловаться",
            on_click=on_report,
        )

    row_controls: list[ft.Control] = [back_btn, pill_wrap]
    if report_btn is not None:
        row_controls.append(report_btn)

    return ft.Container(
        padding=ft.Padding.symmetric(horizontal=12, vertical=12),
        content=ft.Row(
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=row_controls,
        ),
    )


def build_chat(page: ft.Page) -> ft.Control:
    cid = STATE.draft.get("_open_chat_id") or "c2"
    is_group = bool(STATE.draft.get("_open_is_group"))
    group = chat_data.get_group(cid) if is_group else None
    contact = None if is_group else (chat_data.get_contact(cid) or chat_data.CONTACTS[0])
    if is_group and group is None:
        is_group = False
        contact = chat_data.CONTACTS[0]
        cid = contact.id

    is_favorites = (
        (not is_group)
        and contact is not None
        and contact.id == chat_data.FAVORITES_ID
    )

    if is_group and group is not None:
        chat_data.mark_group_read(group.id)
        peer_title = group.name
        peer_status = group.status
        peer_seed = group.seed
        peer_first = group.name[:1]
        peer_last = ""
    else:
        assert contact is not None
        chat_data.mark_read(contact.id)
        peer_title = contact.display_name
        peer_status = "только вы · заметки" if is_favorites else contact.status
        peer_seed = contact.seed
        peer_first = contact.first
        peer_last = contact.last
        if not is_favorites:
            from core import privacy as priv

            cid_s = str(contact.id or "")
            peer_pid = cid_s[2:] if cid_s.startswith("u:") else (contact.seed or "")
            if peer_pid:
                peer_status = priv.status_for_others(peer_pid, peer_status or "")
                if priv.for_user(peer_pid).get("hide_avatar"):
                    peer_first, peer_last = "?", ""

    photo = theme.asset("assets", "images", "photo_2026-09-30_00-09-10.jpg")
    if theme._image_exists(photo):
        chat_data.attach_demo_photo(photo)

    state = {
        "offset": 0,
        "loaded": 0,
        "reply_to": None,
        "edit_id": None,
        "online": True,
        "alive": True,
        "menu_msg": None,
        "is_group": is_group,
        "chat_id": cid,
        "picking": False,
        "file_picker": None,
    }

    online_label = ft.Text(
        peer_status,
        size=12,
        color=STATUS_MUTED,
        font_family=theme.FONT_FAMILY,
    )
    banner_text = ft.Text("", size=12, color=theme.PRIMARY, font_family=theme.FONT_FAMILY, expand=True)
    banner_bar = ft.Container(visible=False, padding=ft.Padding.symmetric(horizontal=16, vertical=4))
    field_ref: dict = {}

    # Scrim ловит тап в «пустое» место; панель — поверх, с анимацией.
    # Само сообщение остаётся в ленте (только подсветка).
    menu_card_host = ft.Container(
        left=24,
        top=200,
        opacity=0,
        offset=ft.Offset(0, 0.08),
        animate_opacity=ft.Animation(180, ft.AnimationCurve.EASE_OUT),
        animate_offset=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
        content=None,
    )
    scrim = ft.Container(
        expand=True,
        bgcolor="#00000033" if not theme.is_dark() else "#00000066",
        opacity=0,
        animate_opacity=ft.Animation(180, ft.AnimationCurve.EASE_OUT),
        on_click=lambda e: close_menu(),
    )
    menu_host = ft.Container(
        visible=False,
        expand=True,
        content=ft.Stack(
            expand=True,
            controls=[scrim, menu_card_host],
        ),
    )

    def _page_msgs(limit: int, offset: int = 0):
        if is_group:
            return chat_data.page_group_messages(cid, limit=limit, offset=offset)
        return chat_data.page_messages(cid, limit=limit, offset=offset)

    def _older_ok(loaded: int) -> bool:
        if is_group:
            return chat_data.older_group_available(cid, loaded)
        return chat_data.older_available(cid, loaded)

    def _all_messages() -> list:
        if is_group and group is not None:
            return group.messages
        return contact.messages if contact is not None else []

    def _highlight_id() -> Optional[str]:
        m = state.get("menu_msg")
        return m.id if m is not None and not getattr(m, "date", None) else None

    def _refresh_list():
        window = _page_msgs(PAGE_SIZE + state["offset"], 0)
        state["loaded"] = len(window)
        list_col.controls = _build_message_controls(
            window,
            actions,
            is_group=is_group,
            highlight_id=_highlight_id(),
        )
        try:
            list_col.update()
        except Exception:
            pass

    def _event_xy(e):
        if e is None:
            return None, None, None, None
        gx = getattr(e, "global_x", None)
        gy = getattr(e, "global_y", None)
        lx = getattr(e, "local_x", None)
        ly = getattr(e, "local_y", None)
        gp = getattr(e, "global_position", None)
        lp = getattr(e, "local_position", None)
        if gp is not None:
            gx = getattr(gp, "x", gx)
            gy = getattr(gp, "y", gy)
        if lp is not None:
            lx = getattr(lp, "x", lx)
            ly = getattr(lp, "y", ly)
        try:
            return (
                float(gx) if gx is not None else None,
                float(gy) if gy is not None else None,
                float(lx) if lx is not None else None,
                float(ly) if ly is not None else None,
            )
        except (TypeError, ValueError):
            return None, None, None, None

    def _menu_anchor(msg: chat_data.Message, e=None, *, width: float, bubble_h: float):
        """Панель под пузырём, по стороне сообщения."""
        pad = 8.0
        pw = float(theme.PHONE_WIDTH)
        ph = float(theme.PHONE_HEIGHT)
        left_pad = 12.0 if not msg.mine else 48.0
        right_pad = 12.0 if msg.mine else 48.0
        gx, gy, lx, ly = _event_xy(e)
        if gx is not None and gy is not None:
            try:
                win = getattr(page, "window", None)
                wx = float(getattr(win, "left", 0) or 0) if win else 0.0
                wy = float(getattr(win, "top", 0) or 0) if win else 0.0
            except Exception:
                wx = wy = 0.0
            title = 32.0
            bubble_left = gx - wx - (lx if lx is not None else width * 0.5)
            bubble_top = gy - wy - title - (ly if ly is not None else bubble_h * 0.5)
            left = bubble_left
            top = bubble_top + bubble_h + 6.0
        else:
            left = pw - right_pad - width if msg.mine else left_pad
            top = ph * 0.42
        left = max(pad, min(left, pw - width - pad))
        top = max(64.0, min(top, ph - 200.0))
        return left, top

    def _set_banner(text: str, *, visible: bool) -> None:
        banner_text.value = text
        banner_bar.visible = visible
        try:
            banner_bar.update()
        except Exception:
            pass

    def _clear_composer_modes() -> None:
        state["reply_to"] = None
        state["edit_id"] = None
        _set_banner("", visible=False)
        tf = field_ref.get("tf")
        if tf is not None:
            tf.hint_text = "Сообщение"
            try:
                tf.update()
            except Exception:
                pass

    def cancel_banner(_e=None):
        tf = field_ref.get("tf")
        if state.get("edit_id") and tf is not None:
            tf.value = ""
            try:
                tf.update()
            except Exception:
                pass
        _clear_composer_modes()

    banner_bar.content = ft.Row(
            spacing=8,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            banner_text,
            ft.Container(
                on_click=cancel_banner,
                padding=ft.Padding.symmetric(horizontal=8, vertical=4),
                border_radius=12,
                content=ft.Text("Отмена", size=12, color=STATUS_MUTED, font_family=theme.FONT_FAMILY),
            ),
        ],
    )

    def on_copy(msg: chat_data.Message):
        text = msg.text or ""
        try:
            page.set_clipboard(text)
            STATE.snack("Скопировано")
        except Exception:
            STATE.snack(text[:80] if text else "Пусто")

    def on_reply(msg: chat_data.Message):
        state["edit_id"] = None
        state["reply_to"] = msg.id
        _set_banner(f"Ответ на: {(msg.text or 'фото')[:40]}", visible=True)
        tf = field_ref.get("tf")
        if tf is not None:
            tf.hint_text = "Ваш ответ…"
            try:
                tf.focus()
                tf.update()
            except Exception:
                pass

    def on_edit(msg: chat_data.Message):
        """Редактирование прямо в панели ввода внизу."""
        if not msg.mine or msg.deleted:
            return
        tf = field_ref.get("tf")
        if not tf:
            return
        state["reply_to"] = None
        state["edit_id"] = msg.id
        tf.value = msg.text or ""
        tf.hint_text = "Измените сообщение…"
        _set_banner("Редактирование", visible=True)
        try:
            tf.focus()
            tf.update()
        except Exception:
            pass

    def on_delete(msg: chat_data.Message):
        chat_data.delete_message(cid, msg.id)
        page.pubsub.send_all({
            "type": "chat_delete",
            "chat_id": cid,
            "msg_id": msg.id,
        })
        if state.get("edit_id") == msg.id:
            _clear_composer_modes()
        _refresh_list()

    def close_menu(_e=None):
        if state.get("menu_msg") is None and not menu_host.visible:
            return
        state["menu_msg"] = None

        async def _hide():
            import asyncio

            scrim.opacity = 0
            menu_card_host.opacity = 0
            menu_card_host.offset = ft.Offset(0, 0.08)
            try:
                scrim.update()
                menu_card_host.update()
            except Exception:
                pass
            await asyncio.sleep(0.2)
            if not state["alive"]:
                return
            menu_host.visible = False
            menu_card_host.content = None
            try:
                menu_host.update()
            except Exception:
                pass
            try:
                _refresh_list()
            except Exception:
                pass

        try:
            page.run_task(_hide)
        except Exception:
            menu_host.visible = False
            menu_card_host.content = None
            try:
                _refresh_list()
                menu_host.update()
            except Exception:
                pass

    def open_menu(msg: chat_data.Message, e=None):
        if msg.date:
            return
        cur = state.get("menu_msg")
        if cur is not None and cur.id == msg.id:
            close_menu()
            return

        state["menu_msg"] = msg
        try:
            _refresh_list()
        except Exception:
            pass

        bw = _approx_bubble_width(msg)
        bh = _approx_bubble_height(msg)
        left, top = _menu_anchor(msg, e, width=bw, bubble_h=bh)
        menu_card_host.left = left
        menu_card_host.top = top
        menu_card_host.content = ft.GestureDetector(
            on_tap=lambda _e: None,
            content=_context_menu_card(msg, actions, close_menu, width=bw),
        )
        scrim.opacity = 0
        menu_card_host.opacity = 0
        menu_card_host.offset = ft.Offset(0, 0.08)
        menu_host.visible = True
        try:
            menu_host.update()
        except Exception:
            try:
                page.update()
            except Exception:
                pass

        async def _show():
            import asyncio

            await asyncio.sleep(0.02)
            if state.get("menu_msg") is not msg:
                return
            scrim.opacity = 1
            menu_card_host.opacity = 1
            menu_card_host.offset = ft.Offset(0, 0)
            try:
                scrim.update()
                menu_card_host.update()
            except Exception:
                pass

        try:
            page.run_task(_show)
        except Exception:
            scrim.opacity = 1
            menu_card_host.opacity = 1
            menu_card_host.offset = ft.Offset(0, 0)

    def _report_target_pid() -> str:
        if contact is not None:
            if str(contact.id).startswith("u:"):
                return str(contact.id)[2:]
            return (contact.seed or contact.name or contact.id or "").strip()
        return (peer_title or cid or "").strip()

    def open_report_screen(msg: Optional[chat_data.Message] = None):
        from flet_app.screens.report import report_route

        STATE.draft["_report_target_pid"] = _report_target_pid()
        STATE.draft["_report_target_name"] = (
            (contact.display_name if contact is not None else "")
            or peer_title
            or _report_target_pid()
        )
        STATE.draft["_report_chat_id"] = str(cid)
        STATE.draft["_report_msg_id"] = (msg.id if msg else "") or ""
        STATE.draft["_report_back"] = "/chat"
        STATE.draft["_open_chat_id"] = cid
        STATE.draft["_open_is_group"] = bool(is_group)
        STATE.go(report_route())

    def on_report_msg(msg: chat_data.Message):
        open_report_screen(msg)

    def on_report_user(_e=None):
        open_report_screen(None)

    actions = {
        "edit": on_edit,
        "copy": on_copy,
        "reply": on_reply,
        "delete": on_delete,
        "report": on_report_msg,
        "open_menu": open_menu,
        "close_menu": close_menu,
        "is_menu_open": lambda: state.get("menu_msg") is not None,
    }

    initial = _page_msgs(PAGE_SIZE, 0)
    state["loaded"] = len(initial)

    def _scroll_to_end(*, animate: bool = True) -> None:
        """Прокрутка к концу: scroll_to в Flet 1.x — coroutine, нужен await."""

        async def _go():
            try:
                await list_col.scroll_to(
                    offset=-1,
                    duration=220 if animate else 0,
                    curve=ft.AnimationCurve.EASE_OUT,
                )
            except Exception:
                pass

        try:
            page.run_task(_go)
        except Exception:
            pass

    try:
        list_col = ft.ListView(
            expand=True,
            spacing=0,
            padding=ft.Padding.only(top=4, bottom=12),
            auto_scroll=False,
            controls=_build_message_controls(initial, actions, is_group=is_group),
        )
    except Exception:
        list_col = ft.Column(
            spacing=0,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
            controls=_build_message_controls(initial, actions, is_group=is_group),
            auto_scroll=False,
        )

    # Убираем глючный белый «зубчатый» скроллбар
    try:
        list_col.scrollbar_theme = ft.ScrollbarTheme(
            thickness=0,
            thumb_visibility=False,
            track_visibility=False,
        )
    except Exception:
        try:
            list_col.scrollbar_theme = ft.ScrollbarTheme(thickness=0)
        except Exception:
            pass

    load_older_btn = ft.TextButton(
        "Загрузить ранее",
        visible=_older_ok(state["loaded"]),
        on_click=lambda e: load_older(),
    )

    def load_older(_=None):
        state["offset"] += PAGE_SIZE
        _refresh_list()
        load_older_btn.visible = _older_ok(state["loaded"])
        try:
            load_older_btn.update()
        except Exception:
            pass

    def go_back(_=None):
        close_menu()
        state["alive"] = False
        STATE.draft["_open_is_group"] = False
        try:
            page.pubsub.unsubscribe(on_pubsub)
        except Exception:
            try:
                page.pubsub.unsubscribe_all()
            except Exception:
                pass
        STATE.go("/home")

    def _punch_send_btn():
        body = field_ref.get("send_body")
        if body is None:
            return

        async def _punch():
            import asyncio

            try:
                body.scale = 0.78
                body.update()
            except Exception:
                return
            await asyncio.sleep(0.07)
            if not state.get("alive"):
                return
            try:
                body.scale = 1.12
                body.update()
            except Exception:
                return
            await asyncio.sleep(0.14)
            if not state.get("alive"):
                return
            try:
                body.scale = 1.0
                body.update()
            except Exception:
                pass

        try:
            page.run_task(_punch)
        except Exception:
            pass

    def _append_local(m: chat_data.Message):
        msgs = _all_messages()
        gap = 2.0
        show_sender = False
        if len(msgs) >= 2:
            prev = msgs[-2]
            same = _same_sender(prev, m)
            if same:
                gap = 2.0
            else:
                gap = 10.0
            show_sender = bool(is_group and not m.mine and not same)
        elif is_group and not m.mine:
            show_sender = True
        bubble = _bubble(
            m,
            gap_top=gap,
            actions=actions,
            is_group=is_group,
            show_sender=show_sender,
            animate_in=True,
        )
        list_col.controls.append(bubble)
        try:
            list_col.update()
        except Exception:
            pass
        _scroll_to_end(animate=True)
        if m.mine:
            _punch_send_btn()

        async def _play_in():
            import asyncio

            await asyncio.sleep(0.016)
            if not state.get("alive"):
                return
            info = bubble.data if isinstance(bubble.data, dict) else {}
            motion = info.get("motion") or bubble
            origin = info.get("origin") or ft.Alignment(1, 1)
            # фаза 1 — вылет из композера с лёгким overshoot
            motion.opacity = 1
            motion.offset = ft.Offset(0, 0)
            motion.rotate = ft.Rotate(angle=0, alignment=origin)
            motion.scale = ft.Scale(scale=1.05, alignment=origin)
            try:
                motion.update()
            except Exception:
                return
            await asyncio.sleep(0.30)
            if not state.get("alive"):
                return
            # фаза 2 — мягкий settle
            motion.scale = ft.Scale(scale=1.0, alignment=origin)
            try:
                motion.update()
            except Exception:
                pass

        try:
            page.run_task(_play_in)
        except Exception:
            info = bubble.data if isinstance(bubble.data, dict) else {}
            motion = info.get("motion") or bubble
            origin = info.get("origin") or ft.Alignment(1, 1)
            motion.opacity = 1
            motion.scale = ft.Scale(scale=1.0, alignment=origin)
            motion.offset = ft.Offset(0, 0)
            motion.rotate = ft.Rotate(angle=0, alignment=origin)
            try:
                motion.update()
            except Exception:
                pass

    def _deliver_now(text: str, image: Optional[str], reply_to: Optional[str], *, pending: bool = False):
        if is_group:
            m = chat_data.add_group_message(
                cid,
                text,
                mine=True,
                image=image,
                reply_to_id=reply_to,
                pending=pending,
            )
        else:
            m = chat_data.add_message(
                cid,
                text,
                mine=True,
                image=image,
                reply_to_id=reply_to,
                pending=pending,
            )
        if m:
            _append_local(m)
            if not pending:
                sounds.play_send()
            # «Избранное» — только локальные заметки, без рассылки
            if not pending and not is_favorites:
                page.pubsub.send_all({
                    "type": "chat_message",
                    "chat_id": cid,
                    "is_group": is_group,
                    "msg": {
                        "id": m.id,
                        "text": m.text,
                        "image": m.image,
                        "mine": True,
                        "reply_to_id": m.reply_to_id,
                        "reply_preview": m.reply_preview,
                        "time": m.time,
                    },
                    "from_user": getattr(STATE.user, "public_id", None),
                })
        return m

    def flush_outbox():
        for item in list(offline_outbox.pending(cid)):
            try:
                image = item.get("attachment_path") or None
                if image and not uploads.is_image(image):
                    image = None
                m = _deliver_now(
                    item.get("text") or "",
                    image,
                    item.get("reply_to_id"),
                    pending=False,
                )
                if m:
                    for old in _all_messages():
                        if old.pending and old.id != m.id and old.text == m.text:
                            old.pending = False
                offline_outbox.remove(item["id"])
            except Exception:
                pass

    def on_send(_=None):
        tf = field_ref.get("tf")
        if not tf:
            return
        text = (tf.value or "").strip()
        if not text:
            return

        # Режим редактирования — меняем существующее сообщение, не шлём новое
        edit_id = state.get("edit_id") or ""
        if edit_id:
            updated = chat_data.edit_message(cid, edit_id, text)
            if updated is None:
                STATE.error("Не удалось изменить сообщение")
                return
            page.pubsub.send_all({
                "type": "chat_edit",
                "chat_id": cid,
                "msg_id": edit_id,
                "text": text,
            })
        tf.value = ""
        try:
            tf.update()
        except Exception:
            pass
            _clear_composer_modes()
            _refresh_list()
            return

        try:
            rate_limit.check(
                f"ui-msg:{getattr(STATE.user, 'id', 'anon')}:{cid}",
                limit=40,
                window_sec=60,
                block_sec=20,
                action="отправка",
            )
        except rate_limit.RateLimitError as exc:
            STATE.error(str(exc))
            return

        tf.value = ""
        try:
            tf.update()
        except Exception:
            pass
        reply_to = state["reply_to"]
        _clear_composer_modes()

        if is_favorites:
            _deliver_now(text, None, reply_to, pending=False)
            return

        if not state["online"]:
            offline_outbox.enqueue(chat_id=cid, text=text, reply_to_id=reply_to)
            _deliver_now(text, None, reply_to, pending=True)
            STATE.snack("Нет сети — сообщение в очереди")
            return

        try:
            _deliver_now(text, None, reply_to, pending=False)
        except Exception as exc:
            offline_outbox.enqueue(chat_id=cid, text=text, reply_to_id=reply_to)
            _deliver_now(text, None, reply_to, pending=True)
            STATE.snack(f"Оффлайн: сохранено локально ({exc})")

    def _attach_path(path: str) -> None:
        """Обработать уже выбранный файл (только из UI-потока Flet)."""
        if not path or not state.get("alive"):
            return
        try:
            stored = uploads.save_upload(path, subdir="chat")
        except uploads.UploadError as exc:
            STATE.error(str(exc))
            return

        if state.get("edit_id"):
            STATE.snack("Сначала завершите редактирование")
            return

        reply_to = state["reply_to"]
        _clear_composer_modes()

        caption = ""
        tf = field_ref.get("tf")
        if tf and (tf.value or "").strip():
            caption = tf.value.strip()
            tf.value = ""
            try:
                tf.update()
            except Exception:
                pass

        image = stored if uploads.is_image(stored) else None
        text = caption if image else (caption or os.path.basename(stored))
        if is_favorites:
            _deliver_now(text, image, reply_to, pending=False)
            return
        if not state["online"]:
            offline_outbox.enqueue(
                chat_id=cid,
                text=text,
                attachment_path=stored,
                reply_to_id=reply_to,
            )
            _deliver_now(text, image, reply_to, pending=True)
            STATE.snack("Нет сети — файл в очереди")
            return
        _deliver_now(text, image, reply_to, pending=False)

    def on_attach(_=None):
        """Неблокирующий выбор файла: иначе tkinter/fut.result() замораживали UI."""
        if state.get("picking") or not state.get("alive"):
            return
        if state.get("edit_id"):
            STATE.snack("Сначала завершите редактирование")
            return
        state["picking"] = True

        async def _pick():
            try:
                picker = state.get("file_picker")
                if picker is None:
                    picker = ft.FilePicker()
                    try:
                        page.services.append(picker)
                    except Exception:
                        # старые сборки — overlay
                        try:
                            page.overlay.append(picker)
                            page.update()
                        except Exception:
                            pass
                    state["file_picker"] = picker

                files = await picker.pick_files(
                    dialog_title="Фото или PDF",
                    allow_multiple=False,
                    allowed_extensions=["jpg", "jpeg", "png", "pdf", "webp"],
                    file_type=ft.FilePickerFileType.CUSTOM,
                )
                if not state.get("alive"):
                    return
                if not files:
                    return
                path = getattr(files[0], "path", None) or ""
                if path:
                    _attach_path(path)
            except Exception as exc:
                if state.get("alive"):
                    STATE.error(f"Не удалось выбрать файл: {exc}")
            finally:
                state["picking"] = False

        try:
            page.run_task(_pick)
        except Exception as exc:
            state["picking"] = False
            STATE.error(f"Не удалось открыть выбор файла: {exc}")

    def on_pubsub(message):
        if not state["alive"]:
            return
        if not isinstance(message, dict):
            return
        if message.get("chat_id") != cid:
            return
        mtype = message.get("type")
        if mtype == "chat_message":
            payload = message.get("msg") or {}
            # своё уже добавлено локально
            if payload.get("mine") and payload.get("id"):
                if chat_data.get_message(cid, payload["id"]):
                    return
            if message.get("from_user") and STATE.user and message["from_user"] == STATE.user.public_id:
                return
            if is_group:
                m = chat_data.add_group_message(
                    cid,
                    payload.get("text") or "",
                    mine=False,
                    image=payload.get("image"),
                    reply_to_id=payload.get("reply_to_id"),
                    msg_id=payload.get("id"),
                    sender_nick=payload.get("sender_nick") or "Участник",
                    sender_seed=payload.get("sender_seed") or "u",
                    sender_first=payload.get("sender_first") or "?",
                    sender_last=payload.get("sender_last") or "",
                )
            else:
                m = chat_data.add_message(
                    cid,
                    payload.get("text") or "",
                    mine=False,
                    image=payload.get("image"),
                    reply_to_id=payload.get("reply_to_id"),
                    msg_id=payload.get("id"),
                )
            if m:
                _append_local(m)
                from core import prefs as _prefs

                muted_chat = (not is_group) and chat_data.is_muted(cid)
                if not muted_chat:
                    sounds.play_ding()
                if (not muted_chat) and _prefs.notif_allowed(is_group=bool(is_group)):
                    preview = (m.text or "Фото")[:80]
                    if not _prefs.notif_preview():
                        preview = "Новое сообщение"
                    push.notify(peer_title or "Сообщение", preview)
        elif mtype == "chat_edit":
            chat_data.edit_message(cid, message.get("msg_id"), message.get("text") or "")
            _refresh_list()
        elif mtype == "chat_delete":
            chat_data.delete_message(cid, message.get("msg_id"))
            _refresh_list()
        elif mtype == "net_status":
            state["online"] = bool(message.get("online", True))
            online_label.value = peer_status if state["online"] else "нет сети · очередь"
            try:
                online_label.update()
            except Exception:
                pass
            if state["online"]:
                flush_outbox()

    try:
        page.pubsub.subscribe(on_pubsub)
    except Exception:
        pass

    # реконнект / первичная досылка
    flush_outbox()

    # демо: имитация потери сети кнопкой долгого жеста не нужна —
    # публикуем online=True при входе
    try:
        page.pubsub.send_all({"type": "net_status", "online": True, "chat_id": cid})
    except Exception:
        pass

    composer = _composer(on_send, on_attach, field_ref)

    header_host: dict = {"ctrl": None}

    def open_contact_profile(_=None):
        if is_group or contact is None or is_favorites:
            return
        from flet_app.screens.contact_profile import contact_route

        STATE.draft["_profile_contact_id"] = contact.id
        STATE.draft["_open_chat_id"] = contact.id
        STATE.draft["_open_is_group"] = False
        route = contact_route(contact.id)

        hdr = header_host.get("ctrl")
        if hdr is None:
            STATE.go(route)
            return

        # лёгкий «пульс» шапки перед переходом
        async def _pulse_then_go():
            import asyncio

            try:
                hdr.animate_scale = ft.Animation(160, ft.AnimationCurve.EASE_OUT)
                hdr.scale = 0.97
                hdr.update()
                await asyncio.sleep(0.12)
                hdr.scale = 1.02
                hdr.update()
                await asyncio.sleep(0.1)
            except Exception:
                pass
            STATE.go(route)

        try:
            page.run_task(_pulse_then_go)
        except Exception:
            STATE.go(route)

    header_ctrl = _header(
        title=peer_title,
        seed=peer_seed,
        first=peer_first,
        last=peer_last,
        on_back=go_back,
        online_label=online_label,
        full_title=is_group or is_favorites,
        on_report=None if (is_group or is_favorites) else on_report_user,
        on_profile=None if (is_group or is_favorites) else open_contact_profile,
    )
    header_anim = ft.Container(
        content=header_ctrl,
        scale=1,
        animate_scale=ft.Animation(160, ft.AnimationCurve.EASE_OUT),
    )
    header_host["ctrl"] = header_anim

    body_controls: list = [
        header_anim,
        ft.Container(padding=ft.Padding.symmetric(horizontal=12), content=load_older_btn),
        banner_bar,
        list_col,
    ]
    if is_group and group is not None:
        from flet_app import questions_data

        q_count = questions_data.sync_group_count(group.id)

        def _open_questions(_=None):
            STATE.draft["_questions_group_id"] = group.id
            STATE.draft["_open_chat_id"] = group.id
            STATE.draft["_open_is_group"] = True
            STATE.go("/questions")

        body_controls.append(
            _questions_plaque(count=q_count, on_open=_open_questions)
        )
    body_controls.append(composer)

    chat_body = ft.Column(
        expand=True,
        spacing=0,
        controls=body_controls,
    )

    async def _boot_scroll():
        import asyncio
        await asyncio.sleep(0.05)
        if state["alive"]:
            _scroll_to_end(animate=False)

    try:
        page.run_task(_boot_scroll)
    except Exception:
        pass

    root = ft.Container(
        expand=True,
        bgcolor=theme.BG,
        content=ft.Stack(
            expand=True,
            controls=[chat_body, menu_host],
        ),
    )
    return theme.edge_swipe_back(root, on_back=go_back)


def _questions_plaque(*, count: int = 0, on_open=None) -> ft.Control:
    """Плашка «Вопросы» над композером в групповом чате."""
    eye = mono_icons.ui_icon("eye", size=22)
    count_label = "нет" if count <= 0 else str(int(count))

    def _tap(_=None):
        if on_open:
            on_open()
        else:
            try:
                STATE.snack("Вопросы класса")
            except Exception:
                pass

    row = ft.Row(
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
            ft.Row(
                spacing=8,
                tight=True,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Text(
                        "Вопросы",
                        size=16,
                        weight=ft.FontWeight.W_600,
                        color=theme.INK,
                        font_family=theme.FONT_FAMILY,
                    ),
                    ft.Text(
                        count_label,
                        size=14,
                        weight=ft.FontWeight.W_500,
                        color=theme.MUTED,
                        font_family=theme.FONT_FAMILY,
                    ),
                ],
            ),
            ft.Row(
                spacing=6,
                tight=True,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Text(
                        "Смотреть",
                        size=13,
                        weight=ft.FontWeight.W_500,
                        color=theme.PRIMARY,
                        font_family=theme.FONT_FAMILY,
                    ),
                    eye,
                ],
            ),
        ],
    )

    # полный stadium: radius больше половины высоты
    plaque = liquid_glass.glass_capsule(
        row,
        radius=40,
        blur=20,
        tint=liquid_glass.white_glass_tint(),
        border_color=liquid_glass.white_glass_border(),
        padding=ft.Padding.symmetric(horizontal=20, vertical=14),
        highlight=True,
        shadow=True,
    )
    return ft.Container(
        padding=ft.Padding.only(left=12, right=12, top=4, bottom=2),
        content=ft.Container(content=plaque, on_click=_tap, ink=False),
    )


def _composer(on_send, on_attach, field_ref: dict) -> ft.Control:
    btn_size = 44.0
    field_radius = btn_size / 2  # полный stadium, как торцы кругов 44→22

    tf = ft.TextField(
        hint_text="Сообщение",
        filled=True,
        bgcolor=liquid_glass._a("#FFFFFF", 0.0),
        border=theme.field_border(
            field_radius, color="transparent", focused_color="transparent"
        ),
        cursor_color=theme.PRIMARY,
        text_size=15,
        color=theme.INK,
        # вертикальный padding под высоту 44 — текст вровень с иконками
        content_padding=ft.Padding.symmetric(horizontal=18, vertical=8),
        text_style=ft.TextStyle(font_family=theme.FONT_FAMILY, size=15, color=theme.INK),
        hint_style=ft.TextStyle(color=theme.HINT, font_family=theme.FONT_FAMILY),
        expand=True,
        multiline=False,
        min_lines=1,
        max_lines=1,
        height=btn_size,
        on_submit=on_send,
    )
    field_ref["tf"] = tf

    message_inner = ft.Container(
        content=tf,
        expand=True,
        height=btn_size,
        border_radius=field_radius,
        bgcolor=liquid_glass.white_glass_tint(),
        blur=liquid_glass._blur(liquid_glass.BTN_BLUR),
        border=ft.Border.all(1.0, liquid_glass.white_glass_border()),
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        padding=ft.Padding.symmetric(horizontal=2, vertical=0),
        alignment=ft.Alignment.CENTER,
    )
    message_field = ft.Container(
        content=message_inner,
        expand=True,
        height=btn_size,
        border_radius=field_radius,
        clip_behavior=ft.ClipBehavior.NONE,
        alignment=ft.Alignment.CENTER,
        shadow=ft.BoxShadow(
            blur_radius=18,
            spread_radius=0,
            color=liquid_glass.white_glass_shadow(),
            offset=ft.Offset(0, 6),
        ),
    )

    # спрайты из проект/raisehand-icon-kit (light/dark + акцент)
    attach_icon = mono_icons.ui_icon("attach", size=22)
    send_icon = mono_icons.ui_icon("send", size=20, variant="onaccent")

    attach = liquid_glass.glass_circle_button(
        on_attach, content=attach_icon, size=btn_size, variant="white"
    )
    send_btn = liquid_glass.glass_circle_button(
        on_send, content=send_icon, size=btn_size, variant="purple"
    )
    # тело кнопки (с animate_scale) — для панча при отправке
    send_body = getattr(send_btn, "content", None)
    if send_body is not None:
        send_body.animate_scale = ft.Animation(160, ft.AnimationCurve.EASE_OUT_CUBIC)
        field_ref["send_body"] = send_body

    return ft.Container(
        padding=ft.Padding.only(
            left=12,
            right=12,
            top=6,
            bottom=float(theme.bottom_inset()),
        ),
        content=ft.Row(
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[attach, message_field, send_btn],
        ),
    )
