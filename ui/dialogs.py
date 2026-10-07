"""Всплывающие окна: сообщение и выбор файла. Оформления нет — стандартный вид Kivy."""

import os

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.filechooser import FileChooserIconView
from kivy.uix.label import Label
from kivy.uix.popup import Popup


def show_message(title: str, message: str) -> None:
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
    """Открывает проводник. on_choice(path) вызывается после выбора файла."""
    start_path = start_path or os.path.expanduser("~")
    chooser = FileChooserIconView(path=start_path,
                                  filters=["*.png", "*.jpg", "*.jpeg", "*.webp"])

    box = BoxLayout(orientation="vertical", padding=10, spacing=8)
    box.add_widget(chooser)

    buttons = BoxLayout(size_hint_y=None, height=44, spacing=8)
    cancel = Button(text="Отмена")
    select = Button(text="Выбрать")
    buttons.add_widget(cancel)
    buttons.add_widget(select)
    box.add_widget(buttons)

    popup = Popup(title=title, content=box, size_hint=(0.95, 0.9))

    def _select(*_):
        if chooser.selection:
            popup.dismiss()
            on_choice(chooser.selection[0])

    select.bind(on_release=_select)
    cancel.bind(on_release=popup.dismiss)
    popup.open()
