# -*- coding: utf-8 -*-
"""Экран переписки: pubsub, меню сообщений, файлы, оффлайн, пагинация, звук."""
from __future__ import annotations

import os
from typing import NamedTuple, Optional

import flet as ft

from core import gradients, logs, offline_outbox, prefs, push, rate_limit, sounds, uploads
from core.config import DATA_DIR
from core.i18n import t
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
MENU_WIDTH = 210.0
MENU_DANGER = "#E11D48"


class DisplayPrefs(NamedTuple):
    """Снимок prefs на одну сборку ленты — без повторных чтений на каждое сообщение."""

    bubble_corners: str
    font_scale: float
    show_message_time: bool
    show_read_receipts: bool
    swipe_to_reply: bool
    reduce_motion: bool
    link_previews: bool
    media_autoload: bool


def _snapshot_display_prefs() -> DisplayPrefs:
    return DisplayPrefs(
        bubble_corners=prefs.bubble_corners(),
        font_scale=prefs.font_scale(),
        show_message_time=prefs.show_message_time(),
        show_read_receipts=prefs.show_read_receipts_send(),
        swipe_to_reply=prefs.swipe_to_reply(),
        reduce_motion=prefs.reduce_motion(),
        link_previews=prefs.link_previews(),
        media_autoload=bool(
            prefs.media_auto_download_wifi() or prefs.media_auto_download_mobile()
        ),
    )


def _image_display_size(path: str, *, max_w: float) -> tuple[float, float]:
    """Ширина/высота превью без обрезки (CONTAIN), по реальному aspect ratio."""
    max_h = min(float(theme.PHONE_WIDTH) * 1.15, 480.0)
    w, h = max_w, max_w * 0.75
    try:
        from PIL import Image as _PILImage

        with _PILImage.open(path) as im:
            iw, ih = im.size
        if iw > 0 and ih > 0:
            scale = min(max_w / float(iw), max_h / float(ih), 1.0)
            w = max(120.0, float(iw) * scale)
            h = max(80.0, float(ih) * scale)
    except Exception:
        pass
    return w, h


def _approx_bubble_width(msg: chat_data.Message) -> float:
    """Ширина пузыря — панель меню делается такой же."""
    max_w = float(theme.PHONE_WIDTH) * 0.78
    if msg.image and theme._image_exists(msg.image) and not msg.deleted:
        w, _h = _image_display_size(msg.image, max_w=max_w)
        return w
    text = msg.text or ""
    if msg.deleted:
        text = t("common.deleted")
    if "\n" in text or len(text) > 36:
        return max_w
    # текст + время в одной строке
    est = 28.0 + max(len(text), 1) * 8.0 + 46.0
    return float(min(max_w, max(128.0, est)))


def _approx_bubble_height(msg: chat_data.Message) -> float:
    if msg.image and theme._image_exists(msg.image) and not msg.deleted:
        max_w = float(theme.PHONE_WIDTH) * 0.78
        _w, h = _image_display_size(msg.image, max_w=max_w)
        extra = 28.0 if (msg.text or "").strip() else 18.0
        return h + extra
    text = msg.text or ""
    if "\n" in text or len(text) > 36:
        lines = text.count("\n") + 1
        wrap = max(lines, len(text) // 32 + 1)
        return float(18 + wrap * 20 + 12)
    return 42.0


def _menu_bg() -> str:
    return liquid_glass.white_glass_tint()


def _menu_item_bg() -> str:
    return theme.PRIMARY_SOFT if theme.is_dark() else "#EEEBE6"


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


def _bubble_ticks(
    msg: chat_data.Message, dp: DisplayPrefs
) -> Optional[ft.Control]:
    """Галочки на своём сообщении; офлайн/очередь — часы из kit (status-sending)."""
    if not msg.mine or msg.deleted:
        return None
    try:
        from core import net_status

        offline = not net_status.is_online()
    except Exception:
        offline = False
    if msg.pending or offline:
        img = mono_icons.status_image("sending", size=13, on_bubble=True)
        return img or ft.Icon(ft.Icons.SCHEDULE, size=13, color="#FFFFFF99")
    # «прочитано» скрываем, если выключены read receipts
    show_read = dp.show_read_receipts
    kind = "read" if (msg.read and show_read) else "sent"
    img = mono_icons.status_image(kind, size=14, on_bubble=True)
    if img is not None:
        return img
    if msg.read and show_read:
        return ft.Icon(ft.Icons.DONE_ALL, size=14, color="#F2EFEA")
    return ft.Icon(ft.Icons.DONE, size=14, color="#FFFFFFB3")


def _meta(msg: chat_data.Message, time_color: str, dp: DisplayPrefs) -> ft.Control:
    """Время у всех сообщений; галочки — только у исходящих."""
    parts: list[ft.Control] = []
    if msg.edited and not msg.deleted:
        parts.append(
            ft.Text(t("chat.edited"), size=11, color=time_color, font_family=theme.FONT_FAMILY)
        )
    # время — если включено в оформлении
    if msg.time and dp.show_message_time:
        parts.append(
            ft.Text(msg.time, size=12, color=time_color, font_family=theme.FONT_FAMILY)
        )
    ticks = _bubble_ticks(msg, dp)
    if ticks is not None:
        parts.append(ticks)
    return ft.Row(
        spacing=4,
        tight=True,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=parts,
    )


def _corners(mine: bool, dp: DisplayPrefs):
    style = dp.bubble_corners
    if style == "sharp":
        base, tip = 8, 2
    elif style == "super":
        base, tip = 22, 8
    else:
        base, tip = 16, 5
    tl = tr = base
    if mine:
        bl, brc = base, tip
    else:
        bl, brc = tip, base
    try:
        return ft.BorderRadius(top_left=tl, top_right=tr, bottom_left=bl, bottom_right=brc)
    except Exception:
        return base


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


def _link_preview_chip(text: str, fg: str) -> Optional[ft.Control]:
    """Простое превью первой http(s)-ссылки в тексте (без сетевого fetch)."""
    import re

    m = re.search(r"https?://[^\s<>\"']+", text or "")
    if not m:
        return None
    url = m.group(0).rstrip(".,);]")
    host = url.split("/")[2] if "://" in url else url
    return ft.Container(
        bgcolor="#00000018",
        border_radius=10,
        padding=ft.Padding.symmetric(horizontal=8, vertical=6),
        content=ft.Column(
            spacing=2,
            tight=True,
            controls=[
                ft.Text(
                    host,
                    size=12,
                    weight=ft.FontWeight.W_600,
                    color=fg,
                    font_family=theme.FONT_FAMILY,
                    max_lines=1,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
                ft.Text(
                    url,
                    size=11,
                    color=fg,
                    font_family=theme.FONT_FAMILY,
                    max_lines=1,
                    overflow=ft.TextOverflow.ELLIPSIS,
                    opacity=0.75,
                ),
            ],
        ),
    )


def _text_bubble(
    msg: chat_data.Message, bg: str, fg: str, time_color: str, br, dp: DisplayPrefs
) -> ft.Control:
    if msg.deleted:
        body = ft.Text(t("chat.msg_deleted"), size=14, italic=True, color=time_color, font_family=theme.FONT_FAMILY)
        return ft.Container(
            bgcolor=bg,
            border_radius=br,
            padding=ft.Padding.symmetric(horizontal=12, vertical=7),
            content=body,
        )

    quote = _reply_quote(msg, fg)
    text = msg.text or ""
    fs = max(12, int(round(15 * dp.font_scale)))
    text_ctrl = ft.Text(text, size=fs, color=fg, font_family=theme.FONT_FAMILY)
    meta = _meta(msg, time_color, dp)
    long = len(text) > 28 or "\n" in text or text.count(" ") > 4
    link_preview = _link_preview_chip(text, fg) if dp.link_previews else None

    column_controls: list[ft.Control] = []
    if quote:
        column_controls.append(quote)
    if long:
        column_controls.extend([
                text_ctrl,
                ft.Container(alignment=ft.Alignment.CENTER_RIGHT, content=meta),
        ])
    else:
        column_controls.append(
            ft.Row(
                spacing=8,
            tight=True,
            vertical_alignment=ft.CrossAxisAlignment.END,
            controls=[text_ctrl, meta],
            )
        )
    if link_preview is not None:
        column_controls.append(link_preview)
    inner = (
        ft.Column(spacing=2, tight=True, controls=column_controls)
        if len(column_controls) > 1 or quote or link_preview
        else column_controls[0]
        )

    return ft.Container(
        bgcolor=bg,
        border_radius=br,
        padding=ft.Padding.symmetric(horizontal=12, vertical=7),
        content=inner,
    )


_photo_viewer: dict = {"path": None, "close": None}


def _show_photo(
    page: ft.Page,
    path: str,
    *,
    msg_id: str | None = None,
    chat_id: str | None = None,
    on_changed=None,
) -> None:
    """Фото на весь экран. Тап по фону или крестик закрывают."""
    if not path or not theme._image_exists(path):
        return
    if _photo_viewer.get("path") == path and _photo_viewer.get("close"):
        return
    prev = _photo_viewer.get("close")
    if prev:
        try:
            prev(True)
        except Exception:
            pass

    try:
        w = float(getattr(page, "width", 0) or 0) or float(theme.PHONE_WIDTH)
        h = float(getattr(page, "height", 0) or 0) or float(theme.PHONE_HEIGHT)
    except Exception:
        w, h = float(theme.PHONE_WIDTH), float(theme.PHONE_HEIGHT)

    reduce = False
    try:
        reduce = prefs.reduce_motion()
    except Exception:
        pass

    holder: dict = {"ctrl": None}

    def _remove() -> None:
        ctrl = holder.get("ctrl")
        holder["ctrl"] = None
        if _photo_viewer.get("path") == path:
            _photo_viewer["path"] = None
            _photo_viewer["close"] = None
        if ctrl is None:
            return
        try:
            page.overlay.remove(ctrl)
        except Exception:
            pass
        try:
            page.update()
        except Exception:
            pass

    def _close(immediate: bool = False, _e=None) -> None:
        if immediate or reduce or holder.get("ctrl") is None:
            _remove()
            return
        ctrl = holder["ctrl"]
        ctrl.opacity = 0
        try:
            photo.opacity = 0
            photo.scale = 0.98
            ctrl.update()
        except Exception:
            _remove()
            return

        async def _gone():
            import asyncio

            await asyncio.sleep(0.18)
            _remove()

        try:
            page.run_task(_gone)
        except Exception:
            _remove()

    photo = ft.Container(
        alignment=ft.Alignment.CENTER,
        opacity=1 if reduce else 0,
        scale=1 if reduce else 0.98,
        animate_opacity=theme.motion_appear(280),
        animate_scale=theme.motion_appear(360),
        content=ft.Image(src=path, fit=ft.BoxFit.CONTAIN, width=w, height=h),
    )
    close_btn = ft.Container(
        width=36,
        height=36,
        border_radius=18,
        bgcolor="#66000000",
        alignment=ft.Alignment.CENTER,
        content=ft.Icon(ft.Icons.CLOSE, color="#FFFFFF", size=22),
        on_click=lambda e: _close(False),
    )
    close_top = 54.0 if theme.is_mobile_runtime() else float(theme.SAFE_MIN_TOP) + 8

    def _photo_action(label: str, tap) -> ft.Control:
        return theme.pressable(
            ft.Container(
                padding=ft.Padding.symmetric(horizontal=12, vertical=10),
                border_radius=14,
                bgcolor="#2A2A2EE6",
                content=ft.Text(
                    label,
                    size=14,
                    weight=ft.FontWeight.W_600,
                    color="#FFFBFF",
                    font_family=theme.FONT_FAMILY,
                ),
            ),
            tap,
        )

    def _save(_e=None):
        import shutil
        from pathlib import Path

        dest_dir = Path.home() / "Downloads"
        try:
            dest_dir.mkdir(exist_ok=True)
            shutil.copy(path, dest_dir / Path(path).name)
        except Exception:
            pass

    def _delete(_e=None):
        if chat_id and msg_id:
            try:
                chat_data.delete_message(chat_id, msg_id)
            except Exception:
                pass
            if on_changed:
                on_changed()
        _close(True)

    def _forward(_e=None):
        targets: list[ft.Control] = []

        def _send(cid: str):
            def _go(_e=None, target=cid):
                chat_data.add_message(target, "", image=path, mine=True)
                try:
                    page.pop_dialog()
                except Exception:
                    pass
                _close(True)

            return _go

        for c in chat_data.sorted_contacts_for_ui():
            if c.id == chat_id:
                continue
            targets.append(
                theme.pressable(
                    ft.Container(
                        padding=ft.Padding.symmetric(horizontal=8, vertical=10),
                        content=ft.Text(c.display_name, size=16, color=theme.INK, font_family=theme.FONT_FAMILY),
                    ),
                    _send(c.id),
                )
            )
        for g in chat_data.sorted_groups():
            gid = g.id
            if gid == chat_id:
                continue

            def _send_group(_e=None, target=gid):
                msgs = chat_data._messages_of(target)
                if msgs is not None:
                    msgs.append(chat_data.Message(text="", image=path, mine=True, time="сейчас"))
                try:
                    page.pop_dialog()
                except Exception:
                    pass
                _close(True)

            targets.append(
                theme.pressable(
                    ft.Container(
                        padding=ft.Padding.symmetric(horizontal=8, vertical=10),
                        content=ft.Text(g.name, size=16, color=theme.INK, font_family=theme.FONT_FAMILY),
                    ),
                    _send_group,
                )
            )
        pick = ft.AlertDialog(
            modal=True,
            bgcolor=theme.CARD,
            title=ft.Text("Переслать", color=theme.INK, font_family=theme.FONT_FAMILY),
            content=ft.Column(tight=True, scroll=ft.ScrollMode.AUTO, height=280, controls=targets or [
                ft.Text("Нет других чатов", color=theme.MUTED, font_family=theme.FONT_FAMILY),
            ]),
            actions=[theme.action_button("Отмена", lambda e: page.pop_dialog(), width=160)],
        )
        try:
            page.show_dialog(pick)
        except Exception:
            pass

    actions_bar = ft.Container(
        left=12,
        right=12,
        bottom=24,
        content=ft.Row(
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=8,
            controls=[
                _photo_action("Переслать", _forward),
                _photo_action("Сохранить", _save),
                _photo_action("Удалить", _delete),
            ],
        ),
    )
    ctrl = ft.Container(
        width=w,
        height=h,
        bgcolor="#F2000000",
        opacity=1 if reduce else 0,
        animate_opacity=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
        content=ft.Stack(
            controls=[
                ft.Container(
                    width=w,
                    height=h,
                    alignment=ft.Alignment.CENTER,
                    on_click=lambda e: _close(False),
                    content=photo,
                ),
                ft.Container(right=16, top=close_top, content=close_btn),
                actions_bar,
            ]
        ),
    )
    holder["ctrl"] = ctrl
    _photo_viewer["path"] = path
    _photo_viewer["close"] = _close
    try:
        page.overlay.append(ctrl)
        page.update()
    except Exception:
        _photo_viewer["path"] = None
        _photo_viewer["close"] = None
        holder["ctrl"] = None
        return

    if reduce:
        return

    async def _show():
        import asyncio

        await asyncio.sleep(0.02)
        if holder.get("ctrl") is not ctrl:
            return
        ctrl.opacity = 1
        photo.opacity = 1
        photo.scale = 1
        try:
            ctrl.update()
        except Exception:
            pass

    try:
        page.run_task(_show)
    except Exception:
        ctrl.opacity = 1
        photo.opacity = 1
        photo.scale = 1


def _image_bubble(
    msg: chat_data.Message,
    bg: str,
    time_color: str,
    br,
    dp: DisplayPrefs,
    on_photo=None,
) -> ft.Control:
    max_w = float(theme.PHONE_WIDTH) * 0.78
    img_w, img_h = _image_display_size(msg.image or "", max_w=max_w)
    quote = _reply_quote(msg, theme.PRIMARY_TEXT if msg.mine else theme.INK)
    controls: list[ft.Control] = []
    if quote:
        controls.append(quote)
    if msg.deleted:
        controls.append(ft.Text(t("chat.msg_deleted"), size=14, italic=True, color=time_color))
    else:
        shot = ft.Container(
            width=img_w,
            height=img_h,
            border_radius=12,
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
            content=ft.Image(
                src=msg.image,
                width=img_w,
                height=img_h,
                fit=ft.BoxFit.CONTAIN,
                border_radius=12,
            ),
        )
        if on_photo is not None:
            shot = ft.GestureDetector(
                content=shot,
                on_tap=lambda e, p=msg.image: on_photo(p),
            )
        controls.append(shot)
        caption = (msg.text or "").strip()
        if caption:
            fs = max(12, int(round(15 * dp.font_scale)))
            controls.append(
                ft.Container(
                    padding=ft.Padding.only(left=6, right=6, top=4),
                    content=ft.Text(
                        caption,
                        size=fs,
                        color=theme.PRIMARY_TEXT if msg.mine else theme.INK,
                        font_family=theme.FONT_FAMILY,
                    ),
                )
            )
    controls.append(
                ft.Container(
                    alignment=ft.Alignment.CENTER_RIGHT,
            padding=ft.Padding.only(right=6, bottom=4, top=2),
            content=_meta(msg, time_color, dp),
        )
    )
    return ft.Container(
        width=img_w + 8,
        bgcolor=bg,
        border_radius=br,
        padding=4,
        content=ft.Column(spacing=2, tight=True, controls=controls),
    )


def _bubble_body(
    msg: chat_data.Message,
    *,
    highlighted: bool = False,
    dp: DisplayPrefs,
    on_photo=None,
) -> ft.Control:
    """Сам пузырь без жестов — подсветка на месте в ленте."""
    bg = theme.BUBBLE_OUT if msg.mine else theme.BUBBLE_IN
    fg = theme.PRIMARY_TEXT if msg.mine else theme.INK
    time_color = theme.TIME_OUT if msg.mine else theme.TIME_IN
    br = _corners(msg.mine, dp)
    max_w = float(theme.PHONE_WIDTH) * 0.72

    if msg.image and theme._image_exists(msg.image) and not msg.deleted:
        if msg.mine or dp.media_autoload:
            body = _image_bubble(msg, bg, time_color, br, dp, on_photo=on_photo)
        else:
            # автозагрузка выкл. — плейсхолдер, тап раскрывает и открывает фото
            shown = {"v": False}
            host: dict = {"c": None}

            def _reveal(_e=None):
                if not shown["v"]:
                    shown["v"] = True
                    host["c"].content = _image_bubble(
                        msg, bg, time_color, br, dp, on_photo=on_photo
                    )
                    host["c"].on_click = None
                    host["c"].ink = False
                    host["c"].padding = ft.Padding.all(0)
                    try:
                        host["c"].update()
                    except Exception:
                        pass
                if on_photo and msg.image:
                    on_photo(msg.image)

            host["c"] = ft.Container(
                bgcolor=bg,
                border_radius=br,
                padding=ft.Padding.symmetric(horizontal=14, vertical=12),
                ink=True,
                on_click=_reveal,
                content=ft.Row(
                    spacing=8,
                    tight=True,
                    controls=[
                        ft.Icon(ft.Icons.IMAGE_OUTLINED, size=18, color=fg),
                        ft.Text(
                            t("chat.photo_tap_load"),
                            size=13,
                            color=fg,
                            font_family=theme.FONT_FAMILY,
                ),
            ],
        ),
    )
            body = host["c"]
    else:
        body = _text_bubble(msg, bg, fg, time_color, br, dp)
        if len(msg.text or "") > 36 or "\n" in (msg.text or ""):
            body = ft.Container(content=body, width=max_w)

    if highlighted:
        body = ft.Container(
            content=body,
            border_radius=br,
            shadow=ft.BoxShadow(
                blur_radius=10,
                spread_radius=0,
                color="#2A283028" if not theme.is_dark() else "#00000055",
                offset=ft.Offset(0, 2),
            ),
            border=ft.Border.all(1.2, theme.PRIMARY),
        )
    return body

def _sender_nick_label(msg: chat_data.Message) -> ft.Control:
    nick = msg.sender_nick or msg.sender_first or t("common.participant")
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
    dp: Optional[DisplayPrefs] = None,
) -> ft.Control:
    if msg.date:
        return _date_chip(msg.date)

    if dp is None:
        dp = _snapshot_display_prefs()

    align = ft.MainAxisAlignment.END if msg.mine else ft.MainAxisAlignment.START

    def _open_photo(path: str | None = None):
        opener = actions.get("open_photo")
        if opener and (path or msg.image):
            try:
                opener(path or msg.image, msg.id)
            except TypeError:
                opener(path or msg.image)

    body = _bubble_body(
        msg, highlighted=highlighted, dp=dp, on_photo=_open_photo
    )

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
            return
        if (
            msg.image
            and not msg.deleted
            and theme._image_exists(msg.image)
            and (msg.mine or dp.media_autoload)
        ):
            _open_photo(msg.image)

    swipe_state = {"dx": 0.0}
    swipe_on = dp.swipe_to_reply

    def _pan_update(e):
        if not swipe_on:
            return
        try:
            dx = float(getattr(getattr(e, "local_delta", None), "x", 0) or 0)
        except Exception:
            dx = 0.0
        swipe_state["dx"] += dx

    def _pan_end(_e=None):
        if not swipe_on:
            swipe_state["dx"] = 0.0
            return
        dx = swipe_state["dx"]
        swipe_state["dx"] = 0.0
        # свайп вправо (входящие) / влево (свои) → ответ
        if (not msg.mine and dx > 48) or (msg.mine and dx < -48):
            reply = actions.get("reply")
            if reply:
                reply(msg)

    pressed = ft.GestureDetector(
        content=body,
        on_tap=_tap,
        on_long_press_start=_long,
        on_secondary_tap=_long,  # ПКМ на десктопе
        on_horizontal_drag_update=_pan_update if swipe_on else None,
        on_horizontal_drag_end=_pan_end if swipe_on else None,
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
    if animate_in and not dp.reduce_motion:
        start_scale = ft.Scale(scale=0.96, alignment=origin)
        start_offset = (
            ft.Offset(0.02, 0.06) if msg.mine else ft.Offset(-0.015, 0.05)
        )
        motion = ft.Container(
            content=row,
            opacity=0,
            scale=start_scale,
            offset=start_offset,
            animate_opacity=theme.motion_appear(320),
            animate_scale=theme.motion_appear(380),
            animate_offset=theme.motion_appear(380),
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
        left.append(mono_icons.ui_icon(sprite, size=16))
    left.append(
        ft.Text(
            label,
            size=14,
            color=color,
            weight=ft.FontWeight.W_500,
            font_family=theme.FONT_FAMILY,
            max_lines=1,
        )
    )
    row = ft.Container(
        border_radius=10,
        bgcolor=_menu_item_bg() if not danger else ("#3A1A22" if theme.is_dark() else "#FEE2E8"),
        padding=ft.Padding.symmetric(horizontal=12, vertical=7),
        content=ft.Row(spacing=8, controls=left),
    )
    return theme.pressable(row, on_click, scale_to=theme.PRESS_SCALE)


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
            t("chat.edit"),
            lambda e: (close(), actions["edit"](msg)),
            sprite="edit",
        ))
    rows.append(_menu_row(
        t("chat.copy"),
        lambda e: (close(), actions["copy"](msg)),
        sprite="copy",
    ))
    rows.append(_menu_row(
        t("chat.reply"),
        lambda e: (close(), actions["reply"](msg)),
        sprite="reply",
    ))
    if not msg.deleted:
        rows.append(_menu_row(
            t("chat.delete_msg"),
            lambda e: (close(), actions["delete"](msg)),
            danger=True,
            sprite="delete",
        ))
    if not msg.mine and not msg.deleted and actions.get("report"):
        rows.append(_menu_row(
            t("chat.report"),
            lambda e: (close(), actions["report"](msg)),
            danger=True,
            sprite="flag",
        ))

    return ft.Container(
        width=width,
        bgcolor=_menu_bg(),
        border_radius=MENU_RADIUS,
        padding=5,
        shadow=theme.grounded_shadow(lift=6),
        border=None,
        content=ft.Column(spacing=2, tight=True, controls=rows),
    )


def _same_sender(a: Optional[chat_data.Message], b: chat_data.Message) -> bool:
    if a is None or a.date or b.date:
        return False
    if a.mine and b.mine:
        return True
    if a.mine != b.mine:
        return False
    return (a.sender_seed or a.sender_nick) == (b.sender_seed or b.sender_nick)


def _chat_top_inset() -> float:
    """Отступ кнопок шапки под статус / Dynamic Island (полку фона не рисуем)."""
    return 54.0 if theme.is_mobile_runtime() else float(theme.SAFE_MIN_TOP)


def _chat_header_h() -> float:
    return _chat_top_inset() + 58.0


def _chat_composer_h() -> float:
    return 48.0 + 4.0 + float(theme.bottom_inset()) + 14.0


def _build_message_controls(
    messages: list[chat_data.Message],
    actions: dict,
    *,
    is_group: bool = False,
    highlight_id: Optional[str] = None,
    dp: Optional[DisplayPrefs] = None,
    top_inset: float = 0.0,
    bottom_inset: float = 0.0,
) -> list[ft.Control]:
    out: list[ft.Control] = []
    if top_inset > 0:
        out.append(ft.Container(height=top_inset))
    prev: Optional[chat_data.Message] = None
    menu_open = bool(highlight_id)
    if dp is None:
        dp = _snapshot_display_prefs()
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
                dp=dp,
            )
        )
        prev = msg
    if bottom_inset > 0:
        out.append(ft.Container(height=bottom_inset))
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
    on_search=None,
) -> ft.Control:
    chrome_shadow = ft.BoxShadow(
        blur_radius=22,
        spread_radius=0,
        color=liquid_glass.white_glass_shadow(),
        offset=ft.Offset(0, 6),
    )

    back_icon = mono_icons.ui_icon("back", size=22)
    back_btn = liquid_glass.glass_circle_button(
        on_back, content=back_icon, size=44, variant="white"
    )
    try:
        back_btn.shadow = chrome_shadow
    except Exception:
        pass

    short = title if full_title else (title.split()[0] if title else (first or "?"))
    # Та же белая заливка и высота, что у кругов «назад» и «пожаловаться».
    avatar: ft.Control = _avatar_circle(seed, first or short[:1], last, size=36)
    title_block: ft.Control = ft.Column(
        spacing=0,
        tight=True,
        expand=True,
        alignment=ft.MainAxisAlignment.CENTER,
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
    )
    account = ft.Container(
        expand=True,
        height=50,
        border_radius=25,
        bgcolor=liquid_glass.white_glass_tint(),
        padding=ft.Padding.only(left=7, right=16),
        alignment=ft.Alignment.CENTER_LEFT,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        ink=False,
        animate_scale=theme.motion_press_out(),
        scale=1,
        content=ft.Row(
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[avatar, title_block],
        ),
    )
    pressed = (
        liquid_glass._press_wrap(account, on_profile, scale_to=0.97, expand=True)
        if on_profile is not None
        else account
    )
    pill_wrap = ft.Container(
        expand=True,
        height=50,
        border_radius=25,
        clip_behavior=ft.ClipBehavior.NONE,
        shadow=chrome_shadow,
        content=pressed,
    )

    report_btn = None
    if on_report is not None:
        flag = ft.Icon(ft.Icons.FLAG_OUTLINED, size=20, color=theme.PRIMARY)
        report_btn = liquid_glass.glass_circle_button(
            on_report, content=flag, size=44, variant="white"
        )
        try:
            report_btn.shadow = chrome_shadow
        except Exception:
            pass

    row_controls: list[ft.Control] = [back_btn, pill_wrap]
    if on_search is not None:
        find_icon = ft.Icon(ft.Icons.SEARCH, size=20, color=theme.INK)
        find_btn = liquid_glass.glass_circle_button(
            on_search, content=find_icon, size=44, variant="white"
        )
        try:
            find_btn.shadow = chrome_shadow
        except Exception:
            pass
        row_controls.append(find_btn)
    if report_btn is not None:
        row_controls.append(report_btn)

    return ft.Container(
        padding=ft.Padding.only(
            left=12, right=12, top=_chat_top_inset(), bottom=0
        ),
        bgcolor=ft.Colors.TRANSPARENT,
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
        peer_status = t("chat.favorites_status") if is_favorites else contact.status
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

    try:
        from core import net_status as _net0

        _online0 = _net0.is_online()
    except Exception:
        _online0 = True

    state = {
        "offset": 0,
        "loaded": 0,
        "reply_to": None,
        "edit_id": None,
        "online": _online0,
        "alive": True,
        "menu_msg": None,
        "is_group": is_group,
        "chat_id": cid,
        "picking": False,
        "file_picker": None,
        "dp": _snapshot_display_prefs(),
        "pending_image": None,
        "query": "",
    }

    online_label = ft.Text(
        peer_status if _online0 else t("common.offline_queue"),
        size=12,
        color=STATUS_MUTED,
        font_family=theme.FONT_FAMILY,
    )
    banner_text = ft.Text(
        "",
        size=14,
        weight=ft.FontWeight.W_600,
        color=theme.INK,
        font_family=theme.FONT_FAMILY,
        expand=True,
    )
    banner_bar = ft.Container(
        visible=False,
        opacity=0,
        offset=ft.Offset(0, 0.08),
        animate_opacity=theme.motion_appear(280),
        animate_offset=theme.motion_appear(320),
        margin=ft.Margin.symmetric(horizontal=12, vertical=6),
        padding=ft.Padding.symmetric(horizontal=14, vertical=10),
        border_radius=16,
        bgcolor=theme.CARD,
        border=None,
        shadow=theme.grounded_shadow(lift=4),
    )
    field_ref: dict = {}

    # Scrim ловит тап в «пустое» место; панель — поверх, с анимацией.
    # Само сообщение остаётся в ленте (только подсветка).
    menu_card_host = ft.Container(
        left=24,
        top=200,
        opacity=0,
        scale=0.98,
        offset=ft.Offset(0, 0.06),
        animate_opacity=theme.motion_appear(280),
        animate_offset=theme.motion_appear(320),
        animate_scale=theme.motion_appear(340),
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
        query = (state.get("query") or "").strip().lower()
        if query:
            window = [
                m
                for m in _all_messages()
                if not m.date and query in (m.text or "").lower()
            ]
        else:
            window = _page_msgs(PAGE_SIZE + state["offset"], 0)
        state["loaded"] = len(window)
        list_col.controls = _build_message_controls(
            window,
            actions,
            is_group=is_group,
            highlight_id=_highlight_id(),
            dp=state.get("dp"),
            top_inset=_chat_header_h(),
            bottom_inset=_chat_composer_h(),
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
        if not visible:
            banner_bar.opacity = 0
            banner_bar.offset = ft.Offset(0, 0.08)
            banner_bar.visible = False
            try:
                banner_bar.update()
            except Exception:
                pass
            return
        banner_bar.visible = True
        banner_bar.opacity = 0
        banner_bar.offset = ft.Offset(0, 0.08)
        try:
            banner_bar.update()
        except Exception:
            pass

        async def _in():
            import asyncio

            await asyncio.sleep(0.02)
            banner_bar.opacity = 1
            banner_bar.offset = ft.Offset(0, 0)
            try:
                banner_bar.update()
            except Exception:
                pass

        try:
            page.run_task(_in)
        except Exception:
            banner_bar.opacity = 1
            banner_bar.offset = ft.Offset(0, 0)

    def _clear_composer_modes() -> None:
        state["reply_to"] = None
        state["edit_id"] = None
        _set_banner("", visible=False)
        tf = field_ref.get("tf")
        if tf is not None:
            tf.hint_text = t("chat.hint_message")
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
            theme.pressable(
                ft.Container(
                    padding=ft.Padding.symmetric(horizontal=10, vertical=6),
                    border_radius=12,
                    bgcolor=theme.SURFACE,
                    border=None,
                    content=ft.Text(
                        t("common.cancel"),
                        size=14,
                        weight=ft.FontWeight.W_700,
                        color=theme.INK,
                        font_family=theme.FONT_FAMILY,
                    ),
                ),
                cancel_banner,
            ),
        ],
    )

    def on_copy(msg: chat_data.Message):
        text = msg.text or ""
        try:
            page.set_clipboard(text)
            STATE.snack(t("common.copied"))
        except Exception:
            STATE.snack(text[:80] if text else t("common.empty"))

    def on_reply(msg: chat_data.Message):
        state["edit_id"] = None
        state["reply_to"] = msg.id
        _set_banner(t("chat.reply_banner", preview=(msg.text or t("common.photo"))[:40]), visible=True)
        tf = field_ref.get("tf")
        if tf is not None:
            tf.hint_text = t("chat.reply_hint")
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
        tf.hint_text = t("chat.edit_hint")
        _set_banner(t("chat.edit_banner"), visible=True)
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
            menu_card_host.scale = 0.94
            menu_card_host.offset = ft.Offset(0, 0.06)
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
        if msg.mine:
            left += max(0.0, bw - MENU_WIDTH)
        left = max(8.0, min(left, float(theme.PHONE_WIDTH) - MENU_WIDTH - 8.0))
        menu_card_host.left = left
        menu_card_host.top = top
        menu_card_host.content = ft.GestureDetector(
            on_tap=lambda _e: None,
            content=_context_menu_card(msg, actions, close_menu, width=MENU_WIDTH),
        )
        scrim.opacity = 0
        menu_card_host.opacity = 0
        menu_card_host.scale = 0.94
        menu_card_host.offset = ft.Offset(0, 0.06)
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
            menu_card_host.scale = 1
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
            menu_card_host.scale = 1
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
        "open_photo": lambda path, mid=None: _show_photo(
            page,
            path,
            msg_id=mid,
            chat_id=cid,
            on_changed=_refresh_list,
        ),
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
            padding=ft.Padding.only(top=4, bottom=8),
            auto_scroll=False,
            controls=_build_message_controls(
                initial,
                actions,
                is_group=is_group,
                dp=state["dp"],
                top_inset=_chat_header_h(),
                bottom_inset=_chat_composer_h(),
            ),
        )
    except Exception:
        list_col = ft.Column(
            spacing=0,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
            controls=_build_message_controls(
                initial,
                actions,
                is_group=is_group,
                dp=state["dp"],
                top_inset=_chat_header_h(),
                bottom_inset=_chat_composer_h(),
            ),
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
        t("chat.load_earlier"),
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
        closer = _photo_viewer.get("close")
        if closer:
            try:
                closer(True)
            except Exception:
                pass
        state["alive"] = False
        # Снять фокус с композера ДО смены роута — иначе iOS оставляет клавиатуру на /home
        try:
            theme.dismiss_keyboard(page, field_ref.get("tf"))
        except Exception:
            pass
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
            dp=state.get("dp"),
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
            motion.scale = ft.Scale(scale=1.02, alignment=origin)
            try:
                motion.update()
            except Exception:
                return
            await asyncio.sleep(0.16)
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

    pending_preview = ft.Container(visible=False, padding=ft.Padding.only(left=12, right=12, top=4))

    def _refresh_pending_preview() -> None:
        path_img = state.get("pending_image")
        tf = field_ref.get("tf")
        sync = field_ref.get("sync_send")
        if sync is not None:
            typed = (tf.value or "") if tf is not None else ""
            sync(typed, force=bool(path_img) or None)
        if not path_img or not theme._image_exists(path_img):
            pending_preview.visible = False
            pending_preview.content = None
            if tf is not None:
                tf.hint_text = t("chat.hint_message")
                try:
                    tf.update()
                except Exception:
                    pass
            try:
                pending_preview.update()
            except Exception:
                pass
            return
        thumb_w, thumb_h = _image_display_size(path_img, max_w=96.0)
        thumb_h = min(thumb_h, 72.0)
        thumb_w = min(thumb_w, 96.0)

        def _clear_pending(_e=None):
            state["pending_image"] = None
            _refresh_pending_preview()

        pending_preview.content = ft.Container(
            bgcolor=theme.CARD,
            border_radius=16,
            padding=ft.Padding.all(8),
            border=None,
            content=ft.Row(
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.GestureDetector(
                        on_tap=lambda e, p=path_img: _show_photo(page, p),
                        content=ft.Container(
                            width=thumb_w,
                            height=thumb_h,
                            border_radius=10,
                            clip_behavior=ft.ClipBehavior.HARD_EDGE,
                            content=ft.Image(
                                src=path_img,
                                width=thumb_w,
                                height=thumb_h,
                                fit=ft.BoxFit.COVER,
                            ),
                        ),
                    ),
                    ft.Column(
                        expand=True,
                        spacing=2,
                        tight=True,
                        controls=[
                            ft.Text(
                                "Фото готово к отправке",
                                size=13,
                                weight=ft.FontWeight.W_600,
                                color=theme.INK,
                                font_family=theme.FONT_FAMILY,
                            ),
                            ft.Text(
                                "Напишите подпись и нажмите отправить",
                                size=12,
                                color=theme.MUTED,
                                font_family=theme.FONT_FAMILY,
                            ),
                        ],
                    ),
                    ft.IconButton(
                        icon=ft.Icons.CLOSE_ROUNDED,
                        icon_size=20,
                        icon_color=theme.MUTED,
                        on_click=_clear_pending,
                    ),
                ],
            ),
        )
        pending_preview.visible = True
        if tf is not None:
            tf.hint_text = "Подпись к фото…"
            try:
                tf.update()
            except Exception:
                pass
        try:
            pending_preview.update()
        except Exception:
            pass

    def on_send(_=None):
        tf = field_ref.get("tf")
        if not tf:
            return
        text = (tf.value or "").strip()
        pending_image = state.get("pending_image")

        # Режим редактирования — меняем существующее сообщение, не шлём новое
        edit_id = state.get("edit_id") or ""
        if edit_id:
            if not text:
                return
            updated = chat_data.edit_message(cid, edit_id, text)
            if updated is None:
                STATE.error(t("chat.edit_failed"))
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

        if not text and not pending_image:
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
        image = pending_image
        state["pending_image"] = None
        _refresh_pending_preview()
        _clear_composer_modes()

        if is_favorites:
            _deliver_now(text, image, reply_to, pending=False)
            return

        if not state["online"]:
            offline_outbox.enqueue(
                chat_id=cid,
                text=text,
                attachment_path=image,
                reply_to_id=reply_to,
            )
            _deliver_now(text, image, reply_to, pending=True)
            STATE.snack(t("chat.offline_queue") if not image else t("chat.offline_file"))
            return

        try:
            _deliver_now(text, image, reply_to, pending=False)
        except Exception as exc:
            offline_outbox.enqueue(
                chat_id=cid,
                text=text,
                attachment_path=image,
                reply_to_id=reply_to,
            )
            _deliver_now(text, image, reply_to, pending=True)
            STATE.snack(t("chat.offline_saved", detail=exc))

    def _ensure_picker() -> ft.FilePicker:
        picker = state.get("file_picker")
        if picker is not None:
            return picker
        picker = ft.FilePicker()
        try:
            page.services.append(picker)
        except Exception:
            try:
                page.overlay.append(picker)
                page.update()
            except Exception:
                pass
        state["file_picker"] = picker
        return picker

    def _attach_path(path: str) -> None:
        """Файл выбран: фото → превью+подпись; остальное — сразу в чат."""
        if not path or not state.get("alive"):
            return
        try:
            stored = uploads.save_upload(path, subdir="chat")
        except uploads.UploadError as exc:
            STATE.error(str(exc))
            return

        if state.get("edit_id"):
            STATE.snack(t("chat.finish_edit"))
            return

        if uploads.is_image(stored):
            state["pending_image"] = stored
            _refresh_pending_preview()
            return

        reply_to = state["reply_to"]
        _clear_composer_modes()
        text = os.path.basename(stored)
        if is_favorites:
            _deliver_now(text, None, reply_to, pending=False)
            return
        if not state["online"]:
            offline_outbox.enqueue(
                chat_id=cid,
                text=text,
                attachment_path=stored,
                reply_to_id=reply_to,
            )
            _deliver_now(text, None, reply_to, pending=True)
            STATE.snack(t("chat.offline_file"))
            return
        _deliver_now(text, None, reply_to, pending=False)

    def _pick_files(*, kind: str) -> None:
        """kind: gallery | camera | file"""
        if state.get("picking") or not state.get("alive"):
            return
        state["picking"] = True

        async def _pick():
            try:
                picker = _ensure_picker()
                if kind == "gallery":
                    files = await picker.pick_files(
                        dialog_title="Галерея",
                        allow_multiple=False,
                        file_type=ft.FilePickerFileType.IMAGE,
                        compression_quality=0,
                    )
                elif kind == "camera":
                    # Системный IMAGE-пикер: на телефоне часто есть пункт «Снять фото».
                    files = await picker.pick_files(
                        dialog_title="Камера / фото",
                        allow_multiple=False,
                        file_type=ft.FilePickerFileType.IMAGE,
                        compression_quality=0,
                    )
                else:
                    files = await picker.pick_files(
                        dialog_title=t("chat.file_dialog"),
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
                    STATE.error(t("chat.file_pick_failed", detail=exc))
            finally:
                state["picking"] = False

        try:
            page.run_task(_pick)
        except Exception as exc:
            state["picking"] = False
            STATE.error(t("chat.file_open_failed", detail=exc))

    attach_open = {"v": False}
    attach_gen = {"n": 0}
    lift = float(theme.bottom_inset()) + 64
    _anchor = ft.Alignment(-1, 1)

    def _attach_row(icon, label: str, kind: str) -> ft.Control:
        def _tap(_e=None, k=kind):
            _set_attach_menu(False)
            _pick_files(kind=k)

        return ft.Container(
            opacity=0,
            offset=ft.Offset(0, 0.35),
            animate_opacity=ft.Animation(180, ft.AnimationCurve.EASE_OUT),
            animate_offset=ft.Animation(240, ft.AnimationCurve.EASE_OUT_CUBIC),
            content=theme.pressable(
                ft.Container(
                    border_radius=16,
                    padding=ft.Padding.symmetric(horizontal=8, vertical=6),
                    content=ft.Row(
                        spacing=12,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Container(
                                width=36,
                                height=36,
                                border_radius=18,
                                bgcolor=theme.PRIMARY_SOFT,
                                alignment=ft.Alignment.CENTER,
                                content=ft.Icon(icon, size=20, color=theme.PRIMARY),
                            ),
                            ft.Text(
                                label,
                                size=16,
                                weight=ft.FontWeight.W_500,
                                color=theme.INK,
                                font_family=theme.FONT_FAMILY,
                            ),
                        ],
                    ),
                ),
                _tap,
                scale_to=theme.PRESS_SCALE,
            ),
        )

    attach_rows = [
        _attach_row(ft.Icons.PHOTO_CAMERA_OUTLINED, "Камера", "camera"),
        _attach_row(ft.Icons.PHOTO_LIBRARY_OUTLINED, "Галерея", "gallery"),
        _attach_row(ft.Icons.ATTACH_FILE_ROUNDED, "Файл", "file"),
    ]

    attach_card = ft.Container(
        visible=False,
        opacity=0,
        scale=ft.Scale(0.96, alignment=_anchor),
        offset=ft.Offset(0, 0.06),
        animate_opacity=theme.motion_appear(280),
        animate_scale=theme.motion_appear(360),
        animate_offset=theme.motion_appear(360),
        width=228,
        left=10,
        bottom=lift,
        border_radius=22,
        bgcolor=theme.CARD,
        border=None,
        shadow=theme.grounded_shadow(lift=8),
        padding=ft.Padding.symmetric(horizontal=6, vertical=6),
        content=ft.Column(spacing=2, tight=True, controls=attach_rows),
    )

    def _rows_at(shown: bool) -> None:
        for row in attach_rows:
            row.opacity = 1 if shown else 0
            row.offset = ft.Offset(0, 0) if shown else ft.Offset(0, 0.35)

    def _paint_attach() -> None:
        try:
            attach_scrim.update()
            attach_card.update()
        except Exception:
            pass

    def _set_attach_menu(on: bool) -> None:
        attach_open["v"] = on
        attach_gen["n"] += 1
        token = attach_gen["n"]
        reduce = False
        try:
            reduce = prefs.reduce_motion()
        except Exception:
            pass

        if on:
            attach_scrim.visible = True
            attach_card.visible = True
            if reduce:
                attach_scrim.opacity = 1
                attach_card.opacity = 1
                attach_card.scale = ft.Scale(1, alignment=_anchor)
                attach_card.offset = ft.Offset(0, 0)
                _rows_at(True)
                _paint_attach()
                return
            attach_scrim.opacity = 0
            attach_card.opacity = 0
            attach_card.scale = ft.Scale(0.55, alignment=_anchor)
            attach_card.offset = ft.Offset(0, 0.18)
            _rows_at(False)
            _paint_attach()

            async def _show():
                import asyncio

                await asyncio.sleep(0.02)
                if token != attach_gen["n"] or not attach_open["v"]:
                    return
                attach_scrim.opacity = 1
                attach_card.opacity = 1
                attach_card.scale = ft.Scale(1, alignment=_anchor)
                attach_card.offset = ft.Offset(0, 0)
                _paint_attach()
                for row in attach_rows:
                    await asyncio.sleep(0.045)
                    if token != attach_gen["n"] or not attach_open["v"]:
                        return
                    row.opacity = 1
                    row.offset = ft.Offset(0, 0)
                    try:
                        row.update()
                    except Exception:
                        pass

            try:
                page.run_task(_show)
            except Exception:
                attach_scrim.opacity = 1
                attach_card.opacity = 1
                attach_card.scale = ft.Scale(1, alignment=_anchor)
                attach_card.offset = ft.Offset(0, 0)
                _rows_at(True)
                _paint_attach()
            return

        if reduce:
            attach_scrim.opacity = 0
            attach_card.opacity = 0
            attach_card.visible = False
            attach_scrim.visible = False
            _rows_at(False)
            _paint_attach()
            return

        attach_scrim.opacity = 0
        attach_card.opacity = 0
        attach_card.scale = ft.Scale(0.72, alignment=_anchor)
        attach_card.offset = ft.Offset(0, 0.12)
        _rows_at(False)
        _paint_attach()

        async def _hide():
            import asyncio

            await asyncio.sleep(0.2)
            if token != attach_gen["n"] or attach_open["v"]:
                return
            attach_card.visible = False
            attach_scrim.visible = False
            _paint_attach()

        try:
            page.run_task(_hide)
        except Exception:
            attach_card.visible = False
            attach_scrim.visible = False
            _paint_attach()

    def _scrim_tap(_e=None):
        _set_attach_menu(False)

    attach_scrim = ft.Container(
        visible=False,
        opacity=0,
        animate_opacity=ft.Animation(180, ft.AnimationCurve.EASE_OUT),
        expand=True,
        bgcolor="#00000022",
        on_click=_scrim_tap,
    )

    def on_attach(_=None):
        """Меню вложений над кнопкой — камера, галерея, файл."""
        if state.get("picking") or not state.get("alive"):
            return
        if state.get("edit_id"):
            STATE.snack(t("chat.finish_edit"))
            return
        _set_attach_menu(not attach_open["v"])

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
                    sender_nick=payload.get("sender_nick") or t("common.participant"),
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

                img_path = (m.image or "").strip()
                if img_path and _prefs.save_to_gallery():
                    try:
                        import shutil

                        gal = os.path.join(DATA_DIR, "gallery")
                        os.makedirs(gal, exist_ok=True)
                        if os.path.isfile(img_path):
                            dest = os.path.join(gal, os.path.basename(img_path))
                            if not os.path.isfile(dest):
                                shutil.copy2(img_path, dest)
                    except Exception:
                        pass
                muted_chat = (not is_group) and chat_data.is_muted(cid)
                if not muted_chat:
                    sounds.play_ding()
                if (not muted_chat) and _prefs.notif_allowed(is_group=bool(is_group)):
                    preview = (m.text or t("common.photo"))[:80]
                    if not _prefs.notif_preview():
                        preview = t("common.new_message")
                    push.notify(peer_title or t("common.message"), preview)
        elif mtype == "chat_typing":
            if not prefs.show_typing():
                return
            if message.get("from_user") and STATE.user and message["from_user"] == STATE.user.public_id:
                return
            online_label.value = t("chat.typing")
            try:
                online_label.update()
            except Exception:
                pass

            async def _restore_status():
                import asyncio

                await asyncio.sleep(2.2)
                if not state.get("alive"):
                    return
                online_label.value = peer_status if state.get("online", True) else t("common.offline_queue")
                try:
                    online_label.update()
                except Exception:
                    pass

            try:
                page.run_task(_restore_status)
            except Exception:
                pass
        elif mtype == "chat_edit":
            chat_data.edit_message(cid, message.get("msg_id"), message.get("text") or "")
            _refresh_list()
        elif mtype == "chat_delete":
            chat_data.delete_message(cid, message.get("msg_id"))
            _refresh_list()
        elif mtype == "net_status":
            state["online"] = bool(message.get("online", True))
            online_label.value = peer_status if state["online"] else t("common.offline_queue")
            try:
                online_label.update()
            except Exception:
                pass
            # Часы ↔ галочки на пузырях
            try:
                _refresh_list()
            except Exception:
                pass
            if state["online"]:
                flush_outbox()

    try:
        page.pubsub.subscribe(on_pubsub)
    except Exception:
        pass

    # реконнект / первичная досылка (только если сеть уже есть)
    if state["online"]:
        flush_outbox()

    _typing_sent = {"t": 0.0}

    def _on_composer_change(_e=None):
        if not prefs.show_typing() or is_favorites:
            return
        import time

        now = time.time()
        if now - _typing_sent["t"] < 1.6:
            return
        _typing_sent["t"] = now
        try:
            page.pubsub.send_all(
                {
                    "type": "chat_typing",
                    "chat_id": cid,
                    "from_user": getattr(STATE.user, "public_id", None),
                }
            )
        except Exception:
            pass

    composer = _composer(on_send, on_attach, field_ref, on_change=_on_composer_change)

    def open_contact_profile(_=None):
        if is_group or contact is None or is_favorites:
            return
        from flet_app.screens.contact_profile import contact_route

        STATE.draft["_profile_contact_id"] = contact.id
        STATE.draft["_open_chat_id"] = contact.id
        STATE.draft["_open_is_group"] = False
        STATE.go(contact_route(contact.id))

    def open_group_profile(_=None):
        if not is_group or group is None:
            return
        STATE.draft["_profile_group_id"] = group.id
        STATE.draft["_open_chat_id"] = group.id
        STATE.draft["_open_is_group"] = True
        STATE.go("/group_profile")

    search_field = ft.TextField(
        hint_text="Поиск в чате",
        filled=True,
        bgcolor=theme.FIELD_BG,
        color=theme.INK,
        cursor_color=theme.PRIMARY,
        border=theme.field_border(22, color="transparent", focused_color=theme.PRIMARY),
        text_style=ft.TextStyle(font_family=theme.FONT_FAMILY, size=15, color=theme.INK),
        hint_style=ft.TextStyle(font_family=theme.FONT_FAMILY, size=15, color=theme.HINT),
        content_padding=ft.Padding.symmetric(horizontal=16, vertical=10),
        on_change=lambda e: (
            state.__setitem__("query", e.control.value or ""),
            _refresh_list(),
        ),
    )
    search_wrap = ft.Container(
        visible=bool(STATE.draft.pop("_chat_search_open", False)),
        padding=ft.Padding.only(left=12, right=12, bottom=8),
        content=search_field,
    )
    if search_wrap.visible:
        state["query"] = ""

    def toggle_search(_=None):
        search_wrap.visible = not search_wrap.visible
        if not search_wrap.visible:
            state["query"] = ""
            search_field.value = ""
            _refresh_list()
        try:
            search_wrap.update()
        except Exception:
            pass

    header_ctrl = _header(
        title=peer_title,
        seed=peer_seed,
        first=peer_first,
        last=peer_last,
        on_back=go_back,
        online_label=online_label,
        full_title=is_group or is_favorites,
        on_report=None if (is_group or is_favorites) else on_report_user,
        on_profile=open_group_profile if is_group else (None if is_favorites else open_contact_profile),
        on_search=None,
    )

    # Шапка и композер поверх ленты — без полос фона до края экрана.
    body_controls: list = [
        search_wrap,
        ft.Container(padding=ft.Padding.symmetric(horizontal=12), content=load_older_btn),
        banner_bar,
        list_col,
    ]
    dock_controls: list = []
    if is_group and group is not None:
        from flet_app import questions_data

        q_count = questions_data.sync_group_count(group.id)

        def _open_questions(_=None):
            STATE.draft["_questions_group_id"] = group.id
            STATE.draft["_open_chat_id"] = group.id
            STATE.draft["_open_is_group"] = True
            STATE.go("/questions")

        dock_controls.append(
            _questions_plaque(count=q_count, on_open=_open_questions)
        )
    dock_controls.append(pending_preview)
    dock_controls.append(composer)

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

    dim = float(prefs.chat_bg_dim() or 0.0)
    stack_controls: list[ft.Control] = [chat_body]
    if dim > 0.01:
        stack_controls.insert(
            0,
            ft.Container(
                expand=True,
                bgcolor=f"#000000{int(min(dim, 0.4) * 255):02X}",
            ),
        )
    stack_controls.append(
        ft.Container(
            left=0,
            right=0,
            top=0,
            bgcolor=ft.Colors.TRANSPARENT,
            content=header_ctrl,
        )
    )
    stack_controls.append(
        ft.Container(
            left=0,
            right=0,
            bottom=0,
            bgcolor=ft.Colors.TRANSPARENT,
            content=ft.Column(
                spacing=0,
                tight=True,
                controls=dock_controls,
            ),
        )
    )
    stack_controls.append(menu_host)
    stack_controls.append(attach_scrim)
    stack_controls.append(attach_card)
    root = ft.Container(
        expand=True,
        bgcolor=theme.BG,
        content=ft.Stack(
            expand=True,
            controls=stack_controls,
        ),
    )
    return theme.edge_swipe_back(root, on_back=go_back)


def _questions_plaque(*, count: int = 0, on_open=None) -> ft.Control:
    """Плашка «Вопросы» над композером в групповом чате."""
    eye = mono_icons.ui_icon("eye", size=22)
    count_label = t("common.none") if count <= 0 else str(int(count))

    def _tap(_=None):
        if on_open:
            on_open()
        else:
            try:
                STATE.snack(t("chat.questions_snack"))
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
                        t("chat.questions_title"),
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
                        t("chat.questions_watch"),
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


def _composer(on_send, on_attach, field_ref: dict, on_change=None) -> ft.Control:
    # Пропорции как в Telegram: круги ≈ поле по высоте, поле тянется по ширине
    # Скрепка крупнее — удобнее тапать на телефоне
    btn_size = 44.0
    attach_size = 48.0
    field_radius = btn_size / 2
    gap = 6.0
    fs = max(14, int(round(16 * prefs.font_scale())))

    tf = ft.TextField(
        hint_text=t("chat.hint_message"),
        filled=True,
        bgcolor=liquid_glass._a("#FFFFFF", 0.0),
        border=theme.field_border(
            field_radius, color="transparent", focused_color="transparent"
        ),
        cursor_color=theme.PRIMARY,
        text_size=fs,
        color=theme.INK,
        content_padding=ft.Padding.symmetric(horizontal=14, vertical=8),
        text_style=ft.TextStyle(font_family=theme.FONT_FAMILY, size=fs, color=theme.INK),
        hint_style=ft.TextStyle(
            color=theme.HINT, font_family=theme.FONT_FAMILY, size=fs
        ),
        expand=True,
        multiline=prefs.chat_send_by_ctrl_enter() or not prefs.chat_enter_to_send(),
        min_lines=1,
        max_lines=4 if (prefs.chat_send_by_ctrl_enter() or not prefs.chat_enter_to_send()) else 1,
        height=btn_size if prefs.chat_enter_to_send() and not prefs.chat_send_by_ctrl_enter() else None,
        on_submit=on_send
        if prefs.chat_enter_to_send() and not prefs.chat_send_by_ctrl_enter()
        else None,
        on_change=None,
    )
    field_ref["tf"] = tf

    message_inner = ft.Container(
        content=tf,
        expand=True,
        height=btn_size,
        border_radius=field_radius,
        bgcolor=theme.CARD,
        border=None,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        padding=0,
        alignment=ft.Alignment.CENTER_LEFT,
    )
    message_field = ft.Container(
        content=message_inner,
        expand=True,
        height=btn_size,
        border_radius=field_radius,
        clip_behavior=ft.ClipBehavior.NONE,
        alignment=ft.Alignment.CENTER,
        shadow=theme.grounded_shadow(lift=4),
    )

    attach_icon = mono_icons.ui_icon("attach", size=28)
    send_icon = mono_icons.ui_icon("send", size=20, variant="onaccent")

    attach = liquid_glass.glass_circle_button(
        on_attach, content=attach_icon, size=attach_size, variant="white"
    )
    send_btn = liquid_glass.glass_circle_button(
        on_send, content=send_icon, size=btn_size, variant="purple"
    )
    try:
        send_btn.shadow = None
    except Exception:
        pass
    gd = getattr(send_btn, "content", None)
    send_body = getattr(gd, "content", None) if gd is not None else None
    if send_body is not None:
        send_body.animate_scale = theme.motion_press_out()
        field_ref["send_body"] = send_body

    send_host = ft.Container(
        width=0,
        height=btn_size,
        opacity=0,
        scale=0.35,
        border_radius=btn_size / 2,
        animate=ft.Animation(180, ft.AnimationCurve.EASE_OUT),
        animate_opacity=ft.Animation(160, ft.AnimationCurve.EASE_OUT),
        animate_scale=ft.Animation(320, ft.AnimationCurve.EASE_OUT_BACK),
        content=send_btn,
    )

    def _sync_send(text: str = "", *, force: bool | None = None) -> None:
        show = bool(force) if force is not None else bool((text or "").strip())
        if show:
            send_host.animate_scale = ft.Animation(320, ft.AnimationCurve.EASE_OUT_BACK)
            send_host.width = btn_size + gap
            send_host.opacity = 1
            send_host.scale = 1
        else:
            send_host.animate_scale = ft.Animation(140, ft.AnimationCurve.EASE_IN)
            send_host.scale = 0.35
            send_host.opacity = 0
            send_host.width = 0
        try:
            send_host.update()
        except Exception:
            pass

    def _changed(e):
        _sync_send(getattr(e, "control", e).value if e is not None else "")
        if on_change is not None:
            on_change(e)

    tf.on_change = _changed
    field_ref["sync_send"] = _sync_send

    # Без нижней «полки» фона: прозрачный контейнер; inset снизу сохраняем.
    return ft.Container(
        bgcolor=ft.Colors.TRANSPARENT,
        padding=ft.Padding.only(
            left=8,
            right=8,
            top=4,
            bottom=float(theme.bottom_inset()) + 14,
        ),
        content=ft.Row(
            spacing=gap,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[attach, message_field, send_host],
        ),
    )
