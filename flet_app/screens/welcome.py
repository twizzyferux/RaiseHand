# -*- coding: utf-8 -*-
"""Welcome — ритм φ, пузыри в координатах макета (как в ui/bubbles.py)."""
from __future__ import annotations

import flet as ft

from core.i18n import t
from flet_app.app_state import STATE
from flet_app import theme

# палитра welcome совпадает с брендом RaiseHand (theme.PRIMARY)

PHI = 1.6180339887
BASE = 8.0


def phi_n(n: float) -> float:
    return round(BASE * (PHI ** n))


S5, S8, S13, S21, S34, S55, S89 = (
    phi_n(-1), phi_n(0), phi_n(1), phi_n(2), phi_n(3), phi_n(4), phi_n(5)
)

LOGO = int(S34)
WORDMARK_H = int(S21)
TITLE_SIZE = int(S34)
SUB_SIZE = int(S13 + 3)

# ---------------------------------------------------------------------------
#  Пузыри — те же данные, что WELCOME_BUBBLES в ui/bubbles.py
#  Холст макета 450×920; y — от низа (как в Kivy).
#  (цвет_rgba, x, y, [(cx, cy, d), ...])
# ---------------------------------------------------------------------------
_DESIGN_W = 450.0
_BUBBLE_W = 127.0
_BUBBLE_H = 39.0
Y_LIFT = 8.0  # подобрано вручную

# Порядок совпадает с темами RaiseHand: фиолетовая, голубая, розовая,
# зелёная, коралловая, оранжевая.
_BUBBLE_THEMES = ("violet", "blue", "pink", "green", "coral", "orange")
_RAW_BUBBLES = [
    (56, 172, [(44, 147, 25), (34, 127, 20), (29, 110, 15)]),
    (276, 152, [(393, 129, 20), (406, 113, 15)]),
    (141, 125, [(134, 110, 15)]),
    (230, 79, [(218, 54, 25), (208, 34, 20), (203, 17, 15)]),
    (44, 64, [(159, 37, 25), (174, 17, 20)]),
    (247, 34, [(367, 17, 15)]),
]


def _bubble_color(index: int) -> str:
    """Цвет пузыря — icon выбранной темы, тот же, что в настройках."""
    from core.branding import theme_tokens

    key = _BUBBLE_THEMES[index % len(_BUBBLE_THEMES)]
    mode = "dark" if theme.is_dark() else "light"
    tok = theme_tokens(key, mode)
    return tok.get("icon") or tok.get("fill") or theme.PRIMARY


def _build_bubbles_stack(target_w: float) -> ft.Stack:
    """Пузыри edge-to-edge, без взаимных перекрытий.

    Масштаб один (как в макете) — фигуры не раздуваются отдельно,
    поэтому таблетки не наезжают друг на друга. Нижние хвостики
    могут чуть выходить за низ стека (clip выключен).
    """
    min_x = 1e9
    max_x = -1e9
    min_y = 1e9
    max_y = -1e9
    for x, y, dots in _RAW_BUBBLES:
        min_x = min(min_x, x)
        max_x = max(max_x, x + _BUBBLE_W)
        min_y = min(min_y, y)
        max_y = max(max_y, y + _BUBBLE_H)
        for cx, cy, d in dots:
            min_x = min(min_x, cx)
            max_x = max(max_x, cx + d)
            min_y = min(min_y, cy)
            max_y = max(max_y, cy + d)

    span_x = max(1.0, max_x - min_x)
    span_y = max(1.0, max_y - min_y)
    sx = target_w / span_x

    # Полная высота композиции и видимая зона: низ обрезаем, хвостики
    # выходят за stack_h (clip_behavior=NONE).
    full_h = span_y * sx + Y_LIFT * sx
    overflow_bottom = 10.0
    stack_h = max(100.0, full_h - overflow_bottom)

    def to_left(x: float) -> float:
        return (x - min_x) * sx

    def to_top(y_bottom: float, h: float) -> float:
        # от верха bbox: чем ниже y_bottom, тем больше top
        # top + h*sx может быть > stack_h → выход за низ
        return (max_y - (y_bottom + h + Y_LIFT)) * sx

    controls: list[ft.Control] = []
    floaters: list[ft.Control] = []
    bw = _BUBBLE_W * sx
    bh = _BUBBLE_H * sx

    for i, (x, y, dots) in enumerate(_RAW_BUBBLES):
        color = _bubble_color(i)
        # группа: таблетка + хвостики, двигаются вместе
        group_parts: list[ft.Control] = [
            ft.Container(
                left=to_left(x),
                top=to_top(y, _BUBBLE_H),
                width=bw,
                height=bh,
                border_radius=bh / 2,
                bgcolor=color,
            )
        ]
        for cx, cy, d in dots:
            ds = d * sx
            group_parts.append(
                ft.Container(
                    left=to_left(cx),
                    top=to_top(cy, d),
                    width=ds,
                    height=ds,
                    border_radius=ds / 2,
                    bgcolor=color,
                )
            )
        floater = ft.Container(
            width=target_w,
            height=stack_h,
            animate_offset=ft.Animation(400, ft.AnimationCurve.EASE_IN_OUT),
            offset=ft.Offset(0, 0),
            content=ft.Stack(
                width=target_w,
                height=stack_h,
                controls=group_parts,
                clip_behavior=ft.ClipBehavior.NONE,
            ),
        )
        floaters.append(floater)
        controls.append(floater)

    stack = ft.Stack(
        width=target_w,
        height=stack_h,
        controls=controls,
        clip_behavior=ft.ClipBehavior.NONE,
    )
    stack.floaters = floaters  # type: ignore
    return stack


def build_welcome(page: ft.Page) -> ft.Control:
    slides = STATE.slides()
    index = {"i": 0}
    content_w = float(theme.PHONE_WIDTH - theme.PAGE_PADDING * 2)

    # --- логотип -----------------------------------------------------------
    if theme._image_exists(theme.SPRITE_LOGO):
        logo = ft.Image(
            src=theme.SPRITE_LOGO, width=LOGO, height=LOGO, fit=ft.BoxFit.CONTAIN
        )
    else:
        logo = ft.Container(
            width=LOGO,
            height=LOGO,
            border_radius=S8,
            bgcolor="#EDE7FF",
            alignment=ft.Alignment.CENTER,
            content=ft.Text(
                "R",
                size=int(S21),
                weight=ft.FontWeight.BOLD,
                color=theme.PRIMARY,
                font_family=theme.FONT_FAMILY,
            ),
        )

    wm = (
        theme.asset("assets", "images", "mono", "white" if theme.is_dark() else "black", "wordmark.png")
    )
    if theme._image_exists(wm):
        wordmark = ft.Image(src=wm, height=WORDMARK_H, fit=ft.BoxFit.CONTAIN)
    elif theme._image_exists(theme.SPRITE_WORDMARK):
        wordmark = ft.Image(
            src=theme.SPRITE_WORDMARK, height=WORDMARK_H, fit=ft.BoxFit.CONTAIN
        )
    else:
        wordmark = ft.Text(
            spans=[
                ft.TextSpan(
                    "Raise",
                    style=ft.TextStyle(
                        size=int(S21),
                        weight=ft.FontWeight.BOLD,
                        color=theme.PRIMARY,
                        font_family=theme.FONT_FAMILY,
                    ),
                ),
                ft.TextSpan(
                    "Hand",
                    style=ft.TextStyle(
                        size=int(S21),
                        weight=ft.FontWeight.BOLD,
                        color=theme.INK,
                        font_family=theme.FONT_FAMILY,
                    ),
                ),
            ],
        )

    header = ft.Row(
        spacing=S8,
        alignment=ft.MainAxisAlignment.START,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[logo, wordmark],
    )

    # фиксированная высота — смена слайда не сдвигает кнопки
    title = ft.Text(
        slides[0]["title"],
        size=TITLE_SIZE,
        weight=ft.FontWeight.BOLD,
        color=theme.INK,
        font_family=theme.FONT_FAMILY,
        text_align=ft.TextAlign.LEFT,
        width=content_w,
        no_wrap=False,
        max_lines=3,
        animate_opacity=ft.Animation(280, ft.AnimationCurve.EASE_IN_OUT),
        opacity=1,
    )
    subtitle = ft.Text(
        slides[0].get("subtitle", ""),
        size=SUB_SIZE,
        color=theme.MUTED,
        font_family=theme.FONT_FAMILY,
        text_align=ft.TextAlign.LEFT,
        width=content_w,
        no_wrap=False,
        max_lines=3,
        animate_opacity=ft.Animation(280, ft.AnimationCurve.EASE_IN_OUT),
        opacity=1,
    )
    slogan = ft.Column(
        spacing=4,
        tight=True,
        controls=[
            ft.Container(height=int(TITLE_SIZE * 1.15 * 3), content=title, alignment=ft.Alignment.TOP_LEFT),
            ft.Container(height=int(SUB_SIZE * 1.4 * 3), content=subtitle, alignment=ft.Alignment.TOP_LEFT),
        ],
    )

    dots = ft.Row(
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=S8,
        controls=[
            ft.Container(
                width=10,
                height=10,
                border_radius=5,
                bgcolor=theme.DOT_ON if i == 0 else theme.DOT_OFF,
                animate=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
            )
            for i in range(len(slides))
        ],
    )

    def paint_dots():
        for i, c in enumerate(dots.controls):
            c.bgcolor = theme.DOT_ON if i == index["i"] else theme.DOT_OFF
        try:
            dots.update()
        except Exception:
            pass

    def apply_slide(i: int):
        index["i"] = i % len(slides)
        s = slides[index["i"]]

        async def swap():
            import asyncio

            title.opacity = 0
            subtitle.opacity = 0
            try:
                title.update()
                subtitle.update()
            except Exception:
                pass
            await asyncio.sleep(0.12)
            title.value = s["title"]
            subtitle.value = s.get("subtitle", "")
            title.opacity = 1
            subtitle.opacity = 1
            try:
                title.update()
                subtitle.update()
            except Exception:
                pass
            paint_dots()

        try:
            page.run_task(swap)
        except Exception:
            title.value = s["title"]
            subtitle.value = s.get("subtitle", "")
            paint_dots()

    for i, c in enumerate(dots.controls):
        c.on_click = (lambda i=i: (lambda _e: apply_slide(i)))()

    def go_student(_):
        STATE.reset_draft()
        STATE.go("/reg/name")

    def go_teacher(_):
        STATE.reset_draft()
        STATE.draft["role"] = "teacher"
        STATE.go("/reg/name")

    def go_login(_):
        STATE.go("/login")

    # «Я Ученик» / «Я Учитель» — purple / white liquid glass
    btn_student = ft.Container(
        alignment=ft.Alignment.CENTER,
        content=theme.student_image_button(t("common.student"), go_student),
    )
    btn_teacher = ft.Container(
        alignment=ft.Alignment.CENTER,
        content=theme.secondary_image_button(t("common.teacher"), go_teacher),
    )

    login_line = ft.Text(
        spans=[
            ft.TextSpan(
                t("common.already_registered"),
                style=ft.TextStyle(
                    size=int(S13 + 2),
                    color=theme.INK,
                    font_family=theme.FONT_FAMILY,
                ),
            ),
            ft.TextSpan(
                t("auth.sign_in"),
                style=ft.TextStyle(
                    size=int(S13 + 2),
                    color=theme.PRIMARY,
                    weight=ft.FontWeight.W_600,
                    font_family=theme.FONT_FAMILY,
                ),
                on_click=go_login,
            ),
        ],
        text_align=ft.TextAlign.CENTER,
        width=content_w,
    )

    join_label = ft.Text(
        t("common.join_as"),
        size=int(S13 + 5),
        color=theme.INK,
        font_family=theme.FONT_FAMILY,
        text_align=ft.TextAlign.CENTER,
        width=content_w,
    )

    # Пузыри: каждый набор (таблетка+хвостики) двигается отдельно
    bubbles_area = _build_bubbles_stack(float(theme.PHONE_WIDTH))

    def fade(ctrl: ft.Control, delay: int = 0, width: float | None = None) -> ft.Control:
        return theme.fade_box(ctrl, delay_ms=delay, width=width)

    parts = [
        fade(header, 0),
        fade(slogan, 40),
        fade(ft.Container(content=dots, width=content_w, alignment=ft.Alignment.CENTER), 80),
        fade(join_label, 120),
        fade(btn_student, 160),
        fade(btn_teacher, 200),
        fade(login_line, 240),
        fade(bubbles_area, 280, width=float(theme.PHONE_WIDTH)),
    ]

    # Верх с боковыми полями; пузыри — на всю ширину телефона
    upper = ft.Container(
        padding=ft.Padding.symmetric(horizontal=theme.PAGE_PADDING),
        content=ft.Column(
            spacing=0,
            tight=True,
            controls=[
                ft.Container(height=S34),  # логотип ниже от верха
                parts[0],
                ft.Container(height=S21),  # ближе к слогану
                parts[1],
                ft.Container(height=S21),
                parts[2],
                ft.Container(height=S34),
                parts[3],
                ft.Container(height=S13),
                parts[4],
                ft.Container(height=S13),
                parts[5],
                ft.Container(height=S21),
                parts[6],
            ],
        ),
    )

    body = ft.Column(
        expand=True,
        spacing=0,
        controls=[
            upper,
            ft.Container(expand=True, min_height=S13),
            parts[7],  # пузыри; нижние хвостики могут выйти за низ
        ],
    )

    root = ft.Container(
        content=body,
        # SafeArea снаружи; горизонталь уже в content_w (PAGE_PADDING)
        padding=ft.Padding.only(top=4, bottom=0, left=0, right=0),
        bgcolor=theme.BG,
        expand=True,
    )

    async def intro():
        import asyncio

        await asyncio.sleep(0.04)
        await theme.play_fade_in(parts, page, step_ms=45)

    async def float_bubbles():
        import asyncio
        import math
        floaters = getattr(bubbles_area, "floaters", [])
        # разные фазы и периоды — никто не синхронен
        phases = [0.0, 1.7, 3.1, 4.4, 0.9, 2.4]
        periods = [5.5, 7.2, 4.4, 8.1, 6.0, 9.0]  # разные медленные скорости
        amp = 0.012
        t0 = 0.0
        while True:
            await asyncio.sleep(0.05)
            t0 += 0.05
            for i, fl in enumerate(floaters):
                ph = phases[i % len(phases)]
                per = periods[i % len(periods)]
                y = amp * math.sin(2 * math.pi * t0 / per + ph)
                try:
                    fl.offset = ft.Offset(0, y)
                    fl.update()
                except Exception:
                    return

    async def auto_slides():
        import asyncio

        while True:
            await asyncio.sleep(5.0)
            apply_slide(index["i"] + 1)

    try:
        page.run_task(intro)
        page.run_task(float_bubbles)
        page.run_task(auto_slides)
    except Exception:
        for p in parts:
            p.opacity = 1
            p.offset = ft.Offset(0, 0)

    return root
