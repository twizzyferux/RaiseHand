"""Загрузка настроек из config/settings.json."""

import json
import os
import sys
import tempfile

def _detect_platform() -> str:
    """ios / android / win / linux / macos."""
    plat = (sys.platform or "").lower()
    if plat == "darwin":
        return "macos"
    if plat.startswith("win"):
        return "win"
    # Flet / mobile runtime hints
    if os.environ.get("FLET_PLATFORM", "").lower() in ("ios", "android"):
        return os.environ["FLET_PLATFORM"].lower()
    if "iphone" in plat or "ios" in plat:
        return "ios"
    if "android" in plat:
        return "android"
    return "linux"


_app_platform = _detect_platform()


def get_app_platform() -> str:
    """ios / android / win / linux / macos."""
    return _app_platform


# Если программа собрана PyInstaller, BASE_DIR указывает на временную папку _MEIPASS
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CONFIG_SRC_DIR = os.path.join(BASE_DIR, "config")


def _writable_dir(name: str) -> str:
    """Папка для данных — та, куда действительно можно записать."""

    candidates = []

    # Если это .exe, сохраняем данные рядом с самим .exe (а не во временной папке)
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        candidates.append(os.path.join(exe_dir, name))
    else:
        candidates.append(os.path.join(BASE_DIR, name))

    if _app_platform == "ios":
        container = os.path.dirname(BASE_DIR)
        home = os.environ.get("HOME") or os.path.expanduser("~")
        candidates = [
            os.path.join(home, name),
            os.path.join(home, "Documents", name),
            os.path.join(container, "Documents", name),
            os.path.join(container, name),
            os.path.join(container, "Library", name),
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

    sys.stderr.write("config: не удалось создать %s: %s\n"
                     % (name, "; ".join(reason)))
    return candidates[-1]


CONFIG_DIR = _writable_dir("config")
DATA_DIR = _writable_dir("data")

try:
    os.makedirs(os.path.join(DATA_DIR, "uploads"), exist_ok=True)
except OSError as e:
    sys.stderr.write("config: не создать папку uploads: %s\n" % e)


def _config_path(name: str) -> str:
    """Откуда читать настройки."""
    written = os.path.join(CONFIG_DIR, name)
    if os.path.exists(written):
        return written

    # Читаем из ресурсов, упакованных в .exe
    bundled = os.path.join(CONFIG_SRC_DIR, name)
    return bundled if os.path.exists(bundled) else written


def _load_json(name: str) -> dict:
    try:
        with open(_config_path(name), "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        sys.stderr.write(f"Файл {name} не найден!\n")
        return {}
    except (OSError, json.JSONDecodeError) as e:
        sys.stderr.write(f"Файл {name} не прочитан: {e}\n")
        return {}


def _load_settings() -> dict:
    data = _load_json("settings.json")
    if data:
        return data
    # Репозиторий/IPA: без локальных секретов — безопасные defaults
    return _load_json("settings.defaults.json")


SETTINGS = _load_settings()


def text(name: str) -> str:
    return SETTINGS.get("texts", {}).get(name, "")


def rule(name: str):
    return SETTINGS.get("rules", {}).get(name)


def sprite(name: str) -> str:
    """Путь к спрайту."""
    rel = SETTINGS.get("sprites", {}).get(name, "")
    if not rel:
        return ""
    path = rel if os.path.isabs(rel) else os.path.join(BASE_DIR, rel)
    return path if os.path.exists(path) else ""


DB_PATH = os.environ.get("RH_DB") or os.path.join(DATA_DIR, "messenger.db")
UPLOADS_DIR = os.path.join(DATA_DIR, "uploads")
OUTBOX_PATH = os.path.join(DATA_DIR, "outbox.log")


def save_settings() -> None:
    """Записать SETTINGS обратно в config/settings.json."""
    with open(os.path.join(CONFIG_DIR, "settings.json"), "w",
              encoding="utf-8") as f:
        json.dump(SETTINGS, f, ensure_ascii=False, indent=2)


# ==========================================
# НОВОЕ: Безопасное получение токена
# ==========================================
def get_token() -> str:
    """Токен Discord-бота: env, затем settings.json."""
    for key in ("DISCORD_BOT_TOKEN", "DISCORD_TOKEN"):
        token = os.environ.get(key)
        if token:
            return token.strip()
    discord = SETTINGS.get("discord") or {}
    token = discord.get("bot_token") or SETTINGS.get("token") or ""
    return str(token).strip()