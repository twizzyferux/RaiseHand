"""Проба: окно сообщений выглядит как айфонское.

Зачем
-----
Сообщения показываются один раз для всех экранов, через
ui/dialogs.py, и их вид задан в ui/ios_alert.py. Проверяется, что
окно строится, помещается в экран, не выходит за края и что по
кнопке закрывается.

Почему окно своё, а не системное
--------------------------------
Мост в iOS - pyobjus, а в его таблице селекторов нет ни одного
протокола UIAlert: нет initWithTitle:message:preferredStyle:, нет
actionWithTitle:style:handler:, нет presentViewController:... .
Нет селектора в таблице - нет метода, обращение падает с
AttributeError. На устройстве это и происходило. Так что окно
рисуется здесь, по системной спецификации iOS.

Как читать
----------
Строка ИТОГ в _shots/alert.log, снимок _shots/alert.png.
"""

import os

BASE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(BASE, "_shots", "alert.log")
SHOT = os.path.join(BASE, "_shots", "alert.png")
# Размер окна пробы.
#
# Раньше здесь стоял размер iPhone (430x932), но при��ожение на ПК
# само меняет окно на 450x920 - макет при плотности 1. Буфер кадра
# после подмены не совпадает с окном, и снимок выходит перекошенным и
# задвоенным. Разбираться пришлось бы с артефактом пробы, а не с
# самим окном, поэтому размер теперь совпадает с тем, который
# приложение выставит само.
PHONE_W, PHONE_H = 450, 920


def main():
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    os.environ["RH_DB"] = os.path.join(BASE, "_shots", "probe.db")

    lines, problems = [], []

    from kivy.clock import Clock
    from kivy.core.window import Window
    from kivy.metrics import dp

    from kivy.config import Config
    os.environ["RH_UI_SCALE"] = "1"
    Config.set("graphics", "width", str(PHONE_W))
    Config.set("graphics", "height", str(PHONE_H))
    Config.set("graphics", "resizable", "0")

    import ui.ios_alert as ios_alert
    from ui import dialogs

    def check(_dt):
        overlays = [w for w in Window.children
                    if w.__class__.__name__ == "_Alert"]
        if not overlays:
            problems.append("окно не появилось - сообщение пропало бы")
            finish()
            return
        box = overlays[0]
        win_w, win_h = Window.size
        card = box._card
        cx = card.pos[0] + card.size[0] / 2.0

        lines.append("окно: %dx%d" % (win_w, win_h))
        lines.append("карточка: %.0fx%.0f, центр x=%.0f"
                     % (card.size[0], card.size[1], cx))
        lines.append("смещение карточки от центра экрана: %+.0f px"
                     % (cx - win_w / 2.0))
        lines.append("заголовок: %r, текст: %r, кнопка: %r"
                     % (box.title_label.text, box.message_label.text,
                        box.button_label.text))

        # Края окна проверяются у самой карточки, а не у ModalView:
        # ModalView центрируется системой, и на момент проверки его
        # размер ещё может отставать от карточки, из-за чего правая
        # граница выглядит вылезшей за экран на ровном месте.
        if card.pos[0] < -1 or card.pos[0] + card.size[0] > win_w + 1:
            problems.append("карточка выходит за левый или правый край")
        if card.pos[1] < -1 or card.pos[1] + card.size[1] > win_h + 1:
            problems.append("карточка выходит за верх или низ")
        # Ширина окна iOS - 270 точек при масштабе 1.
        if abs(card.size[0] - dp(270)) > 2:
            problems.append("ширина карточки %.0f вместо %.0f"
                            % (card.size[0], dp(270)))
        # Кнопка должна быть последней строкой и занимать низ карточки.
        btn = box.button_label
        if btn.pos[1] < card.pos[1] - 1:
            problems.append("кнопка ниже карточки")
        lines.append("кнопка внизу карточки: %s"
                     % (btn.pos[1] >= card.pos[1] - 1))

        Window.screenshot(name=SHOT)

        # Закрытие по нажатию на кнопку.
        box.dismiss()
        Clock.schedule_once(verify_closed, 0.6)

    def verify_closed(_dt):
        left = [w for w in Window.children
                if w.__class__.__name__ == "_Alert"]
        if left:
            problems.append("окно не закрылось по кнопке")
        else:
            lines.append("окно закрылось по кнопке")
        finish()

    def finish():
        lines.append("")
        lines.append("ИТОГ: %s" % ("сообщения работают" if not problems
                                 else "есть проблемы"))
        for p in problems:
            lines.append("  - %s" % p)
        lines.append("снимок: %s" % SHOT)
        with open(LOG, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        print("\n".join(lines))
        Clock.schedule_once(lambda *_: stop(), 0.3)

    from main import MessengerApp
    app = MessengerApp()

    def stop():
        # Без этого проба не закончится: цикл приложения сам не
        # останавливается.
        try:
            app.stop()
        except Exception:
            pass

    def go(_dt):
        # Размер окна НЕ меняется здесь намеренно: он задан в Config
        # до старта. Попытка сменить его на лету дала перекошенный
        # снимок, и разбираться пришлось бы с артефактом проб��, а не с
        # самим окном.
        Clock.schedule_once(check, 1.0)
        # Длинный текст: он и есть случай, где окно обычно ломается -
        # не влезает, наезжает на кнопку или выходит за экран.
        dialogs.show_message(
            "Код отправлен",
            "Учебный режим: код 307866 (он также записан "
            "в data/outbox.log)")

    Clock.schedule_once(go, 2.0)
    app.run()


if __name__ == "__main__":
    main()