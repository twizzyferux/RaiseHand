# -*- coding: utf-8 -*-
"""Свой градиент для каждого пользователя.

Задача: у ученика (и учителя) должен быть свой аватар — не одна картинка
на всех, а свой градиент. При этом цвета обязательно сочетаться, а не
выбираться случайно из всего подряд.

Как это сделано:
  * за основу взяты 6 градиентов из набора кита (appicons): синий,
    коралловый, зелёный, оранжевый, розовый, фиолетовый. Это фирменные
    пары «сверху светлее → снизу темнее», они уже проверены;
  * к каждой паре добавлена светлая версия (та же пара, но подмешан
    белый), итого 12 сочетаний;
  * номер сочетания считается из ID пользователя, поэтому у одного
    человека градиент всегда один и тот же — и на этом устройстве, и
    на другом, и после перезапуска. Случайности, которая «прыгает», нет.

Картинка рисуется сама: чистый Python пишет PNG (никаких Pillow в
приложении не нужно — иначе на телефоне пришлось бы ставить
дополнительный пакет). Файлы кэшируются в data/avatars/, поэтому
считаются один раз на пользователя.

Акцентная точка (маленькая точка рядом с буквой) тоже своя: она
взята из того же набора и гарантированно контрастна своему градиенту.
"""
import os
import struct
import zlib

from core.config import DATA_DIR

AVATAR_DIR = os.path.join(DATA_DIR, "avatars")
AVATAR_SIZE = 256           # сторона PNG в пикселях

# --- фирменные пары из кита (app-icons/*-light.svg) ----------------------- #
# (сверху, снизу, акцентная точка)
KIT_PAIRS = [
    ((0x4F, 0x97, 0xF3), (0x1F, 0x7B, 0xF0), (0xFF, 0x7B, 0xA7)),   # синий
    ((0xEF, 0x75, 0x6A), (0xEA, 0x4B, 0x3C), (0x82, 0x6A, 0xF7)),   # коралл
    ((0x0E, 0xC8, 0x74), (0x0B, 0x98, 0x58), (0xFF, 0x7B, 0xA7)),   # зелёный
    ((0xF5, 0x7A, 0x28), (0xE0, 0x60, 0x0A), (0x82, 0x6A, 0xF7)),   # оранж
    ((0xEC, 0x67, 0x9D), (0xE6, 0x3A, 0x80), (0x82, 0x6A, 0xF7)),   # розовый
    ((0x83, 0x6E, 0xF4), (0x5B, 0x3F, 0xF0), (0xFF, 0x7B, 0xA7)),   # фиолетовый
]


def _mix(color, other, amount):
    """Смешать цвет с другим: amount=0 — как был, 1 — полностью другой."""
    return tuple(int(round(c + (o - c) * amount)) for c, o in zip(color, other))


WHITE = (255, 255, 255)
BLACK = (0, 0, 0)


def _build_palette():
    """12 сочетаний: 6 фирменных пар + 6 их светлых версий."""
    palette = []
    for top, bottom, accent in KIT_PAIRS:
        palette.append({"top": top, "bottom": bottom, "accent": accent})
    for top, bottom, accent in KIT_PAIRS:
        palette.append({
            "top": _mix(top, WHITE, 0.30),
            "bottom": _mix(bottom, WHITE, 0.16),
            "accent": _mix(accent, WHITE, 0.20),
        })
    return palette


PALETTE = _build_palette()


# --------------------------------------------------------------------------- #
#  Выбор сочетания по пользователю
# --------------------------------------------------------------------------- #

def colors_for(seed: str) -> dict:
    """Сочетание цветов по ID/нику пользователя. Всегда одно и то же."""
    key = (seed or "").strip()
    index = 0
    for ch in key:
        index = (index * 31 + ord(ch)) % 1000003
    return PALETTE[index % len(PALETTE)]


def initials_for(first_name: str, last_name: str) -> str:
    """Инициалы для аватара: «Иван Иванов» -> «ИИ»."""
    first = (first_name or "").strip()[:1]
    last = (last_name or "").strip()[:1]
    text = (first + last).upper()
    return text or "?"


def _rgb(color):
    return "%02X%02X%02X" % color


def avatar_filename(seed: str) -> str:
    """Имя файла кэша: стабильное и читаемое."""
    safe = "".join(c for c in (seed or "") if c.isalnum())[:16] or "user"
    colors = colors_for(seed)
    return "avatar_%s_%s.png" % (
        safe, ("%02x%02x%02x" % colors["top"])[:6])


def avatar_path(seed: str) -> str:
    """Путь к файлу аватара (создаётся при первом обращении)."""
    os.makedirs(AVATAR_DIR, exist_ok=True)
    path = os.path.join(AVATAR_DIR, avatar_filename(seed))
    if not os.path.exists(path):
        _render(path, colors_for(seed))
    return path


# --------------------------------------------------------------------------- #
#  Рисуем PNG сами (без внешних библиотек)
# --------------------------------------------------------------------------- #

def _chunk(tag: bytes, data: bytes) -> bytes:
    return (struct.pack(">I", len(data)) + tag + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))


def _write_png(path: str, size: int, pixels: bytes) -> None:
    """pixels — RGBA, построчно, без фильтров."""
    header = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)
    raw = b"".join(
        b"\x00" + pixels[y * size * 4:(y + 1) * size * 4] for y in range(size))
    body = (b"\x89PNG\r\n\x1a\n"
            + _chunk(b"IHDR", header)
            + _chunk(b"IDAT", zlib.compress(raw, 9))
            + _chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(body)


def _render(path: str, colors: dict) -> None:
    """Круглый аватар: градиент сверху вниз + акцентная точка."""
    size = AVATAR_SIZE
    top = colors["top"]
    bottom = colors["bottom"]
    accent = colors["accent"]
    center = (size - 1) / 2.0
    radius = size / 2.0 - 1.0

    # точка в правом верхнем углу, как в иконке приложения
    dot_cx = size * 0.79
    dot_cy = size * 0.21
    dot_r = size * 0.075

    buf = bytearray(size * size * 4)
    for y in range(size):
        ratio = y / float(size - 1)
        base = tuple(int(round(t + (b - t) * ratio))
                     for t, b in zip(top, bottom))
        row = y * size * 4
        for x in range(size):
            dx = x - center
            dy = y - center
            dist = (dx * dx + dy * dy) ** 0.5
            if dist > radius:
                continue                      # снаружи круга — пусто
            # сглаживание края: последний пиксель делаем полупрозрачным
            alpha = 255 if dist <= radius - 1 else int(
                max(0.0, min(1.0, radius - dist)) * 255)

            color = base
            ddx = x - dot_cx
            ddy = y - dot_cy
            if ddx * ddx + ddy * ddy <= dot_r * dot_r:
                color = accent

            i = row + x * 4
            buf[i] = color[0]
            buf[i + 1] = color[1]
            buf[i + 2] = color[2]
            buf[i + 3] = alpha

    _write_png(path, size, bytes(buf))


def clear_cache() -> None:
    """Убрать все нарисованные аватары (например, при сбросе базы)."""
    if not os.path.isdir(AVATAR_DIR):
        return
    for name in os.listdir(AVATAR_DIR):
        if name.endswith(".png"):
            try:
                os.remove(os.path.join(AVATAR_DIR, name))
            except OSError:
                pass