# -*- coding: utf-8 -*-
"""Выбор картинки системным способом, не проводником Kivy.

Снизу показывается меню как на iOS: галерея, камера, файлы.
Дальше открывается диалог самой системы (на Windows — обычное
окно «Открыть»). Проводник Kivy остаётся только если системный
диалог вызвать не удалось.
"""

import os
import sys
import tempfile

from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.modalview import ModalView

_BLUE = (0.0, 0.478, 1.0, 1.0)
_BLACK = (0.0, 0.0, 0.0, 1.0)
_SEP = (0.78, 0.78, 0.80, 1.0)


def choose_image(on_choice, title="Фото"):
    """Меню источника. on_choice(path) — когда файл выбран."""
    sheet = _SourceSheet(title, on_choice)
    sheet.open()


class _SourceSheet(ModalView):
    def __init__(self, title, on_choice, **kwargs):
        kwargs.setdefault("size_hint", (None, None))
        kwargs.setdefault("auto_dismiss", True)
        kwargs.setdefault("background", "")
        kwargs.setdefault("background_color", (0, 0, 0, 0))
        kwargs.setdefault("overlay_color", (0, 0, 0, 0.35))
        super().__init__(**kwargs)
        self.on_choice = on_choice
        self._build(title)
        from kivy.core.window import Window
        width = min(Window.width - dp(16), dp(400))
        self.size = (width, self._height)
        self.pos_hint = {"center_x": 0.5, "y": 0.012}

    def _build(self, title):
        rows = [
            (title, None, True),
            ("Выбрать из галереи", "gallery", False),
            ("Сделать фото", "camera", False),
            ("Выбрать из файлов", "files", False),
        ]
        group = self._group(rows)
        cancel = self._button("Отмена", bold=True, color=_BLUE)
        cancel.bind(on_release=lambda *_: self.dismiss())

        root = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(8))
        root.add_widget(group)
        root.add_widget(cancel)
        self.add_widget(root)
        self._height = dp(56) * 4 + dp(8) + dp(56) + dp(16)

    def _group(self, rows):
        box = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(56) * len(rows))
        with box.canvas.before:
            from kivy.graphics import Color, RoundedRectangle
            Color(1, 1, 1, 1)
            box._bg = RoundedRectangle(pos=box.pos, size=box.size, radius=[dp(14)])
        box.bind(pos=lambda w, v: setattr(w._bg, "pos", v),
                 size=lambda w, v: setattr(w._bg, "size", v))
        for index, (text, kind, header) in enumerate(rows):
            if index:
                line = Label(size_hint_y=None, height=dp(0.6), text="")
                with line.canvas.before:
                    from kivy.graphics import Color, Rectangle
                    Color(*_SEP)
                    line._r = Rectangle(pos=line.pos, size=line.size)
                line.bind(pos=lambda w, v: setattr(w._r, "pos", v),
                          size=lambda w, v: setattr(w._r, "size", v))
                # разделитель входит в высоту кнопки, отдельный виджет
                # раздувает меню — рисуем линию на самой кнопке ниже
            button = self._button(
                text,
                bold=header,
                color=(0.45, 0.45, 0.48, 1) if header else _BLUE,
            )
            if kind is not None:
                button.bind(on_release=lambda *_b, k=kind: self._pick(k))
            box.add_widget(button)
        return box

    def _button(self, text, bold, color):
        return Button(
            text=text,
            font_size=dp(17),
            bold=bold,
            color=color,
            background_normal="",
            background_color=(0, 0, 0, 0),
            size_hint_y=None,
            height=dp(56),
        )

    def _pick(self, kind):
        callback = self.on_choice
        self.dismiss()
        Clock.schedule_once(lambda *_: _open(kind, callback), 0.2)


def _open(kind, on_choice):
    if kind == "camera":
        if not _camera(on_choice):
            from ui.dialogs import show_message
            show_message(
                "Камера",
                "Камера на этом устройстве недоступна. "
                "Выберите готовое фото из галереи или файлов.",
            )
        return
    from kivy.utils import platform as kivy_platform
    if kivy_platform in ("android", "ios"):
        if not _mobile_file(on_choice):
            from ui.dialogs import show_message
            show_message("Фото", "Системный выбор фото открыть не удалось.")
        return
    initial = _pictures() if kind == "gallery" else os.path.expanduser("~")
    try:
        path = _system_file(initial, "Выберите изображение")
    except Exception:
        path = _tk_file(initial, "Выберите изображение")
    if path:
        on_choice(path)


def _pictures():
    home = os.path.expanduser("~")
    for name in ("Pictures", "Изображения", "pictures"):
        path = os.path.join(home, name)
        if os.path.isdir(path):
            return path
    return home


def _system_file(initial, title):
    """Диалог открытия файла самой ОС. None — отмена или нет диалога."""
    if sys.platform == "win32":
        return _windows_file(initial, title)
    if sys.platform == "darwin":
        return _mac_file()
    return _tk_file(initial, title)


def _windows_file(initial, title):
    import ctypes
    from ctypes import wintypes

    class OPENFILENAMEW(ctypes.Structure):
        _fields_ = [
            ("lStructSize", wintypes.DWORD),
            ("hwndOwner", wintypes.HWND),
            ("hInstance", wintypes.HINSTANCE),
            ("lpstrFilter", wintypes.LPCWSTR),
            ("lpstrCustomFilter", wintypes.LPWSTR),
            ("nMaxCustFilter", wintypes.DWORD),
            ("nFilterIndex", wintypes.DWORD),
            ("lpstrFile", wintypes.LPWSTR),
            ("nMaxFile", wintypes.DWORD),
            ("lpstrFileTitle", wintypes.LPWSTR),
            ("nMaxFileTitle", wintypes.DWORD),
            ("lpstrInitialDir", wintypes.LPCWSTR),
            ("lpstrTitle", wintypes.LPCWSTR),
            ("Flags", wintypes.DWORD),
            ("nFileOffset", wintypes.WORD),
            ("nFileExtension", wintypes.WORD),
            ("lpstrDefExt", wintypes.LPCWSTR),
            ("lCustData", wintypes.LPARAM),
            ("lpfnHook", ctypes.c_void_p),
            ("lpTemplateName", wintypes.LPCWSTR),
            ("pvReserved", ctypes.c_void_p),
            ("dwReserved", wintypes.DWORD),
            ("FlagsEx", wintypes.DWORD),
        ]

    buf = ctypes.create_unicode_buffer(4096)
    ofn = OPENFILENAMEW()
    ofn.lStructSize = ctypes.sizeof(OPENFILENAMEW)
    ofn.lpstrFilter = (
        "Изображения\0*.png;*.jpg;*.jpeg;*.webp;*.bmp;*.gif;*.heic\0"
        "Все файлы\0*.*\0\0"
    )
    ofn.lpstrFile = ctypes.cast(buf, wintypes.LPWSTR)
    ofn.nMaxFile = 4096
    ofn.lpstrInitialDir = initial
    ofn.lpstrTitle = title
    try:
        ofn.hwndOwner = ctypes.windll.user32.GetForegroundWindow()
    except Exception:
        pass
    # OFN_EXPLORER | OFN_FILEMUSTEXIST | OFN_PATHMUSTEXIST | OFN_NOCHANGEDIR
    ofn.Flags = 0x80000 | 0x1000 | 0x800 | 0x8
    if not ctypes.windll.comdlg32.GetOpenFileNameW(ctypes.byref(ofn)):
        return None
    return buf.value or None


def _mac_file():
    import subprocess
    script = 'POSIX path of (choose file of type {"public.image"})'
    try:
        out = subprocess.check_output(["osascript", "-e", script], text=True)
    except Exception:
        return None
    path = out.strip()
    return path or None


def _tk_file(initial, title):
    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception:
        return None
    root = tk.Tk()
    root.withdraw()
    try:
        root.wm_attributes("-topmost", 1)
    except Exception:
        pass
    path = filedialog.askopenfilename(
        initialdir=initial,
        title=title,
        filetypes=[("Изображения", "*.png *.jpg *.jpeg *.webp *.bmp *.gif")],
    )
    root.destroy()
    return path or None


def _mobile_file(on_choice):
    """На телефоне plyer открывает системный выбор. Путь приходит в колбэк."""
    try:
        from plyer import filechooser
    except Exception:
        return False

    def done(selection):
        if selection:
            on_choice(selection[0])

    try:
        filechooser.open_file(
            on_selection=done,
            filters=["*.png", "*.jpg", "*.jpeg", "*.webp", "*.heic"],
        )
    except Exception:
        return False
    return True


def _camera(on_choice):
    path = os.path.join(tempfile.gettempdir(), "raisehand_avatar.jpg")
    try:
        from plyer import camera
        camera.take_picture(filename=path, on_complete=lambda p: on_choice(p) if p else None)
        return True
    except Exception:
        return False
