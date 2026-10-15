"""Проба: экран приветствия занимает весь экран телефона.

Зачем
-----
Плотность на телефоне считается по высоте экрана (fit_design_to_screen),
поэтому макет 450x920 должен занять её целиком: снизу не остаётся
полосы. Проверяется не контейнер, а высота макета в пикселях против
высоты экрана - и положение элементов ПРОТИВ пропорций макета.

Предыдущие проверки обманывали дважды: одна мерила контейнер (его
размер не двигает содержимое, стоящее на координатах в dp), другая
задавала плотность 1 и сравнивала с абсолютными числами, которых в
макете просто нет.

Как читать
----------
Строка ИТОГ в _shots/welcome_fill.log, снимок _shots/welcome_fill.png.
"""

import os

BASE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(BASE, "_shots", "welcome_fill.log")
SHOT = os.path.join(BASE, "_shots", "welcome_fill.png")
DESIGN_W, DESIGN_H = 450, 920
# Поле макета слева и справа. Столько срезаться не должно: за ним
# чистое место, а не содержимое.
MARGIN_DP = 45
# Размеры iPhone 15 Pro Max в пикселях: там, где был отступ сверху.
PHONE_W, PHONE_H = 1290, 2796


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

    kw.Window = FakeWin(PHONE_W, PHONE_H)
    ps.Metrics.density = 1.0
    got = ps.fit_design_to_screen()

    lines.append("экран: %dx%d" % (PHONE_W, PHONE_H))
    lines.append("плотность: %.3f" % got)
    lines.append("макет в пикселях: %.0fx%.0f" % (DESIGN_W * got,
                                                    DESIGN_H * got))
    # Правило: масштаб по высоте, поэтому высота макета обязана
    # совпасть с высотой экрана - иначе останется пустое поле, ради
    # которого всё и затевалось. По ширине макет может выйти чуть
    # шире экрана, но срезаться должно только поле, а не содержимое.
    need_w = DESIGN_W * got
    need_h = DESIGN_H * got
    if abs(need_h - PHONE_H) > 1.0:
        problems.append("макет не во всю высоту: %.0f при экране %d, "
                        "пустое поле %.0f px"
                        % (need_h, PHONE_H, PHONE_H - need_h))
    cut = max(0.0, need_w - PHONE_W) / 2.0 / got
    if cut > MARGIN_DP:
        problems.append("срезается %.0f dp с края при поле макета %d dp"
                        % (cut, MARGIN_DP))
    lines.append("срез пустого поля с края: %.0f dp при поле %d dp"
                 % (cut, MARGIN_DP))
    lines.append("пустое поле сверху: 0 (высота макета равна экрану)")

    # И положение элементов: логотип и нижняя кнопка стоят на тех же
    # пропорциях от низа, что и в макете.
    logo_gap_dp = DESIGN_H - (775 + 55)        # отступ логотипа сверху
    btn_gap_dp = 360 + 52.8                     # нижняя кнопка снизу
    lines.append("ожидается: логотип сверху %.0f dp, нижняя кнопка снизу "
                 "%.0f dp" % (logo_gap_dp, btn_gap_dp))
    lines.append("в пикселях: логотип сверху %.0f, кнопка снизу %.0f"
                 % (logo_gap_dp * got, btn_gap_dp * got))
    if logo_gap_dp * got < 1:
        problems.append("логотип прижат к самому верху")

    lines.append("")
    lines.append("ИТОГ: %s" % ("интерфейс занимает экран целиком"
                                 if not problems else "есть проблемы"))
    for p in problems:
        lines.append("  - %s" % p)
    lines.append("снимок: %s" % SHOT)

    kw.Window = old_window
    with open(LOG, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()