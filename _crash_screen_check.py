"""Проба: показывает ли экран ошибки текст или остаётся чёрным.

Зачем
-----
Если ошибка при старте случилась, приложение показывает окно с текстом.
Но окно устроено так: подпись внутри прокрутки, её высота задаётся
绑定 по размеру текста. Если эта связка не сработает, текст не рисуется,
прокрутка останется пустой, а фон окна чёрным. Ровно это и наблюдалось
на телефоне: чёрный экран вместо причины ошибки.

Как читать
----------
Строка ИТОГ в _shots/crash_screen.log.
"""

import os

from kivy.clock import Clock
from kivy.core.window import Window

BASE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(BASE, "_shots", "crash_screen.log")


def main():
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    os.environ["RH_DB"] = os.path.join(BASE, "_shots", "probe.db")
    import main as app_main

    lines = []
    problems = []

    detail = ("Traceback (most recent call last):\n"
              "  File \"YourApp/main.pyc\", line 1, in <module>\n"
              "  File \"YourApp/core/config.pyc\", line 12, in <module>\n"
              "OSError: [Errno 30] Read-only file system\n")
    root = app_main._crash_screen(detail)

    # Окно нужно показать по-настоящему: ширина подписи назначается
    # родителем, и только после этого пересчитывается текст. Проверка
    # «просто создали виджет» ничего не значит — так текст не виден.
    Window.add_widget(root)
    from kivy.base import EventLoop

    event = EventLoop.idle()

    from kivy.uix.label import Label
    from kivy.uix.scrollview import ScrollView

    lines.append("=== что вернул _crash_screen ===")
    lines.append("тип: %s" % type(root).__name__)
    lines.append("размер окна: %sx%s" % (root.width, root.height))
    del event, ScrollView

    label = None
    for child in root.walk():
        if isinstance(child, Label):
            label = child
            break
    if label is None:
        problems.append("внутри окна ошибки нет подписи")
    else:
        lines.append("подпись: ширина %s, высота %s" % (label.width, label.height))
        lines.append("text_size: %s" % (getattr(label, "text_size", None),))
        lines.append("texture_size: %s" % (label.texture_size,))
        lines.append("текст: %r" % label.text[:40])

        if label.width <= 1 or label.height <= 1:
            problems.append("подпись нулевого размера: текст не виден")

        # Текстура появляется только после расчёта; сравниваем с
        # ожидаемым числом строк.
        label.texture_update()
        tex = label.texture
        lines.append("текстура: %s" % str(tex.size if tex else None))
        if tex is None or tex.width <= 1 or tex.height <= 1:
            problems.append("текстура пустая: текст не отрисовался")

        expected_lines = detail.count("\n") + 1
        if tex and tex.height < expected_lines * 5:
            problems.append("текстура ниже, чем строк в тексте "
                            "(%s против %s)" % (tex.height, expected_lines))

    lines.append("")
    lines.append("ИТОГ: %s" % ("окно показывает текст" if not problems
                               else "окно НЕ показывает текст"))
    for p in problems:
        lines.append("  - %s" % p)

    with open(LOG, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    Window.remove_widget(root)


if __name__ == "__main__":
    main()