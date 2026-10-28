"""Всплывающие окна: сообщение и выбор файла.

Сообщение на iOS показывается штатным окном iOS (ui/ios_alert.py), а
не серым окном Kivy. На ПК остаётся окно Kivy: айфонского вида там
быть не может.
"""

import os

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup

from ui import ios_alert


def show_message(title: str, message: str) -> None:
    """Сообщение пользователю.

    Окно айфонского вида (ui/ios_alert.py). Старое окно Kivy осталось
    запасным путём: если новое почему-то не построилось, сообщение
    всё равно должно быть видно.
    """
    try:
        if ios_alert.show(title, message):
            return
    except Exception as e:
        # Молча проглоченная ошибка - это то, из-за чего окно на
        # телефоне выглядело "ничего не поменялось", а причину не
        # найти было негде. Причина пишется в журнал запуска.
        try:
            import main
            main._record("ОКНО НЕ ПОСТРОИЛОСЬ", "%s: %s"
                         % (type(e).__name__, e))
        except Exception:
            pass

    box = BoxLayout(orientation="vertical", padding=12, spacing=10)
    label = Label(text=message, halign="center", valign="middle")
    label.bind(size=lambda inst, val: setattr(inst, "text_size", val))
    button = Button(text="Понятно", size_hint_y=None, height=44)

    box.add_widget(label)
    box.add_widget(button)

    popup = Popup(title=title, content=box, size_hint=(0.85, 0.45))
    button.bind(on_release=popup.dismiss)
    popup.open()


def choose_file(on_choice, title: str = "Выберите файл", start_path: str = None) -> None:
    """Системный выбор картинки: галерея, камера или файлы.

    start_path оставлен в сигнатуре, чтобы старые вызовы не сломались.
    Сам путь задаёт система (галерея — «Изображения», файлы — домашняя).
    """
    del start_path
    from ui.image_pick import choose_image
    choose_image(on_choice, title=title)
