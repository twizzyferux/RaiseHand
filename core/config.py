"""Загрузка настроек из config/settings.json.

Дизайна здесь нет: только тексты, правила и пути к спрайтам (по умолчанию пустые).
Когда нарисуешь свои картинки — пропиши их в settings.json -> "sprites".
"""

import json
import os
import tempfile

from kivy.utils import platform as _kivy_platform

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Исходник настроек лежит внутри поставки. BASE_DIR на iOS указывает в
# саму папку приложения, а она только для чтения: записать туда нельзя.
CONFIG_SRC_DIR = os.path.join(BASE_DIR, "config")


def _writable_dir(name: str) -> str:
    """Папка для данных — та, куда действительно можно записать.

    На iOS папка приложения только для чтения, поэтому данные уходят в
    домашнюю папку приложения. Какой именно путь там, код не знает,
    поэтому берётся первый, в который запись реально прошла: создаём
    папку, пишем в неё пробный файл, удаляем. Не получилось — берём
    следующий кандидат, в конце папку системы.

    На ПК поведение не меняется: первой идёт та же папка data рядом с
    кодом, что и раньше.
    """
    candidates = [os.path.join(BASE_DIR, name)]
    if _kivy_platform == "ios":
        candidates = [
            os.path.join(os.path.expanduser("~"), name),
            os.path.join(os.path.expanduser("~"), "Documents", name),
        ]
    candidates.append(os.path.join(tempfile.gettempdir(), "raisehand", name))
    last_error = None
    for path in candidates:
        try:
            os.makedirs(path, exist_ok=True)
            probe = os.path.join(path, ".probe")
            with open(probe, "w", encoding="utf-8"):
                pass
            os.remove(probe)
            return path
        except OSError as e:
            last_error = e
            continue
    raise RuntimeError("нет папки, куда можно писать: %s" % last_error)


CONFIG_DIR = _writable_dir("config")
DATA_DIR = _writable_dir("data")

os.makedirs(os.path.join(DATA_DIR, "uploads"), exist_ok=True)


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
