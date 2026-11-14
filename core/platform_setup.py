# -*- coding: utf-8 -*-
"""Окно, масштаб и safe-area.

Новая модель (2026-11):

  1. Макет живёт в фиксированной СЕТКЕ 450×920 (design units).
  2. LayoutEngine один раз считает scale и прямоугольник сцены
     внутри окна (с учётом safe-area).
  3. Metrics.density = scale → все dp() в .kv совпадают с сеткой.
  4. PhoneStage ставится в готовый прямоугольник явными x/y/w/h —
     без pos_hint и без отрицательного x «наугад».

Режимы (RH_LAYOUT_MODE или config):

  fill_width  — ширина = экран, высота по пропорции, сцена к верху
                (safe top). Нет обрезки по бокам, нет сдвига вправо.
                На вытянутых iPhone снизу остаётся поле. **По умолчанию.**

  fit         — contain: весь макет виден, поля по длинной стороне.

  fill_height — высота = экран; по бокам возможна симметричная обрезка
                ~13 pt (поля контента 25–45 dp, кнопки на экране).

  fill        — cover: экран закрыт целиком, лишнее обрезается.

Переопределить масштаб числом: RH_UI_SCALE=2.87
"""
from __future__ import annotations

import ctypes
import os
import sys
from dataclasses import dataclass

from kivy.config import Config
from kivy.metrics import Metrics
from kivy.utils import platform as kivy_platform

DESIGN_W, DESIGN_H = 450, 920

IS_MOBILE = kivy_platform in ("android", "ios")
IS_ANDROID = kivy_platform == "android"
IS_IOS = kivy_platform == "ios"
IS_DESKTOP = not IS_MOBILE

# Публичное состояние — читают screens / логи.
UI_SCALE = None
UI_SAFE = (0, 0)          # (top, bottom) в пикселях окна
UI_LAYOUT = None          # актуальный LayoutResult
LAYOUT_MODE = "fill_width"


# ---------------------------------------------------------------------------
#  Движок раскладки
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class LayoutResult:
    """Куда поставить PhoneStage в координатах родителя (пиксели окна)."""
    scale: float
    x: float
    y: float
    width: float
    height: float
    mode: str
    window_w: int
    window_h: int
    safe_top: int
    safe_bottom: int


def _env_scale():
    raw = os.environ.get("RH_UI_SCALE", "").strip()
    if not raw:
        return None
    try:
        return max(0.5, min(8.0, float(raw)))
    except ValueError:
        return None


def _env_mode():
    raw = (os.environ.get("RH_LAYOUT_MODE") or "").strip().lower()
    if raw in ("fill_width", "fill_height", "fit", "fill", "contain", "cover"):
        if raw == "contain":
            return "fit"
        if raw == "cover":
            return "fill"
        return raw
    return None


def _read_mode_from_settings():
    try:
        from core.config import SETTINGS
        mode = str(SETTINGS.get("layout_mode", "")).strip().lower()
        if mode in ("fill_width", "fill_height", "fit", "fill"):
            return mode
    except Exception:
        pass
    return None


def resolve_mode() -> str:
    return _env_mode() or _read_mode_from_settings() or LAYOUT_MODE


def compute_layout(window_w: int, window_h: int,
                   safe_top: int = 0, safe_bottom: int = 0,
                   mode: str | None = None,
                   forced_scale: float | None = None) -> LayoutResult:
    """Считает scale и прямоугольник сцены.

    Координаты y — как в Kivy: 0 внизу.
    Сцена никогда не уходит в отрицательный x, если width <= window_w;
    если шире (fill_height/fill) — центрируется явно.
    """
    mode = mode or resolve_mode()
    safe_top = max(0, int(safe_top or 0))
    safe_bottom = max(0, int(safe_bottom or 0))
    avail_x = 0.0
    avail_y = float(safe_bottom)
    avail_w = float(max(1, window_w))
    avail_h = float(max(1, window_h - safe_top - safe_bottom))

    sx = avail_w / float(DESIGN_W)
    sy = avail_h / float(DESIGN_H)

    if forced_scale is not None:
        scale = max(0.5, min(8.0, float(forced_scale)))
    elif mode == "fill_width":
        # Ширина = avail; если по высоте не влезает — уменьшаем (как fit).
        scale = sx if sx * DESIGN_H <= avail_h else min(sx, sy)
    elif mode == "fill_height":
        scale = sy if sy * DESIGN_W <= avail_w * 1.15 else min(sx, sy)
        # 1.15: лёгкая обрезка по бокам допустима; сильную не делаем.
    elif mode == "fill":
        scale = max(sx, sy)
    else:  # fit
        scale = min(sx, sy)

    scale = max(0.5, min(8.0, scale))
    width = DESIGN_W * scale
    height = DESIGN_H * scale

    # Горизонталь: всегда центр доступной области.
    x = avail_x + (avail_w - width) * 0.5

    # Вертикаль зависит от режима.
    if mode == "fill_width":
        # К верху safe-area (под статус-бар / Dynamic Island не залезаем,
        # если safe_top известен; иначе к верху окна).
        y = avail_y + avail_h - height
        if y < avail_y:
            y = avail_y + (avail_h - height) * 0.5
    elif mode in ("fill_height", "fill"):
        y = avail_y + (avail_h - height) * 0.5
    else:  # fit
        y = avail_y + (avail_h - height) * 0.5

    return LayoutResult(
        scale=scale, x=x, y=y, width=width, height=height,
        mode=mode, window_w=int(window_w), window_h=int(window_h),
        safe_top=safe_top, safe_bottom=safe_bottom,
    )


def apply_layout_to_widget(stage, parent, layout: LayoutResult | None = None) -> LayoutResult:
    """Ставит PhoneStage в parent по LayoutResult.

    Явные x/y/size, pos_hint сбрасывается. Так iOS не «забывает»
    центр, когда сцена шире родителя.
    """
    if layout is None:
        layout = UI_LAYOUT
    if layout is None:
        return layout
    try:
        stage.pos_hint = {}
        stage.size_hint = (None, None)
        # size через dp уже заложен в Metrics.density=scale, но
        # фиксируем пиксели напрямую — одна точка правды с LayoutResult.
        stage.width = layout.width
        stage.height = layout.height
        stage.x = parent.x + layout.x
        stage.y = parent.y + layout.y
    except Exception:
        pass
    return layout


# ---------------------------------------------------------------------------
#  Размеры рабочего стола / safe-area
# ---------------------------------------------------------------------------

def _desktop_size():
    if not IS_DESKTOP:
        return DESIGN_W, DESIGN_H
    try:
        user32 = ctypes.windll.user32
        user32.SetProcessDPIAware()

        class RECT(ctypes.Structure):
            _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                        ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

        rect = RECT()
        if user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0):
            w = int(rect.right - rect.left)
            h = int(rect.bottom - rect.top)
            if w > 200 and h > 200:
                return w, h
        return int(user32.GetSystemMetrics(0)), int(user32.GetSystemMetrics(1))
    except Exception:
        try:
            from kivy.core.window import Window
            return int(Window.width), int(Window.height)
        except Exception:
            return 1920, 1080


def safe_insets():
    """Safe-area top/bottom в пикселях окна Kivy (не в points UIKit)."""
    if not IS_IOS:
        return (0, 0)
    try:
        from pyobjus import autoclass

        def value(part):
            got = getattr(part, "value", part)
            try:
                return float(got)
            except (TypeError, ValueError):
                return 0.0

        def from_window(window):
            if window is None:
                return None
            try:
                insets = window.safeAreaInsets()
                # UIKit points → умножаем на nativeScale окна.
                scale = 1.0
                try:
                    scale = float(window.screen.nativeScale)
                except Exception:
                    try:
                        scale = float(window.contentScaleFactor)
                    except Exception:
                        scale = 3.0
                top = int(value(insets.top) * scale)
                bottom = int(value(insets.bottom) * scale)
                if top or bottom:
                    return (top, bottom)
            except Exception:
                pass
            return None

        app = autoclass("UIApplication").sharedApplication()
        try:
            got = from_window(app.keyWindow)
            if got is not None:
                return got
        except Exception:
            pass
        try:
            windows = app.windows
            count = int(windows.count()) if windows is not None else 0
            for i in range(count):
                got = from_window(windows.objectAtIndex_(i))
                if got is not None:
                    return got
        except Exception:
            pass
        try:
            scenes = app.connectedScenes
            if scenes is not None:
                for scene in scenes.allObjects():
                    try:
                        for window in scene.windows:
                            got = from_window(window)
                            if got is not None:
                                return got
                    except Exception:
                        continue
        except Exception:
            pass
        return (0, 0)
    except Exception:
        return (0, 0)


# ---------------------------------------------------------------------------
#  Публичный API запуска
# ---------------------------------------------------------------------------

def fit_design_to_screen():
    """Пересчитать scale + UI_LAYOUT по текущему Window."""
    global UI_SCALE, UI_LAYOUT, UI_SAFE
    forced = _env_scale()
    try:
        from kivy.core.window import Window
        w, h = int(Window.width), int(Window.height)
    except Exception:
        return Metrics.density
    if w <= 0 or h <= 0:
        return Metrics.density

    top, bottom = UI_SAFE if UI_SAFE != (0, 0) else safe_insets()
    UI_SAFE = (top, bottom)
    layout = compute_layout(w, h, top, bottom, forced_scale=forced)
    UI_LAYOUT = layout
    UI_SCALE = layout.scale
    Metrics.density = layout.scale
    return layout.scale


def apply_window_size():
    """После создания окна: scale на мобиле, размер+центр на ПК."""
    global UI_SCALE, UI_LAYOUT
    if IS_MOBILE:
        scale = fit_design_to_screen()
        _report_scale()
        return scale

    scale = _env_scale()
    if scale is None:
        dw, dh = _desktop_size()
        scale = min(dw / float(DESIGN_W), dh / float(DESIGN_H), 5.0)
        scale = max(0.5, scale)
    UI_SCALE = scale
    Metrics.density = scale
    layout = compute_layout(int(DESIGN_W * scale), int(DESIGN_H * scale),
                            mode="fit", forced_scale=scale)
    UI_LAYOUT = layout
    try:
        from kivy.clock import Clock
        from kivy.core.window import Window
        Window.size = (int(round(DESIGN_W * scale)),
                       int(round(DESIGN_H * scale)))
        Clock.schedule_once(lambda dt: _center_window(Window), 0)
        Clock.schedule_once(lambda dt: _center_window(Window), 0.15)
    except Exception:
        pass
    return scale


def _center_window(window) -> None:
    area_w, area_h = _desktop_size()
    try:
        size = window.system_size
    except Exception:
        size = window.size
    w, h = int(size[0]), int(size[1])
    x = max(0, (area_w - w) // 2)
    y = max(0, (area_h - h) // 2)
    for holder, setter in ((getattr(window, "_win", None), "set_window_pos"),
                           (window, "_set_window_pos")):
        if holder is None or not hasattr(holder, setter):
            continue
        try:
            getattr(holder, setter)(x, y)
            return
        except Exception:
            continue
    try:
        import win32con
        info = window._win.get_window_info()
        hwnd = info.window if hasattr(info, "window") else info
        ctypes.windll.user32.SetWindowPos(
            hwnd, win32con.HWND_TOP, x, y, 0, 0,
            win32con.SWP_NOSIZE | win32con.SWP_NOZORDER)
    except Exception:
        pass


def _report_scale() -> None:
    try:
        from kivy.core.window import Window
        points = getattr(Window, "system_size", None)
        pixels = Window.size
        layout = UI_LAYOUT
        mode = layout.mode if layout else resolve_mode()
        line = ("окно %sx%s точек, %sx%s пикселей, плотность %s, "
                "макет %sx%s, режим %s, коэффициент %s"
                % (points[0] if points else "?",
                   points[1] if points else "?",
                   pixels[0], pixels[1], Metrics.density,
                   DESIGN_W, DESIGN_H, mode,
                   layout.scale if layout else Metrics.density))
    except Exception:
        return
    try:
        sys.stderr.write("[raisehand] %s\n" % line)
        sys.stderr.flush()
    except Exception:
        pass
    try:
        import main
        main._record("МАСШТАБ", line)
        if UI_SAFE:
            main._record("ОТСТУПЫ", "сверху %s, снизу %s" % UI_SAFE)
    except Exception:
        pass


def _kill_mouse_emulation() -> None:
    if not IS_IOS:
        return
    try:
        import kivy
        kivy.kivy_options.get("input", {}).pop("mouse", None)
    except Exception:
        pass


def _max_fps() -> int:
    raw = os.environ.get("RH_MAX_FPS", "").strip()
    if raw:
        try:
            return max(30, min(240, int(float(raw))))
        except ValueError:
            pass
    return 120


def init_window():
    """До создания Window (Config) и первичная настройка на мобиле."""
    global UI_SCALE, UI_SAFE, UI_LAYOUT, LAYOUT_MODE
    LAYOUT_MODE = resolve_mode()
    max_fps = _max_fps()
    Config.set("graphics", "maxfps", str(max_fps))
    try:
        from kivy.clock import Clock
        Clock._max_fps = float(max_fps)
    except Exception:
        pass

    if IS_MOBILE:
        UI_SCALE = fit_design_to_screen()
        _report_scale()
        _kill_mouse_emulation()
        top, bottom = safe_insets()
        UI_SAFE = (top, bottom)
        # Пересчёт с реальными insets.
        UI_SCALE = fit_design_to_screen()
        _report_scale()
        return UI_SCALE

    scale = _env_scale()
    if scale is None:
        dw, dh = _desktop_size()
        scale = min(dw / float(DESIGN_W), dh / float(DESIGN_H), 5.0)
        scale = max(0.5, scale)
    UI_SCALE = scale
    Metrics.density = scale
    Config.set("graphics", "width", str(int(round(DESIGN_W * scale))))
    Config.set("graphics", "height", str(int(round(DESIGN_H * scale))))
    Config.set("graphics", "resizable", "1")
    Config.set("input", "mouse", "mouse,disable_multitouch")
    return scale
