"""Экраны приложения (логика). Внешний вид описан в файлах ui/kv/*.kv.

Каждому классу-экрану соответствует одноимённое правило в .kv-файле:
    WelcomeScreen        -> ui/kv/welcome.kv
    RegStep1Screen..RegStep5Screen -> ui/kv/register.kv
    ... и так далее.
"""

from kivy.app import App
from kivy.clock import Clock
from kivy.factory import Factory
from kivy.properties import (BooleanProperty, ListProperty, NumericProperty,
                             ObjectProperty, StringProperty)
from kivy.uix.floatlayout import FloatLayout

import os

from core import formatters, gradients, logs, session
from ui import anim
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen

from core import auth, chat, teacher_proof, verification
from core.config import SETTINGS, sprite
from ui.dialogs import choose_file, show_message


class MessageBubble(Label):
    """Сообщение в чате. mine=True — сообщение написано вами.

    Сейчас свои и чужие сообщения выглядят одинаково — разный фон для них
    делается в ui/kv/chat.kv (см. DESIGN.md).
    """

    mine = BooleanProperty(False)


Factory.register("MessageBubble", cls=MessageBubble)


class BaseScreen(Screen):
    """Небольшие удобства для всех экранов."""

    @property
    def app(self):
        return App.get_running_app()

    def error(self, message: str) -> None:
        show_message("Ошибка", message)

    def info(self, message: str, title: str = "Готово") -> None:
        show_message(title, message)


# --------------------------------------------------------------------------- #
#  Приветствие и вход
# --------------------------------------------------------------------------- #

class WelcomeScreen(BaseScreen):
    """Стартовый экран: три фразы по очереди + точки-индикаторы.

    Тексты берутся из config/settings.json -> "welcome_slides", чтобы их
    можно было менять без правки кода. Автосмена каждые SLIDE_SECONDS,
    точки кликабельны (зона касания 44dp).
    """

    slide_title = StringProperty("")
    slide_subtitle = StringProperty("")
    slide_index = NumericProperty(0)

    SLIDE_SECONDS = 5.0

    # Порядок появления при входе на экран (лесенкой, как в Телеграме)
    INTRO = ("w_logo", "w_word", "w_title", "w_sub", "dot0", "dot1",
             "dot2", "w_join", "w_student", "w_teacher", "w_link")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.slides = self._load_slides()
        # Паузу между фразами можно менять в config/settings.json
        raw = SETTINGS.get("welcome_slide_seconds")
        try:
            self.slide_seconds = max(2.0, float(raw))
        except (TypeError, ValueError):
            self.slide_seconds = self.SLIDE_SECONDS
        self._apply_slide(0, animate=False)
        self._timer = None

    @staticmethod
    def _load_slides():
        default = [
            {"title": "Не бойся\nподнять руку",
             "subtitle": "Отправляйте вопросы учителю\nв чате. Получайте ответы\nбыстро и без стеснения."},
            {"title": "Задавай\nвопросы смело",
             "subtitle": "Учитель ответит в чате\nкласса — быстро, понятно\nи без стеснения."},
            {"title": "Помогай\nодноклассникам",
             "subtitle": "Делись знаниями\nи поддерживай тех,\nкому сейчас трудно."},
        ]
        raw = SETTINGS.get("welcome_slides")
        if not isinstance(raw, list) or not raw:
            return default
        slides = []
        for item in raw:
            if isinstance(item, dict) and item.get("title"):
                slides.append({"title": item.get("title", ""),
                               "subtitle": item.get("subtitle", "")})
        return slides or default

    # -- точки-индикаторы --------------------------------------------------- #

    def _dot(self, index):
        return self.ids.get("dot%d" % index) if self.ids else None

    def _paint_dots(self, animate=True):
        """Активная точка темнеет, остальные светлеют — плавно."""
        for i in range(len(self.slides)):
            dot = self._dot(i)
            if dot is None:
                continue
            target = 1.0 if i == self.slide_index else 0.0
            if animate:
                anim.fade_to(dot, "active_t", target, duration=0.26)
            else:
                dot.active_t = target

    # -- смена фразы ------------------------------------------------------- #

    def _apply_slide(self, index, animate=True):
        if not self.slides:
            return
        index = index % len(self.slides)
        self.slide_index = index
        slide = self.slides[index]

        title = self.ids.get("w_title") if self.ids else None
        subtitle = self.ids.get("w_sub") if self.ids else None

        def put_title():
            self.slide_title = slide["title"]

        def put_subtitle():
            self.slide_subtitle = slide["subtitle"]

        if animate and title is not None:
            # Текст не перескакивает, а мягко перетекает: сначала гаснет,
            # потом появляется новая фраза.
            anim.swap_text(title, put_title)
            if subtitle is not None:
                anim.swap_text(subtitle, put_subtitle)
        else:
            put_title()
            put_subtitle()

        self._paint_dots(animate=animate)

    def set_slide(self, index):
        """Клик по точке — переключение на указанный слайд."""
        self._apply_slide(int(index))

    def next_slide(self):
        self._apply_slide(self.slide_index + 1)

    def _tick(self, _dt):
        self.next_slide()

    # -- появление экрана -------------------------------------------------- #

    def on_pre_enter(self, *args):
        self._start()

    def on_enter(self, *args):
        self._start()
        self._play_intro()
        decor = self.ids.get("w_decor")
        if decor is not None:
            decor.start_floating()

    def on_leave(self, *args):
        self._stop()
        decor = self.ids.get("w_decor")
        if decor is not None:
            decor.stop_floating()

    def _play_intro(self):
        if not self.ids:
            return
        widgets = [self.ids.get(name) for name in self.INTRO]
        anim.stagger_in(widgets, start=0.12, step=0.04)

    def _start(self):
        if self._timer is None:
            from kivy.clock import Clock
            self._timer = Clock.schedule_interval(self._tick, self.slide_seconds)

    def _stop(self):
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None


class LoginScreen(BaseScreen):
    login_field = ObjectProperty(None)
    password_field = ObjectProperty(None)
    remember_toggle = ObjectProperty(None)

    def do_login(self):
        login_value = self.login_field.text
        try:
            user = auth.login(login_value, self.password_field.text)
        except auth.AuthError as exc:
            logs.warn("Вход не удался: %s (логин: %s)", exc, login_value)
            self.error(str(exc))
            return
        except IndexError:
            self.error("Заполните поля")
            return

        self.password_field.text = ""
        self.app.current_user = user

        # «Запомнить меня»: сессия на этом устройстве — при следующем
        # запуске сразу попадём в приложение, без ввода пароля.
        remember = (self.remember_toggle is not None
                    and self.remember_toggle.state == "down")
        if remember:
            session.save(user.id, user.public_id)
            _save_remember(True, login_value)      # подсказка логина на входе
        else:
            session.clear()
        logs.event("ВОЙТИ", user=user.display_name, id=user.public_id,
                   запомнил="да" if remember else "нет")

        if not user.contact_verified:
            self.app.go("verify")
        elif user.is_teacher and not user.teacher_verified:
            self.app.go("teacher_proof")
        else:
            self.app.go("home")

    def on_pre_enter(self, *args):
        """Подставляем логин, который запомнили в прошлый раз."""
        remembered = SETTINGS.get("remember_login", "")
        if remembered and not self.login_field.text:
            self.login_field.text = remembered
        # Галочка уже стоит, если на устройстве была сессия
        if session.user_id() and self.remember_toggle is not None:
            self.remember_toggle.state = "down"


# --------------------------------------------------------------------------- #
#  Регистрация ученика (пошаговая, макет проект/регистрация.svg)
# --------------------------------------------------------------------------- #

# Данные, набранные на разных шагах, живут здесь до создания аккаунта.
DRAFT: dict = {}


def reset_draft() -> None:
    """Начать регистрацию заново (вызывается кнопкой «Я Ученик»)."""
    DRAFT.clear()
    DRAFT.update({
        "first_name": "", "last_name": "", "password": "",
        "remember": False, "city": "", "invite_code": "",
        "class_name": "", "school_name": "",
        "contact_type": "", "contact_value": "",
        "code": None, "user": None, "_fresh": True,
    })


def clear_if_fresh(screen, *fields) -> None:
    """При свежем старте (кнопка «Я Ученик») очистить поля шага."""
    if DRAFT.get("_fresh"):
        for field in fields:
            field.text = ""


class RegChrome(FloatLayout):
    """Общая «шапка» шагов регистрации: назад, заголовок, прогресс,
    текст-подпись, согласие и кнопка «Далее →».

    Экран-шаг добавляет только свои поля ввода.
    """

    back_to = StringProperty("welcome")
    header_title = StringProperty("Регистрация ученика")
    title = StringProperty("")
    subtitle = StringProperty("")          # строки разделяются \n
    subtitle_cy = NumericProperty(663)     # центр подзаголовка (y вверх)
    progress = NumericProperty(0)          # залитая длина из 295 px
    show_back = BooleanProperty(True)
    show_progress = BooleanProperty(True)
    show_consent = BooleanProperty(True)
    next_label = StringProperty("Далее →")
    next_callback = ObjectProperty(None, allownone=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._grow_progress()

    def _grow_progress(self):
        """Полоска прогресса не перескакивает, а доезжает — как в Телеграме."""
        target = self.progress
        if not target:
            return
        self.progress = 0
        from kivy.clock import Clock
        Clock.schedule_once(
            lambda dt: anim.fade_to(self, "progress", target,
                                    duration=0.5, transition="out_cubic"), 0.08)

    def do_next(self):
        if self.next_callback is not None:
            self.next_callback()


class RegStep1Screen(BaseScreen):
    """Шаг 1 — «Как вас зовут?» (имя и фамилия)."""

    first_name = ObjectProperty(None)
    last_name = ObjectProperty(None)

    def next(self):
        first = self.first_name.text.strip()
        last = self.last_name.text.strip()
        if len(first) < 2 or len(last) < 2:
            self.error("Введите имя и фамилию (минимум 2 символа)")
            return
        DRAFT["first_name"] = first
        DRAFT["last_name"] = last
        DRAFT["_fresh"] = False
        self.app.go("reg_step2")

    def on_pre_enter(self, *args):
        clear_if_fresh(self, self.first_name, self.last_name)


class RegStep2Screen(BaseScreen):
    """Шаг 2 — «Введите пароль». password + повтор + «Запомнить меня»."""

    password = ObjectProperty(None)
    password_repeat = ObjectProperty(None)
    remember = ObjectProperty(None)        # CheckToggle

    def next(self):
        try:
            auth.validate_password(self.password.text, self.password_repeat.text)
        except auth.AuthError as exc:
            self.error(str(exc))
            return
        DRAFT["password"] = self.password.text
        DRAFT["remember"] = self.remember.state == "down"
        self.app.go("reg_step3")

    def on_pre_enter(self, *args):
        clear_if_fresh(self, self.password, self.password_repeat)
        if DRAFT.get("_fresh"):
            self.remember.state = "down"


class RegStep3Screen(BaseScreen):
    """Шаг 3 — «Где вы учитесь?» (город и код приглашения)."""

    city = ObjectProperty(None)
    invite_code = ObjectProperty(None)
    # подсказки городов под полем ввода
    city_suggestions = ListProperty([])

    def format_invite(self, text):
        """Код приглашения всегда заглавными.

        Пришлось текст поправить — ставим обратно; повторный вызов уже
        ничего не меняет, поэтому рекурсии не будет.
        """
        formatted = formatters.uppercase(text)
        if formatted != text:
            self.invite_code.text = formatted

    # -- подсказки городов -------------------------------------------------- #

    def on_city_typed(self, text):
        """Показать города, подходящие под ввод."""
        found = (formatters.city_suggestions(text, limit=5)
                 if (text or "").strip() else [])
        self.city_suggestions = found
        self._rebuild_city_box()

    def pick_city(self, name):
        """Город выбран — подставляем и прячем список."""
        if not name:
            return
        self.city.text = name
        self.city_suggestions = []
        self._rebuild_city_box()

    def _rebuild_city_box(self):
        """Пересобрать строки списка подсказок."""
        box = self.ids.get("city_box")
        if box is None:
            return
        box.clear_widgets()
        for name in self.city_suggestions:
            row = Factory.CityRow(text=name, on_release=lambda n=name: self.pick_city(n))
            box.add_widget(row)

    # -- переход дальше ---------------------------------------------------- #

    def next(self):
        city = self.city.text.strip()
        if len(city) < 2:
            self.error("Город: минимум 2 символа")
            return
        code = self.invite_code.text.strip()
        try:
            row = auth.find_class(code)
        except auth.AuthError as exc:
            self.error(str(exc))
            return
        DRAFT["city"] = city
        DRAFT["invite_code"] = code
        DRAFT["class_name"] = row["class_name"]
        DRAFT["school_name"] = row["school_name"]
        self.app.go("reg_step4")

    def on_pre_enter(self, *args):
        clear_if_fresh(self, self.city, self.invite_code)


class RegStep4Screen(BaseScreen):
    """Шаг 4 — «Подтверждение» (почта/телефон + код)."""

    contact = ObjectProperty(None)
    code_field = ObjectProperty(None)

    def format_contact(self, text):
        """Почта/телефон: заглавные буквы и тире между 3-м и 4-м символом.

        Вызывается из .kv на каждое изменение текста. Если пришлось текст
        поправить, ставим его обратно — повторный вызов уже ничего
        не меняет, поэтому рекурсии не возникает.
        """
        formatted = formatters.contact_format(text)
        if formatted != text:
            self.contact.text = formatted

    def send_code(self):
        value = self.contact.text.strip()
        contact_type = _detect_contact(value)
        if contact_type is None:
            self.error("Введите почту (ivan@example.com) или номер телефона")
            return
        DRAFT["contact_type"] = contact_type
        DRAFT["contact_value"] = value
        DRAFT["code"] = _generate_code()
        if SETTINGS.get("dev_mode"):
            self.info(f"Учебный режим: код {DRAFT['code']} "
                      f"(он также записан в data/outbox.log)", "Код отправлен")
        else:
            self.info("Код отправлен. Проверьте почту или сообщения.", "Отправлено")

    def next(self):
        if DRAFT.get("user") is not None:
            self.app.go("reg_step5")
            return
        if DRAFT.get("contact_value") is None or not DRAFT.get("contact_value"):
            self.error("Сначала укажите почту/телефон и запросите код")
            return
        if DRAFT.get("code") is None:
            self.error("Сначала запросите код")
            return
        entered = self.code_field.text.strip()
        if entered != str(DRAFT["code"]):
            self.error("Код не совпадает. Проверьте и попробуйте ещё раз")
            return

        try:
            user = auth.register_student(
                DRAFT["first_name"], DRAFT["last_name"],
                DRAFT["password"], DRAFT["password"],
                contact_type=DRAFT["contact_type"],
                contact_value=DRAFT["contact_value"],
                city=DRAFT["city"],
                class_name=DRAFT["class_name"],
                school_name=DRAFT["school_name"],
            )
        except auth.AuthError as exc:
            self.error(str(exc))
            return

        DRAFT["user"] = user
        _save_remember(DRAFT.get("remember"), DRAFT["contact_value"])
        logs.event("РЕГИСТРАЦИЯ", user=user.display_name, id=user.public_id)
        self.app.go("reg_step5")

    def on_pre_enter(self, *args):
        clear_if_fresh(self, self.contact, self.code_field)


class RegStep5Screen(BaseScreen):
    """Шаг 5 — «Всё готово!» (аватар, приветствие, класс/школа/роль)."""

    initials = StringProperty("")
    welcome_text = StringProperty("")
    class_value = StringProperty("")
    school_value = StringProperty("")

    def on_pre_enter(self, *args):
        user = DRAFT.get("user")
        if user is None:
            self.app.go("welcome")
            return
        # Инициалы рисует сам аватар (GradientAvatar), здесь только текст.
        self.initials = gradients.initials_for(user.first_name, user.last_name)
        self.welcome_text = f"Добро пожаловать,\n{user.first_name}!"
        self.class_value = user.class_name or DRAFT.get("class_name", "")
        self.school_value = user.school_name or DRAFT.get("school_name", "")
        avatar = self.ids.get("avatar")
        if avatar is not None:
            avatar.set_user(user, initials=self.initials)

    def start(self):
        user = DRAFT.get("user")
        if user is None:
            self.app.go("welcome")
            return
        self.app.current_user = user
        self.app.go("home")


def _detect_contact(value: str):
    """'email', если похоже на почту; 'phone' — на телефон; иначе None."""
    import re
    if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
        return "email"
    if re.fullmatch(r"\+?[\d\s()\-.]{6,}", value):
        return "phone"
    return None


def _generate_code() -> str:
    import random
    length = SETTINGS.get("rules", {}).get("code_length", 6)
    code = "".join(str(random.randint(0, 9)) for _ in range(length))
    try:
        from core.config import OUTBOX_PATH
        with open(OUTBOX_PATH, "a", encoding="utf-8") as f:
            f.write(f"[код подтверждения] {code}\n")
    except OSError:
        pass
    return code


def _save_remember(remember: bool, login_value: str) -> None:
    """«Запомнить меня»: запомнить/забыть логин для экрана входа."""
    from core.config import save_settings, SETTINGS as S
    if remember:
        S["remember_login"] = login_value
    else:
        S.pop("remember_login", None)
    save_settings()


class RegisterTeacherScreen(BaseScreen):
    first_name = ObjectProperty(None)
    last_name = ObjectProperty(None)
    password = ObjectProperty(None)
    password_repeat = ObjectProperty(None)

    def do_register(self):
        try:
            user = auth.register_teacher(
                self.first_name.text, self.last_name.text,
                self.password.text, self.password_repeat.text,
            )
        except auth.AuthError as exc:
            self.error(str(exc))
            return

        self.app.current_user = user
        self.info(f"Аккаунт создан. Ваш ID учителя: {user.public_id}", "Почти всё")
        self.app.go("teacher_proof")


class TeacherProofScreen(BaseScreen):
    mode = StringProperty("code")            # 'code' или 'screenshot'
    selected_file = StringProperty("")
    platform_spinner = ObjectProperty(None)
    code_field = ObjectProperty(None)

    def set_mode(self, mode: str):
        self.mode = mode

    def open_file_chooser(self):
        choose_file(self._on_file, "Скриншот личного кабинета")

    def _on_file(self, path: str):
        self.selected_file = path

    def do_submit(self):
        user = self.app.current_user
        if user is None:
            self.app.go("welcome")
            return

        platform = self.platform_spinner.text
        try:
            if self.mode == "code":
                status = teacher_proof.submit_code(user.id, platform, self.code_field.text)
            else:
                status = teacher_proof.submit_screenshot(user.id, platform, self.selected_file)
        except teacher_proof.ProofError as exc:
            self.error(str(exc))
            return

        self.app.refresh_user()
        if status == "approved":
            self.info("Статус учителя подтверждён")
        else:
            self.info("Заявка отправлена, ожидайте проверки администратором")
        self.app.go("verify")


class VerifyScreen(BaseScreen):
    channel = StringProperty("email")
    hint = StringProperty("")
    target_field = ObjectProperty(None)
    code_field = ObjectProperty(None)

    def set_channel(self, channel: str):
        self.channel = channel

    def send_code(self):
        user = self.app.current_user
        if user is None:
            self.app.go("welcome")
            return
        try:
            code = verification.create_code(user.id, self.channel, self.target_field.text)
        except verification.VerificationError as exc:
            self.error(str(exc))
            return

        if SETTINGS.get("dev_mode"):
            self.hint = (f"Учебный режим: код {code} "
                         f"(он также записан в data/outbox.log)")
        else:
            self.hint = "Код отправлен. Проверьте почту или сообщения."

    def confirm(self):
        user = self.app.current_user
        try:
            verification.check_code(user.id, self.code_field.text)
        except verification.VerificationError as exc:
            self.error(str(exc))
            return

        self.code_field.text = ""
        self.hint = ""
        self.app.refresh_user()
        user = self.app.current_user
        if user.is_teacher and not user.teacher_verified:
            self.info("Почта/телефон подтверждены. Остался статус учителя.")
            self.app.go("teacher_proof")
        else:
            self.info("Аккаунт подтверждён!")
            self.app.go("home")


# --------------------------------------------------------------------------- #
#  Главный экран, чат, настройки
# --------------------------------------------------------------------------- #

class HomeScreen(BaseScreen):
    display_name = StringProperty("")
    role_line = StringProperty("")
    public_id = StringProperty("")
    avatar = StringProperty("")
    search_field = ObjectProperty(None)
    contacts_box = ObjectProperty(None)

    def on_pre_enter(self, *args):
        self.refresh()

    def refresh(self):
        user = self.app.current_user
        if user is None:
            self.app.go("welcome")
            return

        self.display_name = user.display_name
        self.role_line = ("Учитель" if user.is_teacher else "Ученик") + \
                         (f" • {user.full_name}" if user.nickname else "")
        self.public_id = user.public_id
        self.avatar = user.avatar_path or sprite("default_avatar")

        avatar_widget = self.ids.get("my_avatar")
        if avatar_widget is not None:
            avatar_widget.set_user(user)

        self.contacts_box.clear_widgets()
        contacts = chat.list_contacts(user.id)
        if not contacts:
            label = Factory.MutedLabel(text="Пока нет чатов. Найдите человека по ID выше.")
            self.contacts_box.add_widget(label)
            return

        for contact in contacts:
            last = chat.last_message(user.id, contact.id)
            unread = chat.unread_count(user.id, contact.id)
            preview = last["body"] if last else "Нет сообщений"
            if len(preview) > 40:
                preview = preview[:40] + "..."
            caption = f"{contact.display_name}  ({contact.public_id})\n{preview}"
            if unread:
                caption += f"   • новых: {unread}"
            row = Factory.ContactRow(text=caption)
            row.bind(on_release=lambda _btn, c=contact: self.app.open_chat(c))
            self.contacts_box.add_widget(row)

    def do_search(self):
        user = self.app.current_user
        try:
            found = chat.add_contact(user.id, self.search_field.text)
        except chat.ChatError as exc:
            self.error(str(exc))
            return
        self.search_field.text = ""
        self.refresh()
        self.info(f"Добавлен: {found.display_name} ({found.public_id})")


class ChatScreen(BaseScreen):
    partner_title = StringProperty("")
    messages_box = ObjectProperty(None)
    scroller = ObjectProperty(None)
    message_field = ObjectProperty(None)
    partner = ObjectProperty(None, allownone=True)

    def on_pre_enter(self, *args):
        self.reload()

    def reload(self):
        user = self.app.current_user
        if user is None or self.partner is None:
            self.app.go("home")
            return

        self.partner_title = f"{self.partner.display_name} ({self.partner.public_id})"
        avatar = self.ids.get("partner_avatar")
        if avatar is not None:
            avatar.set_user(self.partner)
        chat.mark_read(user.id, self.partner.id)

        self.messages_box.clear_widgets()
        for message in chat.get_dialog(user.id, self.partner.id):
            mine = message["sender_id"] == user.id
            author = "Вы" if mine else self.partner.display_name
            bubble = Factory.MessageBubble(
                text=f"[b]{author}[/b]\n{message['body']}\n[size=11]{message['created_at']}[/size]",
                markup=True, mine=mine,
            )
            bubble.size_hint_x = 0.78
            bubble.pos_hint = {"right": 1} if mine else {"x": 0}
            self.messages_box.add_widget(bubble)

        Clock.schedule_once(lambda _dt: setattr(self.scroller, "scroll_y", 0), 0.05)

    def do_send(self):
        user = self.app.current_user
        text_to_send = self.message_field.text
        try:
            chat.send_message(user.id, self.partner.id, text_to_send)
        except chat.ChatError as exc:
            logs.warn("Сообщение не отправлено: %s", exc)
            self.error(str(exc))
            return
        logs.event("СООБЩЕНИЕ", от=user.display_name,
                   кому=self.partner.display_name, длина=len(text_to_send))
        self.message_field.text = ""
        self.reload()


class SettingsScreen(BaseScreen):
    is_teacher = BooleanProperty(False)
    avatar_hint = StringProperty("")
    nickname_field = ObjectProperty(None)
    status_field = ObjectProperty(None)
    password_field = ObjectProperty(None)
    password_repeat_field = ObjectProperty(None)
    _new_avatar = StringProperty("")

    def on_pre_enter(self, *args):
        user = self.app.current_user
        if user is None:
            self.app.go("welcome")
            return
        self.is_teacher = user.is_teacher
        self.nickname_field.text = user.nickname or ""
        self.status_field.text = user.status_text
        self.avatar_hint = user.avatar_path or "Аватар не выбран"

    def choose_avatar(self):
        choose_file(self._on_avatar, "Выберите аватар")

    def _on_avatar(self, path: str):
        self._new_avatar = path
        self.avatar_hint = path

    def save_profile(self):
        user = self.app.current_user
        try:
            auth.update_profile(
                user.id,
                nickname=None if user.is_teacher else self.nickname_field.text.strip(),
                avatar_path=self._new_avatar or None,
                status_text=self.status_field.text.strip(),
            )
        except auth.AuthError as exc:
            self.error(str(exc))
            return
        self.app.refresh_user()
        self.info("Профиль сохранён")

    def do_logout(self):
        """Выйти из аккаунта: забыть сессию и вернуться на стартовый экран."""
        self.app.logout()

    def save_password(self):
        user = self.app.current_user
        try:
            auth.change_password(user.id, self.password_field.text,
                                 self.password_repeat_field.text)
        except auth.AuthError as exc:
            self.error(str(exc))
            return
        self.password_field.text = ""
        self.password_repeat_field.text = ""
        logs.event("ПАРОЛЬ_СМЕНЁН", user=user.display_name)
        self.info("Пароль изменён")


class LogsScreen(BaseScreen):
    """Просмотр лога прямо в приложении.

    Лог пишется всегда в data/app.log, а на этом экране видно его хвост —
    удобно проверять, что приложение делало, не открывая файлы вручную.
    """

    log_text = StringProperty("")
    log_path = StringProperty("")

    def on_pre_enter(self, *args):
        self.reload_log()

    def reload_log(self, *_):
        self.log_text = logs.tail(200)
        self.log_path = logs.path()

    def open_logs_file(self):
        """Открыть папку с логом в проводнике — на ПК."""
        import subprocess
        import sys
        folder = os.path.dirname(logs.path())
        try:
            if sys.platform.startswith("win"):
                os.startfile(folder)               # noqa: S606 - папка из настроек
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])
        except Exception as exc:
            self.error("Не удалось открыть папку: %s" % exc)
