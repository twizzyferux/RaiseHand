# -*- coding: utf-8 -*-
"""Логи приложения: пишем в файл, который не потеряется при перезапуске.

Зачем:
  * видно, что приложение делало, если что-то пошло не так;
  * лог переживает закрытие — в отличие от вывода в консоль;
  * ошибки самого Kivy (его Logger) попадают в тот же файл.

Файл: data/app.log, старая версия переименовывается в app.log.1,
чтобы лог не рос бесконечно. Хвост лога можно посмотреть прямо
в приложении (экран «Логи»).
"""
import logging
import os
import platform
import socket
import sys
from logging.handlers import RotatingFileHandler

from core.config import DATA_DIR

LOG_PATH = os.path.join(DATA_DIR, "app.log")

MAX_BYTES = 1024 * 1024      # 1 МБ на текущий лог
BACKUPS = 3                  # и три предыдущих
_to_app: logging.Logger = None


def _device() -> str:
    """Что-то человеческое про машину: чтобы в логе было видно, откуда запуск."""
    try:
        name = socket.gethostname()
    except Exception:
        name = "unknown"
    return "%s/%s, Python %s" % (name, platform.system(), platform.python_version())


def setup() -> logging.Logger:
    """Готовит логирование. Вызывается один раз при старте приложения."""
    global _to_app
    if _to_app is not None:
        return _to_app

    logger = logging.getLogger("raisehand")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    if not logger.handlers:
        try:
            handler = RotatingFileHandler(LOG_PATH, maxBytes=MAX_BYTES,
                                          backupCount=BACKUPS, encoding="utf-8")
            handler.setFormatter(logging.Formatter(
                "%(asctime)s  %(levelname)-7s %(message)s", "%Y-%m-%d %H:%M:%S"))
            logger.addHandler(handler)
        except Exception:
            # Если файл недоступен (например, только чтение) — не падаем,
            # просто пишем в консоль.
            logger.addHandler(logging.StreamHandler(sys.stderr))

    # Ошибки Kivy (traceback из .kv и виджетов) — в тот же файл
    kivy_logger = logging.getLogger("kivy")
    kivy_logger.setLevel(logging.WARNING)
    if not kivy_logger.handlers:
        kivy_logger.addHandler(logging.StreamHandler(sys.stdout))
    for handler in list(logger.handlers):
        kivy_logger.addHandler(handler)

    _to_app = logger
    return logger


def _log(level: int, message: str, *args) -> None:
    logger = _to_app or setup()
    try:
        logger.log(level, message, *args)
    except Exception:
        pass


def info(message: str, *args) -> None:
    _log(logging.INFO, message, *args)


def warn(message: str, *args) -> None:
    _log(logging.WARNING, message, *args)


def error(message: str, *args) -> None:
    _log(logging.ERROR, message, *args)


def event(action: str, **fields) -> None:
    """Запись о действии пользователя: вход, сообщение, выход и т.п.

    Пишется отдельной строкой, чтобы по логу можно было быстро понять,
    что человек делал: `ВОЙТИ user=Иван (4820193) ip=...`
    """
    extra = " ".join("%s=%s" % (k, v) for k, v in fields.items())
    _log(logging.INFO, "%-14s %s" % (action, extra))


def tail(lines: int = 200) -> str:
    """Последние строки лога — для экрана «Логи» в приложении."""
    try:
        with open(LOG_PATH, "r", encoding="utf-8", errors="replace") as f:
            content = f.read().splitlines()
    except Exception:
        return "Лог пока пуст."
    return "\n".join(content[-lines:])


def path() -> str:
    return LOG_PATH