# -*- coding: utf-8 -*-
"""Отдельный экран жалобы на пользователя → Discord через бота."""
from __future__ import annotations

import flet as ft

from core import blacklist, logs, push, reports
from flet_app import liquid_glass, mono_icons, theme
from flet_app.app_state import STATE


def report_route() -> str:
    return "/report"


def _back(_=None):
    back = STATE.draft.get("_report_back") or "/chat"
    if back == "/chat":
        cid = STATE.draft.get("_report_chat_id") or STATE.draft.get("_open_chat_id")
        if cid:
            STATE.draft["_open_chat_id"] = cid
            STATE.draft["_open_is_group"] = False
    STATE.go(back)


def _card(content: ft.Control) -> ft.Control:
    card_w = float(theme.PHONE_WIDTH - 32)
    return ft.Container(
        width=card_w,
        alignment=ft.Alignment.CENTER,
        content=liquid_glass.glass_capsule(
            content,
            radius=22,
            blur=liquid_glass.BTN_BLUR,
            tint=liquid_glass.white_glass_tint(),
            border_color=liquid_glass.white_glass_border(),
            padding=ft.Padding.all(16),
            shadow=True,
            highlight=True,
            width=card_w,
        ),
    )


def build_report(page: ft.Page) -> ft.Control:
    target = (STATE.draft.get("_report_target_pid") or "").strip() or "—"
    chat_id = str(STATE.draft.get("_report_chat_id") or "")
    msg_id = str(STATE.draft.get("_report_msg_id") or "")

    reason_dd = ft.Dropdown(
        label="Причина",
        value=reports.REPORT_REASONS[0],
        options=[ft.dropdown.Option(r) for r in reports.REPORT_REASONS],
        filled=True,
        bgcolor=theme.FIELD_BG,
        color=theme.INK,
        border=theme.field_border(16, color=theme.STROKE, focused_color=theme.PRIMARY),
        text_style=ft.TextStyle(font_family=theme.FONT_FAMILY, color=theme.INK),
        label_style=ft.TextStyle(color=theme.MUTED, font_family=theme.FONT_FAMILY),
        dense=True,
        expand=True,
    )
    details_tf = ft.TextField(
        label="Описание",
        hint_text="Что произошло? Коротко опишите ситуацию",
        multiline=True,
        min_lines=4,
        max_lines=8,
        filled=True,
        bgcolor=theme.FIELD_BG,
        color=theme.INK,
        border=theme.field_border(16, color=theme.STROKE, focused_color=theme.PRIMARY),
        cursor_color=theme.PRIMARY,
        text_style=ft.TextStyle(font_family=theme.FONT_FAMILY, color=theme.INK),
        hint_style=ft.TextStyle(color=theme.HINT, font_family=theme.FONT_FAMILY),
        label_style=ft.TextStyle(color=theme.MUTED, font_family=theme.FONT_FAMILY),
    )
    status_text = ft.Text("", size=13, color=theme.MUTED, font_family=theme.FONT_FAMILY)
    sending = {"on": False}
    btns_ref: dict = {}

    def _set_busy(on: bool, label: str = "") -> None:
        sending["on"] = on
        if label:
            status_text.value = label
            status_text.color = theme.MUTED
        for b in btns_ref.values():
            try:
                b.disabled = on
                b.update()
            except Exception:
                pass
        try:
            status_text.update()
        except Exception:
            pass

    def submit(*, also_block: bool = False):
        if sending["on"]:
            return
        details = (details_tf.value or "").strip()
        if not details:
            status_text.value = "Нужно описание жалобы"
            status_text.color = "#E11D48"
            try:
                status_text.update()
            except Exception:
                pass
            return
        if target in ("", "—"):
            status_text.value = "Не указан ID пользователя"
            status_text.color = "#E11D48"
            try:
                status_text.update()
            except Exception:
                pass
            return

        _set_busy(
            True,
            "Отправка в Discord…" if not also_block else "Жалоба и блокировка…",
        )

        async def _send():
            import asyncio

            await asyncio.sleep(0.05)
            try:
                rid = reports.submit_report(
                    reporter_id=STATE.user.id if STATE.user else None,
                    reporter_public_id=getattr(STATE.user, "public_id", "") or "",
                    target_public_id=target,
                    reason=reason_dd.value or reports.REPORT_REASONS[0],
                    details=details,
                    chat_id=chat_id,
                    msg_id=msg_id,
                )
                blocked_ok = False
                if also_block and STATE.user is not None:
                    display = (
                        (STATE.draft.get("_report_target_name") or "").strip()
                        or target
                    )
                    blocked_ok = blacklist.block(
                        STATE.user.public_id,
                        target,
                        name=display,
                    )
                try:
                    if also_block and blocked_ok:
                        push.notify(
                            "Жалоба и блокировка",
                            f"№{rid} · {target} в чёрном списке",
                        )
                    else:
                        push.notify("Жалоба отправлена", f"№{rid}")
                except Exception:
                    pass
                if also_block and blocked_ok:
                    STATE.snack(f"Жалоба №{rid} · пользователь в чёрном списке")
                else:
                    STATE.snack(f"Жалоба №{rid} отправлена модераторам")
                _back()
            except reports.ReportError as exc:
                logs.error("report failed: %s", exc)
                _set_busy(False)
                status_text.value = str(exc)
                status_text.color = "#E11D48"
                try:
                    status_text.update()
                except Exception:
                    pass
                STATE.error(str(exc), "Жалоба")
            except Exception as exc:
                logs.error("report failed: %s", exc)
                _set_busy(False)
                status_text.value = str(exc)
                status_text.color = "#E11D48"
                try:
                    status_text.update()
                except Exception:
                    pass
                STATE.error(str(exc), "Жалоба")

        try:
            page.run_task(_send)
        except Exception as exc:
            _set_busy(False)
            STATE.error(str(exc), "Жалоба")

    back = liquid_glass.glass_circle_button(
        _back,
        content=mono_icons.ui_icon("back", size=22),
        size=44,
        variant="white",
    )
    header = ft.Container(
        padding=ft.Padding.symmetric(horizontal=12, vertical=8),
        content=ft.Row(
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                back,
                ft.Text(
                    "Пожаловаться",
                    size=20,
                    weight=ft.FontWeight.W_700,
                    color=theme.INK,
                    font_family=theme.FONT_FAMILY,
                    expand=True,
                ),
            ],
        ),
    )

    target_card = _card(
        ft.Column(
            spacing=6,
            tight=True,
            controls=[
                ft.Text("Пользователь", size=13, color=theme.MUTED, font_family=theme.FONT_FAMILY),
                ft.Text(
                    target,
                    size=22,
                    weight=ft.FontWeight.W_700,
                    color=theme.INK,
                    font_family=theme.FONT_FAMILY,
                    selectable=True,
                ),
                ft.Text(
                    "ID из приложения — уйдёт модераторам в Discord",
                    size=12,
                    color=theme.MUTED,
                    font_family=theme.FONT_FAMILY,
                ),
            ],
        )
    )

    form_card = _card(
        ft.Column(
            spacing=14,
            tight=True,
            controls=[
                reason_dd,
                details_tf,
                status_text,
            ],
        )
    )

    submit_btn = liquid_glass.purple_glass_button(
        "Отправить жалобу",
        lambda e=None: submit(also_block=False),
        expand=True,
    )
    submit_block_btn = ft.Container(
        ink=True,
        on_click=lambda e=None: submit(also_block=True),
        border_radius=18,
        bgcolor=theme.FIELD_BG,
        padding=ft.Padding.symmetric(horizontal=16, vertical=14),
        border=ft.Border.all(1, theme.STROKE),
        content=ft.Text(
            "Жалоба + в чёрный список",
            size=15,
            weight=ft.FontWeight.W_600,
            color=theme.INK,
            font_family=theme.FONT_FAMILY,
            text_align=ft.TextAlign.CENTER,
        ),
    )
    btns_ref["submit"] = submit_btn
    btns_ref["block"] = submit_block_btn

    scroller = ft.ListView(
        expand=True,
        spacing=12,
        padding=ft.Padding.only(left=16, right=16, top=8, bottom=28),
        controls=[
            ft.Container(alignment=ft.Alignment.CENTER, content=target_card),
            ft.Container(alignment=ft.Alignment.CENTER, content=form_card),
            ft.Container(alignment=ft.Alignment.CENTER, content=submit_btn),
            ft.Container(alignment=ft.Alignment.CENTER, content=submit_block_btn),
            ft.Text(
                "Чёрный список: пользователь исчезнет из поиска, "
                "новый чат с ним открыть будет нельзя.",
                size=12,
                color=theme.MUTED,
                font_family=theme.FONT_FAMILY,
                text_align=ft.TextAlign.CENTER,
            ),
        ],
    )

    wrap = ft.Container(
        expand=True,
        opacity=0,
        offset=ft.Offset(0, 0.04),
        animate_opacity=ft.Animation(260, ft.AnimationCurve.EASE_OUT),
        animate_offset=ft.Animation(280, ft.AnimationCurve.EASE_OUT),
        bgcolor=theme.BG,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        content=ft.Column(
            expand=True,
            spacing=0,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[
                header,
                scroller,
            ],
        ),
    )

    async def _play():
        import asyncio

        await asyncio.sleep(0.03)
        wrap.opacity = 1
        wrap.offset = ft.Offset(0, 0)
        try:
            wrap.update()
        except Exception:
            pass

    try:
        page.run_task(_play)
    except Exception:
        wrap.opacity = 1
        wrap.offset = ft.Offset(0, 0)

    return wrap


def register_routes() -> dict:
    return {report_route(): build_report}
