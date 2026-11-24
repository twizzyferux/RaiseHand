# -*- coding: utf-8 -*-
"""Состояние приложения: пользователь, черновик регистрации, навигация."""
from __future__ import annotations

from typing import Any, Callable, Optional

from core import auth, session
from core.config import SETTINGS


class AppState:
    def __init__(self):
        self.user: Optional[auth.User] = None
        self.draft: dict[str, Any] = {}
        self._go: Optional[Callable[[str], None]] = None
        self._snack: Optional[Callable[[str], None]] = None
        self._dialog: Optional[Callable[[str, str], None]] = None

    def bind(self, go, snack, dialog):
        self._go = go
        self._snack = snack
        self._dialog = dialog

    def go(self, route: str) -> None:
        if self._go:
            self._go(route)

    def snack(self, message: str) -> None:
        if self._snack:
            self._snack(message)

    def error(self, message: str, title: str = "Ошибка") -> None:
        if self._dialog:
            self._dialog(title, message)
        else:
            self.snack(message)

    def info(self, message: str, title: str = "Готово") -> None:
        if self._dialog:
            self._dialog(title, message)

    def reset_draft(self) -> None:
        self.draft = {
            "first_name": "", "last_name": "", "password": "",
            "remember": False, "city": "", "invite_code": "",
            "class_name": "", "school_name": "",
            "contact_type": "", "contact_value": "",
            "code": None, "user": None, "_fresh": True,
        }

    def restore_session(self) -> str:
        """Вернуть стартовый route."""
        uid = session.user_id()
        if not uid:
            return "/welcome"
        user = auth.get_user_by_id(uid)
        if user is None:
            session.clear()
            return "/welcome"
        if auth.inactivity_due(user):
            auth.delete_account(user.id)
            session.clear()
            return "/welcome"
        try:
            auth.touch_last_active(user.id)
            user = auth.get_user_by_id(uid) or user
        except Exception:
            pass
        self.user = user
        if not user.contact_verified:
            return "/verify"
        if user.is_teacher and not user.teacher_verified:
            return "/teacher_proof"
        return "/home"

    def texts(self) -> dict:
        return SETTINGS.get("texts") or {}

    def slides(self) -> list:
        raw = SETTINGS.get("welcome_slides")
        if isinstance(raw, list) and raw:
            return raw
        return [
            {"title": t("welcome.slide1_title"),
             "subtitle": t("welcome.slide1_sub")},
            {"title": t("welcome.slide2_title"),
             "subtitle": t("welcome.slide2_sub")},
            {"title": t("welcome.slide3_title"),
             "subtitle": t("welcome.slide3_sub")},
        ]


STATE = AppState()
