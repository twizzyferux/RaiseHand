# -*- coding: utf-8 -*-
"""Регистрация ученика — 5 шагов, спрайты из assets/, как на макете."""
from __future__ import annotations

import random
import re

import flet as ft

from core import auth, verification, formatters, session
from core.config import OUTBOX_PATH, SETTINGS, rule, save_settings
from flet_app.app_state import STATE
from flet_app import theme


def _detect_contact(value: str):
    value = (value or "").strip()
    if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
        return "email"
    if re.fullmatch(r"\+?[\d\s()\-.]{6,}", value):
        return "phone"
    return None


def _generate_code() -> str:
    length = int(rule("code_length") or 6)
    code = "".join(str(random.randint(0, 9)) for _ in range(length))
    try:
        with open(OUTBOX_PATH, "a", encoding="utf-8") as f:
            f.write(f"[код подтверждения] {code}\n")
    except OSError:
        pass
    return code


def _save_remember(remember: bool, login_value: str) -> None:
    if remember:
        SETTINGS["remember_login"] = login_value
    else:
        SETTINGS.pop("remember_login", None)
    try:
        save_settings()
    except Exception:
        pass


def _form_width() -> float:
    content_w = float(theme.PHONE_WIDTH - theme.PAGE_PADDING * 2)
    return min(content_w * 0.82, 300.0)


def _pill_field(
    label: str,
    hint: str = "",
    *,
    value: str = "",
    password: bool = False,
    helper: str = "",
    on_change=None,
) -> tuple[ft.Control, ft.TextField]:
    """Поле фиксированной ширины, блок по центру экрана."""
    fw = _form_width()
    content_w = float(theme.PHONE_WIDTH - theme.PAGE_PADDING * 2)
    tf = ft.TextField(
        value=value,
        hint_text=hint,
        password=password,
        can_reveal_password=password,
        border_radius=28,
        filled=True,
        bgcolor="#F0F0F5",
        border_color="#F0F0F5",
        focused_border_color=theme.PRIMARY,
        cursor_color=theme.PRIMARY,
        text_size=16,
        color=theme.INK,
        width=fw,
        height=52,
        content_padding=ft.Padding.symmetric(horizontal=20, vertical=14),
        text_style=ft.TextStyle(font_family=theme.FONT_FAMILY, size=16, color=theme.INK),
        hint_style=ft.TextStyle(color=theme.HINT, font_family=theme.FONT_FAMILY),
        on_change=on_change,
    )

    col = ft.Column(
        spacing=6,
        tight=True,
        width=fw,
        horizontal_alignment=ft.CrossAxisAlignment.START,
        controls=[
            ft.Text(
                label,
                size=17,
                weight=ft.FontWeight.W_600,
                color=theme.INK,
                font_family=theme.FONT_FAMILY,
            ),
            tf,
            *([ft.Text(helper, size=13, color=theme.MUTED, font_family=theme.FONT_FAMILY, width=fw)] if helper else []),
        ],
    )
    return (
        ft.Container(width=content_w, alignment=ft.Alignment.CENTER, content=col),
        tf,
    )


def _back_row(header: str, back_route: str) -> ft.Control:
    """Назад слева, заголовок по центру экрана (как на макете)."""
    back_icon = theme.asset("assets", "images", "raisehand", "back.png")
    if theme._image_exists(back_icon):
        back_ctrl = ft.GestureDetector(
            on_tap=lambda _: STATE.go(back_route),
            content=ft.Row(
                spacing=4,
                tight=True,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Image(src=back_icon, width=18, height=18, fit=ft.BoxFit.CONTAIN),
                    ft.Text(
                        "Назад",
                        size=15,
                        color=theme.PRIMARY,
                        weight=ft.FontWeight.W_600,
                        font_family=theme.FONT_FAMILY,
                    ),
                ],
            ),
        )
    else:
        back_ctrl = ft.TextButton(
            "← Назад",
            on_click=lambda _: STATE.go(back_route),
            style=ft.ButtonStyle(color=theme.PRIMARY),
        )

    # back_ctrl поверх заголовка — иначе клик не доходит
    return ft.Stack(
        height=36,
        controls=[
            ft.Container(
                content=ft.Text(
                    header,
                    size=15,
                    weight=ft.FontWeight.W_600,
                    color=theme.INK,
                    font_family=theme.FONT_FAMILY,
                    text_align=ft.TextAlign.CENTER,
                ),
                alignment=ft.Alignment.CENTER,
                left=0,
                right=0,
                top=0,
                bottom=0,
            ),
            ft.Container(
                content=back_ctrl,
                left=0,
                top=0,
                bottom=0,
                width=120,
                alignment=ft.Alignment.CENTER_LEFT,
            ),
        ],
    )


def _reg_header() -> str:
    return "Регистрация учителя" if STATE.draft.get("role") == "teacher" else "Регистрация ученика"


def _chrome(
    title: str,
    progress: float,
    body: list,
    on_next,
    back_route: str,
    *,
    next_label: str = "Далее",
    show_consent: bool = True,
    header: str = "",
    show_back: bool = True,
    subtitle: str = "",
) -> ft.Control:
    """Шапка + поля (scroll) + «Далее» всегда внизу."""
    if not header:
        header = _reg_header()
    header_block: list = []
    if show_back:
        header_block.append(_back_row(header, back_route))
    else:
        header_block.append(
            ft.Container(
                alignment=ft.Alignment.CENTER,
                content=ft.Text(
                    header,
                    size=15,
                    weight=ft.FontWeight.W_600,
                    color=theme.MUTED,
                    font_family=theme.FONT_FAMILY,
                    text_align=ft.TextAlign.CENTER,
                ),
            )
        )

    content_w = float(theme.PHONE_WIDTH - theme.PAGE_PADDING * 2)
    form_w = min(content_w * 0.82, 300.0)

    title_block: list = [
        ft.Container(height=14),
    ]
    if title:
        title_block.append(
            ft.Text(
                title,
                size=30,
                weight=ft.FontWeight.BOLD,
                color=theme.INK,
                font_family=theme.FONT_FAMILY,
                text_align=ft.TextAlign.LEFT,
            )
        )
    if subtitle:
        title_block += [
            ft.Container(height=8),
            ft.Text(
                subtitle,
                size=15,
                color=theme.MUTED,
                font_family=theme.FONT_FAMILY,
                text_align=ft.TextAlign.LEFT,
            ),
        ]
    if title or progress < 1.0:
        title_block += [
            ft.Container(height=10),
            ft.ProgressBar(
                value=progress,
                color=theme.PRIMARY,
                bgcolor="#E8E8EE",
                bar_height=3,
                border_radius=2,
            ),
            ft.Container(height=22),
        ]

    # середина — поля по центру
    middle = ft.Column(
        expand=True,
        scroll=ft.ScrollMode.AUTO,
        spacing=0,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        controls=list(body),
    )

    footer: list = []
    if show_consent:
        footer.append(
            ft.Container(
                width=content_w,
                alignment=ft.Alignment.CENTER,
                content=ft.Text(
                    "Нажимая далее вы соглашаетесь\nс правилами RaiseHand",
                    size=13,
                    color=theme.HINT,
                    font_family=theme.FONT_FAMILY,
                    text_align=ft.TextAlign.CENTER,
                    width=content_w,
                ),
            )
        )
        footer.append(ft.Container(height=10))
    footer.append(theme.primary_image_button(next_label, on_next))  # спрайт btn_next с тенью
    footer.append(ft.Container(height=8))

    return ft.Container(
        bgcolor=theme.BG,
        expand=True,
        width=theme.PHONE_WIDTH,
        padding=ft.Padding.symmetric(horizontal=theme.PAGE_PADDING, vertical=14),
        content=ft.Column(
            expand=True,
            spacing=0,
            horizontal_alignment=ft.CrossAxisAlignment.START,
            controls=[
                *header_block,
                *title_block,
                middle,   # у middle свой CENTER
                *footer,  # кнопка/consent сами центрируются
            ],
        ),
    )



# ---------------------------------------------------------------------------
#  Шаг 1 — имя
# ---------------------------------------------------------------------------

def build_reg_name(page: ft.Page) -> ft.Control:
    first_col, first = _pill_field(
        "Имя", "Иван", value=STATE.draft.get("first_name", ""), helper="Видно всем"
    )
    last_col, last = _pill_field(
        "Фамилия", "Иванов", value=STATE.draft.get("last_name", ""), helper="Видно всем"
    )

    def next_(_):
        fn = (first.value or "").strip()
        ln = (last.value or "").strip()
        if len(fn) < 2 or len(ln) < 2:
            STATE.error("Введите имя и фамилию (минимум 2 символа)")
            return
        if any(ch.isdigit() for ch in fn + ln):
            STATE.error("Имя и фамилия не должны содержать цифры")
            return
        STATE.draft["first_name"] = fn
        STATE.draft["last_name"] = ln
        STATE.draft["_fresh"] = False
        STATE.go("/reg/password")

    return _chrome(
        "Как вас зовут?",
        0.2,
        [first_col, ft.Container(height=16), last_col],
        next_,
        "/welcome",
        show_consent=True,
    )


# ---------------------------------------------------------------------------
#  Шаг 2 — пароль
# ---------------------------------------------------------------------------

def build_reg_password(page: ft.Page) -> ft.Control:
    min_len = int(rule("min_password_length") or 6)
    pwd_col, pwd = _pill_field(
        "Пароль", password=True, helper=f"Минимум {min_len} символов"
    )
    pwd2_col, pwd2 = _pill_field("Подтверждение пароля", password=True)
    remember = ft.Checkbox(
        label="Запомнить меня",
        value=bool(STATE.draft.get("remember", False)),
        active_color=theme.PRIMARY,
        label_style=ft.TextStyle(font_family=theme.FONT_FAMILY, size=15, color=theme.INK),
    )
    remember_box = ft.Container(
        width=float(theme.PHONE_WIDTH - theme.PAGE_PADDING * 2),
        alignment=ft.Alignment.CENTER,
        content=ft.Container(width=_form_width(), content=remember),
    )

    def next_(_):
        try:
            auth.validate_password(pwd.value or "", pwd2.value or "")
        except auth.AuthError as exc:
            STATE.error(str(exc))
            return
        STATE.draft["password"] = pwd.value or ""
        STATE.draft["remember"] = bool(remember.value)
        if STATE.draft.get("role") == "teacher":
            STATE.go("/reg/work")
        else:
            STATE.go("/reg/school")

    return _chrome(
        "Введите пароль",
        0.4,
        [pwd_col, ft.Container(height=14), pwd2_col, ft.Container(height=8), remember_box],
        next_,
        "/reg/name",
        show_consent=True,
    )


# ---------------------------------------------------------------------------
#  Шаг 3 — город + код
# ---------------------------------------------------------------------------

def build_reg_school(page: ft.Page) -> ft.Control:
    city_col, city = _pill_field(
        "Город",
        "Москва",
        value=STATE.draft.get("city", ""),
        helper="Мин. 2 символа",
    )
    invite_col, invite = _pill_field(
        "Код приглашения",
        "A12-3B4",
        value=STATE.draft.get("invite_code", ""),
        helper="Код можно узнать у учителя\nили в чате класса",
    )
    suggestions = ft.Column(spacing=4, controls=[])

    def pick_city(name: str):
        city.value = name
        city.update()
        suggestions.controls.clear()
        try:
            suggestions.update()
        except Exception:
            pass

    def on_city_change(e):
        suggestions.controls.clear()
        q = city.value or ""
        found = formatters.city_suggestions(q, limit=5) if q.strip() else []
        for name in found:
            suggestions.controls.append(
                ft.Container(
                    content=ft.Text(name, size=15, color=theme.INK, font_family=theme.FONT_FAMILY),
                    padding=ft.Padding.symmetric(horizontal=14, vertical=10),
                    bgcolor="#F0F0F5",
                    border_radius=14,
                    on_click=lambda e, n=name: pick_city(n),
                    ink=True,
                )
            )
        try:
            suggestions.update()
        except Exception:
            pass

    def on_invite_change(e):
        formatted = formatters.invite_format(invite.value or "")
        if formatted != (invite.value or ""):
            invite.value = formatted
            invite.update()

    city.on_change = on_city_change
    invite.on_change = on_invite_change

    def next_(_):
        city_val = (city.value or "").strip()
        if len(city_val) < 2:
            STATE.error("Город: минимум 2 символа")
            return
        code = (invite.value or "").strip()
        if not code:
            STATE.error("Введите код приглашения от учителя")
            return
        row = None
        try:
            row = auth.find_class(code)
        except auth.AuthError:
            row = None
        # dev_mode: пока нет реальных кодов — принимаем учебный A12-3B4
        if row is None and SETTINGS.get("dev_mode"):
            demo = "A12-3B4"
            if code.replace("-", "").upper() == demo.replace("-", ""):
                row = {"class_name": "5А", "school_name": "Школа №67"}
            else:
                STATE.error("Код не найден. В учебном режиме используйте A12-3B4")
                return
        if row is None:
            STATE.error("Код приглашения не найден. Попросите у учителя новый код")
            return
        STATE.draft["city"] = city_val
        STATE.draft["invite_code"] = code
        STATE.draft["class_name"] = row["class_name"]
        STATE.draft["school_name"] = row["school_name"]
        STATE.go("/reg/contact")

    return _chrome(
        "Где вы учитесь?",
        0.6,
        [
            city_col,
            suggestions,
            ft.Container(height=12),
            invite_col,
        ],
        next_,
        "/reg/password",
        show_consent=True,
        subtitle="Введите город и код от учителя,\nчтобы присоединиться к классу",
    )


# ---------------------------------------------------------------------------
#  Шаг 4 — контакт + код
# ---------------------------------------------------------------------------

def build_reg_contact(page: ft.Page) -> ft.Control:
    contact_col, contact = _pill_field(
        "E-mail/Телефон",
        "ivan@example.com",
        value=STATE.draft.get("contact_value", ""),
        helper="Код придет вам на почту либо\nна ваш номер телефона",
    )
    code_col, code_field = _pill_field(
        "Код подтверждения",
        "123ABC",
    )

    def send_code(_):
        value = (contact.value or "").strip()
        kind = _detect_contact(value)
        if kind is None:
            STATE.error("Введите почту (ivan@example.com) или номер (+79001234567)")
            return
        try:
            code = verification.send_registration_code(kind, value)
        except verification.VerificationError as exc:
            STATE.error(str(exc))
            return
        except Exception as exc:
            STATE.error(f"Не удалось отправить код: {exc}")
            return
        STATE.draft["contact_type"] = kind
        STATE.draft["contact_value"] = value
        STATE.draft["code"] = code
        if SETTINGS.get("dev_mode") and not (
            (kind == "email" and SETTINGS.get("email", {}).get("enabled"))
            or (kind == "phone" and SETTINGS.get("sms", {}).get("enabled"))
        ):
            STATE.info(
                f"Учебный режим: код {code}\n(data/outbox.log)",
                "Код отправлен",
            )
        else:
            where = "почту" if kind == "email" else "телефон"
            STATE.info(f"Код отправлен на {where}.", "Отправлено")

    send_btn = theme.primary_image_button("Получить код", send_code)

    def next_(_):
        if STATE.draft.get("user") is not None:
            STATE.go("/reg/done")
            return
        if not STATE.draft.get("contact_value"):
            STATE.error("Сначала укажите почту/телефон и запросите код")
            return
        if STATE.draft.get("code") is None:
            STATE.error("Сначала запросите код")
            return
        entered = formatters.code_format(code_field.value or "")
        if entered != str(STATE.draft["code"]):
            STATE.error("Код не совпадает. Проверьте и попробуйте ещё раз")
            return
        try:
            user = auth.register_student(
                STATE.draft["first_name"],
                STATE.draft["last_name"],
                STATE.draft["password"],
                STATE.draft["password"],
                contact_type=STATE.draft.get("contact_type"),
                contact_value=STATE.draft.get("contact_value"),
                city=STATE.draft.get("city", ""),
                class_name=STATE.draft.get("class_name", ""),
                school_name=STATE.draft.get("school_name", ""),
            )
        except Exception as exp:
            STATE.error(str(exp))
            return
        STATE.draft["user"] = user
        STATE.user = user
        _save_remember(bool(STATE.draft.get("remember")), STATE.draft.get("contact_value") or "")
        if STATE.draft.get("remember"):
            try:
                session.save(user.id, user.public_id)
            except Exception:
                pass
        STATE.go("/reg/done")

    return _chrome(
        "Подтверждение",
        0.8,
        [
            contact_col,
            ft.Container(height=8),
            send_btn,
            ft.Container(height=14),
            code_col,
        ],
        next_,
        "/reg/school",
        show_consent=True,
        header="Последний этап!",
        subtitle="Впишите свой адрес электронной\nпочты, либо номер телефона,\nчтобы подтвердить свой аккаунт",
    )


# ---------------------------------------------------------------------------
#  Шаг 5 — всё готово (улучшенная подача)
# ---------------------------------------------------------------------------

def build_reg_done(page: ft.Page) -> ft.Control:
    user = STATE.draft.get("user") or STATE.user
    if user is None:
        return ft.Container(
            bgcolor=theme.BG,
            expand=True,
            padding=16,
            content=ft.Column(
                controls=[
                    ft.Text("Аккаунт не создан", size=20),
                    theme.primary_image_button("Начать сначала", lambda _: STATE.go("/welcome")),
                ],
            ),
        )

    try:
        from core import gradients
        initials = gradients.initials_for(user.first_name, user.last_name)
    except Exception:
        initials = (user.first_name[:1] + user.last_name[:1]).upper()

    class_name = user.class_name or STATE.draft.get("class_name", "") or "—"
    school_name = user.school_name or STATE.draft.get("school_name", "") or "—"

    # Градиентный аватар — Container с мягким фиолетово-розовым
    avatar = ft.Container(
        width=100,
        height=100,
        border_radius=50,
        gradient=ft.LinearGradient(
            begin=ft.Alignment(-1, -1),
            end=ft.Alignment(1, 1),
            colors=["#C4B5FD", "#F9A8D4"],
        ),
        alignment=ft.Alignment.CENTER,
        content=ft.Text(
            initials,
            size=32,
            weight=ft.FontWeight.BOLD,
            color="#FFFFFF",
            font_family=theme.FONT_FAMILY,
        ),
        shadow=ft.BoxShadow(blur_radius=16, color="#4B2FE033", offset=ft.Offset(0, 6)),
    )

    def info_card(label: str, value: str) -> ft.Control:
        """Карточка: слева метка, справа значение — чище, чем две колонки текста."""
        return ft.Container(
            bgcolor="#F0F0F5",
            border_radius=28,
            padding=ft.Padding.symmetric(horizontal=22, vertical=16),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Text(
                        label,
                        size=16,
                        weight=ft.FontWeight.W_600,
                        color=theme.MUTED,
                        font_family=theme.FONT_FAMILY,
                    ),
                    ft.Text(
                        value,
                        size=16,
                        weight=ft.FontWeight.W_600,
                        color=theme.INK,
                        font_family=theme.FONT_FAMILY,
                        text_align=ft.TextAlign.RIGHT,
                    ),
                ],
            ),
        )

    def start(_):
        STATE.user = user
        STATE.go("/home")

    # ID мелким текстом под приветствием — полезно, не перегружает
    body = [
        ft.Container(height=8),
        ft.Row(alignment=ft.MainAxisAlignment.CENTER, controls=[avatar]),
        ft.Container(height=16),
        ft.Text(
            f"Добро пожаловать,\n{user.first_name}!",
            size=28,
            weight=ft.FontWeight.BOLD,
            color=theme.INK,
            font_family=theme.FONT_FAMILY,
            text_align=ft.TextAlign.CENTER,
            width=float(theme.PHONE_WIDTH - theme.PAGE_PADDING * 2),
        ),
        ft.Container(height=6),
        ft.Text(
            f"ID {user.public_id}",
            size=13,
            color=theme.HINT,
            font_family=theme.FONT_FAMILY,
            text_align=ft.TextAlign.CENTER,
            width=float(theme.PHONE_WIDTH - theme.PAGE_PADDING * 2),
        ),
        ft.Container(height=22),
        info_card("Класс", class_name),
        ft.Container(height=10),
        info_card("Школа", school_name),
        ft.Container(height=10),
        info_card("Роль", "Ученик"),
    ]

    return _chrome(
        "",  # title пустой — приветствие в body
        1.0,
        body,
        start,
        "/reg/contact",
        next_label="Начать общение",
        show_consent=False,
        show_back=False,
        header="Всё готово!",
    )


# ---------------------------------------------------------------------------
#  Учитель: где работаете
# ---------------------------------------------------------------------------

def build_reg_work(page: ft.Page) -> ft.Control:
    city_col, city = _pill_field("Город", "Москва", value=STATE.draft.get("city", ""))
    school_col, school = _pill_field("Школа", "Школа №67", value=STATE.draft.get("school_name", ""))
    city_sug = ft.Column(spacing=4, controls=[])
    school_sug = ft.Column(spacing=4, controls=[])

    def _item(text: str, on_pick):
        return ft.Container(
            content=ft.Text(text, size=15, color=theme.INK, font_family=theme.FONT_FAMILY),
            padding=ft.Padding.symmetric(horizontal=14, vertical=10),
            bgcolor="#F0F0F5",
            border_radius=14,
            on_click=on_pick,
            ink=True,
        )

    def pick_city(name: str):
        city.value = name
        city.update()
        city_sug.controls.clear()
        try:
            city_sug.update()
        except Exception:
            pass
        refresh_schools()

    def pick_school(name: str):
        school.value = name
        school.update()
        school_sug.controls.clear()
        try:
            school_sug.update()
        except Exception:
            pass

    def on_city_change(e):
        city_sug.controls.clear()
        q = city.value or ""
        found = formatters.city_suggestions(q, limit=5) if q.strip() else []
        for name in found:
            city_sug.controls.append(_item(name, lambda e, n=name: pick_city(n)))
        try:
            city_sug.update()
        except Exception:
            pass

    def refresh_schools():
        school_sug.controls.clear()
        c = (city.value or "").strip()
        q = school.value or ""
        if len(c) < 2:
            try:
                school_sug.update()
            except Exception:
                pass
            return
        from core import schools as _schools
        found = _schools.search(c, q, limit=6)
        for name in found:
            school_sug.controls.append(_item(name, lambda e, n=name: pick_school(n)))
        try:
            school_sug.update()
        except Exception:
            pass

    def on_school_change(e):
        refresh_schools()

    city.on_change = on_city_change
    school.on_change = on_school_change

    def next_(_):
        c = (city.value or "").strip()
        s = (school.value or "").strip()
        if len(c) < 2 or len(s) < 2:
            STATE.error("Укажите город и школу")
            return
        STATE.draft["city"] = c
        STATE.draft["school_name"] = s
        STATE.go("/reg/proof")

    return _chrome(
        "Где вы работаете?",
        0.55,
        [city_col, city_sug, ft.Container(height=8), school_col, school_sug],
        next_,
        "/reg/password",
        show_consent=True,
    )


def build_reg_proof(page: ft.Page) -> ft.Control:
    """Фото/скриншот из школьного приложения → Discord."""
    status = ft.Text("", size=13, color=theme.MUTED, font_family=theme.FONT_FAMILY)
    preview = ft.Container(height=0)

    def _set_file(path: str):
        if not path:
            return
        STATE.draft["proof_path"] = path
        name = path.replace("\\", "/").split("/")[-1]
        status.value = f"Файл: {name}"
        try:
            status.update()
        except Exception:
            pass

    def pick(_):
        # Flet 1.x не знает control FilePicker — системный диалог Windows
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            path = filedialog.askopenfilename(
                title="Скриншот или фото",
                filetypes=[
                    ("Изображения", "*.png *.jpg *.jpeg *.webp"),
                    ("Все файлы", "*.*"),
                ],
            )
            root.destroy()
            _set_file(path)
        except Exception as exc:
            STATE.error(f"Не удалось открыть выбор файла: {exc}")

    def send(_):
        path = STATE.draft.get("proof_path") or ""
        if not path:
            STATE.error("Прикрепите фото или скриншот")
            return
        name = f"{STATE.draft.get('first_name', '')} {STATE.draft.get('last_name', '')}".strip()
        try:
            from core import teacher_proof
            app_id = teacher_proof.submit_to_discord(
                name,
                STATE.draft.get("city", ""),
                STATE.draft.get("school_name", ""),
                path,
            )
        except Exception as exc:
            STATE.error(f"Не удалось отправить: {exc}")
            return
        STATE.draft["proof_sent"] = True
        STATE.draft["proof_app_id"] = app_id
        STATE.info(
            f"Анкета #{app_id} отправлена в Discord.\nПосле одобрения нажмите «Проверить».",
            "Отправлено",
        )
        if SETTINGS.get("dev_mode") and not (SETTINGS.get("discord") or {}).get("webhook_url"):
            STATE.draft["teacher_approved"] = True

    body = [
        ft.Text(
            "Прикрепите фото или скриншот из школьного приложения,\nгде видно, что вы учитель.",
            size=15,
            color=theme.MUTED,
            font_family=theme.FONT_FAMILY,
        ),
        ft.Container(height=16),
        theme.primary_image_button("Выбрать файл", pick),
        ft.Container(height=8),
        status,
        ft.Container(height=16),
        theme.primary_image_button("Отправить на проверку", send),
        ft.Container(height=8),
        theme.secondary_image_button("Проверить статус", lambda _: _check_status()),
    ]

    def _check_status():
        app_id = STATE.draft.get("proof_app_id")
        if not app_id:
            STATE.error("Сначала отправьте анкету")
            return
        from core import teacher_proof
        st = teacher_proof.approval_status(app_id)
        if st == "approved":
            STATE.draft["teacher_approved"] = True
            STATE.info("Одобрено. Можно продолжить.", "Готово")
        elif st == "rejected":
            STATE.draft["teacher_approved"] = False
            STATE.error("Анкета отклонена. Пройдите регистрацию заново.")
        else:
            STATE.info("Пока на проверке.", "Ожидание")

    return _chrome(
        "Подтверждение",
        0.75,
        body,
        lambda _: STATE.go("/reg/contact") if STATE.draft.get("teacher_approved") else STATE.error("Дождитесь одобрения"),
        "/reg/work",
        next_label="Далее",
        show_consent=False,
    )
