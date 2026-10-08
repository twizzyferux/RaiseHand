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
from ui import anim, screens  # noqa: E402
from ui.avatar import GradientAvatar  # noqa: E402,F401  (нужен .kv)
from ui.bubbles import WelcomeDecor  # noqa: E402,F401  (нужен .kv)
from ui.chats import ChatRow, NavItem, UnreadBadge  # noqa: E402,F401  (нужны .kv)

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


class MessengerApp(App):
    """Главный класс. Все .kv-файлы обращаются к нему через слово `app`."""

    current_user = ObjectProperty(None, allownone=True)
    teacher_platforms = ListProperty([])
    # Имя зарегистрированного шрифта: его подставляют все .kv-правила
    font_name = StringProperty("SFPro")

    def build(self):
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
