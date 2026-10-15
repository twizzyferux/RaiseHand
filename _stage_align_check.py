"""Проба: сцена стоит по верху, пустого места сверху нет.

Зачем
-----
Макет 450x920, а экран iPhone 15 Pro Max выше макета. Раньше сцена
центрировалась, и лишняя высота делилась поровну: сверва оставалось
пустое место под логотипом, тем заметнее, что там же вырез камеры.
Теперь сцена прижата к верху, а сверху ровно отступ системы.

Проба открывает окно размером с телефон и проверяет, что между верхом
окна и верхом сцены ничего нет, а снизу свободное место есть - там
декор, и пустоты не видно.

Как читать
----------
Строка ИТОГ в _shots/stage_align.log, снимок _shots/stage_align.png.
"""

import os

BASE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(BASE, "_shots", "stage_align.log")
SHOT = os.path.join(BASE, "_shots", "stage_align.png")
DESIGN_W, DESIGN_H = 450, 920


def main():
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    os.environ["RH_DB"] = os.path.join(BASE, "_shots", "probe.db")

    from kivy.config import Config
    # Окно шире и заметно выше макета - как на телефоне.
    # Плотность 1 задаётся через RH_UI_SCALE: так размеры макета
    # равны пикселям, и окно можно сделать выше макета - как на телефоне.
    os.environ["RH_UI_SCALE"] = "1"
    Config.set("graphics", "width", str(DESIGN_W))
    Config.set("graphics", "height", str(1050))
    Config.set("graphics", "resizable", "0")

    from kivy.clock import Clock
    from kivy.core.window import Window

    from main import MessengerApp

    lines, problems = [], []
    app = MessengerApp()
    state = {}

    def go(_dt):
        # Плотность задаём прямо: иначе она считается от окна,
        # открытого прогонами раньше, и сцена выходит не того размера.
        Window.size = (DESIGN_W, 1050)
        app.manager.current = "welcome"
        Clock.schedule_once(measure, 1.0)

    def measure(_dt):
        read(_dt)

    def read(_dt):
        scr = app.manager.get_screen("welcome")
        stage = None
        for child in scr.walk():
            if child.__class__.__name__ == "PhoneStage":
                stage = child
                break
        if stage is None:
            problems.append("сцена на экране не найдена")
            finish()
            return
        top_gap = Window.height - stage.top
        bottom_gap = stage.y
        state.update(top=top_gap, bottom=bottom_gap,
                     win=Window.height, stage=stage.height)
        Window.screenshot(name=SHOT)
        finish()

    def finish():
        if state:
            lines.append("окно по высоте: %s" % state["win"])
            lines.append("сцена по высоте: %s" % state["stage"])
            lines.append("сверху пустого места: %s" % round(state["top"], 1))
            lines.append("снизу свободно: %s" % round(state["bottom"], 1))
            # Сверху допустим только отступ системы, он на ПК нулевой.
            if state["top"] > 1:
                problems.append("сверху пустое место: %s px"
                                % round(state["top"], 1))
            if state["bottom"] < 1:
                problems.append("снизу нет свободного места: %s"
                                % round(state["bottom"], 1))
            lines.append("снимок: %s" % SHOT)
        lines.append("")
        lines.append("ИТОГ: %s" % ("сцена прижата к верху" if not problems
                                 else "есть проблемы"))
        for p in problems:
            lines.append("  - %s" % p)
        with open(LOG, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        print("\n".join(lines))
        app.stop()

    Clock.schedule_once(go, 2.0)
    app.run()


if __name__ == "__main__":
    main()