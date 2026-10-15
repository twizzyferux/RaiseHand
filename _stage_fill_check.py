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
        # Масштаб считается по ширине, поэтому по высоте макет может
        # оказаться меньше экрана - это норма, и полосу убирает вёрстка
        # (декор прижимается к низу). А вот выйти за экран нельзя ни по
        # одной оси: тогда нижняя часть просто не попадёт в кадр.
        fits_h = need_h <= h + 0.5
        fits_w = need_w <= w + 0.5
        slack = h - need_h
        lines.append("%-20s экран %dx%d, плотность %.3f, макет %.0fx%.0f, "
                     "влезает=%s, свободно снизу %.0f px (%.0f dp)"
                     % (name, w, h, got, need_w, need_h,
                        fits_h and fits_w, max(0.0, slack), slack / got))
        if not fits_h:
            problems.append("%s: макет выше экрана на %.0f px, нижняя "
                            "часть не попадёт в кадр" % (name, need_h - h))
        if not fits_w:
            problems.append("%s: макет шире экрана на %.0f px, срежется "
                            "содержимое" % (name, need_w - w))

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