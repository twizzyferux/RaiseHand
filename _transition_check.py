"""Проба: переход между экранами гаснет и приближает.

Зачем
-----
Пользователь попросил заменить сдвиг экранов на «затухание с
приближением»: старый экран гаснет и отдаляется, новый приходит
крупнее и проявляется на месте. Проверяется, что так и есть:

  - в середине перехода уходящий экран темнее единицы и меньше
    исходного размера;
  - входящий темнее единицы (ещё не проявился) и крупнее исходного;
  - после перехода оба сброшены: прозрачность 1, масштаб 1.

Именно последний пункт чаще всего забывают: масштаб, оставленный на
уходящем экране, всплывает при следующем заходе и выглядит как
«съехавший» экран.

Как читать
----------
Строка ИТОГ в _shots/transition.log.
"""

import os

BASE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(BASE, "_shots", "transition.log")


def main():
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    os.environ["RH_DB"] = os.path.join(BASE, "_shots", "probe.db")

    from kivy.clock import Clock
    from kivy.metrics import Metrics

    from main import MessengerApp

    lines, problems = [], []
    app = MessengerApp()
    out_screen = None
    in_screen = None
    sampled = {"done": False}

    def read_zoom(screen):
        """Масштаб экрана: 1.0, если масштаба нет или он сброшен."""
        if screen is None or getattr(screen, "_zoom_origin", None) is None:
            return 1.0
        return float(screen._zoom_scale.x)

    def start(_dt):
        app.manager.current = "welcome"
        Clock.schedule_once(run, 1.0)

    def run(_dt):
        nonlocal out_screen, in_screen
        out_screen = app.manager.get_screen("welcome")
        # Переход начинается сразу после подстановки экрана.
        app.manager.current = "login"
        in_screen = app.manager.get_screen("login")
        Clock.schedule_once(sample, 0.17)

    def sample(_dt):
        o_op = out_screen.opacity
        o_zoom = read_zoom(out_screen)
        i_op = in_screen.opacity
        i_zoom = read_zoom(in_screen)

        lines.append("середина перехода:")
        lines.append("  уходящий: прозрачность %.2f, масштаб %.3f" % (o_op, o_zoom))
        lines.append("  входящий: прозрачность %.2f, масштаб %.3f" % (i_op, i_zoom))

        if o_op >= 1.0:
            problems.append("уходящий не гаснет: прозрачность %.2f" % o_op)
        if o_zoom >= 1.0:
            problems.append("уходящий не отдаляется: масштаб %.3f" % o_zoom)
        if i_op >= 1.0:
            problems.append("входящий проявился раньше времени: %.2f" % i_op)
        if i_zoom <= 1.0:
            problems.append("входящий не крупнее: масштаб %.3f" % i_zoom)

        Clock.schedule_once(finish, 0.6)

    def finish(_dt):
        sampled["done"] = True
        o_op = out_screen.opacity
        o_zoom = read_zoom(out_screen)
        i_op = in_screen.opacity
        i_zoom = read_zoom(in_screen)

        lines.append("после перехода:")
        lines.append("  уходящий: прозрачность %.2f, масштаб %.3f" % (o_op, o_zoom))
        lines.append("  входящий: прозрачность %.2f, масштаб %.3f" % (i_op, i_zoom))

        if abs(o_op - 1.0) > 0.01:
            problems.append("уходящий не восстановлен: прозрачность %.2f" % o_op)
        if abs(o_zoom - 1.0) > 0.01:
            problems.append("у уходящего остался масштаб %.3f" % o_zoom)
        if abs(i_op - 1.0) > 0.01:
            problems.append("входящий не восстановлен: прозрачность %.2f" % i_op)
        if abs(i_zoom - 1.0) > 0.01:
            problems.append("у входящего остался масштаб %.3f" % i_zoom)

        # Второе: появление содержимого лесенкой.
        # Поля должны проявляться по очереди, а кнопка-галочка — нет:
        # пользователь попросил убрать лесенку с кнопок.
        login = app.manager.get_screen("login")
        login._intro_played = False
        # Появление запускается напрямую: on_enter срабатывает только при
        # переходе между экранами, а здесь нужен именно показ лесенки.
        login._play_intro()
        Clock.schedule_once(check_intro, 0.25)

    def check_intro(_dt):
        login = app.manager.get_screen("login")
        # Поля: должны анимироваться.
        for name in ("login_field", "password_field"):
            widget = login.ids.get(name)
            if widget is None:
                problems.append("%s: нет такого элемента" % name)
                continue
            lines.append("%-16s прозрачность %.2f" % (name, widget.opacity))
            if widget.opacity >= 1.0:
                problems.append("%s проявился сразу, без лесенки" % name)
        # Кнопка: НЕ должна анимироваться.
        toggle = login.ids.get("remember_toggle")
        if toggle is None:
            problems.append("remember_toggle: нет такого элемента")
        else:
            lines.append("%-16s прозрачность %.2f" % ("remember_toggle", toggle.opacity))
            if toggle.opacity < 1.0:
                problems.append("кнопка анимируется, а не должна")

        # Третье: на главном экране кнопка «+» тоже не анимируется.
        home = app.manager.get_screen("home")
        home._intro_played = False
        home._play_intro()
        Clock.schedule_once(check_home, 0.25)

    def check_home(_dt):
        home = app.manager.get_screen("home")
        fab = home.ids.get("fab")
        if fab is None:
            problems.append("fab: нет такого элемента")
        else:
            lines.append("%-16s прозрачность %.2f" % ("fab", fab.opacity))
            if fab.opacity < 1.0:
                problems.append("кнопка «+» анимируется, а не должна")

        lines.append("")
        lines.append("ИТОГ: %s" % ("переход гаснет и приближает, "
                                 "лесенка только у полей"
                                 if not problems else "есть проблемы"))
        for p in problems:
            lines.append("  - %s" % p)
        with open(LOG, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        print("\n".join(lines))
        Clock.schedule_once(lambda *_: app.stop(), 0.3)

    Clock.schedule_once(start, 2.0)
    app.run()


if __name__ == "__main__":
    main()