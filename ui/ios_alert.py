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

    Идём по цепочке presentedViewController до конца: показывать надо
    поверх всего, что уже открыто.
    """
    try:
        app = autoclass("UIApplication").sharedApplication()
    except Exception:
        return None
    window = None
    # На iOS 13 и новее окон может быть несколько, и нужное - то,
    # которое сейчас на экране.
    for getter in ("keyWindow",):
        try:
            window = getattr(app, getter)
            break
        except Exception:
            window = None
    if window is None:
        try:
            windows = app.windows()
            window = windows.lastObject() if windows else None
        except Exception:
            window = None
    if window is None:
        return None
    try:
        controller = window.rootViewController()
    except Exception:
        return None
    # Поднимаемся по цепочке открытых окон наверх.
    for _ in range(20):
        if controller is None:
            return None
        try:
            presented = controller.presentedViewController()
        except Exception:
            presented = None
        if presented is None:
            return controller
        controller = presented
    return controller


def show(title: str, message: str, button: str = "Понятно",
         on_close=None) -> bool:
    """Показать системное окно iOS. True - показано, False - нет.

    on_close вызывается после нажатия кнопки. Он нужен там, где окно
    завершает работу: например, проводник выбора файла не закрывается
    сам по себе.
    """
    kit = _ui_kit()
    if kit is None:
        return False
    autoclass, objc_str = kit

    try:
        from pyobjus import objc_block
    except ImportError:
        return False

    try:
        controller = _top_controller(autoclass)
        if controller is None:
            Logger.warning("ios_alert: не нашлось окна для показа")
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
        Logger.info("ios_alert: показано %r" % (title,))
        return True
    except Exception:
        # Любая ошибка означает, что окно не показалось. Вызывающий
        # код покажет своё - приложение продолжит работать.
        Logger.exception("ios_alert: системное окно не показалось")
        return False