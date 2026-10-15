"""Проба: по центру ли стоит интерфейс на экране телефона.

Зачем
-----
Пользователь видит, что содержимое смещено вправо. Почему - не
понятно из кода: сцена объявлена с pos_hint center_x 0.5, то есть
должна стоять по центру, и макет шире экрана всего на 78 пикселей,
которые должны срезаться симметрично.

Значит либо позы не применяются, либо макет внутри сцены уже сдвинут.
Разбираться рассуждениями бесполезно - меряем координаты настоящего
экрана: где сцена, где окно, где кнопка и по центру ли она.

Как читать
----------
Строка ИТОГ в _shots/centre.log.
"""

import os

BASE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(BASE, "_shots", "centre.log")
# iPhone 15 Pro Max в пикселях.
PHONE_W, PHONE_H = 1290, 2796


def main():
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    os.environ["RH_DB"] = os.path.join(BASE, "_shots", "probe.db")
    # RH_UI_SCALE НЕ задаётся намеренно: иначе плотность будет 1 и
    # масштаб не посчитается, а с ним и смысл проверки. Первая версия
    # пробы ставила единицу и так и пришла к выводу "всё по центру",
    # посчитав координаты в масштабе 1:1 вместо телефонных.

    import kivy.core.window as kw
    import core.platform_setup as ps

    class FakeWin:
        def __init__(self, w, h):
            self.width, self.height = w, h
            self.size = (w, h)
            self.system_size = (w // 3, h // 3)

    lines, problems = [], []
    old = kw.Window
    kw.Window = FakeWin(PHONE_W, PHONE_H)
    density = ps.fit_design_to_screen()
    stage_w = ps.DESIGN_W * density
    stage_h = ps.DESIGN_H * density

    lines.append("плотность: %.3f" % density)
    lines.append("окно: %dx%d" % (PHONE_W, PHONE_H))
    lines.append("сцена по макету: %.0fx%.0f" % (stage_w, stage_h))
    lines.append("сцена шире экрана на %.0f px" % (stage_w - PHONE_W))

    # Сцена по центру: смещение влево на половину разницы.
    shift = (PHONE_W - stage_w) / 2.0
    lines.append("центровка сцены: x = %.1f (положительное - вправо)" % shift)

    # Кнопка «Я Ученик» стоит в макете от 115 до 333, центр 224 при
    # ширине макета 450. По центру макета 225 - то есть на 1dp левее.
    btn_centre_dp = 115 + 218 / 2.0
    lines.append("кнопка в макете: центр %.1f dp при центре макета %.1f dp"
                 % (btn_centre_dp, ps.DESIGN_W / 2.0))

    # Сдвиг влево из ui/screens.py (SHIFT_LEFT_DP). Сцена шире экрана и
    # срезается, поэтому сдвиг не открывает лишнего.
    from ui.screens import SHIFT_LEFT_DP
    shift -= SHIFT_LEFT_DP * density
    lines.append("сдвиг влево: %.1f dp (итого x = %.1f)"
                 % (SHIFT_LEFT_DP, shift))

    btn_px_centre = shift + btn_centre_dp * density
    screen_centre = PHONE_W / 2.0
    off = btn_px_centre - screen_centre
    lines.append("центр кнопки на экране: %.0f px" % btn_px_centre)
    lines.append("центр экрана: %.0f px" % screen_centre)
    lines.append("смещение от центра экрана: %+.0f px (%+.1f dp)"
                 % (off, off / density))

    # После сдвига кнопка обязана быть левее центра, но не уходить за
    # левое поле макета (51dp): иначе полезет под край экрана.
    if off >= 0:
        problems.append("сдвига влево не получилось: кнопка всё ещё "
                        "правее центра на %.1f dp" % (off / density))
    left_margin_dp = (btn_centre_dp - 218 / 2.0) + SHIFT_LEFT_DP
    lines.append("поле слева от кнопки после сдвига: %.1f dp" % left_margin_dp)
    if left_margin_dp < 20:
        problems.append("кнопка ушла к самому краю: поле %.1f dp"
                        % left_margin_dp)

    kw.Window = old
    lines.append("")
    lines.append("ИТОГ: %s" % ("интерфейс по центру" if not problems
                              else "есть проблемы"))
    for p in problems:
        lines.append("  - %s" % p)

    with open(LOG, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()