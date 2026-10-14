"""Загрузка настроек из config/settings.json.

Дизайна здесь нет: только тексты, правила и пути к спрайтам (по умолчанию пустые).
Когда нарисуешь свои картинки — пропиши их в settings.json -> "sprites".
"""

import json
import os
import sys
import tempfile

from kivy.utils import platform as _kivy_platform

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Исходник настроек лежит внутри поставки. BASE_DIR на iOS указывает в
# саму папку приложения, а она только для чтения: записать туда нельзя.
CONFIG_SRC_DIR = os.path.join(BASE_DIR, "config")


def _writable_dir(name: str) -> str:
    """Папка для данных — та, куда действительно можно записать.

    На iOS папка приложения только для чтения, поэтому данные уходят в
    записываемое место. Какой именно путь там, код не знает, поэтому
    берётся первый, в который запись реально прошла: папка создаётся, в
    неё пишется пробный файл, файл удаляется.

    Исключение отсюда НЕ бросается, и это главное. На iOS kivy-ios не
    выставляет HOME, а TMP указывает внутрь папки приложения — туда
    тоже нельзя писать. Если бы падение было единственным исходом,
    приложение умирало бы на импорте, ещё до первого экрана, и на
    телефоне не оставалось бы ни единого следа: iOS успевает записать
    лог только для падений, которые случились после старта процесса.
    Лучше запуститься и потерять часть данных, чем не запуститься вовсе.

    На ПК поведение не меняется: первой идёт та же папка рядом с кодом.
    """
    candidates = [os.path.join(BASE_DIR, name)]
    if _kivy_platform == "ios":
        home = os.environ.get("HOME") or os.path.expanduser("~")
        candidates = [
            os.path.join(home, name),
            os.path.join(home, "Documents", name),
            os.path.join(home, "Library", name),
        ]
    candidates.extend([
        os.path.join(tempfile.gettempdir(), "raisehand", name),
        os.path.join(os.getcwd(), name),
    ])
    reason = []
    for path in candidates:
        try:
            os.makedirs(path, exist_ok=True)
            probe = os.path.join(path, ".probe")
            with open(probe, "w", encoding="utf-8"):
                pass
            os.remove(probe)
            if reason:
                sys.stderr.write("config: %s недоступны: %s\n"
                                 % (name, "; ".join(reason)))
            return path
        except OSError as e:
            reason.append("%s (%s)" % (path, e))
    # Ничего не подошло: отдаём последний путь и продолжаем. Дальше
    # запись выдаст свою ошибку в том месте, где её видно, а не при
    # импорте всего пакета.
    sys.stderr.write("config: не удалось создать %s: %s\n"
                     % (name, "; ".join(reason)))
    return candidates[-1]


CONFIG_DIR = _writable_dir("config")
DATA_DIR = _writable_dir("data")

# Папка для вложений — через ту же защиту, что и остальные. Раньше здесь
# стоял прямой вызов makedirs, и он ронял импорт целиком там, где
# _writable_dir уже решил не падать: приложение умирало на создании
# папки, не успев ничего показать.
try:
    os.makedirs(os.path.join(DATA_DIR, "uploads"), exist_ok=True)
except OSError as e:
    sys.stderr.write("config: не создать папку uploads: %s\n" % e)


def _config_path(name: str) -> str:
    """Откуда читать настройки.

    Сначала копия, которую приложение перезаписало само (на iOS она в
    папке с данными), а если её нет — исходник из поставки. Иначе на
    iOS первый запуск упал бы с «файла нет», хотя файл внутри
    приложения лежит.
    """
    written = os.path.join(CONFIG_DIR, name)
    if os.path.exists(written):
        return written
    bundled = os.path.join(CONFIG_SRC_DIR, name)
    return bundled if os.path.exists(bundled) else written


def _load_json(name: str) -> dict:
    with open(_config_path(name), "r", encoding="utf-8") as f:
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


# Свою базу можно указать переменной RH_DB — этим пользуются проверочные
# прогоны (_probe*.py): они создают временных собеседников в отдельном
# файле и не трогают настоящие данные.
DB_PATH = os.environ.get("RH_DB") or os.path.join(DATA_DIR, "messenger.db")
UPLOADS_DIR = os.path.join(DATA_DIR, "uploads")
OUTBOX_PATH = os.path.join(DATA_DIR, "outbox.log")


def save_settings() -> None:
    """Записать SETTINGS обратно в config/settings.json.

    Нужно для «Запомнить меня» (запоминаем логин для экрана входа).
    """
    with open(os.path.join(CONFIG_DIR, "settings.json"), "w",
              encoding="utf-8") as f:
        json.dump(SETTINGS, f, ensure_ascii=False, indent=2)
