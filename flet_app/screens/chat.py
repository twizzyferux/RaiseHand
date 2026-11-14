# -*- coding: utf-8 -*-
"""Экран переписки — полировка UX/UI, только спрайты из проекта."""
from __future__ import annotations

import flet as ft

from core import gradients
from flet_app import chat_data
from flet_app.app_state import STATE
from flet_app import theme

BUBBLE_IN_BG = "#F0F0F5"
BUBBLE_OUT_BG = "#4B2FE0"
TIME_IN = "#7A7A85"       # контрастнее на сером
TIME_OUT = "#EDE7FF"      # светлее на фиолетовом
DATE_BG = "#E8E8EE"
HEADER_PILL = "#F5F5F8"
STATUS_MUTED = "#8A8A8E"


def _sprite(*parts: str) -> str:
    return theme.asset("assets", "images", *parts)


def _status_icon(kind: str) -> str:
    return _sprite("chats", f"status_{kind}.png")


def _avatar_circle(seed: str, first: str, last: str, size: float = 40) -> ft.Control:
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
            bgcolor=DATE_BG,
            border_radius=14,
            padding=ft.Padding.symmetric(horizontal=14, vertical=5),
            content=ft.Text(label, size=12, color=STATUS_MUTED, font_family=theme.FONT_FAMILY),
        ),
    )


def _meta(msg: chat_data.Message, time_color: str) -> ft.Control:
    """Время 12px + галочки из спрайтов status_sent / status_read."""
    parts: list[ft.Control] = [
        ft.Text(msg.time, size=12, color=time_color, font_family=theme.FONT_FAMILY),
    ]
    if msg.mine:
        kind = "read" if msg.read else "sent"
        path = _status_icon(kind)
        if theme._image_exists(path):
            parts.append(ft.Image(src=path, width=15, height=15, fit=ft.BoxFit.CONTAIN))
    return ft.Row(
        spacing=4,
        tight=True,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=parts,
    )


def _corners(mine: bool):
    """Хвостик к отправителю: свой — справа снизу, чужой — слева снизу."""
    tl = tr = 16
    # mine справа: острый bottom_right; входящий слева: острый bottom_left
    if mine:
        bl, brc = 16, 5
    else:
        bl, brc = 5, 16
    try:
        return ft.BorderRadius(top_left=tl, top_right=tr, bottom_left=bl, bottom_right=brc)
    except Exception:
        try:
            return ft.BorderRadius(tl, tr, bl, brc)
        except Exception:
            return 16


def _text_bubble(msg: chat_data.Message, bg: str, fg: str, time_color: str, br) -> ft.Control:
    """Короткое — текст и время в одной строке; длинное — время снизу справа."""
    text = msg.text or ""
    text_ctrl = ft.Text(text, size=15, color=fg, font_family=theme.FONT_FAMILY)
    meta = _meta(msg, time_color)
    long = len(text) > 28 or "\n" in text or text.count(" ") > 4

    if long:
        inner = ft.Column(
            spacing=2,
            tight=True,
            controls=[
                text_ctrl,
                ft.Container(alignment=ft.Alignment.CENTER_RIGHT, content=meta),
            ],
        )
    else:
        inner = ft.Row(
            spacing=10,
            tight=True,
            vertical_alignment=ft.CrossAxisAlignment.END,
            controls=[text_ctrl, meta],
        )

    return ft.Container(
        bgcolor=bg,
        border_radius=br,
        padding=ft.Padding.symmetric(horizontal=12, vertical=7),
        content=inner,
    )


def _image_bubble(msg: chat_data.Message, bg: str, time_color: str, br) -> ft.Control:
    img_w = 220
    return ft.Container(
        width=img_w,
        bgcolor=bg,
        border_radius=br,
        padding=4,
        content=ft.Column(
            spacing=2,
            tight=True,
            controls=[
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
                ),
                ft.Container(
                    alignment=ft.Alignment.CENTER_RIGHT,
                    padding=ft.Padding.only(right=6, bottom=2),
                    content=_meta(msg, time_color),
                ),
            ],
        ),
    )


def _bubble(msg: chat_data.Message, *, gap_top: float) -> ft.Control:
    if msg.date:
        return _date_chip(msg.date)

    align = ft.MainAxisAlignment.END if msg.mine else ft.MainAxisAlignment.START
    bg = BUBBLE_OUT_BG if msg.mine else BUBBLE_IN_BG
    fg = "#FFFFFF" if msg.mine else theme.INK
    time_color = TIME_OUT if msg.mine else TIME_IN
    br = _corners(msg.mine)
    max_w = float(theme.PHONE_WIDTH) * 0.72

    if msg.image and theme._image_exists(msg.image):
        body = _image_bubble(msg, bg, time_color, br)
    else:
        body = _text_bubble(msg, bg, fg, time_color, br)
        # длинные ограничиваем по ширине
        if len(msg.text or "") > 36 or "\n" in (msg.text or ""):
            body = ft.Container(content=body, width=max_w)

    return ft.Container(
        padding=ft.Padding.only(
            left=12 if not msg.mine else 48,
            right=12 if msg.mine else 48,
            top=gap_top,
            bottom=2,
        ),
        content=ft.Row(
            alignment=align,
            tight=True,
            controls=[body],
        ),
    )


def _build_message_controls(messages: list[chat_data.Message]) -> list[ft.Control]:
    """Группировка: тот же автор подряд — 2px, смена автора — 10px."""
    out: list[ft.Control] = []
    prev_mine = None
    for msg in messages:
        if msg.date:
            out.append(_date_chip(msg.date))
            prev_mine = None
            continue
        if prev_mine is None:
            gap = 6.0
        elif prev_mine == msg.mine:
            gap = 2.0
        else:
            gap = 10.0
        out.append(_bubble(msg, gap_top=gap))
        prev_mine = msg.mine
    return out


def _header(contact: chat_data.Contact, on_back) -> ft.Control:
    back_src = _sprite("chat", "back_chevron.png")
    if not theme._image_exists(back_src):
        back_src = _sprite("raisehand", "back.png")

    back_btn = ft.Container(
        width=40,
        height=40,
        border_radius=20,
        bgcolor=HEADER_PILL,
        alignment=ft.Alignment.CENTER,
        on_click=on_back,
        content=(
            ft.Image(src=back_src, width=22, height=22, fit=ft.BoxFit.CONTAIN)
            if theme._image_exists(back_src)
            else ft.Text("‹", size=32, color=theme.PRIMARY)
        ),
    )

    short = contact.first or (contact.name.split() or ["?"])[0]
    pill = ft.Container(
        expand=True,
        bgcolor=HEADER_PILL,
        border_radius=28,
        padding=ft.Padding.only(left=6, right=16, top=6, bottom=6),
        content=ft.Row(
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                _avatar_circle(contact.seed, contact.first, contact.last, size=40),
                ft.Column(
                    spacing=0,
                    tight=True,
                    controls=[
                        ft.Text(
                            short,
                            size=16,
                            weight=ft.FontWeight.W_600,
                            color=theme.INK,
                            font_family=theme.FONT_FAMILY,
                        ),
                        ft.Text(
                            contact.status,
                            size=12,
                            color=STATUS_MUTED,
                            font_family=theme.FONT_FAMILY,
                        ),
                    ],
                ),
            ],
        ),
    )

    # назад СЛЕВА (стандарт iOS/Android)
    return ft.Container(
        padding=ft.Padding.symmetric(horizontal=12, vertical=12),
        content=ft.Row(
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[back_btn, pill],
        ),
    )


def _composer(on_send, field_ref: dict) -> ft.Control:
    import os
    # Явные пути: Flet на Windows лучше берёт absolute path
    candidates_attach = [
        theme.asset("assets", "images", "chat", "attach.png"),
        theme.asset("assets", "images", "raisehand", "attach.png"),
        os.path.join(os.getcwd(), "assets", "images", "chat", "attach.png"),
        os.path.join(os.getcwd(), "assets", "images", "raisehand", "attach.png"),
    ]
    attach_src = next((c for c in candidates_attach if os.path.isfile(c)), candidates_attach[0])

    candidates_send = [
        theme.asset("assets", "images", "raisehand", "send.png"),
        os.path.join(os.getcwd(), "assets", "images", "raisehand", "send.png"),
    ]
    send_src = next((c for c in candidates_send if os.path.isfile(c)), candidates_send[0])

    tf = ft.TextField(
        hint_text="Сообщение",
        border_radius=28,
        filled=True,
        bgcolor="#F0F0F5",
        border_color="transparent",
        focused_border_color=theme.PRIMARY,
        cursor_color=theme.PRIMARY,
        text_size=15,
        color=theme.INK,
        content_padding=ft.Padding.symmetric(horizontal=18, vertical=12),
        text_style=ft.TextStyle(font_family=theme.FONT_FAMILY, size=15, color=theme.INK),
        hint_style=ft.TextStyle(color=theme.HINT, font_family=theme.FONT_FAMILY),
        expand=True,
        multiline=True,
        min_lines=1,
        max_lines=5,
        on_submit=on_send,
    )
    field_ref["tf"] = tf

    # скрепка: только наш PNG, без emoji-fallback (на Win emoji может рисоваться «лицом»)
    attach = ft.Container(
        width=44,
        height=44,
        border_radius=22,
        bgcolor="#F0F0F5",
        alignment=ft.Alignment.CENTER,
        content=ft.Image(
            src=attach_src,
            width=26,
            height=26,
            fit=ft.BoxFit.CONTAIN,
        ),
    )

    # кнопка отправки: серый фон — send.png фиолетовый, на PRIMARY не видно
    send_btn = ft.Container(
        width=44,
        height=44,
        border_radius=22,
        bgcolor="#F0F0F5",
        alignment=ft.Alignment.CENTER,
        on_click=on_send,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        content=(
            ft.Image(src=send_src, width=22, height=22, fit=ft.BoxFit.CONTAIN)
            if theme._image_exists(send_src)
            else ft.Text("➤", size=18, color=theme.PRIMARY)
        ),
    )

    return ft.Container(
        padding=ft.Padding.only(left=12, right=12, top=6, bottom=14),
        content=ft.Row(
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.END,
            controls=[attach, tf, send_btn],
        ),
    )


def build_chat(page: ft.Page) -> ft.Control:
    cid = STATE.draft.get("_open_chat_id") or "c2"
    contact = chat_data.get_contact(cid) or chat_data.CONTACTS[0]
    chat_data.mark_read(contact.id)

    photo = _sprite("photo_2026-09-30_00-09-10.jpg")
    # path is assets/images/photo...
    photo = theme.asset("assets", "images", "photo_2026-09-30_00-09-10.jpg")
    if theme._image_exists(photo):
        chat_data.attach_demo_photo(photo)

    msg_controls = _build_message_controls(contact.messages)
    try:
        list_col = ft.ListView(
            expand=True,
            spacing=0,
            padding=ft.Padding.symmetric(vertical=4),
            auto_scroll=True,
            controls=msg_controls,
        )
    except Exception:
        list_col = ft.Column(
            spacing=0,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
            controls=msg_controls,
            auto_scroll=True,
        )

    field_ref: dict = {}

    def go_back(_=None):
        STATE.go("/home")

    def on_send(_=None):
        tf = field_ref.get("tf")
        if not tf:
            return
        text = (tf.value or "").strip()
        if not text:
            return
        tf.value = ""
        try:
            tf.update()
        except Exception:
            pass
        m = chat_data.add_message(contact.id, text, mine=True)
        if m:
            # gap: как от своего к своему
            gap = 2.0
            if contact.messages and len(contact.messages) >= 2:
                prev = contact.messages[-2]
                if not prev.date and prev.mine != m.mine:
                    gap = 10.0
            list_col.controls.append(_bubble(m, gap_top=gap))
            try:
                list_col.update()
            except Exception:
                pass

    return ft.Container(
        bgcolor=theme.BG,
        expand=True,
        width=theme.PHONE_WIDTH,
        content=ft.Column(
            expand=True,
            spacing=0,
            controls=[
                _header(contact, go_back),
                list_col,
                _composer(on_send, field_ref),
            ],
        ),
    )
