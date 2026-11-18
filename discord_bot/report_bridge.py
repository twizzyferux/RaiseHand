# -*- coding: utf-8 -*-
"""Мост: приложение → Discord-бот → канал жалоб.

Если бот онлайн — сообщение уходит сразу.
Если нет — пишется в pending-очередь, бот досылает при старте.
"""
from __future__ import annotations

import asyncio
import json
import os
from typing import Any, Optional

from core import logs
from core.config import DATA_DIR, SETTINGS

DEFAULT_REPORTS_CHANNEL_ID = 1571586506064400414
_PENDING_PATH = os.path.join(DATA_DIR, "pending_discord_reports.jsonl")


def reports_channel_id() -> int:
    raw = (SETTINGS.get("discord") or {}).get("reports_channel_id") or DEFAULT_REPORTS_CHANNEL_ID
    try:
        return int(str(raw).strip())
    except Exception:
        return DEFAULT_REPORTS_CHANNEL_ID


def _append_pending(payload: dict[str, Any]) -> None:
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(_PENDING_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception as exc:
        logs.warn("pending report save failed: %s", exc)


def _load_pending() -> list[dict[str, Any]]:
    if not os.path.isfile(_PENDING_PATH):
        return []
    items: list[dict[str, Any]] = []
    try:
        with open(_PENDING_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    items.append(json.loads(line))
                except Exception:
                    pass
    except Exception:
        return []
    return items


def _clear_pending() -> None:
    try:
        if os.path.isfile(_PENDING_PATH):
            os.remove(_PENDING_PATH)
    except Exception:
        pass


def build_embed_dict(payload: dict[str, Any]) -> dict[str, Any]:
    """Сериализуемый embed для Discord API / discord.py."""
    rid = payload.get("report_id") or "?"
    target = payload.get("target_public_id") or "—"
    reporter = payload.get("reporter_public_id") or "anon"
    reason = payload.get("reason") or "Другое"
    details = (payload.get("details") or "").strip()
    chat_id = payload.get("chat_id") or ""
    msg_id = payload.get("msg_id") or ""
    when = payload.get("created_at") or ""

    fields = [
        {"name": "ID нарушителя", "value": f"`{target}`", "inline": True},
        {"name": "Кто пожаловался", "value": f"`{reporter}`", "inline": True},
        {"name": "Причина", "value": reason, "inline": False},
    ]
    if details:
        fields.append(
            {"name": "Описание", "value": details[:1000], "inline": False}
        )
    ctx = []
    if chat_id:
        ctx.append(f"чат `{chat_id}`")
    if msg_id:
        ctx.append(f"сообщение `{msg_id}`")
    if ctx:
        fields.append({"name": "Контекст", "value": " · ".join(ctx), "inline": False})
    if when:
        fields.append({"name": "Время", "value": when, "inline": False})

    return {
        "title": f"Жалоба #{rid}",
        "color": 0xE11D48,
        "fields": fields,
        "footer": {"text": "RaiseHand · модерация"},
    }


async def deliver_report(bot, payload: dict[str, Any]) -> None:
    import discord

    channel_id = reports_channel_id()
    ch = bot.get_channel(channel_id)
    if ch is None:
        ch = await bot.fetch_channel(channel_id)
    embed = discord.Embed.from_dict(build_embed_dict(payload))
    content = f"🚨 Новый репорт на пользователя `{payload.get('target_public_id') or '—'}`"
    await ch.send(content=content, embed=embed)


def send_report_to_discord(payload: dict[str, Any]) -> str:
    """Синхронно из UI-потока. Возвращает 'bot' | 'queued' | 'webhook'."""
    try:
        from discord_bot.bot import bot

        loop = getattr(bot, "loop", None)
        if (
            bot is not None
            and getattr(bot, "is_ready", lambda: False)()
            and loop is not None
            and loop.is_running()
        ):
            fut = asyncio.run_coroutine_threadsafe(deliver_report(bot, payload), loop)
            fut.result(timeout=20)
            return "bot"
    except Exception as exc:
        logs.warn("discord bot report send failed: %s — queue", exc)

    _append_pending(payload)
    return "queued"


async def flush_pending_reports(bot) -> int:
    """Вызвать из on_ready / периодически."""
    items = _load_pending()
    if not items:
        return 0
    sent = 0
    rest: list[dict[str, Any]] = []
    for payload in items:
        try:
            await deliver_report(bot, payload)
            sent += 1
        except Exception as exc:
            logs.warn("flush report failed: %s", exc)
            rest.append(payload)
    _clear_pending()
    for payload in rest:
        _append_pending(payload)
    if sent:
        logs.info("flushed %s pending discord reports", sent)
    return sent
