# -*- coding: utf-8 -*-
"""Новый чат и новая группа / класс."""
from __future__ import annotations

import flet as ft

from core import auth
from core.i18n import t
from flet_app import chat_data, liquid_glass, theme
from flet_app.app_state import STATE

SUBJECTS = (
    "math",
    "physics",
    "literature",
    "history",
    "chemistry",
    "biology",
    "geography",
    "cs",
    "english",
    "russian",
)
CLASS_NUMBERS = tuple(str(n) for n in range(1, 12))
CLASS_LETTERS = ("А", "Б", "В", "Г", "Д", "Е")


def _me_id() -> int | None:
    return int(STATE.user.id) if STATE.user is not None else None


def _contacts_allowed() -> bool:
    from core import prefs

    return prefs.get("contacts_perm") == "yes"


def _accounts() -> list[auth.User]:
    if not _contacts_allowed():
        return []
    try:
        return auth.list_accounts(exclude_user_id=_me_id())
    except Exception:
        return []


def _matches(user: auth.User, query: str) -> bool:
    q = (query or "").strip().lower().lstrip("@")
    if not q:
        return True
    blob = " ".join(
        [
            user.display_name or "",
            user.first_name or "",
            user.last_name or "",
            user.nickname or "",
            user.public_id or "",
            user.contact_value or "",
        ]
    ).lower()
    digits = "".join(ch for ch in q if ch.isdigit())
    if digits and digits in "".join(ch for ch in (user.contact_value or "") if ch.isdigit()):
        return True
    return q in blob


def _open_direct(user: auth.User) -> None:
    from flet_app.screens.home import _open_found_account

    def go(contact: chat_data.Contact):
        def _(_e=None):
            chat_data.mark_read(contact.id)
            STATE.draft["_open_chat_id"] = contact.id
            STATE.draft["_open_is_group"] = False
            STATE.go("/chat")

        return _

    _open_found_account(
        public_id=user.public_id,
        name=user.display_name,
        first=user.first_name,
        last=user.last_name,
        status=user.status_text or t("common.online"),
        role=user.role,
        on_open=go,
    )


def _close_to(tab: str) -> None:
    STATE.draft["_home_tab"] = tab
    STATE.go("/home")


def _reveal(panel: ft.Control, page: ft.Page) -> None:
    """Дорисовать панель уже на экране, чтобы сработал fade и подъём."""
    async def _go():
        import asyncio

        await asyncio.sleep(0.03)
        try:
            panel.opacity = 1
            panel.offset = ft.Offset(0, 0)
            panel.scale = 1
            panel.update()
        except Exception:
            pass

    try:
        page.run_task(_go)
    except Exception:
        try:
            panel.opacity = 1
            panel.offset = ft.Offset(0, 0)
            panel.scale = 1
        except Exception:
            pass


def _header(title: str, on_close) -> ft.Control:
    btn = liquid_glass.glass_circle_button(
        on_close,
        content=ft.Icon(ft.Icons.CLOSE, size=20, color=theme.INK),
        size=36,
        variant="white",
    )
    return ft.Container(
        padding=ft.Padding.only(left=8, right=12, top=6, bottom=8),
        content=ft.Stack(
            height=40,
            controls=[
                ft.Container(
                    alignment=ft.Alignment.CENTER,
                    content=ft.Text(
                        title,
                        size=17,
                        weight=ft.FontWeight.W_600,
                        color=theme.INK,
                        font_family=theme.FONT_FAMILY,
                    ),
                ),
                ft.Container(alignment=ft.Alignment.CENTER_RIGHT, content=btn),
            ],
        ),
    )


def _action_row(icon, label: str, on_click) -> ft.Control:
    row = ft.Container(
        padding=ft.Padding.symmetric(horizontal=16, vertical=12),
        content=ft.Row(
            spacing=14,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(
                    width=40,
                    height=40,
                    border_radius=20,
                    bgcolor=theme.PRIMARY_SOFT,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Icon(icon, size=22, color=theme.PRIMARY),
                ),
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
    return theme.pressable(row, on_click, scale_to=theme.PRESS_SCALE, expand=True)


def _person_row(user: auth.User, on_click, *, picked: bool = False) -> ft.Control:
    from flet_app.screens.home import _avatar_from_seed

    nick = f"@{user.nickname}" if user.nickname else f"ID {user.public_id}"
    if user.contact_value:
        sub = user.contact_value
    else:
        sub = nick
    body = ft.Container(
        padding=ft.Padding.symmetric(horizontal=16, vertical=8),
        content=ft.Row(
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                _avatar_from_seed(
                    user.public_id or user.first_name,
                    user.first_name,
                    user.last_name,
                    size=48,
                ),
                ft.Column(
                    expand=True,
                    spacing=2,
                    tight=True,
                    controls=[
                        ft.Text(
                            user.display_name,
                            size=16,
                            weight=ft.FontWeight.W_600,
                            color=theme.INK,
                            font_family=theme.FONT_FAMILY,
                            max_lines=1,
                        ),
                        ft.Text(
                            sub,
                            size=13,
                            color=theme.MUTED,
                            font_family=theme.FONT_FAMILY,
                            max_lines=1,
                        ),
                    ],
                ),
                ft.Icon(ft.Icons.CHECK_CIRCLE, color=theme.PRIMARY, size=22)
                if picked
                else ft.Container(width=22),
            ],
        ),
    )
    return theme.pressable(body, on_click, scale_to=theme.PRESS_SCALE, expand=True)


def _search_field(hint: str, on_change) -> ft.TextField:
    return ft.TextField(
        hint_text=hint,
        prefix_icon=ft.Icons.SEARCH,
        filled=True,
        bgcolor=theme.FIELD_BG,
        border=theme.field_border(22, color="transparent", focused_color=theme.PRIMARY),
        color=theme.INK,
        cursor_color=theme.PRIMARY,
        text_style=ft.TextStyle(font_family=theme.FONT_FAMILY, size=15, color=theme.INK),
        hint_style=ft.TextStyle(font_family=theme.FONT_FAMILY, size=15, color=theme.HINT),
        content_padding=ft.Padding.symmetric(horizontal=8, vertical=12),
        on_change=on_change,
    )


def _ask_phone(page: ft.Page) -> None:
    field = ft.TextField(
        hint_text=t("newchat.phone_hint"),
        keyboard_type=ft.KeyboardType.PHONE,
        filled=True,
        bgcolor=theme.FIELD_BG,
        color=theme.INK,
        cursor_color=theme.PRIMARY,
        border=theme.field_border(14, color="transparent", focused_color=theme.PRIMARY),
        text_style=ft.TextStyle(font_family=theme.FONT_FAMILY, color=theme.INK),
        autofocus=True,
    )

    def close(_=None):
        try:
            page.pop_dialog()
        except Exception:
            pass

    def find(_=None):
        user = None
        try:
            user = auth.find_by_phone(field.value or "")
        except Exception:
            user = None
        close()
        if user is None or (STATE.user and user.id == STATE.user.id):
            STATE.snack(t("newchat.no_account"))
            return
        _open_direct(user)

    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Text(t("newchat.phone_title"), font_family=theme.FONT_FAMILY, color=theme.INK),
        content=field,
        actions=[theme.dialog_buttons(t("common.cancel"), close, t("newchat.find"), find)],
        actions_alignment=ft.MainAxisAlignment.CENTER,
    )
    try:
        page.show_dialog(dlg)
    except Exception:
        STATE.snack(t("newchat.phone_title"))


def build_new_chat(page: ft.Page) -> ft.Control:
    query = {"v": ""}
    people_host = ft.Column(spacing=0, tight=True)
    section = ft.Text(
        t("newchat.contacts_section"),
        size=13,
        weight=ft.FontWeight.W_600,
        color=theme.MUTED,
        font_family=theme.FONT_FAMILY,
    )

    def paint():
        rows: list[ft.Control] = []
        if not _contacts_allowed():
            def allow(_=None):
                from core import prefs

                prefs.set_pref("contacts_perm", "yes")
                paint()

            rows.append(
                ft.Container(
                    padding=ft.Padding.symmetric(horizontal=16, vertical=18),
                    content=ft.Column(
                        spacing=10,
                        tight=True,
                        controls=[
                            ft.Text(
                                t("newchat.need_perm"),
                                size=14,
                                color=theme.MUTED,
                                font_family=theme.FONT_FAMILY,
                            ),
                            theme.pressable(
                                ft.Container(
                                    border_radius=14,
                                    bgcolor=theme.PRIMARY_SOFT,
                                    padding=ft.Padding.symmetric(horizontal=14, vertical=8),
                                    content=ft.Text(
                                        t("newchat.allow"),
                                        size=14,
                                        weight=ft.FontWeight.W_600,
                                        color=theme.PRIMARY,
                                        font_family=theme.FONT_FAMILY,
                                    ),
                                ),
                                allow,
                                scale_to=theme.PRESS_SCALE,
                            ),
                        ],
                    ),
                )
            )
        else:
            shown = [u for u in _accounts() if _matches(u, query["v"])]
            letter = ""
            if not shown:
                rows.append(
                    ft.Container(
                        padding=ft.Padding.symmetric(horizontal=16, vertical=18),
                        content=ft.Text(
                            t("newchat.empty"),
                            size=14,
                            color=theme.MUTED,
                            font_family=theme.FONT_FAMILY,
                        ),
                    )
                )
            for user in shown:
                mark = (user.display_name[:1] or "#").upper()
                if mark != letter:
                    letter = mark
                    rows.append(
                        ft.Container(
                            padding=ft.Padding.only(left=16, right=16, top=12, bottom=4),
                            content=ft.Text(
                                letter,
                                size=13,
                                weight=ft.FontWeight.W_600,
                                color=theme.MUTED,
                                font_family=theme.FONT_FAMILY,
                            ),
                        )
                    )
                rows.append(_person_row(user, lambda e, u=user: _open_direct(u)))
        people_host.controls = rows
        try:
            people_host.update()
        except Exception:
            pass

    def on_query(e):
        query["v"] = (e.control.value or "") if e is not None else ""
        paint()

    def open_group(_=None):
        STATE.draft["_group_mode"] = "group"
        STATE.draft["_compose_back"] = "chats"
        STATE.go("/new_group")

    paint()
    screen = ft.Column(
        expand=True,
        spacing=0,
        controls=[
            _header(t("newchat.title"), lambda _: _close_to("chats")),
            ft.Container(
                padding=ft.Padding.symmetric(horizontal=16, vertical=4),
                content=_search_field(t("newchat.search"), on_query),
            ),
            ft.Container(
                margin=ft.Margin.symmetric(horizontal=12, vertical=8),
                border_radius=18,
                bgcolor=theme.CARD,
                clip_behavior=ft.ClipBehavior.HARD_EDGE,
                content=ft.Column(
                    spacing=0,
                    tight=True,
                    controls=[
                        _action_row(ft.Icons.GROUPS_OUTLINED, t("newchat.group"), open_group),
                        ft.Container(height=1, bgcolor=theme.DIVIDER, margin=ft.Margin.only(left=70)),
                        _action_row(ft.Icons.PERSON_ADD_ALT_1_OUTLINED, t("newchat.contact"), lambda _: _ask_phone(page)),
                    ],
                ),
            ),
            ft.Container(
                padding=ft.Padding.only(left=16, right=16, top=6, bottom=4),
                content=section,
            ),
            ft.Column(
                expand=True,
                scroll=ft.ScrollMode.AUTO,
                spacing=0,
                controls=[people_host, ft.Container(height=24)],
            ),
        ],
    )
    panel = theme.live_panel(screen, visible=True)
    try:
        panel.expand = True
    except Exception:
        pass
    return panel


def build_new_group(page: ft.Page) -> ft.Control:
    mode = STATE.draft.get("_group_mode") or "group"
    back_tab = STATE.draft.get("_compose_back") or ("groups" if mode == "class" else "chats")
    is_class = mode == "class"
    subject = {"v": "math"}
    grade = {"num": "10", "letter": "А"}
    picked: set[int] = set()
    host = ft.Column(expand=True, spacing=0)

    def _generated() -> str:
        return f"{t('subj.' + subject['v'])} · {grade['num']}{grade['letter']}"

    name = {"v": _generated() if is_class else ""}

    def _go_back(_=None):
        _close_to("groups" if is_class else back_tab)

    def _chip_box(label: str, on: bool) -> tuple[ft.Control, float]:
        # Ширина заранее: иначе ряд сжимается до экрана и сдвигать некуда.
        width = 52 + len(label) * 12
        box = ft.Container(
            width=width,
            height=44,
            border_radius=16,
            alignment=ft.Alignment.CENTER,
            bgcolor=theme.PRIMARY_SOFT if on else theme.FIELD_BG,
            border=ft.Border.all(2, theme.PRIMARY) if on else None,
            content=ft.Text(
                label,
                size=15,
                weight=ft.FontWeight.W_600 if on else ft.FontWeight.W_500,
                color=theme.PRIMARY if on else theme.INK,
                font_family=theme.FONT_FAMILY,
                text_align=ft.TextAlign.CENTER,
                no_wrap=True,
            ),
        )
        return box, width

    def _pick_subject(key: str) -> None:
        subject["v"] = key
        name["v"] = _generated()
        paint()

    def _pick_num(value: str) -> None:
        grade["num"] = value
        name["v"] = _generated()
        paint()

    def _pick_letter(value: str) -> None:
        grade["letter"] = value
        name["v"] = _generated()
        paint()

    def _row_label(text: str) -> ft.Control:
        return ft.Container(
            padding=ft.Padding.only(left=16, right=16, top=12, bottom=6),
            content=ft.Text(
                text,
                size=16,
                weight=ft.FontWeight.W_600,
                color=theme.INK,
                font_family=theme.FONT_FAMILY,
            ),
        )

    row_shift = {"subject": 0.0, "num": 0.0, "letter": 0.0}

    def _swipe_row(items: list[tuple[str, bool, object]], key: str) -> ft.Control:
        """Строка чипов. Курсор и палец тянут её сами, без полосы прокрутки."""
        gap = 8.0
        chips: list[ft.Control] = []
        widths: list[float] = []
        picks = []
        for label, on, pick in items:
            box, width = _chip_box(label, on)
            chips.append(box)
            widths.append(width)
            picks.append(pick)
        content_w = sum(widths) + gap * max(0, len(widths) - 1)
        shift = {
            "x": float(row_shift.get(key) or 0.0),
            "view": float(theme.PHONE_WIDTH) - 32.0,
            "content": content_w,
            "last": None,
        }
        inner = ft.Row(
            spacing=gap,
            tight=False,
            wrap=False,
            width=content_w,
            controls=chips,
        )
        mover = ft.Container(
            width=content_w,
            margin=ft.Margin.only(left=shift["x"]),
            content=inner,
        )
        frame = ft.Container(
            height=44,
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
            content=mover,
        )

        def _clamp(x: float) -> float:
            lo = min(0.0, shift["view"] - shift["content"])
            return max(lo, min(0.0, x))

        def _apply() -> None:
            shift["x"] = _clamp(shift["x"])
            row_shift[key] = shift["x"]
            mover.margin = ft.Margin.only(left=shift["x"])
            try:
                mover.update()
            except Exception:
                pass

        def _on_view(e: ft.LayoutSizeChangeEvent) -> None:
            width = float(getattr(e, "width", 0) or 0)
            if width > 1:
                shift["view"] = width
            _apply()

        frame.on_size_change = _on_view

        def _start(e: ft.DragStartEvent) -> None:
            pos = getattr(e, "local_position", None)
            shift["last"] = float(pos.x) if pos is not None else None

        def _move(e: ft.DragUpdateEvent) -> None:
            pos = getattr(e, "local_position", None)
            if pos is None:
                return
            x = float(pos.x)
            last = shift["last"]
            shift["last"] = x
            if last is None:
                return
            shift["x"] = shift["x"] + (x - last)
            _apply()

        def _tap(e: ft.TapEvent) -> None:
            pos = getattr(e, "local_position", None)
            if pos is None or not picks:
                return
            x = float(pos.x) - shift["x"]
            acc = 0.0
            for i, w in enumerate(widths):
                if acc <= x <= acc + w:
                    picks[i]()
                    return
                acc += w + gap

        return ft.Container(
            padding=ft.Padding.symmetric(horizontal=16),
            content=ft.GestureDetector(
                mouse_cursor=ft.MouseCursor.GRAB,
                drag_interval=0,
                on_horizontal_drag_start=_start,
                on_horizontal_drag_update=_move,
                on_tap=_tap,
                content=frame,
            ),
        )

    def _details() -> ft.Control:
        name_field = ft.TextField(
            value=name["v"],
            hint_text=t("newgroup.name_hint"),
            text_align=ft.TextAlign.CENTER,
            filled=True,
            bgcolor=theme.FIELD_BG,
            color=theme.INK,
            cursor_color=theme.PRIMARY,
            border=theme.field_border(18, color="transparent", focused_color=theme.PRIMARY),
            text_style=ft.TextStyle(
                font_family=theme.FONT_FAMILY, size=18, weight=ft.FontWeight.W_600, color=theme.INK
            ),
            hint_style=ft.TextStyle(font_family=theme.FONT_FAMILY, size=16, color=theme.HINT),
            on_change=lambda e: name.__setitem__("v", e.control.value or ""),
        )
        members = _accounts()

        def toggle(user: auth.User):
            if user.id in picked:
                picked.discard(user.id)
            else:
                picked.add(user.id)
            paint()

        rows = [_person_row(u, lambda e, user=u: toggle(user), picked=u.id in picked) for u in members]
        if not rows:
            rows = [
                ft.Container(
                    padding=ft.Padding.symmetric(horizontal=16, vertical=12),
                    content=ft.Text(
                        t("newchat.empty"),
                        size=14,
                        color=theme.MUTED,
                        font_family=theme.FONT_FAMILY,
                    ),
                )
            ]

        def create(_=None):
            title = (name["v"] or "").strip()
            if len(title) < 1:
                STATE.snack(t("newgroup.need_name"))
                return
            system = ""
            if is_class:
                try:
                    code = auth.create_class_invite(
                        int(STATE.user.id) if STATE.user else 0,
                        f"{grade['num']}{grade['letter']}",
                        "",
                    )
                except Exception as exc:
                    STATE.error(str(exc))
                    return
                system = t("newgroup.invite", code=code)
            group = chat_data.create_group(title, members=1 + len(picked), system_text=system)
            STATE.draft["_open_chat_id"] = group.id
            STATE.draft["_open_is_group"] = True
            STATE.draft["_home_tab"] = "groups"
            STATE.go("/chat")

        icon = ft.Container(
            width=96,
            height=96,
            border_radius=48,
            bgcolor=theme.PRIMARY_SOFT,
            alignment=ft.Alignment.CENTER,
            content=ft.Icon(ft.Icons.GROUPS_ROUNDED, size=46, color=theme.PRIMARY),
        )
        class_rows: list[ft.Control] = []
        if is_class:
            class_rows = [
                _row_label(t("newgroup.subject")),
                _swipe_row(
                    [
                        (t(f"subj.{key}"), subject["v"] == key, (lambda k=key: _pick_subject(k)))
                        for key in SUBJECTS
                    ],
                    "subject",
                ),
                _row_label(t("newgroup.class_number")),
                _swipe_row(
                    [
                        (n, grade["num"] == n, (lambda v=n: _pick_num(v)))
                        for n in CLASS_NUMBERS
                    ],
                    "num",
                ),
                _row_label(t("newgroup.class_letter")),
                _swipe_row(
                    [
                        (ch, grade["letter"] == ch, (lambda v=ch: _pick_letter(v)))
                        for ch in CLASS_LETTERS
                    ],
                    "letter",
                ),
            ]
        return ft.Column(
            expand=True,
            spacing=0,
            controls=[
                ft.Container(height=18),
                ft.Row(alignment=ft.MainAxisAlignment.CENTER, controls=[icon]),
                ft.Container(
                    padding=ft.Padding.only(left=48, right=48, top=16, bottom=8),
                    content=name_field,
                ),
                *class_rows,
                ft.Container(
                    padding=ft.Padding.only(left=16, right=16, top=12, bottom=4),
                    content=ft.Text(
                        t("newgroup.members"),
                        size=16,
                        weight=ft.FontWeight.W_600,
                        color=theme.INK,
                        font_family=theme.FONT_FAMILY,
                    ),
                ),
                ft.Container(
                    expand=True,
                    clip_behavior=ft.ClipBehavior.HARD_EDGE,
                    content=ft.Column(
                        expand=True,
                        scroll=ft.ScrollMode.AUTO,
                        spacing=0,
                        controls=rows + [ft.Container(height=8)],
                    ),
                ),
                ft.Container(
                    bgcolor=theme.BG,
                    padding=ft.Padding.only(left=16, right=16, top=8, bottom=12),
                    content=theme.primary_button(t("newgroup.create"), create),
                ),
            ],
        )

    body_slot = ft.Container(expand=True)

    def paint(*, appear: bool = False):
        body = _details()
        shown = theme.live_panel(body) if appear else body
        try:
            shown.expand = True
        except Exception:
            pass
        host.controls = [
            _header(t("newgroup.class_title") if is_class else t("newgroup.title"), _go_back),
            body_slot,
        ]
        body_slot.content = shown
        try:
            host.update()
        except Exception:
            pass
        if appear:
            _reveal(shown, page)

    paint()
    return host


def ask_contacts_permission(page: ft.Page) -> None:
    """Один раз при входе: доступ к контактам."""
    from core import prefs

    if prefs.get("contacts_perm") in ("yes", "no"):
        return
    if STATE.draft.get("_contacts_prompt"):
        return
    STATE.draft["_contacts_prompt"] = True

    def allow(_=None):
        prefs.set_pref("contacts_perm", "yes")
        try:
            page.pop_dialog()
        except Exception:
            pass

    def deny(_=None):
        prefs.set_pref("contacts_perm", "no")
        try:
            page.pop_dialog()
        except Exception:
            pass

    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Text(t("newchat.perm_title"), font_family=theme.FONT_FAMILY, color=theme.INK),
        content=ft.Text(t("newchat.perm_body"), size=14, font_family=theme.FONT_FAMILY, color=theme.INK),
        actions=[theme.dialog_buttons(t("newchat.deny"), deny, t("newchat.allow"), allow)],
        actions_alignment=ft.MainAxisAlignment.CENTER,
    )

    async def _show():
        import asyncio

        await asyncio.sleep(0.4)
        try:
            page.show_dialog(dlg)
        except Exception:
            pass

    try:
        page.run_task(_show)
    except Exception:
        try:
            page.show_dialog(dlg)
        except Exception:
            pass
