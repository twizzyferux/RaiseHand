"""Штатные окна iOS вместо серых окон Kivy.

Зачем
-----
Kivy показывает своё окно: серая рамка, кнопка с толстым контуром,
шрифт не тот. В айфонском приложении такого нет - там системный
алерт, который выглядит как все остальные и ведёт себя как все
остальные. Пользователь знаком с этим видом с других приложений, и
переход туда ничего не объяснять не стоит.

Как
---
Окно показывает UIAlertController - тот самый класс, которым
пользуются системные сообщения. Он живёт в слое iOS, поверх канваса
Kivy, поэтому выглядит настоящим айфонским, а не нарисованным.

Тонкость, из-за которой пришлось писать отдельно: окно показывает
тот контроллер, который сейчас на экране, а не корневой. Если поверх
уже открыто другое окно, показывать надо поверх него, иначе iOS
откажется показывать ("whose view is not in the window hierarchy").

Что делаем, если не получилось
------------------------------
Ничего страшного не делаем: возвращаем False, и вызывающий код
показывает обычное окно Kivy. Окно хуже по виду, но приложение
живо и пользователь прочитал, что случилось.
"""

from kivy.logger import Logger

__all__ = ["available", "show"]


def _why(reason: str) -> None:
    """Записать, почему системное окно не показалось.

    В журнал запуска, а не только в системный лог. Причина в том, что
    на iOS строка из Logger уходит в журнал устройства, откуда её не
    достать: приложение запускается через Sideloadly, а не из Xcode,
    и консоли там нет. Первая же попытка показать окно закончилась
    молчаливым откатом на окно Kivy, и понять почему было нечем -
    пришлось бы гадать.

    Поэтому каждая неудачная попытка оставляет след в том самом файле,
    который забирается с телефона из Documents.
    """
    Logger.warning("ios_alert: %s" % reason)
    try:
        import main
        main._record("ОКНО IOS НЕ ПОКАЗАЛОСЬ", reason)
    except Exception:
        # Записать причину важнее, чем записать саму причину: если и
        # сюда не вышло, сообщение всё равно уйдёт в системный лог.
        pass


def _ui_kit():
    """Классы UIKit, нужные для окна. None, если их нет."""
    try:
        from pyobjus import autoclass, objc_str
    except ImportError:
        return None
    return autoclass, objc_str


def available() -> bool:
    """Есть ли смысл пробовать системное окно."""
    from core.platform_setup import IS_IOS
    if not IS_IOS:
        return False
    return _ui_kit() is not None


def _top_controller(autoclass):
    """Контроллер, поверх которого и показывают окно.

    Возвращает кортеж (контроллер, причина_сбоя). Причина нужна для
    разбора: пока здесь было голое "None", любая неудача выглядела
    одинаково, и понять, что именно сломалось, было нечем. Первая
    попытка на телефоне закончилась именно так - молчаливый откат на
    окно Kivy без следа.

    Идём по цепочке presentedViewController до конца: показывать надо
    поверх всего, что уже открыто.
    """
    try:
        app = autoclass("UIApplication").sharedApplication()
    except Exception as e:
        return None, "UIApplication.sharedApplication не ответил: %r" % (e,)
    window = None
    why = "keyWindow вернул пусто"
    # На iOS 13 и новее keyWindow устарел и может быть пустым, пока
    # окна есть: тогда берём последнее из windows.
    for getter in ("keyWindow",):
        try:
            window = getattr(app, getter)
            break
        except Exception as e:
            window = None
            why = "keyWindow не сработал: %r" % (e,)
    if window is None:
        # keyWindow на iOS 13+ может быть пустым. Тогда окно берётся
        # из списка: нужно то, которое сейчас на экране, а это
        # последнее в списке.
        try:
            windows = app.windows()
            count = int(windows.count()) if windows is not None else 0
            if count:
                window = windows.objectAtIndex_(count - 1)
                why = "окно взято из списка (keyWindow пуст), окон: %d" % count
        except Exception as e:
            window = None
            why = "список окон не прочитан: %r" % (e,)
    if window is None:
        return None, "не нашлось окна: %s" % why
    try:
        controller = window.rootViewController()
    except Exception as e:
        return None, "у окна нет rootViewController: %r" % (e,)
    if controller is None:
        return None, "rootViewController пуст"
    # Поднимаемся по цепочке открытых окон наверх: показывать надо
    # поверх всего, что уже открыто, иначе iOS откажется.
    for _ in range(20):
        try:
            presented = controller.presentedViewController()
        except Exception:
            presented = None
        if presented is None:
            return controller, ""
        controller = presented
    return controller, "цепочка окон не кончилась за 20 шагов"


def show(title: str, message: str, button: str = "Понятно",
         on_close=None) -> bool:
    """Показать системное окно iOS. True - показано, False - нет.

    on_close вызывается после нажатия кнопки. Он нужен там, где окно
    завершает работу: например, проводник выбора файла не закрывается
    сам по себе.
    """
    kit = _ui_kit()
    if kit is None:
        _why("нет pyobjus (модуль не установлен в iOS-сборку)")
        return False
    autoclass, objc_str = kit

    try:
        from pyobjus import objc_block
    except ImportError as e:
        _why("в pyobjus нет objc_block: %r" % (e,))
        return False

    try:
        controller, why = _top_controller(autoclass)
        if controller is None:
            _why(why)
            return False

        alert_cls = autoclass("UIAlertController")
        action_cls = autoclass("UIAlertAction")

        # Предупреждение системной плашки - самый частый случай
        # (код приглашения, остаток заряда), поэтому стиль первый.
        alert = alert_cls.alloc().initWithTitle_message_preferredStyle_(
            objc_str(title), objc_str(message), 0)

        def handler(_action):
            if on_close is not None:
                try:
                    on_close()
                except Exception:
                    Logger.exception("ios_alert: сбой в обработчике")

        action = action_cls.actionWithTitle_style_handler_(
            objc_str(button), 0, objc_block(handler, None))
        alert.addAction_(action)

        controller.presentViewController_animated_completion_(
            alert, True, None)
        _ok(title)
        return True
    except Exception as e:
        # Любая ошибка означает, что окно не показалось. Вызывающий
        # код покажет своё - приложение продолжит работать.
        import traceback
        Logger.exception("ios_alert: системное окно не показалось")
        _why("%s: %s" % (type(e).__name__, e))
        try:
            import main
            main._record("ОКНО IOS: ПОЛНЫЙ ТЕКСТ ОШИБКИ",
                         traceback.format_exc())
        except Exception:
            pass
        return False


def _ok(title: str) -> None:
    """Отметка, что окно показано. Нужна для проверки на телефоне."""
    Logger.info("ios_alert: показано %r" % (title,))
    try:
        import main
        main._record("ОКНО IOS ПОКАЗАНО", repr(title))
    except Exception:
        pass