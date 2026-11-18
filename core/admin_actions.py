# -*- coding: utf-8 -*-
"""Админ-действия: бан и перевыдача ID.

Перед каждым действием обязательно:
    if current_user.role != 'admin': ...
"""
from __future__ import annotations

from typing import Optional

from core import auth, database as db, logs
from core.ids import generate_public_id as build_public_id


class AdminError(Exception):
    """Текст можно показать в UI."""


def _require_admin(current_user: Optional[auth.User]) -> auth.User:
    if current_user is None:
        raise AdminError("Нужна авторизация")
    if current_user.role != "admin":
        logs.warn("admin_denied user=%s role=%s", getattr(current_user, "public_id", "?"), current_user.role)
        raise AdminError("Только администратор может выполнить это действие")
    return current_user


def ban_user(current_user: auth.User, target_public_id: str, *, reason: str = "") -> auth.User:
    """Забанить пользователя по public_id."""
    admin = _require_admin(current_user)
    target = auth.find_by_public_id(target_public_id)
    if target is None:
        raise AdminError("Пользователь не найден")
    if target.id == admin.id:
        raise AdminError("Нельзя забанить самого себя")
    if target.role == "admin":
        raise AdminError("Нельзя забанить администратора")
    db.execute("UPDATE users SET is_banned = 1 WHERE id = ?", (target.id,))
    logs.event("BAN", by=admin.public_id, target=target.public_id, reason=reason or "-")
    return auth.get_user_by_id(target.id)


def unban_user(current_user: auth.User, target_public_id: str) -> auth.User:
    admin = _require_admin(current_user)
    target = auth.find_by_public_id(target_public_id)
    if target is None:
        raise AdminError("Пользователь не найден")
    db.execute("UPDATE users SET is_banned = 0 WHERE id = ?", (target.id,))
    logs.event("UNBAN", by=admin.public_id, target=target.public_id)
    return auth.get_user_by_id(target.id)


def issue_new_id(current_user: auth.User, target_public_id: str) -> auth.User:
    """Выдать пользователю новый public_id (старый освобождается)."""
    admin = _require_admin(current_user)
    target = auth.find_by_public_id(target_public_id)
    if target is None:
        raise AdminError("Пользователь не найден")

    def _exists(candidate: str) -> bool:
        return auth._public_id_exists(candidate)

    new_id = build_public_id(target.role, exists=_exists)
    old = target.public_id
    db.execute("UPDATE users SET public_id = ? WHERE id = ?", (new_id, target.id))
    logs.event("ISSUE_ID", by=admin.public_id, old=old, new=new_id)
    return auth.get_user_by_id(target.id)


def list_recent_users(limit: int = 40) -> list[auth.User]:
    rows = db.query_all(
        "SELECT * FROM users ORDER BY id DESC LIMIT ?",
        (max(1, min(int(limit), 200)),),
    )
    out: list[auth.User] = []
    for row in rows:
        u = auth.row_to_user(row)
        if u is not None:
            out.append(u)
    return out
