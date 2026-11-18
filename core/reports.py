# -*- coding: utf-8 -*-
"""Жалобы пользователей → Discord-бот (канал reports) + запись в БД."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from core import database as db, logs
from core.config import SETTINGS

REPORT_REASONS = (
    "Спам",
    "Оскорбления",
    "Травля / буллинг",
    "Неприемлемый контент",
    "Мошенничество",
    "Другое",
)


class ReportError(Exception):
    pass


def reports_channel_id() -> str:
    discord = SETTINGS.get("discord") or {}
    return str(
        discord.get("reports_channel_id") or "1571586506064400414"
    ).strip()


def _ensure_table() -> None:
    try:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reporter_id INTEGER,
                target_public_id TEXT NOT NULL,
                reason TEXT NOT NULL,
                details TEXT DEFAULT '',
                chat_id TEXT DEFAULT '',
                msg_id TEXT DEFAULT '',
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
    except Exception:
        pass


def submit_report(
    *,
    reporter_id: Optional[int],
    reporter_public_id: str,
    target_public_id: str,
    reason: str,
    details: str = "",
    chat_id: str = "",
    msg_id: str = "",
) -> int:
    """Сохранить жалобу и отправить ботом в Discord-канал. Возвращает id."""
    reason = (reason or "").strip() or "Другое"
    target_public_id = (target_public_id or "").strip()
    details = (details or "").strip()
    if not target_public_id:
        raise ReportError("Не указан пользователь")
    if not details:
        raise ReportError("Добавьте описание жалобы")

    _ensure_table()
    report_id = db.execute(
        """
        INSERT INTO reports
            (reporter_id, target_public_id, reason, details, chat_id, msg_id)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            reporter_id,
            target_public_id,
            reason,
            details,
            chat_id or "",
            msg_id or "",
        ),
    )

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    payload = {
        "report_id": int(report_id),
        "reporter_public_id": reporter_public_id or "anon",
        "target_public_id": target_public_id,
        "reason": reason,
        "details": details,
        "chat_id": chat_id or "",
        "msg_id": msg_id or "",
        "created_at": now,
        "channel_id": reports_channel_id(),
    }

    try:
        from discord_bot.report_bridge import send_report_to_discord

        mode = send_report_to_discord(payload)
        logs.info("report #%s delivered via %s → channel %s", report_id, mode, reports_channel_id())
    except Exception as exc:
        logs.error("report discord failed id=%s: %s", report_id, exc)
        raise ReportError(
            f"Жалоба сохранена (№{report_id}), но Discord недоступен: {exc}"
        ) from exc

    logs.event(
        "REPORT",
        id=report_id,
        by=reporter_public_id or "-",
        target=target_public_id,
        reason=reason,
    )
    return int(report_id)


def list_reports(limit: int = 50) -> list[dict[str, Any]]:
    _ensure_table()
    rows = db.query_all(
        """
        SELECT id, reporter_id, target_public_id, reason, details, chat_id, msg_id, created_at
        FROM reports ORDER BY id DESC LIMIT ?
        """,
        (max(1, min(int(limit), 200)),),
    )
    return [dict(r) for r in rows]
