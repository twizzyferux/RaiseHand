# -*- coding: utf-8 -*-
"""Починка захвата касания в этой сборке Kivy.

ЧТО СЛОМАНО
-----------
Kivy держит захват касания в двух полях: grab_list (кто захватил) и
grab_current (кто владеет СЕЙЧАС). ButtonBehavior отпускает кнопку только
при `touch.grab_current is self`:

    def on_touch_up(self, touch):
        if touch.grab_current is not self:
            return super().on_touch_up(touch)   # <- уходим, ничего не делая

В этой сборке MotionEvent.grab() кладёт виджет только в grab_list и НЕ
заполняет grab_current — того самого поля, на котором держится вся
логика кнопок. grab_current остаётся None навсегда, поэтому ни одна
кнопка не доходила до on_release: нажатие визуально срабатывало, но
ничего не происходило.

ПОЧЕМУ ЧИНИМ ФРЕЙМВОРК, А НЕ КНОПКИ
-------------------------------------
От grab_current зависят не только кнопки, но и прокрутка, поля ввода и
перетаскивание. Обходной путь «своя обработка отпускания в каждой
кнопке» пришлось бы повторять везде и всё равно оставил бы сломанной
половину поведения. Здесь восстанавливается сам контракт Kivy: grab()
запоминает владельца, ungrab() — отпускает.

Запуск:  .venv312\\Scripts\\python.exe _grab_check.py   (проверка)

ВТОРАЯ ПОЛОМКА — касания во время перехода между экранами: описаны ниже,
в разделе про ScreenManager.
"""
import sys
import time
import traceback
import weakref

from kivy.input.motionevent import MotionEvent
from kivy.uix.screenmanager import ScreenManager as _ScreenManager

_installed = False
_patched_manager = False
_patched_mouse = False


def _owner(value):
    """Из виджета или связанного метода достаём сам виджет."""
    return getattr(value, '__self__', value)


def _grab(self, class_instance, exclusive=False):
    """Запомнить, кто взял касание."""
    widget = _owner(class_instance)
    if not any(ref() is widget for ref in self.grab_list):
        self.grab_list.append(weakref.ref(widget))
    self.grab_state = True
    self.grab_current = widget
    return True


def _ungrab(self, class_instance):
    """Отпустить касание."""
    widget = _owner(class_instance)
    self.grab_list = [ref for ref in self.grab_list if ref() is not widget]
    if self.grab_current is widget:
        self.grab_current = None
    self.grab_state = bool(self.grab_list)
    return True


# --------------------------------------------------------------------------- #
#  Касания во время перехода между экранами
# --------------------------------------------------------------------------- #
# В Kivy ScreenManager на время перехода (у нас 0.24 с) касания не
# обрабатывает вовсе:
#
#     def on_touch_down(self, touch):
#         if self.transition.is_active:
#             return False      # <- вернули False, дальше никто не смотрит
#
# Из-за этого первое нажатие на нижнюю панель сразу после появления
# экрана пропадало: экран уже виден, а панель ещё «не принимает».
# Пользователь видел, что «Поиск» не срабатывает, пока не зайдёт в
# настройки и не вернётся — то есть пока не пройдёт переход.
#
# Теперь во время перехода касание уходит на входящий экран: он уже
# нарисован, и кнопки на нём настоящие. Пересылаем и движение с
# отпусканием, иначе кнопка осталась бы зажатой — захват ей всё равно
# достаётся, просто раньше времени.

def _forward(name):
    original = getattr(_ScreenManager, name)

    def handler(self, touch):
        # screen_in живёт у перехода, а не у менеджера. Если переход уже
        # почти кончился и перехода «не существует», берём текущий экран.
        transition = self.transition
        screen = getattr(transition, 'screen_in', None) or self.current_screen
        if transition.is_active and screen is not None:
            return getattr(screen, name)(touch)
        return original(self, touch)

    handler.__name__ = name
    return handler


def patch_screen_manager():
    """ScreenManager не должен гасить касания во время перехода."""
    global _patched_manager
    if _patched_manager:
        return
    for name in ('on_touch_down', 'on_touch_move', 'on_touch_up'):
        setattr(_ScreenManager, name, _forward(name))
    _patched_manager = True


def patch_duplicate_mouse():
    """Гасить второе событие от одного касания на iOS.

    На iOS одно касание приходит дважды: SDL2 шлёт его и как событие
    пальца, и как событие мыши. Оба доходят до приложения, и любая
    кнопка срабатывает два раза.

    Штатный ключ Kivy disable_on_activity не помогает: он смотрит,
    есть ли уже другое касание, но события обрабатываются по очереди и
    мышиное приходит раньше, чем касание попало в список.

    Провайдера мыши целиком убрать нельзя: Kivy создаёт его при
    инициализации, и на iOS других провайдеров касаний для мышиного
    списка нет - приложение просто перестало бы получать ввод.

    Поэтому дубликат отсекается здесь: событие мыши, начатое в том же
    месте почти сразу после касания пальцем, не пропускается дальше.
    На ПК ничего не меняется - там провайдер мыши единственный.
    """
    global _patched_mouse
    if _patched_mouse:
        return
    from kivy.core.window import Window

    state = {"_last": None}

    def _near(a, b):
        # Допуск в несколько пикселей и в доли секунды: два события
        # одного касания приходят почти в ту же точку и почти в ту же
        # секунду.
        return (a is not None and b is not None
                and abs(a[0] - b[0]) <= 8 and abs(a[1] - b[1]) <= 8
                and (a[2] - b[2]) <= 0.2)

    original_down = Window.on_touch_down

    def on_touch_down(touch):
        # Именно один аргумент: Kivy зовёт метод на экземпляре окна,
        # window.on_touch_down(touch). Подмена с двумя аргументами
        # падала бы с TypeError на первом же касании, то есть при любом
        # нажатии на кнопку.
        try:
            name = touch.__class__.__name__
            now = time.time()
            if name.endswith("MouseMotionEvent"):
                if _near((touch.x, touch.y, now), state["_last"]):
                    return True      # дубль, дальше не пускаем
            else:
                state["_last"] = (touch.x, touch.y, now)
        except Exception:
            # Фильтр не имеет права ронять приложение: при любой
            # неожиданности просто пропускаем событие как есть.
            sys.stderr.write("[raisehand] фильтр дубля: %s\n"
                             % traceback.format_exc())
        return original_down(touch)

    Window.on_touch_down = on_touch_down
    _patched_mouse = True


def install():
    """Починить захват и переходы. Повторный вызов ничего не делает."""
    global _installed
    if _installed:
        return
    MotionEvent.grab = _grab
    MotionEvent.ungrab = _ungrab
    _installed = True
    patch_screen_manager()
    from core.platform_setup import IS_IOS
    if IS_IOS:
        patch_duplicate_mouse()
