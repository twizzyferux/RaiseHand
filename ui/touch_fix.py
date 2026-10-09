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
import weakref

from kivy.input.motionevent import MotionEvent
from kivy.uix.screenmanager import ScreenManager as _ScreenManager

_installed = False
_patched_manager = False


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


def install():
    """Починить захват и переходы. Повторный вызов ничего не делает."""
    global _installed
    if _installed:
        return
    MotionEvent.grab = _grab
    MotionEvent.ungrab = _ungrab
    _installed = True
    patch_screen_manager()
