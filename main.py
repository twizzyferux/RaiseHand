"""Точка входа приложения RaiseHand.

Запуск на ПК:      python main.py
Запуск на Android: собрать APK через buildozer (см. README.md).
Сборка iOS:        см. PLATFORM.md.

Файл делает четыре вещи:
  1) подбирает размер окна под экран (настольный компьютер или телефон);
  2) создаёт базу данных, если её ещё нет, и включает логирование;
  3) подключает шрифт и загружает все файлы оформления ui/kv/*.kv;
  4) собирает экраны в ScreenManager и запускает окно.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _startup_log_path():
    """Куда записать ошибку старта.

    Путь считается вручную, ничего не импортируя: если падает наш
    модуль, взять путь из него нельзя - он и есть причина. Поэтому
    проверяются известные места и берётся первое, куда запись прошла.

    На iOS переменная HOME не выставляется, а TMP указывает внутрь
    папки приложения (только чтение), поэтому проверка настоящая.
    Контейнер выводится от расположения кода: сам пакет лежит как
    <контейнер>/RaiseHand.app, значит контейнер на два уровня выше, а
    документы - <контейтор>/Documents. Их и показывает раздел Files в
    Apple Devices.
    """
    import tempfile
    here = os.path.dirname(os.path.abspath(__file__))
    # <контейнер>/RaiseHand.app/YourApp -> контейнер на два уровня выше.
    container = os.path.dirname(os.path.dirname(here))
    home = os.environ.get("HOME") or os.path.expanduser("~")
    for base in (home,
                 os.path.join(home, "Documents"),
                 os.path.join(container, "Documents"),
                 container,
                 tempfile.gettempdir(),
                 os.getcwd()):
        if not base:
            continue
        try:
            folder = os.path.join(base, "raisehand")
            os.makedirs(folder, exist_ok=True)
            return os.path.join(folder, "startup.log")
        except OSError:
            continue
    return None


def _record(reason, detail):
    """Отметка в журнале старта.

    Пишется в файл И в консоль. Файл нужен, чтобы забрать причину с
    телефона, но положиться только на него нельзя: папка может
    оказаться недоступной для записи (kivy-ios не выставляет HOME, а
    временная папка указывает внутрь приложения), и тогда файл не
    появится вовсе. Консоль же всегда доступна в журнале устройства.
    """
    import time
    stamp = time.strftime("%H:%M:%S")
    text = "%s %s\n%s\n%s\n" % (stamp, reason, detail, "-" * 40)
    for line in text.splitlines():
        try:
            sys.stderr.write("[raisehand] %s\n" % line)
            sys.stderr.flush()
        except Exception:
            break
    path = _startup_log_path()
    if not path:
        return
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(text)
    except OSError:
        pass


_record("приложение стартует", os.path.dirname(os.path.abspath(__file__)))

# Снимок окружения. На iOS без него диагностика упирается в догадки:
# неизвестно, где система ищет домашнюю папку, куда положились данные
# и что вообще видно приложению. Здесь это видно сразу.
try:
    import sys as _sys
    _env_lines = [
        "платформа: %s" % _sys.platform,
        "исполняемый: %s" % _sys.executable,
        "версия python: %s" % _sys.version.split()[0],
        "cwd: %s" % os.getcwd(),
        "HOME: %s" % os.environ.get("HOME"),
        "expanduser(~): %s" % os.path.expanduser("~"),
        "TMPDIR: %s" % os.environ.get("TMPDIR"),
        "TMP: %s" % os.environ.get("TMP"),
        "PYTHONHOME: %s" % os.environ.get("PYTHONHOME"),
        "PYTHONPATH: %s" % os.environ.get("PYTHONPATH"),
        "KIVY_NO_CONSOLELOG: %s" % os.environ.get("KIVY_NO_CONSOLELOG"),
        "sys.path: %s" % " | ".join(_sys.path),
    ]
    _record("ОКРУЖЕНИЕ", "\n".join(_env_lines))
except BaseException:
    pass

# Что реально лежит рядом с кодом. Если папка с настройками или
# шрифтами не найдена - причина найдена, смотреть больше некуда.
try:
    _here = os.path.dirname(os.path.abspath(__file__))
    _seen = []
    for _rel in ("config/settings.json", "assets/fonts/SF-Pro-Text-Regular.otf",
                 "ui/kv/theme.kv", "ui/glass_widget.py"):
        _p = os.path.join(_here, _rel)
        _seen.append("%s: %s" % (_rel, os.path.exists(_p)))
    _seen.append("в папке %s: %d файлов" % (_here, len(os.listdir(_here))))
    # Что на самом деле важно про стекло.
    #
    # Раньше здесь стояла проверка "есть ли файл ui/glass_widget.py",
    # и она показывала False на телефоне. Вывод "файл потерялся при
    # сборке" был неверным: проверялся исходник, а не то, работает ли
    # код. Если исходник на устройстве лежит скомпилированным, класс
    # импортируется успешно (строки ниже это доказывают - иначе был бы
    # записан "ИМПОРТ НЕ ПРОШЁЛ"), а исходника рядом нет. То есть
    # отсутствие файла ничего не говорит о работоспособности.
    #
    # Проверять надо результат: загрузился ли плагин и зарегистрированы
    # ли классы. Это и написано ниже.
    try:
        # Плагин ищется, но не выполняется: find_spec только смотрит,
        # можно ли его найти. Импортировать его здесь рано - на этой
        # стадии ещё не загружены правила .kv.
        import importlib.util as _ilu
        _found = _ilu.find_spec("kivy_garden.frostedglass") is not None
        _seen.append("плагин стекла: %s"
                     % ("найден" if _found else "НЕ НАЙДЕН"))
    except Exception as _e:
        _seen.append("плагин стекла: не проверить (%s)" % _e)
    # Полный список файлов в папке ui.
    #
    # Добавлено из-за пропажи без следа: ui/glass_widget.py в сборке
    # отсутствовал, хотя в git он есть и под исключения пайплайна не
    # подпадает. Проверка четырёх файлов отвечала только "есть/нет" и
    # не показывала, что происходит с остальными. Список выводит
    # это сразу и целиком.
    try:
        _ui = os.path.join(_here, "ui")
        _names = []
        for _root, _dirs, _files in os.walk(_ui):
            for _fn in _files:
                _names.append(os.path.relpath(os.path.join(_root, _fn),
                                              _ui))
        _seen.append("в ui: %d файлов: %s"
                     % (len(_names), ", ".join(sorted(_names))))
    except Exception as _e:
        _seen.append("в ui: не прочитать (%s)" % _e)
    _record("ФАЙЛЫ", "\n".join(_seen))
except BaseException:
    pass

try:

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    from core import platform_setup  # noqa: E402
    from core.platform_setup import init_window  # noqa: E402

    # --- РАЗРЕШЕНИЕ ОКНА ------------------------------------------------------
    # ПК:        масштаб подбирается под свободное место на экране.
    # iOS/Android: масштаб подбирается под реальный экран устройства.
    # Подробности и ручное переопределение (RH_UI_SCALE) — core/platform_setup.py.
    init_window()
    UI_SCALE = platform_setup.UI_SCALE

    # Дальше импорты идут после init_window(): Kivy читает размер окна из
    # Config при создании окна, и настройка должна быть раньше этого.


    from kivy.app import App  # noqa: E402
    from kivy.core.text import LabelBase  # noqa: E402
    from kivy.lang import Builder  # noqa: E402
    from kivy.properties import ListProperty, ObjectProperty, StringProperty  # noqa: E402
    from kivy.uix.screenmanager import NoTransition, ScreenManager  # noqa: E402

    from core import auth, database, logs, session, teacher_proof  # noqa: E402
    from core.config import BASE_DIR, SETTINGS, sprite, text  # noqa: E402
    from ui import anim, screens, touch_fix  # noqa: E402
    from ui.screens import PhoneStage  # noqa: E402,F401  (нужен .kv)
    from ui.avatar import GradientAvatar  # noqa: E402,F401  (нужен .kv)
    from ui.bubbles import WelcomeDecor  # noqa: E402,F401  (нужен .kv)
    from ui.chats import ChatList, ChatPane, ChatRow, NavItem  # noqa: E402,F401  (нужны .kv)
    from ui.fields import PasswordField, PillPasswordField  # noqa: E402,F401  (.kv)
    from ui.glass_widget import (BlurSource, LiquidFab,  # noqa: E402,F401  (нужны .kv)
                                 LiquidNavBar)
except BaseException:
    # Падение при импорте раньше всего остального: экран с ошибкой
    # показать уже нечем, а iOS об этом не пишет отчёт. Поэтому текст
    # ошибки уходит в файл, который можно забрать с телефона
    # (Apple Devices -> устройство -> Files -> RaiseHand).
    import traceback

    _record("ИМПОРТ НЕ ПРОШЁЛ", traceback.format_exc())
    raise

# Отметка после импортов: раз её нет, а первая строка есть - значит
# упало на импорте; если есть обе, сбой происходит позже.
_record("импорты прошли", "успех")

# Захват касания в этой сборке Kivy не заполняет grab_current, а от него
# зависит отпускание кнопок. Чиним до создания окна — иначе виджеты успеют
# зарегистрировать обработчики. Подробности: ui/touch_fix.py
touch_fix.install()

KV_DIR = os.path.join(BASE_DIR, "ui", "kv")
KV_FILES = [
    "theme.kv",          # общие правила (размеры) — загружается первым
    "welcome.kv",
    "login.kv",
    "register.kv",       # пошаговая регистрация ученика (5 шагов)
    "register_teacher.kv",
    "teacher_proof.kv",
    "verify.kv",
    "home.kv",
    "chat.kv",
    "settings.kv",
    "logs.kv",           # просмотр data/app.log внутри приложения
]

SCREENS = [
    ("welcome", screens.WelcomeScreen),
    ("login", screens.LoginScreen),
    ("reg_step1", screens.RegStep1Screen),
    ("reg_step2", screens.RegStep2Screen),
    ("reg_step3", screens.RegStep3Screen),
    ("reg_step4", screens.RegStep4Screen),
    ("reg_step5", screens.RegStep5Screen),
    ("register_teacher", screens.RegisterTeacherScreen),
    ("teacher_proof", screens.TeacherProofScreen),
    ("verify", screens.VerifyScreen),
    ("home", screens.HomeScreen),
    ("chat", screens.ChatScreen),
    ("settings", screens.SettingsScreen),
    ("logs", screens.LogsScreen),
]


def _crash_screen(detail: str):
    """Окно с текстом ошибки вместо приложения.

    Нужно, чтобы сбой при запуске был виден. Иначе на iOS он
    выглядит как «мигнуло и закрылось», а в системном журнале телефона
    ничего нет.
    """
    from kivy.uix.label import Label
    from kivy.uix.scrollview import ScrollView
    from kivy.core.text import Label as CoreLabel

    label = Label(text=detail, font_size="11sp", halign="left",
                  valign="top", size_hint_y=None, padding=(8, 8))
    # Высота под фактический текст, иначе ScrollView не знает, что
    # показывать, и содержимое обрезается по верхнему краю.
    label.bind(
        width=lambda inst, value: setattr(inst, "text_size", (value, None)),
        texture_size=lambda inst, value: setattr(inst, "height", value[1] + 24),
    )
    del CoreLabel
    box = ScrollView(do_scroll_x=False)
    box.add_widget(label)
    return box


class MessengerApp(App):
    """Главный класс. Все .kv-файлы обращаются к нему через слово `app`."""

    current_user = ObjectProperty(None, allownone=True)
    teacher_platforms = ListProperty([])
    # Имя зарегистрированного шрифта: его подставляют все .kv-правила
    font_name = StringProperty("SFPro")

    def build(self):
        # Ошибка старта показывается на экране, а не теряется.
        #
        # На iOS падение при инициализации не оставляет следов: процесс
        # умирает раньше, чем система начинает записывать отчёт, и в
        # аналитике телефона пусто — непонятно даже, падало ли что-то.
        # Поэтому весь build выполняется под защитой: при ошибке
        # приложение всё равно показывает окно с текстом, и причину
        # видно на экране (или на скриншоте).
        try:
            return self._build()
        except BaseException:
            import traceback

            detail = traceback.format_exc()
            try:
                sys.stderr.write(detail)
                sys.stderr.flush()
            except Exception:
                pass
            return _crash_screen(detail)

    def _build(self):
        self.title = SETTINGS["app_name"]
        self.icon = sprite("logo") or None
        self.teacher_platforms = teacher_proof.platforms()

        # Логи: файл data/app.log + ошибки Kivy в тот же файл.
        logs.setup()
        logs.info("Приложение запущено. Устройство: %s", logs._device())

        # Размер окна/масштаб подбираем после создания окна: на ПК
        # провайдер окна не берёт размер из Config, на телефоне размер
        # экрана известен только к этому моменту.
        platform_setup.apply_window_size()

        database.init_db()
        self._register_fonts()

        for name in KV_FILES:
            Builder.load_file(os.path.join(KV_DIR, name))

        # Переход между экранами — мягкий, как в Телеграме: новый экран
        # въезжает сбоку и проявляется, старый слегка отходит и гаснет
        # (см. ui/anim.py -> SoftSlideTransition).
        self.manager = ScreenManager(transition=self._transition())
        for name, screen_class in SCREENS:
            self.manager.add_widget(screen_class(name=name))
        self.manager.bind(current=lambda _, value: logs.info("Экран: %s", value))

        # Постоянный вход: если на этом устройстве уже входили —
        # сразу открываем домашний экран, без ввода пароля.
        self.start_screen = self._restore_session()
        return self.manager

    def _restore_session(self) -> str:
        """Пользователь из прошлого запуска или 'welcome'."""
        user_id = session.user_id()
        if not user_id:
            return "welcome"
        user = auth.get_user_by_id(user_id)
        if user is None:
            session.clear()
            logs.warn("Сессия сохранена, но аккаунта нет — сброшено")
            return "welcome"
        self.current_user = user
        logs.event("АВТОВХОД", user=user.display_name, id=user.public_id)
        return "home"

    def on_start(self):
        """Стартовый экран выбираем после первого кадра: экраны уже собраны."""
        target = getattr(self, "start_screen", "welcome")
        if target and self.manager.current != target:
            self.go(target, direction="up")

    # -- помощники для .kv-файлов ------------------------------------------ #

    def t(self, name):
        """Текст из config/settings.json (секция "texts")."""
        return text(name)

    def sprite(self, name):
        """Путь к твоему спрайту из config/settings.json (секция "sprites").

        Возвращает пустую строку, если путь не задан или файла нет,
        поэтому приложение работает и без картинок.
        """
        return sprite(name)

    # -- навигация --------------------------------------------------------- #

    @staticmethod
    def _transition():
        """Мягкий переход между экранами (см. ui/anim.py)."""
        return anim.SoftSlideTransition(duration=anim.TRANSITION_DURATION)

    def go(self, screen_name: str, direction: str = "left"):
        self.manager.transition.direction = direction
        self.manager.current = screen_name

    def open_chat(self, partner: auth.User):
        chat_screen = self.manager.get_screen("chat")
        chat_screen.partner = partner
        self.go("chat")

    def logout(self):
        if self.current_user is not None:
            logs.event("ВЫХОД", user=self.current_user.display_name,
                       id=self.current_user.public_id)
        session.clear()
        self.current_user = None
        self.manager.transition = NoTransition()
        self.manager.current = "welcome"
        self.manager.transition = self._transition()

    def refresh_user(self):
        """Перечитать пользователя из базы (после изменений профиля)."""
        if self.current_user is not None:
            self.current_user = auth.get_user_by_id(self.current_user.id)

    def start_student_registration(self):
        """Кнопка «Я Ученик»: очистить черновик и открыть шаг 1."""
        screens.reset_draft()
        self.go("reg_step1")

    # -- шрифты ------------------------------------------------------------ #

    def _register_fonts(self):
        """Регистрирует фирменный шрифт (по умолчанию SF Pro Text).

        Файлы берутся из config/settings.json -> "font". Шрифт
        регистрируется под своим именем ("SFPro") и дополнительно
        подменяет встроенный "Roboto" — тогда весь текст в приложении
        в одном шрифте, даже если где-то остался явный font_name.
        """
        font_cfg = SETTINGS.get("font", {})
        name = font_cfg.get("name") or "SFPro"
        self.font_name = name
        file_name = font_cfg.get("file", "")
        bold_name = font_cfg.get("bold_file", "")
        if not file_name:
            return

        def _resolve(value):
            path = value if os.path.isabs(value) else os.path.join(
                BASE_DIR, "assets", "fonts", value)
            return path if os.path.exists(path) else ""

        regular = _resolve(file_name)
        bold = _resolve(bold_name) or regular
        if not regular:
            return

        LabelBase.register(name=name, fn_regular=regular, fn_bold=bold)
        if name != "Roboto":
            LabelBase.register(name="Roboto", fn_regular=regular, fn_bold=bold)


if __name__ == "__main__":
    MessengerApp().run()
