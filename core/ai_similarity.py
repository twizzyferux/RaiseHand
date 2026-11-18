# -*- coding: utf-8 -*-
"""Семантическая схожесть вопросов через бесплатный Gemini API.

Ключ (бесплатно в Google AI Studio):
  - env GEMINI_API_KEY / GOOGLE_API_KEY
  - или config/settings.json → ai.gemini_api_key

Без ключа модуль возвращает None — вызывающий код использует локальный fallback.
"""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from typing import Optional

from core.config import SETTINGS

_MODEL = "gemini-2.0-flash"
_ENDPOINT = (
    f"https://generativelanguage.googleapis.com/v1beta/models/{_MODEL}:generateContent"
)


def _api_key() -> str:
    cfg = (SETTINGS.get("ai") or {}) if isinstance(SETTINGS, dict) else {}
    return (
        (os.environ.get("GEMINI_API_KEY") or "").strip()
        or (os.environ.get("GOOGLE_API_KEY") or "").strip()
        or str(cfg.get("gemini_api_key") or "").strip()
    )


def available() -> bool:
    return bool(_api_key())


def find_same_question_index(new_text: str, candidates: list[str]) -> Optional[int]:
    """
    Спросить Gemini: есть ли среди candidates тот же смысл, что у new_text.
    Returns 0-based index or None.
    """
    key = _api_key()
    if not key or not candidates:
        return None
    new_text = (new_text or "").strip()
    if not new_text:
        return None

    lines = "\n".join(f"{i + 1}. {c}" for i, c in enumerate(candidates))
    prompt = (
        "Ты помощник школьного мессенджера RaiseHand.\n"
        "Определи, есть ли среди списка вопросов тот же самый вопрос по смыслу "
        "(перефраз, опечатка, «третью»=«3», другая формулировка).\n"
        "Если тот же смысл — ответь ТОЛЬКО номером из списка (например 2).\n"
        "Если ни один не совпадает по смыслу — ответь NONE.\n"
        "Не объясняй.\n\n"
        f"НОВЫЙ ВОПРОС:\n{new_text}\n\n"
        f"СПИСОК:\n{lines}\n"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.0,
            "maxOutputTokens": 16,
        },
    }
    url = f"{_ENDPOINT}?key={urllib.parse.quote(key)}"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None

    try:
        text = (
            raw["candidates"][0]["content"]["parts"][0]["text"]
            .strip()
            .upper()
        )
    except Exception:
        return None

    if "NONE" in text or text in ("", "-", "НЕТ", "NO"):
        return None
    digits = "".join(ch if ch.isdigit() else " " for ch in text).split()
    if not digits:
        return None
    try:
        n = int(digits[0])
    except Exception:
        return None
    if 1 <= n <= len(candidates):
        return n - 1
    return None
