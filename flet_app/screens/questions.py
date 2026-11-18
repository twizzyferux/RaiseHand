# -*- coding: utf-8 -*-
"""Экран вопросов группы: рейтинг, лайки, ответ учителя, добавить вопрос."""
from __future__ import annotations

import flet as ft

from flet_app import chat_data
from flet_app import liquid_glass
from flet_app import questions_data
from flet_app.app_state import STATE
from flet_app import theme

MEDAL_GOLD = "#C9A227"
MEDAL_SILVER = "#8E8E93"
MEDAL_BRONZE = "#B87333"
RANK_MUTED = "#B0B0B8"
LIKE_OFF = "#A0A0A8"
# карточка ответа в light — всегда светлая; body-ink фиксируем тёмным
ANSWER_BG_LIGHT = "#F3F0FF"
ANSWER_BORDER_LIGHT = "#E4DFFF"
ANSWER_INK_LIGHT = "#1C1B2E"


def _like_on() -> str:
    return theme.PRIMARY


def _answer_palette() -> dict[str, str]:
    """Цвета блока ответа с нормальным контрастом в light/dark."""
    if theme.is_dark():
        return {
            "bg": theme.PRIMARY_SOFT or "#242037",
            "border": theme.STROKE,
            "title": theme.PRIMARY,
            "body": theme.INK,
        }
    return {
        "bg": ANSWER_BG_LIGHT,
        "border": ANSWER_BORDER_LIGHT,
        "title": theme.PRIMARY,
        "body": ANSWER_INK_LIGHT,
    }


def _dialog_field(
    *,
    hint: str,
    value: str = "",
    min_lines: int = 2,
    max_lines: int = 4,
) -> ft.TextField:
    """Поле в диалоге: фон и цвет текста всегда из текущей темы."""
    return ft.TextField(
        hint_text=hint,
        value=value,
        multiline=True,
        min_lines=min_lines,
        max_lines=max_lines,
        autofocus=True,
        border=theme.field_border(16, color=theme.STROKE, focused_color=theme.PRIMARY),
        bgcolor=theme.FIELD_BG,
        filled=True,
        color=theme.INK,
        cursor_color=theme.PRIMARY,
        text_style=ft.TextStyle(
            font_family=theme.FONT_FAMILY, size=15, color=theme.INK
        ),
        hint_style=ft.TextStyle(color=theme.HINT, font_family=theme.FONT_FAMILY),
    )


def _is_teacher() -> bool:
    u = STATE.user
    return bool(u and getattr(u, "is_teacher", False))


def _teacher_name() -> str:
    u = STATE.user
    if not u:
        return "Учитель"
    return getattr(u, "display_name", None) or getattr(u, "full_name", None) or "Учитель"


def _rank_color(rank: int) -> str:
    if rank == 1:
        return MEDAL_GOLD
    if rank == 2:
        return MEDAL_SILVER
    if rank == 3:
        return MEDAL_BRONZE
    return RANK_MUTED


def _rank_badge(rank: int) -> ft.Control:
    return ft.Container(
        width=36,
        height=36,
        border_radius=18,
        alignment=ft.Alignment.CENTER,
        bgcolor=ft.Colors.with_opacity(0.14, _rank_color(rank))
        if rank <= 3
        else "#00000000",
        content=ft.Text(
            str(rank),
            size=16 if rank <= 3 else 15,
            weight=ft.FontWeight.W_700,
            color=_rank_color(rank),
            font_family=theme.FONT_FAMILY,
            text_align=ft.TextAlign.CENTER,
        ),
    )


def _like_control(q: questions_data.Question, on_toggle) -> ft.Control:
    color = _like_on() if q.liked_by_me else LIKE_OFF
    icon = ft.Icons.FAVORITE if q.liked_by_me else ft.Icons.FAVORITE_BORDER
    return ft.Container(
        on_click=lambda e, qid=q.id: on_toggle(qid),
        ink=False,
        padding=ft.Padding.symmetric(horizontal=8, vertical=4),
        border_radius=16,
        content=ft.Row(
            spacing=4,
            tight=True,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Icon(icon, size=20, color=color),
                ft.Text(
                    str(q.likes),
                    size=14,
                    weight=ft.FontWeight.W_600,
                    color=color,
                    font_family=theme.FONT_FAMILY,
                ),
            ],
        ),
    )


def _answer_block(q: questions_data.Question) -> ft.Control:
    if not q.answered or not q.answer_text:
        return ft.Container(height=0)
    pal = _answer_palette()
    return ft.Container(
        margin=ft.Margin.only(top=8),
        padding=ft.Padding.all(12),
        border_radius=14,
        bgcolor=pal["bg"],
        border=ft.Border.all(1, pal["border"]),
        content=ft.Column(
            spacing=4,
            tight=True,
            controls=[
                ft.Text(
                    f"Ответ учителя · {q.answer_by or 'Учитель'}",
                    size=12,
                    weight=ft.FontWeight.W_600,
                    color=pal["title"],
                    font_family=theme.FONT_FAMILY,
                ),
                ft.Text(
                    q.answer_text,
                    size=14,
                    color=pal["body"],
                    font_family=theme.FONT_FAMILY,
                ),
            ],
        ),
    )


def _question_row(
    q: questions_data.Question,
    rank: int,
    *,
    is_teacher: bool,
    on_toggle,
    on_answer,
) -> ft.Control:
    meta: list[ft.Control] = []
    if q.author_count > 1:
        meta.append(
            ft.Text(
                f"ещё {q.author_count - 1} похожих",
                size=12,
                color=theme.MUTED,
                font_family=theme.FONT_FAMILY,
            )
        )
    if q.answered:
        meta.append(
            ft.Text(
                "есть ответ",
                size=12,
                weight=ft.FontWeight.W_600,
                color="#1B7A3A",
                font_family=theme.FONT_FAMILY,
            )
        )
    elif is_teacher:
        meta.append(
            ft.Text(
                "без ответа",
                size=12,
                color=theme.HINT,
                font_family=theme.FONT_FAMILY,
            )
        )

    actions: list[ft.Control] = [_like_control(q, on_toggle)]
    if is_teacher:
        actions.insert(
            0,
            ft.TextButton(
                "Изменить" if q.answered else "Ответить",
                on_click=lambda e, qid=q.id: on_answer(qid),
                style=ft.ButtonStyle(color=theme.PRIMARY, padding=ft.Padding.symmetric(horizontal=8)),
            ),
        )

    return ft.Container(
        padding=ft.Padding.symmetric(horizontal=16, vertical=12),
        bgcolor=theme.BG,
        content=ft.Column(
            spacing=0,
            tight=True,
            controls=[
                ft.Row(
                    spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                    controls=[
                        _rank_badge(rank),
                        ft.Column(
                            expand=True,
                            spacing=4,
                            tight=True,
                            controls=[
                                ft.Text(
                                    q.text,
                                    size=15,
                                    weight=ft.FontWeight.W_500,
                                    color=theme.INK,
                                    font_family=theme.FONT_FAMILY,
                                ),
                                ft.Row(spacing=10, tight=True, controls=meta)
                                if meta
                                else ft.Container(height=0),
                                _answer_block(q),
                            ],
                        ),
                        ft.Column(
                            spacing=0,
                            tight=True,
                            horizontal_alignment=ft.CrossAxisAlignment.END,
                            controls=actions,
                        ),
                    ],
                ),
            ],
        ),
    )


def _divider() -> ft.Control:
    return ft.Container(
        height=1,
        bgcolor=theme.DIVIDER,
        margin=ft.Margin.symmetric(horizontal=16),
    )


def build_questions(page: ft.Page) -> ft.Control:
    gid = str(STATE.draft.get("_questions_group_id") or "")
    group = chat_data.get_group(gid) if gid else None
    teacher = _is_teacher()

    list_host = ft.Column(spacing=0, expand=True, scroll=ft.ScrollMode.AUTO, controls=[])

    def refresh() -> None:
        items = questions_data.list_ranked(gid) if gid else []
        questions_data.sync_group_count(gid)
        controls: list[ft.Control] = []
        if not items:
            controls.append(
                ft.Container(
                    padding=ft.Padding.all(24),
                    content=ft.Text(
                        "Пока нет вопросов.\nНажмите «Добавить вопрос».",
                        size=15,
                        color=theme.MUTED,
                        text_align=ft.TextAlign.CENTER,
                        font_family=theme.FONT_FAMILY,
                    ),
                )
            )
        else:
            for i, q in enumerate(items, start=1):
                controls.append(
                    _question_row(
                        q,
                        i,
                        is_teacher=teacher,
                        on_toggle=on_toggle_like,
                        on_answer=open_answer,
                    )
                )
                if i < len(items):
                    controls.append(_divider())
        list_host.controls = controls
        try:
            list_host.update()
        except Exception:
            pass

    def on_toggle_like(qid: str) -> None:
        questions_data.toggle_like(gid, qid)
        refresh()

    def go_back(_=None):
        STATE.draft["_open_chat_id"] = gid
        STATE.draft["_open_is_group"] = True
        STATE.go("/chat")

    def _close_dlg(_=None):
        try:
            page.pop_dialog()
        except Exception:
            pass

    def open_answer(qid: str) -> None:
        if not teacher:
            return
        items = questions_data.list_ranked(gid)
        cur = next((x for x in items if x.id == qid), None)
        tf = _dialog_field(
            hint="Ответ ученикам…",
            value=(cur.answer_text if cur else "") or "",
            min_lines=3,
            max_lines=6,
        )

        def submit(_=None):
            text = (tf.value or "").strip()
            if not text:
                return
            try:
                questions_data.set_answer(
                    gid, qid, text, teacher_name=_teacher_name()
                )
                _close_dlg()
                refresh()
                STATE.snack("Ответ опубликован")
            except Exception as exc:
                STATE.error(str(exc))

        dlg = ft.AlertDialog(
            title=ft.Text(
                "Ответ учителя",
                color=theme.INK,
                font_family=theme.FONT_FAMILY,
            ),
            content=ft.Column(
                tight=True,
                spacing=8,
                width=min(float(theme.PHONE_WIDTH) - 48, 320),
                controls=[
                    ft.Text(
                        (cur.text if cur else "")[:120],
                        size=13,
                        color=theme.MUTED,
                        font_family=theme.FONT_FAMILY,
                    ),
                    tf,
                ],
            ),
            actions=[
                ft.TextButton(
                    "Отмена",
                    on_click=_close_dlg,
                    style=ft.ButtonStyle(color=theme.PRIMARY),
                ),
                ft.TextButton(
                    "Сохранить",
                    on_click=submit,
                    style=ft.ButtonStyle(color=theme.PRIMARY),
                ),
            ],
        )
        try:
            page.show_dialog(dlg)
        except Exception:
            STATE.snack("Не удалось открыть форму ответа")

    def open_add(_=None):
        tf = _dialog_field(hint="Ваш вопрос…", min_lines=2, max_lines=4)
        status = ft.Text(
            "Проверка схожести: Gemini"
            if questions_data.ai_status() == "gemini"
            else "Проверка схожести: локально (+ Gemini, если задать ключ)",
            size=12,
            color=theme.MUTED,
            font_family=theme.FONT_FAMILY,
        )

        def submit(_=None):
            text = (tf.value or "").strip()
            if not text:
                return
            status.value = "Проверяем схожесть…"
            try:
                status.update()
            except Exception:
                pass
            try:
                _q, merged = questions_data.add_or_like(gid, text)
                _close_dlg()
                refresh()
                if merged:
                    STATE.snack("Похожий вопрос уже есть — засчитан как лайк")
                else:
                    STATE.snack("Вопрос добавлен")
            except Exception as exc:
                STATE.error(str(exc))

        dlg = ft.AlertDialog(
            title=ft.Text(
                "Новый вопрос",
                color=theme.INK,
                font_family=theme.FONT_FAMILY,
            ),
            content=ft.Column(
                tight=True,
                spacing=8,
                width=min(float(theme.PHONE_WIDTH) - 48, 320),
                controls=[
                    tf,
                    ft.Text(
                        "Если смысл тот же (даже другими словами),\nвопрос не дублируется — добавляется лайк.",
                        size=12,
                        color=theme.MUTED,
                        font_family=theme.FONT_FAMILY,
                    ),
                    status,
                ],
            ),
            actions=[
                ft.TextButton(
                    "Отмена",
                    on_click=_close_dlg,
                    style=ft.ButtonStyle(color=theme.PRIMARY),
                ),
                ft.TextButton(
                    "Добавить",
                    on_click=submit,
                    style=ft.ButtonStyle(color=theme.PRIMARY),
                ),
            ],
        )
        try:
            page.show_dialog(dlg)
        except Exception:
            STATE.snack("Не удалось открыть форму")

    add_btn = liquid_glass.purple_glass_button(
        "Добавить вопрос",
        open_add,
        width=min(float(theme.PHONE_WIDTH - theme.PAGE_PADDING * 2) * 0.92, 340.0),
        height=52,
    )

    header = ft.Container(
        padding=ft.Padding.symmetric(horizontal=8, vertical=8),
        content=ft.Row(
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.IconButton(
                    icon=ft.Icons.ARROW_BACK_IOS_NEW,
                    icon_size=18,
                    icon_color=theme.INK,
                    on_click=go_back,
                ),
                ft.Column(
                    expand=True,
                    spacing=0,
                    tight=True,
                    controls=[
                        ft.Text(
                            "Вопросы",
                            size=20,
                            weight=ft.FontWeight.W_700,
                            color=theme.INK,
                            font_family=theme.FONT_FAMILY,
                        ),
                        ft.Text(
                            (group.name if group else "")
                            + (" · учитель" if teacher else ""),
                            size=13,
                            color=theme.MUTED,
                            font_family=theme.FONT_FAMILY,
                        ),
                    ],
                ),
            ],
        ),
    )

    hint = (
        "Нажмите «Ответить», чтобы опубликовать ответ для учеников"
        if teacher
        else "Лайк — если вопрос тот же; ответ учителя появится под вопросом"
    )

    refresh()

    return ft.Container(
        bgcolor=theme.BG,
        expand=True,
        content=ft.Column(
            expand=True,
            spacing=0,
            controls=[
                ft.Container(height=28),
                header,
                ft.Container(
                    padding=ft.Padding.symmetric(horizontal=16, vertical=4),
                    content=ft.Text(
                        hint,
                        size=12,
                        color=theme.HINT,
                        font_family=theme.FONT_FAMILY,
                    ),
                ),
                ft.Container(height=4),
                list_host,
                ft.Container(
                    padding=ft.Padding.only(left=16, right=16, top=8, bottom=18),
                    alignment=ft.Alignment.CENTER,
                    content=add_btn,
                ),
            ],
        ),
    )
