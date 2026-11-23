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
    return theme.pressable(row, on_click, scale_to=0.985, expand=True)


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
    return theme.pressable(body, on_click, scale_to=0.985, expand=True)


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
        border=theme.field_border(14, color=theme.STROKE, focused_color=theme.PRIMARY),
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
        actions=[
            ft.TextButton(t("common.cancel"), on_click=close),
            ft.TextButton(t("newchat.find"), on_click=find),
        ],
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
                                scale_to=0.96,
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
                        ft.Container(height=0.5, bgcolor=theme.DIVIDER, margin=ft.Margin.only(left=70)),
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
    panel = theme.live_panel(screen)
    try:
        panel.expand = True
    except Exception:
        pass
    _reveal(panel, page)
    return panel


def build_new_group(page: ft.Page) -> ft.Control:
    mode = STATE.draft.get("_group_mode") or "group"
    back_tab = STATE.draft.get("_compose_back") or ("groups" if mode == "class" else "chats")
    is_class = mode == "class"
    step = {"n": 0 if is_class else 2}
    subject = {"v": ""}
    grade = {"num": "10", "letter": "А"}
    picked: set[int] = set()
    host = ft.Column(expand=True, spacing=0)

    def _title() -> str:
        if not is_class:
            return t("newgroup.title")
        if step["n"] == 0:
            return t("newgroup.subject")
        if step["n"] == 1:
            return t("newgroup.class_step")
        return t("newgroup.class_title")

    def _go_back(_=None):
        if step["n"] > (0 if is_class else 2):
            go_step(step["n"] - 1)
            return
        _close_to("groups" if is_class else back_tab)

    def _chip(label: str, on, on_click) -> ft.Control:
        box = ft.Container(
            border_radius=14,
            padding=ft.Padding.symmetric(horizontal=14, vertical=10),
            bgcolor=theme.PRIMARY_SOFT if on else theme.FIELD_BG,
            border=ft.Border.all(1.5, theme.PRIMARY if on else theme.STROKE),
            content=ft.Text(
                label,
                size=14,
                weight=ft.FontWeight.W_600 if on else ft.FontWeight.W_500,
                color=theme.PRIMARY if on else theme.INK,
                font_family=theme.FONT_FAMILY,
            ),
        )
        return theme.pressable(box, on_click, scale_to=0.96)

    def _subjects() -> ft.Control:
        chips = []
        for key in SUBJECTS:
            chips.append(
                _chip(
                    t(f"subj.{key}"),
                    subject["v"] == key,
                    lambda e, k=key: (subject.__setitem__("v", k), paint()),
                )
            )

        def nxt(_=None):
            if not subject["v"]:
                STATE.snack(t("newgroup.pick_subject"))
                return
            go_step(1)

        return ft.Column(
            expand=True,
            spacing=12,
            controls=[
                ft.Container(
                    padding=ft.Padding.symmetric(horizontal=16),
                    content=ft.Row(spacing=8, wrap=True, controls=chips),
                ),
                ft.Container(expand=True),
                ft.Container(
                    padding=ft.Padding.symmetric(horizontal=16, vertical=12),
                    content=theme.primary_button(t("newgroup.next"), nxt),
                ),
            ],
        )

    def _class_step() -> ft.Control:
        nums = [
            _chip(n, grade["num"] == n, lambda e, v=n: (grade.__setitem__("num", v), paint()))
            for n in CLASS_NUMBERS
        ]
        letters = [
            _chip(ch, grade["letter"] == ch, lambda e, v=ch: (grade.__setitem__("letter", v), paint()))
            for ch in CLASS_LETTERS
        ]

        def nxt(_=None):
            if not grade["num"] or not grade["letter"]:
                STATE.snack(t("newgroup.pick_class"))
                return
            go_step(2)

        return ft.Column(
            expand=True,
            spacing=14,
            controls=[
                ft.Container(
                    padding=ft.Padding.symmetric(horizontal=16),
                    content=ft.Row(spacing=8, wrap=True, controls=nums),
                ),
                ft.Container(
                    padding=ft.Padding.symmetric(horizontal=16),
                    content=ft.Row(spacing=8, wrap=True, controls=letters),
                ),
                ft.Container(expand=True),
                ft.Container(
                    padding=ft.Padding.symmetric(horizontal=16, vertical=12),
                    content=theme.primary_button(t("newgroup.next"), nxt),
                ),
            ],
        )

    name = {"v": ""}

    def _details() -> ft.Control:
        if is_class and subject["v"] and not name["v"].strip():
            name["v"] = f"{t('subj.' + subject['v'])} · {grade['num']}{grade['letter']}"
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
                ft.Container(
                    padding=ft.Padding.only(left=16, right=16, top=12, bottom=4),
                    content=ft.Text(
                        t("newgroup.members"),
                        size=13,
                        weight=ft.FontWeight.W_600,
                        color=theme.MUTED,
                        font_family=theme.FONT_FAMILY,
                    ),
                ),
                ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, spacing=0, controls=rows),
                ft.Container(
                    padding=ft.Padding.symmetric(horizontal=16, vertical=12),
                    content=theme.primary_button(t("newgroup.create"), create),
                ),
            ],
        )

    body_slot = ft.Container(expand=True)

    def paint(*, appear: bool = False):
        body: ft.Control
        if step["n"] == 0:
            body = _subjects()
        elif step["n"] == 1:
            body = _class_step()
        else:
            body = _details()
        shown = theme.live_panel(body) if appear else body
        try:
            shown.expand = True
        except Exception:
            pass
        host.controls = [
            _header(_title(), _go_back),
            body_slot,
        ]
        body_slot.content = shown
        try:
            host.update()
        except Exception:
            pass
        if appear:
            _reveal(shown, page)

    def go_step(n: int) -> None:
        step["n"] = n
        paint(appear=True)

    paint(appear=True)
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
        actions=[
            ft.TextButton(t("newchat.deny"), on_click=deny),
            ft.TextButton(t("newchat.allow"), on_click=allow),
        ],
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
