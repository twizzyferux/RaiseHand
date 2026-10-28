"""Экраны приложения (логика). Внешний вид описан в файлах ui/kv/*.kv.

Каждому классу-экрану соответствует одноимённое правило в .kv-файле:
    WelcomeScreen        -> ui/kv/welcome.kv
    RegStep1Screen..RegStep5Screen -> ui/kv/register.kv
    ... и так далее.
"""

from kivy.app import App
from kivy.clock import Clock
from kivy.factory import Factory
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp
from kivy.properties import (BooleanProperty, ListProperty, NumericProperty,
                             ObjectProperty, StringProperty)
from kivy.uix.floatlayout import FloatLayout

import os
import random

from core import auth, chat, countries, formatters, gradients, logs, session
from ui import anim, chats
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen

from core import teacher_proof, verification
from core.config import OUTBOX_PATH, SETTINGS, save_settings
from ui.dialogs import choose_file, show_message


class MessageBubble(Label):
    """Сообщение в чате. mine=True — сообщение написано вами.

    Сейчас свои и чужие сообщения выглядят одинаково — разный фон для них
    делается в ui/kv/chat.kv (см. DESIGN.md).
    """

    mine = BooleanProperty(False)


Factory.register("MessageBubble", cls=MessageBubble)


class PhoneStage(FloatLayout):
    """Сцена макета.

    Объявлена классом, а не только правилом в .kv, потому что размеры
    макета нужны как числа: на телефоне сцена растягивается по высоте
    экрана, и пересчёт идёт от размера макета. Если бы размеры
    хранились только в size, то масштаб с каждым кадром считался бы от
    уже изменённого размера и уезжал.
    """

    design_w = NumericProperty(450)
    design_h = NumericProperty(920)


# Сдвиг сцены влево от геометрического центра. Ноль - строго по центру.
#
# Величина ненулевая была поставлена по просьбе сдвинуть интерфейс
# чуть влево, но замер показал, что по центру он уже стоит: на iPhone
# 15 Pro Max кнопка попадала на 1dp левее центра экрана, декор был
# симметричен (поле 29dp с каждой стороны). Сдвиг только вносил
# неточность, поэтому убран.
SHIFT_LEFT_DP = 0


class BaseScreen(Screen):
    """Общий для всех экранов: фон, сцена по центру, появление лесенкой.

    INTRO - идентификаторы элементов, которые проявляются по очереди при
    входе на экран. Пустой список означает «без лесенки»: у экрана
    нет содержимого, которое имеет смысл показывать по одному.
    """

    INTRO = ()
    _intro_played = False
    """Общее для всех экранов: кремовый фон и удобства.

    ФОН
    ---
    Раньше фон рисовала только PhoneStage — обёртка экрана, которая есть
    не везде (в настройках, проверке и регистрации её нет). Экраны без
    неё оставались без фона, и сквозь них был виден чёрный цвет окна.
    Теперь фон рисует сам экран: так он есть везде и не зависит от того,
    обёрнут ли экран в сцену.

    Экраны со сценой дублировать фон не надо: он нарисован там же
    (theme.kv, PhoneStage) и лежит под содержимым экрана.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._stage_bound = None
        with self.canvas.before:
            Color(rgba=(1, 0.984, 0.969, 1))      # кремовый #FFFBF7
            self._screen_bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._sync_all, size=self._sync_all,
                  children=self._sync_all)

    def _sync_all(self, *_):
        self._sync_bg()
        self._pin_stage()

    def _pin_stage(self, *_):
        """Прижать сцену к верху; по ширине — ровно в экран.

        Масштаб по ширине: ширина сцены = ширина экрана, x ≈ 0,
        сдвиг вправо математически невозможен.

        Высота сцены на вытянутом iPhone чуть меньше экрана →
        top = parent.top, пустота ~55 pt уходит вниз.

        Подписка на size: пересчёт после реального dp(450)×dp(920).
        """
        for child in self.children:
            if child.__class__.__name__ != "PhoneStage":
                continue
            if self._stage_bound is not child:
                if self._stage_bound is not None:
                    try:
                        self._stage_bound.unbind(size=self._pin_stage)
                    except Exception:
                        pass
                child.bind(size=self._pin_stage)
                self._stage_bound = child
            child.pos_hint = {}
            new_x = self.x + (self.width - child.width) * 0.5 - dp(SHIFT_LEFT_DP)
            new_y = self.y + self.height - child.height
            if abs(child.x - new_x) > 0.5:
                child.x = new_x
            if abs(child.y - new_y) > 0.5:
                child.y = new_y
            return

    def _sync_bg(self, *_):
        self._screen_bg.pos = self.pos
        self._screen_bg.size = self.size

    def on_enter(self, *_):
        """Проявить содержимое экрана лесенкой.

        Появление повторяется только один раз за сеанс: при возврате
        «Назад» человек уже всё видел, и повторять показ незачем.
        """
        self._play_intro()

    def _play_intro(self):
        """Лесенка появления по списку INTRO."""
        if self._intro_played:
            return
        self._intro_played = True
        widgets = [self.ids.get(name) for name in self.INTRO]
        anim.stagger_in([w for w in widgets if w is not None],
                        start=0.06, step=0.035)

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
        self._intro_played = False      # анимация появления — раз за сеанс

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
        """Показать появление содержимого — только один раз за сеанс.

        При возврате «Назад» с регистрации экран открывается снова, но
        анимация повторяться не должна: человек уже всё видел.
        """
        if self._intro_played:
            return
        self._intro_played = True
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
    INTRO = ("login_field", "password_field", "remember_toggle")
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


class NameFieldsMixin:
    """Имя и фамилия без цифр.

    Поля чистятся прямо при вводе: цифра просто не появляется,
    и ничего исправлять вручную не нужно. Из .kv вызывается как
    ``on_text: root.format_name('first', self.text)``.
    """

    _NAME_IDS = {"first": "first_name", "last": "last_name"}

    def format_name(self, which: str, text: str) -> None:
        field = self.ids.get(self._NAME_IDS.get(which, ""))
        if field is None:
            return
        formatted = formatters.name_only(text)
        if formatted == text:
            return
        # поле перезаписываем целиком, поэтому курсор возвращаем на
        # прежнее место — иначе при правке в середине строки он бы
        # прыгнул в конец
        column, row = field.cursor
        field.text = formatted
        field.cursor = (min(column, len(formatted)), row)


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


class RegStep1Screen(NameFieldsMixin, BaseScreen):
    """Шаг 1 — «Как вас зовут?» (имя и фамилия)."""
    # Без лесенки: таблетки не проявляются при «Далее».
    INTRO = ()

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
    INTRO = ()

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
    INTRO = ()

    invite_code = ObjectProperty(None)
    # подсказки городов под полем ввода
    city_suggestions = ListProperty([])

    def format_invite(self, text):
        """Код приглашения: как набирают + тире после 3-го символа.

        Пришлось текст поправить — ставим обратно; повторный вызов уже
        ничего не меняет, поэтому рекурсии не будет.
        """
        formatted = formatters.invite_format(text)
        if formatted != text:
            self.invite_code.text = formatted

    # -- подсказки городов -------------------------------------------------- #

    def _city_field(self):
        """Поле города — по id, а не через self.city.

        В .kv у экрана написано `city: city`, и это имя перехватывается
        виджетами-строками подсказок. Поэтому в Python обращаемся
        к полю только через ids — так однозначно.
        """
        return self.ids.get("city")

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
        field = self._city_field()
        if field is None:
            return
        field.text = name
        field.cursor = (len(name), 0)      # курсор в конец, как при вводе
        self.city_suggestions = []
        self._rebuild_city_box()

    def _rebuild_city_box(self):
        box = self.ids.get("city_box")
        if box is None:
            return
        box.clear_widgets()
        for name in self.city_suggestions:
            row = Factory.CityRow(text=name)
            # Через bind, а не kwarg on_release: обработчик,
            # заданный kwarg, получает первым аргументом сам
            # виджет-строку, и город в него не попадал.
            row.bind(on_release=self._make_pick_handler(name))
            box.add_widget(row)

    def _make_pick_handler(self, name):
        """Обработчик нажатия на строку с городом `name`."""
        def handler(_widget, *_args):
            self.pick_city(name)
        return handler

    # -- переход дальше ---------------------------------------------------- #

    def next(self):
        field = self._city_field()
        city = (field.text if field is not None else "").strip()
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
        clear_if_fresh(self, self._city_field(), self.invite_code)


class RegStep4Screen(BaseScreen):
    """Шаг 4 — «Подтверждение» (почта/телефон + код)."""
    INTRO = ()

    contact = ObjectProperty(None)
    code_field = ObjectProperty(None)
    # подсказка со странами появляется, когда набирают номер
    show_countries = ListProperty([])

    def on_contact_typed(self, text):
        """Появилась подсказка стран, если набирают номер.

        Поле не форматируем: в адресе почты регистр важен, а тире
        внутри адреса его ломает.
        """
        if countries.looks_like_phone(text):
            self.show_countries = list(countries.COUNTRIES[:4])
        else:
            self.show_countries = []
        self._rebuild_countries()

    def pick_country(self, country):
        """Страна выбрана — подставляем её код в поле."""
        field = self._contact_field()
        if field is None:
            return
        field.text = country.dial + " "
        field.cursor = (len(field.text), 0)
        self.show_countries = []
        self._rebuild_countries()

    def _contact_field(self):
        """Поле контакта — по id, чтобы не путать со свойством экрана."""
        return self.ids.get("contact")

    def _rebuild_countries(self):
        """Пересобрать чипы стран (список короткий, делаем целиком)."""
        row = self.ids.get("country_box")
        if row is None:
            return
        row.clear_widgets()
        for country in self.show_countries:
            chip = Factory.CountryChip(text=country.label)
            chip.bind(on_release=self._make_country_handler(country))
            row.add_widget(chip)

    def _make_country_handler(self, country):
        def handler(_widget, *_args):
            self.pick_country(country)
        return handler

    def format_code(self, text):
        """Код подтверждения: заглавные буквы, без разделителей."""
        formatted = formatters.code_format(text)
        if formatted != text:
            self.code_field.text = formatted

    def send_code(self):
        field = self._contact_field()
        value = (field.text if field is not None else "").strip()
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
        entered = formatters.code_format(self.code_field.text)
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
    INTRO = ()

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
    length = SETTINGS.get("rules", {}).get("code_length", 6)
    code = "".join(str(random.randint(0, 9)) for _ in range(length))
    try:
        with open(OUTBOX_PATH, "a", encoding="utf-8") as f:
            f.write(f"[код подтверждения] {code}\n")
    except OSError:
        pass
    return code


def _save_remember(remember: bool, login_value: str) -> None:
    """«Запомнить меня»: запомнить/забыть логин для экрана входа."""
    if remember:
        SETTINGS["remember_login"] = login_value
    else:
        SETTINGS.pop("remember_login", None)
    save_settings()


class RegisterTeacherScreen(NameFieldsMixin, BaseScreen):
    INTRO = ("first_name", "last_name", "password", "password_repeat")
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
    INTRO = ("platform_spinner", "code_field")
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
    INTRO = ("target_field", "code_field")
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
    """Главный экран по макету «основной экран чаты».

    Три вкладки (Поиск / Чаты / Группы) живут на одном экране: в макете
    нарисован только активный пункт, поэтому переключение — мягкая
    смена прозрачности, без перезагрузки экрана.
    """
    INTRO = ("tab_title", "chats_scroll", "search_pane", "groups_pane", "fab")

    TAB_TITLES = {"search": "Поиск", "chats": "Чаты", "groups": "Группы"}

    tab = StringProperty("chats")
    search_field = ObjectProperty(None)
    chats_box = ObjectProperty(None)
    group_box = ObjectProperty(None)
    class_code = ObjectProperty(None)

    # -- вход на экран ------------------------------------------------------- #

    def on_pre_enter(self, *args):
        self._nav_ready = False
        self._setup_nav()
        self.refresh()
        self._setup_glass()
        self._paint_tabs(self.tab, animate=False)

    def on_leave(self, *args):
        """Уходя с экрана, прячем стекло.

        Плагин размывает «то, что позади», и рисует результат сам. Когда
        экран уходит в настройки, панель оставалась висеть поверх них —
        это и было раздваивание на секунду. Прячем её здесь, а вернём
        в _setup_glass() при следующем входе.
        """
        from ui.glass_widget import set_visible

        for name in ("navbar", "fab"):
            widget = self.ids.get(name)
            if widget is not None:
                set_visible(widget, False)

    def _setup_glass(self):
        """Сказать стеклу, что размывать, и показать его.

        Плагину frostedglass нужно знать, что лежит ПОД ним: без этого он
        показывает только шум и выглядит серым прямоугольником. Под панелью
        и кнопкой «+» лежит отдельный тефон размытия (blur_source) — в
        нём только кремовая заливка. Если размывать canvas сцены, плагин
        захватит ещё и иконки панели, и они выйдут раздвоенными.
        """
        from ui.glass_widget import (apply_accessibility, attach_background,
                                     set_visible)

        source = self.ids.get("blur_source")
        if source is None:
            return
        surfaces = []
        for name in ("navbar", "fab"):
            widget = self.ids.get(name)
            if widget is not None:
                set_visible(widget, True)
                attach_background(widget, source)
                surfaces.append(widget)
        apply_accessibility(surfaces)
        # Галочка в настройках должна показывать текущее состояние.
        settings_screen = self.app.manager.get_screen("settings")
        row = getattr(settings_screen, "ids", {}).get("solid_glass")
        if row is not None:
            from ui.glass_widget import reduced_transparency
            row.ids["box"].state = "down" if reduced_transparency() else "normal"

    def refresh(self):
        user = self.app.current_user
        if user is None:
            self.app.go("welcome")
            return

        self.chats_box.clear_widgets()

        # chat_list уже отдаёт закреплённые сверху, остальные — по свежести.
        # Ряд рисует себя сам (ui/chats.py), поэтому позиции ставлю явно:
        # в Kivy содержимое контейнера не смещается вместе с контейнером.
        items = chat.chat_list(user.id)
        if not items:
            self.chats_box.add_widget(
                Factory.ChatEmpty(text="Пока нет чатов. Найдите человека по ID "
                                      "или нажмите «+»."))
            self.chats_box.height = dp(chats.ROW_H)
            self.refresh_groups()
            return

        for index, item in enumerate(items):
            row = self._make_row(item)
            self.chats_box.add_widget(row)
            row.pos = (dp(0), dp(chats.ROW_H) * (len(items) - index - 1))
        self.chats_box.height = dp(chats.ROW_H * len(items))

        self.refresh_groups()

    def _make_row(self, item: dict):
        """Один ряд списка: аватар, имя, превью, время, значки."""
        person = item["user"]
        row = Factory.ChatRow(
            peer_name=person.display_name,
            preview=item["preview"] or "Нет сообщений",
            stamp=item["time"],
            initials=gradients.initials_for(person.first_name, person.last_name),
            avatar_source=person.avatar_path or gradients.avatar_path(
                person.public_id or str(person.id)),
            unread=item["unread"],
            pinned=item["pinned"],
            mine=item["mine"],
            read=item["read"],
        )
        row.on_release = lambda person=person: self.app.open_chat(person)
        return row

    # -- вкладки ------------------------------------------------------------- #

    def switch_tab(self, name: str):
        if name not in self.TAB_TITLES:
            return
        self._paint_tabs(name)

    def new_chat(self):
        """Кнопка «+» в шапке — новый чат, то есть поиск человека."""
        self.switch_tab("search")

    def _pane(self, name):
        return self.ids[{"search": "search_pane", "chats": "chats_scroll",
                         "groups": "groups_pane"}[name]]

    def _paint_tabs(self, current: str, animate: bool = True):
        """Показать нужную вкладку, спрятать остальные (мягко).

        Кнопка «+» в шапке есть только у вкладки «Чаты» — в макете она
        нарисована вместе с ней, и на «Поиске»/«Группы» она бы вводила в
        заблуждение (там и так поле для ввода).
        """
        self.tab = current
        self.ids["tab_title"].text = self.TAB_TITLES[current]
        self.ids["fab"].opacity = 1 if current == "chats" else 0
        self.ids["fab"].disabled = current != "chats"
        for name in self.TAB_TITLES:
            pane = self._pane(name)
            target = 1 if name == current else 0
            pane.disabled = name != current
            if animate and hasattr(self, "_nav_ready"):
                anim.fade_to(pane, "opacity", target, duration=0.2)
            else:
                # Прозрачность ставим напрямую — но сначала гасим
                # анимацию, которая ещё не доиграла. Иначе она допишет
                # своё старое значение уже после того, как мы вернулись
                # на экран, и откроет чужую панель: нажали вкладку, не
                # дождались, ушли в настройки и обратно — а видим не ту.
                # Отсюда и «рандомно»: анимация длится 0.2 с, переход
                # между экранами 0.24 с, и исход зависит от того, кто
                # успел раньше.
                anim.cancel(pane, "opacity")
                pane.opacity = target
        for name, key in (("nav_search", "search"), ("nav_chats", "chats"),
                          ("nav_groups", "groups"), ("nav_settings", None)):
            self.ids[name].active = (key == current)
        self._nav_ready = True

    def _setup_nav(self):
        """Иконки нижней панели: размеры и смещения — из макета.

        В макете у каждой вкладки своя иконка и своё место: «Поиск» 23x23
        в (65.1, 64.2), «Чаты» 38x38 в (153.3, 53.7), «Группы» 44x44
        в (249.3, 50.5), «Настройки» 34x34 в (355.1, 55.8). Переведено
        в сцену приложения.

        Все четыре иконки — из векторного кита, рендером в 512x512
        (tools/nav_icons.py). Лупа раньше рисовалась линиями: обводка
        выходила грубой и рядом с картинками из кита она выглядела
        чужой. Пропорции у неё и нарисованной совпадали, так что смена
        на картинку рисунок не изменила — только стала резкой.

        Размер и положение лупы посчитаны инструментом: чернила в
        PNG занимают не весь холст, а в макете иконка стоит по своим
        координатам, поэтому инструмент печатает и размер, и угол.
        """
        places = {
            "nav_search": (35.3, 58.9, 58.2, 78.0),
            "nav_chats": (41.9, 153.3, 53.7, 173.0),
            "nav_groups": (48.5, 249.3, 50.5, 272.0),
            "nav_settings": (37.5, 355.1, 55.8, 372.5),
        }
        for name, (size, x, y, caption_x) in places.items():
            item = self.ids[name]
            item.icon_size = size
            item.icon_x = x
            item.icon_y = y
            item.caption_x = caption_x
            item.glass = self.ids["navbar"]
            stem = name.replace("nav_", "")
            item.set_icon(self.app.sprite("nav_%s_black" % stem),
                          self.app.sprite("nav_%s_violet" % stem))
        self.ids["nav_search"].caption = "Поиск"     # подпись x 58..98
        self.ids["nav_chats"].caption = "Чаты"
        self.ids["nav_groups"].caption = "Группы"
        self.ids["nav_settings"].caption = "Настройки"

    # -- поиск --------------------------------------------------------------- #

    def do_search(self):
        user = self.app.current_user
        value = self.search_field.text
        try:
            found = chat.add_contact(user.id, value)
        except chat.ChatError as exc:
            self.error(str(exc))
            return
        self.search_field.text = ""
        self.refresh()
        self.ids["search_hint"].text = "Добавлен: %s (%s)" % (
            found.display_name, found.public_id)
        self.info(f"Добавлен: {found.display_name} ({found.public_id})")

    # -- группы -------------------------------------------------------------- #

    def format_class_code(self, text):
        """Код класса — как код приглашения: тире само, регистр как набирают."""
        formatted = formatters.invite_format(text)
        if formatted != text:
            self.class_code.text = formatted

    def join_class(self):
        user = self.app.current_user
        try:
            name = chat.join_class(user.id, self.class_code.text)
        except auth.AuthError as exc:
            self.error(str(exc))
            return
        self.class_code.text = ""
        self.app.refresh_user()
        self.refresh_groups()
        self.info(f"Вы присоединились к классу {name}")

    def refresh_groups(self):
        box = self.group_box
        if box is None:
            return
        box.clear_widgets()
        user = self.app.current_user
        my_class = (user.class_name if user else "") or ""
        for item in chat.list_classes():
            label = Factory.ClassRow(
                text="%s · %s\nкод %s" % (item["class_name"],
                                          item["school_name"] or "школа не указана",
                                          item["invite_code"]))
            label.color = (0, 0, 0, 1) if item["class_name"] == my_class \
                else (0.4, 0.4, 0.4, 1)
            box.add_widget(label)


class ChatScreen(BaseScreen):
    INTRO = ("scroller", "messages_box", "message_field")
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
    INTRO = ("solid_glass", "nickname_field", "status_field")
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
        self.nickname_field.text = user.nickname or ""
        self.status_field.text = user.status_text
        self.avatar_hint = user.avatar_path or "Аватар не выбран"

        # Привязка галочки «Меньше прозрачности» — один раз за жизнь экрана.
        row = self.ids.get("solid_glass")
        if row is not None and not getattr(row, "_bound", False):
            row._bound = True
            row.ids["box"].fbind("state",
                                 lambda *a: self.toggle_solid_glass())

    def choose_avatar(self):
        choose_file(self._on_avatar, "Выберите аватар")

    def toggle_solid_glass(self):
        """«Меньше прозрачности» — как системная настройка в iOS.

        Галочка лежит в строке рядом с подписью, поэтому берём её из
        самой строки, а не запоминаем состояние в поле экрана: иначе
        после перезапуска приложения переключатель врал бы.
        """
        from core.config import SETTINGS, save_settings
        from ui.glass_widget import apply_accessibility

        row = self.ids.get("solid_glass")
        if row is None:
            return
        checked = row.ids["box"].state == "down"
        SETTINGS.setdefault("glass", {})["reduced_transparency"] = checked
        save_settings()
        home = self.app.manager.get_screen("home")
        apply_accessibility([home.ids.get("navbar"), home.ids.get("fab")])

    def _on_avatar(self, path: str):
        self._new_avatar = path
        self.avatar_hint = path

    def save_profile(self):
        user = self.app.current_user
        # ник можно поменять и учителю; пустое поле — значит убрать ник
        nickname = self.nickname_field.text.strip()
        try:
            auth.update_profile(
                user.id,
                nickname=nickname,
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
    INTRO = ("log_scroll",)

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
