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

# Отступы, которые просит не занимать система (вырез сверху, жесты
# снизу). Наполняет init_window на телефоне.
UI_SAFE = (0, 0)


def fit_design_to_screen():
    """Подгоняет плотность под экран устройства — вызывается из App.build().

    Масштаб строго ПО ШИРИНЕ: density = px_w / 450.

    Сцена по ширине = экран → горизонтального сдвига и обрезки по
    бокам быть не может. Scale по высоте делал сцену шире экрана;
    на iOS центрирование с отрицательным x нестабильно — поля и
    кнопки уезжали вправо (см. скрины регистрации).

    По высоте на вытянутых iPhone остаётся ~55 pt. Их убирает
    прижатие сцены к верху в BaseScreen._pin_stage: пустота уходит
    вниз, под декоративные пузыри / кнопку «Далее».

    На коротких экранах (макет выше окна) берём by_height, чтобы
    низ не обрезался.

    Переопределить вручную: переменная окружения RH_UI_SCALE.
    """
    forced = _env_scale()
    if forced:
        Metrics.density = forced
        return forced
    try:
        from kivy.core.window import Window
        w, h = int(Window.width), int(Window.height)
    except Exception:
        return Metrics.density
    if w <= 0 or h <= 0:
        return Metrics.density

    by_width = w / float(DESIGN_W)
    by_height = h / float(DESIGN_H)
    # По ширине, если макет при этом влезает по высоте; иначе по высоте.
    scale = by_width if by_width * DESIGN_H <= h else by_height
    scale = max(0.5, min(scale, 5.0))
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
    """Записать размеры окна и плотность.

    Нужно для проверки на глаз нельзя: по этому сразу видно, во сколько
    раз макет меньше или больше экрана и в каких единицах Kivy считает
    окно - в точках или в пикселях.

    Пишется в ДВА места, и это не дублирование ради дублирования.
    В stderr строка уходит в системный журнал iOS, откуда её не
    достать: приложение запускает��я через Sideloadly, а не из
    Xcode, и консоли там нет. Журнал запуска, который забирается
    с телефона из Documents, писался только из main.py, и сведений
    о масштабе в нём не было вообще - пришлось гадать, отработала
    ли подгонка. Теперь обе строки попадают и туда.
    """
    try:
        from kivy.core.window import Window
        # Подпись раздельно указывает точки и пиксели, потому что это
        # разные числа и на них легко спутаться. iPhone 15 Pro Max
        # сообщает 430x932 ТОЧКИ, а плотность считается из 1290x2796
        # ПИКСЕЛЕЙ. Раньше в строке писалось "430x932 (пиксели)" -
        # это было неверно, и по выводу о масштабе пришлось бы
        # гадать.
        points = getattr(Window, "system_size", None)
        pixels = Window.size
        line = ("окно %sx%s точек, %sx%s пикселей, плотность %s, "
                "макет %sx%s, коэффициент %s"
                % (points[0] if points else "?",
                   points[1] if points else "?",
                   pixels[0], pixels[1], Metrics.density,
                   DESIGN_W, DESIGN_H, scale))
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
    except Exception:
        pass


def safe_insets():
    """Отступы сверху и снизу, которые система просит не занимать.

    На iPhone с вырезом (Dynamic Island, «чёлка») сверху нельзя: там
    камера, а снизу полоска жестов. Обычное приложение смещает
    содержимое, иначе надписи наезжают на вырез, а кнопка уходит под
    жест и не нажимается.

    Kivy таких отступов не знает, поэтому берём их у самой системы
    через UIKit. keyWindow на современных iOS часто пустой (сцены),
    поэтому пробуем и windows из connectedScenes.
    """
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
                top = int(value(insets.top))
                bottom = int(value(insets.bottom))
                if top or bottom:
                    return (top, bottom)
            except Exception:
                pass
            return None

        app = autoclass("UIApplication").sharedApplication()
        # 1) классический keyWindow
        try:
            got = from_window(app.keyWindow)
            if got is not None:
                return got
        except Exception:
            pass
        # 2) любое окно приложения
        try:
            windows = app.windows
            count = int(windows.count()) if windows is not None else 0
            for i in range(count):
                got = from_window(windows.objectAtIndex_(i))
                if got is not None:
                    return got
        except Exception:
            pass
        # 3) окна из connectedScenes (iOS 13+)
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


def _kill_mouse_emulation() -> None:
    """Убрать с телефона события мыши, которые дублируют касание.

    На iOS одно касание приходит дважды: SDL2 шлёт его и как событие
    пальца, и как событие мыши. Оба доходят до приложения, и любая
    кнопка срабатывает два раза.

    Ключ disable_on_activity - штатный для этого случая: он снимает
    событие мыши, если по этому же месту уже пришло касание от другого
    провайдера. Но он не сработал: события обрабатываются в порядке
    очерреди, и мышиное приходит раньше, чем касание успевает появиться
    в списке, поэтому проверка его не находит.

    Значит провайдера мыши на iOS убираем целиком. Касания от этого не
    страдают: на iOS их шлёт отдельный провайдер (события пальца SDL2),
    а не мышиный. На ПК провайдер остаётся - там он нужен по-настоящему.
    """
    if not IS_IOS:
        return
    try:
        import kivy
        kivy.kivy_options.get("input", {}).pop("mouse", None)
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
    global UI_SCALE, UI_SAFE
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
        UI_SCALE = fit_design_to_screen()
        _report_scale(UI_SCALE)
        _kill_mouse_emulation()
        top, bottom = safe_insets()
        UI_SAFE = (top, bottom)
        sys.stderr.write("[raisehand] безопасные отступы: сверху %s, снизу %s\n"
                         % (top, bottom))
        sys.stderr.flush()
        try:
            import main
            main._record("ОТСТУПЫ", "сверху %s, снизу %s" % (top, bottom))
        except Exception:
            pass
        return UI_SCALE

    scale = _env_scale() or _fit_scale(*_desktop_size())
    UI_SCALE = scale
    Metrics.density = scale
    Config.set("graphics", "width", str(int(round(DESIGN_W * scale))))
    Config.set("graphics", "height", str(int(round(DESIGN_H * scale))))
    Config.set("graphics", "resizable", "1")
    Config.set("input", "mouse", "mouse,disable_multitouch")
    return scale