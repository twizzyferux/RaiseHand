"""Загрузка настроек из config/settings.json.

Дизайна здесь нет: только тексты, правила и пути к спрайтам (по умолчанию пустые).
Когда нарисуешь свои картинки — пропиши их в settings.json -> "sprites".
"""

import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(BASE_DIR, "config")
DATA_DIR = os.path.join(BASE_DIR, "data")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(os.path.join(DATA_DIR, "uploads"), exist_ok=True)


def _load_json(name: str) -> dict:
    with open(os.path.join(CONFIG_DIR, name), "r", encoding="utf-8") as f:
        return json.load(f)


SETTINGS = _load_json("settings.json")


def text(name: str) -> str:
    return SETTINGS["texts"][name]


def rule(name: str):
    return SETTINGS["rules"][name]


def sprite(name: str) -> str:
    """Путь к спрайту. Пустая строка, если спрайт не задан или файла нет."""
    rel = SETTINGS.get("sprites", {}).get(name, "")
    if not rel:
        return ""
    path = rel if os.path.isabs(rel) else os.path.join(BASE_DIR, rel)
    return path if os.path.exists(path) else ""


DB_PATH = os.path.join(DATA_DIR, "messenger.db")
UPLOADS_DIR = os.path.join(DATA_DIR, "uploads")
OUTBOX_PATH = os.path.join(DATA_DIR, "outbox.log")


def save_settings() -> None:
    """Записать SETTINGS обратно в config/settings.json.

    Нужно для «Запомнить меня» (запоминаем логин для экрана входа).
    """
    with open(os.path.join(CONFIG_DIR, "settings.json"), "w",
              encoding="utf-8") as f:
        json.dump(SETTINGS, f, ensure_ascii=False, indent=2)
