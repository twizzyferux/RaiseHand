"""Проба: сообщения идут через системное окно iOS, а на ПК не ломаются.

Зачем
-----
Сообщение пользователю показывается из одного места - ui/dialogs.py,
и его вызывают все экраны (код приглашения, остаток заряда, ошибки).
Подмена на системное окно iOS трогает всё сразу, поэтому надо
убедиться в двух вещах:

1. На ПК ничего не сломалось: системного окна тут быть не может,
   должно показаться окно Kivy, как раньше.
2. Показ окна возвращает признак успеха. Если системное окно не
   показалось, вызывающий код обязан откатиться на окно Kivy -
   иначе пользователь просто ничего не увидит.

Чего проба НЕ проверяет
-----------------------
Как выглядит окно на телефоне. Настоящий UIKit на ПК недоступен,
проверить можно только то, что приложение выбирает правильный путь.

Как читать
----------
Строка ИТОГ в _shots/alert.log.
"""

import os

BASE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(BASE, "_shots", "alert.log")


def main():
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    os.environ["RH_DB"] = os.path.join(BASE, "_shots", "probe.db")

    lines, problems = [], []

    from kivy.clock import Clock
    from kivy.core.window import Window
    from kivy.uix.popup import Popup

    import ui.ios_alert as ios_alert
    from ui import dialogs

    # На ПК системное окно недоступно - так и должно быть.
    got = ios_alert.available()
    lines.append("системное окно доступно на ПК: %s" % got)
    if got:
        problems.append("на ПК системное окно считается доступным")

    # Показ без UIKit обязан честно сказать "не показалось", а не
    # упасть и не показать окно Kivy сам по себе.
    try:
        shown = ios_alert.show("Проверка", "текст")
        lines.append("show() без UIKit вернул: %s" % shown)
        if shown:
            problems.append("show() сказал, что показал, хотя UIKit нет")
    except Exception as e:
        problems.append("show() упал без UIKit: %r" % e)

    # Самый важный пункт: сообщение всё равно должно быть видно.
    def check(_dt):
        popups = [w for w in Window.children if isinstance(w, Popup)]
        if not popups:
            problems.append("окно Kivy не открылось - сообщение пропало бы")
            finish()
            return
        popup = popups[0]
        title = getattr(popup, "title", "")
        has_label = any(getattr(c, "text", "") == "текст"
                        for c in popup.content.walk())
        lines.append("окно Kivy открыто, заголовок: %r, текст виден: %s"
                     % (title, has_label))
        if not has_label:
            problems.append("в окне нет текста сообщения")
        popup.dismiss()
        finish()

    def finish():
        lines.append("")
        lines.append("ИТОГ: %s" % ("сообщения работают" if not problems
                                 else "есть проблемы"))
        for p in problems:
            lines.append("  - %s" % p)
        with open(LOG, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        print("\n".join(lines))
        Clock.schedule_once(stop, 0.3)

    from main import MessengerApp
    app = MessengerApp()

    def stop():
        # Без этого проба не закончится: окно Kivy само не закрывает
        # цикл приложения.
        try:
            app.stop()
        except Exception:
            pass

    def go(_dt):
        Clock.schedule_once(check, 0.6)
        dialogs.show_message("Проверка", "текст")

    Clock.schedule_once(go, 2.0)
    app.run()


if __name__ == "__main__":
    main()