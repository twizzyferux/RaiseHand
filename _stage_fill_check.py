"""Проба: макет занимает экран телефона по всей высоте.

Зачем
-----
Экран iPhone 15 Pro Max вытянут по вертикали относительно макета
(450x920). При подгонке "поместиться по обеим осям" упирается ширина,
высота макета перестаёт совпадать с высотой экрана, снизу остаётся
дыра и экран выглядит недозаполненным.

Проверяется та функция, которая принимает решение о масштабе, - на
настоящем размере экрана iPhone 15 Pro Max и ещё на нескольких.
Проверять размер контейнера бесполезно: содержимое стоит на
координатах в dp, и размер контейнера не двигает ничего.

Как читать
----------
Строка ИТОГ в _shots/stage_fill.log.
"""

import os

BASE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(BASE, "_shots", "stage_fill.log")
DESIGN_W, DESIGN_H = 450, 920
# Поле макета слева и справа. Столько не должно срезаться: за ним
# чистое место, а не содержимое.
MARGIN_DP = 45

# Экраны телефонов в пикселях: как есть, так и есть на железе.
SCREENS = [
    ("iPhone 15 Pro Max", 1290, 2796),
    ("iPhone SE", 750, 1334),
    ("iPhone 8", 750, 1334),
    ("Android 1080x1920", 1080, 1920),
    ("iPad Air", 1640, 2360),
]


def main():
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    os.environ["RH_DB"] = os.path.join(BASE, "_shots", "probe.db")

    import kivy.core.window as kw
    import core.platform_setup as ps

    class FakeWin:
        def __init__(self, w, h):
            self.width, self.height = w, h
            self.size = (w, h)

    lines, problems = [], []
    old_window = kw.Window

    for name, w, h in SCREENS:
        kw.Window = FakeWin(w, h)
        ps.Metrics.density = 1.0
        got = ps.fit_design_to_screen()
        need_h = DESIGN_H * got
        need_w = DESIGN_W * got
        # Высота макета обязана совпасть с высотой экрана - это и есть
        # "интерфейс занимает весь экран".
        fills_h = abs(need_h - h) < 1.0
        # По ширине вылет терпим, пока он меньше поля макета (51dp с
        # каждой стороны): срезается пустое поле, а не содержимое.
        over = need_w - w
        cut_dp = max(0.0, over) / 2.0 / got
        lines.append("%-20s экран %dx%d, плотность %.3f, макет %.0fx%.0f, "
                     "заполняет высоту=%s, срез поля %.0f dp"
                     % (name, w, h, got, need_w, need_h, fills_h, cut_dp))
        if not fills_h:
            problems.append("%s: макет не во всю высоту (%.0f из %d)"
                            % (name, need_h, h))
        if cut_dp > MARGIN_DP:
            problems.append("%s: срезается %.0f dp с края при поле макета "
                            "%d dp" % (name, cut_dp, MARGIN_DP))

    kw.Window = old_window
    lines.append("")
    lines.append("ИТОГ: %s" % ("макет занимает экран по высоте"
                                 if not problems else "есть проблемы"))
    for p in problems:
        lines.append("  - %s" % p)

    with open(LOG, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()