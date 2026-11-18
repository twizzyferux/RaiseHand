# -*- coding: utf-8 -*-
"""
Мониторинг RaiseHand: раз в минуту проверяет health URL / доступность БД
и пишет в Discord-канал, если сервис упал.

Запуск отдельно от мессенджера:
    python -m discord_bot.monitor
"""
from __future__ import annotations

import asyncio
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import discord
from discord.ext import tasks

from core.config import DB_PATH, SETTINGS
from core import logs

HEALTH_URL = os.environ.get(
    "RH_HEALTH_URL",
    str((SETTINGS.get("monitor") or {}).get("health_url") or "").strip(),
)
CHECK_SEC = int(os.environ.get("RH_MONITOR_INTERVAL", "60"))


def _db_ok() -> bool:
    try:
        import sqlite3

        if not os.path.isfile(DB_PATH):
            return False
        conn = sqlite3.connect(DB_PATH, timeout=3)
        try:
            conn.execute("SELECT 1").fetchone()
        finally:
            conn.close()
        return True
    except Exception:
        return False


async def _http_ok(url: str) -> bool:
    if not url:
        return True
    try:
        import httpx

        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(url)
            return resp.status_code < 500
    except Exception:
        try:
            import urllib.request

            def _sync():
                with urllib.request.urlopen(url, timeout=8) as resp:
                    return getattr(resp, "status", 200) < 500

            return await asyncio.to_thread(_sync)
        except Exception:
            return False


intents = discord.Intents.default()
bot = discord.Client(intents=intents)
_state = {"down": False}


@bot.event
async def on_ready():
    logs.setup()
    logs.info("monitor bot ready as %s", bot.user)
    if not check_loop.is_running():
        check_loop.start()


@tasks.loop(seconds=CHECK_SEC)
async def check_loop():
    channel_id = int((SETTINGS.get("discord") or {}).get("channel_id") or 0)
    if not channel_id:
        return
    channel = bot.get_channel(channel_id)
    if channel is None:
        try:
            channel = await bot.fetch_channel(channel_id)
        except Exception:
            return

    db_ok = _db_ok()
    http_ok = await _http_ok(HEALTH_URL) if HEALTH_URL else True
    ok = db_ok and http_ok

    if not ok and not _state["down"]:
        _state["down"] = True
        parts = []
        if not db_ok:
            parts.append("БД недоступна")
        if HEALTH_URL and not http_ok:
            parts.append(f"health `{HEALTH_URL}` не отвечает")
        msg = "🚨 **RaiseHand down:** " + "; ".join(parts or ["неизвестная ошибка"])
        try:
            await channel.send(msg)
        except Exception as exc:
            logs.error("monitor notify failed: %s", exc)
        logs.error("monitor: DOWN %s", parts)
    elif ok and _state["down"]:
        _state["down"] = False
        try:
            await channel.send("✅ **RaiseHand снова доступен**")
        except Exception:
            pass
        logs.info("monitor: recovered")


def main():
    token = (SETTINGS.get("discord") or {}).get("bot_token") or ""
    if not token:
        raise SystemExit("Укажите discord.bot_token в settings.json")
    logs.setup()
    bot.run(token)


if __name__ == "__main__":
    main()
