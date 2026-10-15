"""Проба: поля по краям и равное центрирование на всех экранах.

Зачем
-----
Пустые поля по бокам - то, что пользователь назвал "не по центру".
Причина в том, что в макете поле 51dp, а видимая часть макета на
телефоне уже, чем нарисованный: по 12.75dp срезается с каждой
стороны, и из этих 51dp остаётся около 38dp пустоты.

Экраны правятся по одному, и без общей картины каждый раз пришлось
бы гадать, где ещё осталось пустое место. Здесь меряются все экраны
сразу: сколько пустого места слева и справа и насколько блок уехал от
центра.

Что считается за блок
---------------------
Берётся самый широкий элемент на экране - обычно это текст, кнопка
или поле ввода. Именно он задаёт видимую ширину содержимого.

Как читать
----------
Строка ИТОГ в _shots/margin.log. Список экранов - выше.
"""

import os

BASE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(BASE, "_shots", "margin.log")
DESIGN_W = 450
# Экран iPhone 15 Pro Max. Плотность 2796/920 = 3.039.
PHONE_H = 2796
SCREEN_W_PX = 1290
DENSITY = PHONE_H / 920.0
# Сколько макета срезается с каждой стороны, в dp.
CUT_DP = (DESIGN_W - SCREEN_W_PX / DENSITY) / 2.0

# Поле, ниже которого экран считается нормальным. Больше - значит
# осталась пустота, которую видит пользователь.
MAX_MARGIN_DP = 40.0
# Допуск на центр: на столько блок может быть смещён и это незаметно.
MAX_OFF_DP = 6.0

# Классы, которые не задают ширину видимого содержимого.
SKIP_CLASSES = {
    "BoxLayout", "FloatLayout", "RelativeLayout", "GridLayout",
    "StackLayout", "Box", "ScrollView", "Canvas", "Rectangle", "Color",
    "RoundedRectangle", "Ellipse", "Line", "PushMatrix", "PopMatrix",
    "Transform", "Callback", "LineRectangle", "ScreenManager",
    "Screen", "ModalView", "Popup",
}


def main():
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    os.environ["RH_DB"] = os.path.join(BASE, "_shots", "probe.db")

    from kivy.clock import Clock
    from kivy.metrics import Metrics as metrics

    from main import SCREENS, MessengerApp

    lines, problems = [], []
    lines.append("плотность: %.3f, срезается с каждой стороны: %.1f dp"
                 % (metrics.density, CUT_DP))

    app = MessengerApp()

    def measure(_dt):
        from kivy.core.window import Window
        window_w = Window.width
        rows = []
        for name, _cls in SCREENS:
            screen = app.manager.get_screen(name)
            lefts, rights, mains = [], [], []
            # Левый край сцены - начало отсчёта для всего содержимого.
            stage_x = None
            for w in screen.walk():
                if w.__class__.__name__ == "PhoneStage":
                    try:
                        stage_x, _ = w.to_window(w.x, w.y)
                    except Exception:
                        stage_x = w.x
                    break
            if stage_x is None:
                rows.append((name, "нет сцены", 0, 0, 0))
                continue
            for w in screen.walk():
                cls = w.__class__.__name__
                # Раскладки и инструкции рисования ширину видимого
                # содержимого не задают: контейнеры растянуты во всю
                # ширину, и "самый широкий элемент" всегда оказывался
                # ими. Первая версия пробы из-за этого показывала поле
                # в 368dp на экране входа - несуществующее.
                if cls in SKIP_CLASSES or cls.endswith("Screen") or cls == "PhoneStage":
                    continue
                width = getattr(w, "width", 0) or 0
                if width < window_w * 0.05:
                    continue
                # АБСОЛЮТНЫЕ координаты. У вложенного элемента x
                # отсчитывается от родителя, а не от экрана: содержимое
                # лежит в блоке с полями 16dp, и без перевода проба
                # брала координату блока и мерила несуществующее поле
                # в 368dp.
                try:
                    ax, _ay = w.to_window(w.x, w.y)
                except Exception:
                    ax = w.x
                left = (ax - stage_x) / metrics.density
                right = left + width / metrics.density
                lefts.append(left)
                rights.append(right)
                # Крупный блок - по нему и судим о центрировании.
                if width / metrics.density > DESIGN_W * 0.25:
                    mains.append((cls, left, right))

            if not lefts:
                rows.append((name, None, 0, 0, 0))
                continue

            vis_right = DESIGN_W - CUT_DP
            # Поля - по границам всего содержимого, а не по одному
            # элементу: иначе узкий заголовок объявляется "узким
            # содержимым" при растянутых на всю ширину полях.
            vis_l = min(lefts) - CUT_DP
            vis_r = vis_right - max(rights)

            # Центрирование - по самому широкому из крупных блоков.
            main = max(mains, key=lambda t: t[2] - t[1]) if mains else None
            if main is None:
                rows.append((name, "крупных нет", max(0.0, vis_l),
                             max(0.0, vis_r), 0.0))
                continue
            off = (main[1] + main[2]) / 2.0 - DESIGN_W / 2.0
            rows.append((name, main[0], max(0.0, vis_l),
                         max(0.0, vis_r), off))

        lines.append("")
        lines.append("%-18s %-18s %10s %10s %9s"
                     % ("экран", "широкий блок", "поле слева",
                        "поле справа", "центр-225"))
        for name, cls, l, r, off in rows:
            if cls is None:
                lines.append("%-18s %-18s %10s" % (name, "не найден", "-"))
                problems.append("%s: не нашлось ни одного блока" % name)
                continue
            lines.append("%-18s %-18s %10.0f %10.0f %9.1f"
                         % (name, cls, l, r, off))
            if max(l, r) > MAX_MARGIN_DP:
                problems.append("%s: поле до %.0f dp (норма %d)"
                                % (name, max(l, r), MAX_MARGIN_DP))
            if abs(off) > MAX_OFF_DP:
                problems.append("%s: смещён от центра на %.1f dp"
                                % (name, off))

        lines.append("")
        lines.append("ИТОГ: %s" % ("поля нормальные везде"
                                 if not problems else "есть проблемы"))
        for p in problems:
            lines.append("  - %s" % p)
        with open(LOG, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        print("\n".join(lines))
        Clock.schedule_once(lambda *_: app.stop(), 0.3)

    Clock.schedule_once(measure, 3.0)
    app.run()


if __name__ == "__main__":
    main()