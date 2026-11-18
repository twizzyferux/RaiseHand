# -*- coding: utf-8 -*-
"""Темы RaiseHand (цвета пузырей / акцента) + иконки приложения."""
from __future__ import annotations

import json
import os
from typing import Any

from core.config import BASE_DIR

_THEMES_PATH = os.path.join(BASE_DIR, "assets", "images", "branding", "themes", "themes.json")
_ICONS_DIR = os.path.join(BASE_DIR, "assets", "images", "branding", "app-icons")

THEME_KEYS = ("violet", "pink", "blue", "coral", "green", "orange")
THEME_LABELS = {
    "violet": "Фиолетовая",
    "pink": "Розовая",
    "blue": "Голубая",
    "coral": "Коралловая",
    "green": "Зелёная",
    "orange": "Оранжевая",
}


def _load_themes() -> dict[str, Any]:
    try:
        with open(_THEMES_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("themes") or {}
    except Exception:
        return {}


def theme_tokens(key: str, mode: str) -> dict[str, str]:
    themes = _load_themes()
    key = key if key in themes else "violet"
    mode = "dark" if mode == "dark" else "light"
    block = (themes.get(key) or {}).get(mode) or {}
    return {str(k): str(v) for k, v in block.items()}


def app_icon_path(key: str, *, dark: bool = False) -> str:
    key = key if key in THEME_KEYS else "violet"
    suffix = "dark" if dark else "light"
    return os.path.join(_ICONS_DIR, f"appicon-{key}-{suffix}-1024.png")


def list_app_icons(*, dark: bool = False) -> list[tuple[str, str, str]]:
    """[(key, label, path), ...]"""
    out = []
    for key in THEME_KEYS:
        path = app_icon_path(key, dark=dark)
        if os.path.isfile(path):
            out.append((key, THEME_LABELS.get(key, key), path))
    return out
