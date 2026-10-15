"""Проба: поля ввода ведут себя как айфонские.

Зачем
-----
Поля объявлены прямо в разметке как <PillInput@TextInput> и
<Field@TextInput>, то есть класса на Python у них нет. Настройка
поведения подцепляется перехватом создания, и если перехват не
сработал, поля останутся в айфоне с тонким курсором и автозаменой
внутри кода приглашения.

Проверяется на настоящем поле, взятом с экрана регистрации.

Как читать
----------
Строка ИТОГ в _shots/field.log.
"""

import os

BASE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(BASE, "_shots", "field.log")
# Ширина курсора, которую ждём: iPhone рисует 2dp, Kivy по умолчанию 1dp.
WANT_CURSOR_DP = 2


def main():
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    os.environ["RH_DB"] = os.path.join(BASE, "_shots", "probe.db")

    from kivy.clock import Clock
    from kivy.metrics import dp
    from kivy.uix.textinput import TextInput

    import ui.ios_field as ios_field
    _is_code_field = ios_field._is_code_field

    lines, problems = [], []

    def check(_dt):
        # Поля берём настоящие, с экранов, а не синтетические: у
        # синтетического нет подсказки, а по подсказке решается,
        # нужна ли автозамена. Смотрим все экраны, а не первый: поле
        # кода приглашения лежит на другом шаге регистрации.
        want = dp(WANT_CURSOR_DP)
        found = {}
        for screen in app.manager.screens:
            for child in screen.walk():
                if isinstance(child, TextInput):
                    # id есть не у каждого поля: объявленные прямо в
                    # разметке его не имеют, и обращение к нему падает.
                    ident = getattr(child, "id", "") or "поле"
                    found["%s/%s" % (screen.name, ident)] = child

        if not found:
            problems.append("поля ввода на экранах не найдены")
            finish()
            return

        lines.append("найдено полей: %d" % len(found))
        lines.append("dp(%d) в этой пробе: %.3f"
                     % (WANT_CURSOR_DP, want))

        # Мост в iOS должен быть, иначе не будет ни системных окон,
        # ни безопасных отступов экрана. Проверяется здесь же: это та
        # же причина молчаливого отката на ПК-вид, и на телефоне она
        # выглядела бы так же - ничего не работает, а ошибки нет.
        try:
            import importlib.util as _ilu
            has_bridge = _ilu.find_spec("pyobjus") is not None
        except Exception:
            has_bridge = False
        lines.append("мост в iOS (pyobjus): %s"
                     % ("есть" if has_bridge
                        else "нет (на ПК так и должно быть)"))

        for where, field in sorted(found.items()):
            cursor_px = field.cursor_width
            try:
                cursor_px = float(cursor_px)
            except (TypeError, ValueError):
                pass
            wants_none = ios_field._wants_no_suggestions(field)
            got_none = not getattr(field, "keyboard_suggestions", True)
            lines.append("%-34s курсор %.3f, автозамена нужна=%s "
                         "выключена=%s"
                         % (where, cursor_px, wants_none, got_none))
            if abs(cursor_px - want) > 0.01:
                problems.append("%s: курсор %.3f вместо %.3f"
                                % (where, cursor_px, want))
            if wants_none and not got_none:
                problems.append("%s: автозамена не выключена" % where)

        # Код приглашения обязан быть среди найденных: без него
        # проверка того, что автозамена у кода выключена, пустая.
        # Ищем поле кода по образцу подсказки, а не по id: у полей,
        # объявленных прямо в разметке, атрибута id нет вовсе.
        code = [k for k, f in found.items()
                if _is_code_field(f)
                or "A12" in str(getattr(f, "hint_text", ""))]
        lines.append("поле кода приглашения найдено: %s"
                     % (", ".join(sorted(code)) if code else "НЕТ"))
        if not code:
            problems.append("поле кода приглашения не найдено")
        finish()

    def finish():
        lines.append("")
        lines.append("ИТОГ: %s" % ("поля айфонские" if not problems
                                 else "есть проблемы"))
        for p in problems:
            lines.append("  - %s" % p)
        with open(LOG, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        print("\n".join(lines))
        Clock.schedule_once(lambda *_: app.stop(), 0.3)

    from main import MessengerApp
    app = MessengerApp()

    def go(_dt):
        app.manager.current = "reg_step3"
        Clock.schedule_once(check, 1.5)

    Clock.schedule_once(go, 2.0)
    app.run()


if __name__ == "__main__":
    main()