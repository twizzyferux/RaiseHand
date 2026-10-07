# -*- coding: utf-8 -*-
"""Кроссплатформенный запуск: iOS, Android и ПК.

Логика простая: макет нарисован в системе координат 450x920 «логических
единиц» (dp). На любом устройстве мы выбираем коэффициент UI_SCALE и
передаём его в Metrics.density — тогда все dp() в .kv умножаются на него,
и макет занимает экран ровно, без растягивания и мыла.

  * ПК      — масштаб подбирается под разрешение рабочего стола;
  * Android/iOS — масштаб подбирается под реальный экран устройства
    (окно там появляется только вместе с приложением).

Переопределить вручную: переменная окружения RH_UI_SCALE.
    set RH_UI_SCALE=5 && python main.py       # 2250x4600 — 2K по ширине
"""
import ctypes
import os

from kivy.config import Config
from kivy.metrics import Metrics
from kivy.utils import platform as kivy_platform

DESIGN_W, DESIGN_H = 450, 920          # логический холст макета

IS_MOBILE = kivy_platform in ("android", "ios")
IS_ANDROID = kivy_platform == "android"
IS_IOS = kivy_platform == "ios"
IS_DESKTOP = not IS_MOBILE


def _desktop_size():
    """Свободное место на экране в пикселях (только для ПК).

    Берём рабочую область, а не весь экран: так окно не залезает под
    панель задач и не срезается по высоте.
    """
    if not IS_DESKTOP:
        return DESIGN_W, DESIGN_H
    try:
        user32 = ctypes.windll.user32          # есть только в Windows
        user32.SetProcessDPIAware()
        class RECT(ctypes.Structure):
            _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                        ("right", ctypes.c_long), ("bottom", ctypes.c_long)]
        rect = RECT()
        # SPI_GETWORKAREA = 0x0030 — прямоугольник рабочего стола
        if user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0):
            w = int(rect.right - rect.left)
            h = int(rect.bottom - rect.top)
            if w > 200 and h > 200:
                return w, h
        return int(user32.GetSystemMetrics(0)), int(user32.GetSystemMetrics(1))
    except Exception:
        # macOS/Linux или нет ctypes — берём размер окна по умолчанию
        try:
            from kivy.core.window import Window
            return int(Window.width), int(Window.height)
        except Exception:
            return 1920, 1080


def _fit_scale(px_w, px_h, cap=5.0):
    """Коэффициент, при котором макет вписывается в экран по обеим осям."""
    if px_w <= 0 or px_h <= 0:
        return 1.0
    return max(1.0, min(px_h / float(DESIGN_H), px_w / float(DESIGN_W), cap))


def _env_scale():
    raw = os.environ.get("RH_UI_SCALE", "").strip()
    if not raw:
        return None
    try:
        return max(0.5, min(8.0, float(raw)))
    except ValueError:
        return None


# Текущий коэффициент плотности; на мобильных он станет известен
# только после создания окна (см. fit_design_to_screen).
UI_SCALE = None


def fit_design_to_screen():
    """Подгоняет плотность под экран устройства — вызывается из App.build()."""
    forced = _env_scale()
    if forced:
        Metrics.density = forced
        return forced
    try:
        from kivy.core.window import Window
        w = int(getattr(Window, "system_size", (Window.width, Window.height))[0])
        h = int(getattr(Window, "system_size", (Window.width, Window.height))[1])
    except Exception:
        w, h = _desktop_size()
    scale = _fit_scale(w, h)
    Metrics.density = scale
    return scale


def apply_window_size():
    """Ставит размер окна сразу после его создания.

    Некоторые провайдеры окна (в том числе SDL2 на Windows) не берут
    размер из Config и открывают окно 800x600 — тогда макет 450x920 не
    влезает и низ экрана обрезается. Поэтому размер задаётся явно,
    до первого кадра: лишнего «мусорного» ресайза не будет.
    """
    global UI_SCALE
    if IS_MOBILE:
        return fit_design_to_screen()

    scale = _env_scale() or _fit_scale(*_desktop_size())
    UI_SCALE = scale
    Metrics.density = scale
    try:
        from kivy.core.window import Window
        Window.size = (int(round(DESIGN_W * scale)),
                       int(round(DESIGN_H * scale)))
    except Exception:
        pass
    return scale


def init_window():
    """Настройка окна. Вызывается до создания Window (на ПК)."""
    global UI_SCALE
    if IS_MOBILE:
        # На телефоне размер окна задаёт система — переопределять нельзя.
        forced = _env_scale()
        UI_SCALE = forced
        if forced:
            Metrics.density = forced
        Config.set("input", "mouse", "mouse,disable_multitouch")
        return UI_SCALE

    scale = _env_scale() or _fit_scale(*_desktop_size())
    UI_SCALE = scale
    Metrics.density = scale
    Config.set("graphics", "width", str(int(round(DESIGN_W * scale))))
    Config.set("graphics", "height", str(int(round(DESIGN_H * scale))))
    Config.set("graphics", "resizable", "1")
    Config.set("input", "mouse", "mouse,disable_multitouch")
    return scale
