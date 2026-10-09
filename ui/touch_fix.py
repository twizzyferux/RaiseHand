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
"""
import weakref

from kivy.input.motionevent import MotionEvent

_installed = False


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


def install():
    """Починить захват. Повторный вызов ничего не делает."""
    global _installed
    if _installed:
        return
    MotionEvent.grab = _grab
    MotionEvent.ungrab = _ungrab
    _installed = True
