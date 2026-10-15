"""Проба: гасится ли второе событие от одного касания.

Зачем
-----
На iOS одно касание приходит дважды: событием пальца и событием мыши,
которые SDL2 шлёт одновременно. Из-за этого любая кнопка срабатывает
два раза. Проба проверяет наш фильтр: событие мыши рядом с касанием
должно отбрасываться, а одиночное касание (и на ПК) - проходить.

Как читать
----------
Строка ИТОГ в _shots/touch_dup.log.
"""

import os

from kivy.base import EventLoop

BASE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(BASE, "_shots", "touch_dup.log")


class _Touch:
    """Имитация касания. Имя класса решает, кем оно считается."""

    __slots__ = ("x", "y")

    def __init__(self, x, y, mouse):
        self.x, self.y = x, y
        if mouse:
            self.__class__ = MouseMotionEvent


class MouseMotionEvent(_Touch):
    pass


class SDL2MotionEvent(_Touch):
    pass


def main():
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    lines, problems = [], []

    import ui.touch_fix as fix
    from kivy.core.window import Window, WindowBase

    # Счётчик ставим ДО нашей заплатки: patch_duplicate_mouse захватывает
    # текущий on_touch_down, значит счётчик окажется под ним и мы увидим,
    # сколько событий действительно дошло до приложения.
    calls = {"n": 0}
    real_down = WindowBase.on_touch_down

    def counting_down(self, touch):
        calls["n"] += 1
        return None

    WindowBase.on_touch_down = counting_down
    fix.patch_duplicate_mouse()
    WindowBase.on_touch_down = real_down

    # 1) Касание пальцем, затем мышиный дубль рядом -> должен остаться 1.
    calls["n"] = 0
    Window.on_touch_down(None, SDL2MotionEvent(100, 200, False))
    Window.on_touch_down(None, MouseMotionEvent(101, 201, True))
    first = calls["n"]
    lines.append("палец + мышиный дубль: дошло %d (ожидается 1)" % first)
    if first != 1:
        problems.append("дубль не отброшен: дошло %d событий" % first)

    # 2) Только касание -> должно пройти.
    calls["n"] = 0
    Window.on_touch_down(None, SDL2MotionEvent(300, 400, False))
    second = calls["n"]
    lines.append("только палец: дошло %d (ожидается 1)" % second)
    if second != 1:
        problems.append("обычное касание потеряно: %d" % second)

    # 3) Мышь сама по себе, без пальца рядом -> должна пройти.
    calls["n"] = 0
    Window.on_touch_down(None, MouseMotionEvent(700, 800, True))
    third = calls["n"]
    lines.append("только мышь: дошло %d (ожидается 1)" % third)
    if third != 1:
        problems.append("обычная мышь потеряна: %d" % third)

    lines.append("")
    lines.append("ИТОГ: %s" % ("фильтр работает" if not problems
                               else "фильтр не работает"))
    for p in problems:
        lines.append("  - %s" % p)

    with open(LOG, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()