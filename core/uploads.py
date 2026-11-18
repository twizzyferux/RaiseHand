# -*- coding: utf-8 -*-
"""Валидация загружаемых файлов: расширение и размер."""

from __future__ import annotations

import os
import shutil
import uuid
from typing import Iterable, Optional

from core.config import UPLOADS_DIR

DEFAULT_ALLOWED = (".jpg", ".jpeg", ".png", ".pdf", ".webp")
DEFAULT_MAX_BYTES = 5 * 1024 * 1024  # 5 МБ


class UploadError(Exception):
    """Файл не прошёл проверку."""


def validate_file(
    path: str,
    *,
    allowed_ext: Iterable[str] = DEFAULT_ALLOWED,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> str:
    """Проверить файл. Вернуть нормализованный абсолютный путь."""
    if not path or not str(path).strip():
        raise UploadError("Файл не выбран")
    path = os.path.abspath(path)
    if not os.path.isfile(path):
        raise UploadError("Файл не найден")

    ext = os.path.splitext(path)[1].lower()
    allowed = {e.lower() if e.startswith(".") else f".{e.lower()}" for e in allowed_ext}
    if ext not in allowed:
        raise UploadError(
            f"Недопустимый тип файла «{ext or '?'}». "
            f"Можно: {', '.join(sorted(allowed))}"
        )

    size = os.path.getsize(path)
    if size <= 0:
        raise UploadError("Файл пустой")
    if size > max_bytes:
        mb = max_bytes / (1024 * 1024)
        raise UploadError(f"Файл больше {mb:.0f} МБ")
    return path


def save_upload(
    path: str,
    *,
    allowed_ext: Iterable[str] = DEFAULT_ALLOWED,
    max_bytes: int = DEFAULT_MAX_BYTES,
    subdir: str = "chat",
) -> str:
    """Проверить и скопировать файл в data/uploads/… Вернуть новый путь."""
    src = validate_file(path, allowed_ext=allowed_ext, max_bytes=max_bytes)
    dest_dir = os.path.join(UPLOADS_DIR, subdir)
    os.makedirs(dest_dir, exist_ok=True)
    ext = os.path.splitext(src)[1].lower()
    name = f"{uuid.uuid4().hex}{ext}"
    dest = os.path.join(dest_dir, name)
    shutil.copy2(src, dest)
    return dest


def is_image(path: str) -> bool:
    return os.path.splitext(path or "")[1].lower() in {".jpg", ".jpeg", ".png", ".webp"}
