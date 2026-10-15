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
import sys

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
    """Подгоняет плотность под экран устройства — вызывается из App.build().

    На ПК окно измеряется в точках, и макет надо вписать в него своим
    коэффициентом.

    На телефоне так делать нельзя. Там Kivy измеряет окно в пикселях и
    сам выставляет плотность по экрану: dp() уже переводит точки в
    пиксели. Если подменить её своим значением, посчитанным как будто
    окно в точках, макет 450 точек нарисуется как 450 пикселей на
    экране шириной около 1290 — то есть втрое меньше, чем нужно, и
    прижмётся к левому нижнему краю. Поэтому на телефоне своё
    значение не ставится, берётся то, которое вычислил Kivy.

    Переопределить всё же можно: переменная окружения RH_UI_SCALE.
    """
    forced = _env_scale()
    if forced:
        Metrics.density = forced
        return forced
    if IS_MOBILE:
        return Metrics.density
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
    """Ставит размер окна сразу после его создания и центрирует его.

    Некоторые провайдеры окна (в том числе SDL2 на Windows) не берут
    размер из Config и открывают окно 800x600 — тогда макет 450x920 не
    влезает и низ экрана обрезается. Поэтому размер задаётся явно,
    до первого кадра: лишнего «мусорного» ресайза не будет.

    Окно центрируется на экране, но с задержкой на кадр: система
    применяет новый размер не мгновенно, и сразу после присваивания
    координаты ещё старые.
    """
    global UI_SCALE
    if IS_MOBILE:
        return fit_design_to_screen()

    scale = _env_scale() or _fit_scale(*_desktop_size())
    UI_SCALE = scale
    Metrics.density = scale
    try:
        from kivy.clock import Clock
        from kivy.core.window import Window
        Window.size = (int(round(DESIGN_W * scale)),
                       int(round(DESIGN_H * scale)))
        # центр — когда размер уже применён системой
        Clock.schedule_once(lambda dt: _center_window(Window), 0)
        Clock.schedule_once(lambda dt: _center_window(Window), 0.15)
    except Exception:
        pass
    return scale


def _center_window(window) -> None:
    """Поставить окно в середину экрана.

    У Kivy на настольных компьютерах нет готового метода (Window.x/y и
    Window.center есть только на телефонах), поэтому пробуем известные
    пути по очереди: сначала штатный pos провайдера окна, потом —
    напрямую через Win32.
    """
    area_w, area_h = _desktop_size()
    try:
        size = window.system_size
    except Exception:
        size = window.size
    w, h = int(size[0]), int(size[1])
    x = max(0, (area_w - w) // 2)
    y = max(0, (area_h - h) // 2)

    # 1) штатные методы провайдера (SDL2)
    for holder, setter in ((getattr(window, "_win", None), "set_window_pos"),
                           (window, "_set_window_pos")):
        if holder is None or not hasattr(holder, setter):
            continue
        try:
            getattr(holder, setter)(x, y)
            return
        except Exception:
            continue

    # 2) Windows: двигаем окно системным вызовом
    try:
        import ctypes
        import win32con
        info = window._win.get_window_info()
        hwnd = info.window if hasattr(info, "window") else info
        ctypes.windll.user32.SetWindowPos(
            hwnd, win32con.HWND_TOP, x, y, 0, 0,
            win32con.SWP_NOSIZE | win32con.SWP_NOZORDER)
    except Exception:
        pass


def _report_scale(scale) -> None:
    """Напечатать размеры окна и плотность.

    Нужно для проверки на глаз нельзя: по этому сразу видно, во сколько
    раз макет меньше или больше экрана и в каких единицах Kivy считает
    окно - в точках или в пикселях.
    """
    try:
        from kivy.core.window import Window
        size = getattr(Window, "system_size", None) or Window.size
        sys.stderr.write(
            "[raisehand] окно %sx%s, плотность %s, максет %sx%s, "
            "коэффициент %s\n"
            % (size[0], size[1], Metrics.density, DESIGN_W, DESIGN_H, scale))
        sys.stderr.flush()
    except Exception:
        pass


def _max_fps() -> int:
    """Сколько кадров в секунду разрешаем приложению.

    По умолчанию Kivy держит 60, и даже на экране с частотой выше
    приложение рисует реже, чем может. Здесь ставим 120 — этого хватает
    и для 120-герцевых экранов, и для 144 (лишние кадры просто не
    случатся: ограничивает вертикальная синхронизация).

    Переопределить: переменная окружения RH_MAX_FPS.
        set RH_MAX_FPS=60 && python main.py
    """
    raw = os.environ.get("RH_MAX_FPS", "").strip()
    if raw:
        try:
            return max(30, min(240, int(float(raw))))
        except ValueError:
            pass
    return 120


def init_window():
    """Настройка окна. Вызывается до создания Window (на ПК)."""
    global UI_SCALE
    max_fps = _max_fps()
    Config.set("graphics", "maxfps", str(max_fps))
    # Часы берут лимит из конфига ОДИН РАЗ — при создании экземпляра
    # Clock, то есть ещё до того, как мы сюда дошли. Поэтому одной
    # записи в Config мало: Clock продолжал рисовать в 60 кадров, пока
    # в конфиге уже стояло 120. Обновляем и его тоже.
    try:
        from kivy.clock import Clock
        Clock._max_fps = float(max_fps)
    except Exception:
        pass
    if IS_MOBILE:
        # На телефоне размер окна задаёт система — переопределять нельзя.
        forced = _env_scale()
        UI_SCALE = fit_design_to_screen()
        _report_scale(UI_SCALE)
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
