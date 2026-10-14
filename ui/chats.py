# -*- coding: utf-8 -*-
"""Экран чатов по макету «проект/проект экран/основной экран чаты».

Источник истины — полный экран Face ID.svg (холст 408x874). Отдельные
вырезки из него («основной интерфейс», «чаты (закреп)», «чаты (не
закреп)», «панель управления») идут с обрезкой — 404 вместо 408 по
ширине и с подрезанным верхом, из-за чего координаты в них разошлись с
полным макетом и экран «съезжал». Все числа ниже посчитаны по полному
макету и переведены в сцену приложения (450x920):

    x_сцены = x_макета * 450 / 408
    y_сцены = (874 - y_макета) * 920 / 874

Кегли подобраны не «на глаз», а по фактическим размерам букв в макете:
_measure_mock.py рендерит эталон, снимает габариты чернил и подбирает
кегль, при котором тот же текст тем же шрифтом совпадает по ширине и
высоте. Пересчитать всё: .venv312\\Scripts\\python.exe _measure_mock.py

Позиции значков и разделителей пересчитываются из координат макета же:
_offset-инструменты того же набора (_offsets.py, _values.py).

Геометрия ряда, шапки и панели живёт здесь, а не в .kv, потому что ряд
рисуется целиком в своём canvas (см. ниже).

ПОЧЕМУ РЯД РИСУЕТСЯ САМ, А НЕ ЧЕРЕЗ ДЕТЕЙ-WIDGETОВ
-------------------------------------------------
В этой версии Kivy содержимое виджета не смещается вместе с ним: если
родитель стоит на (0, 100), а ребёнок на (0, 0), ребёнок всё равно
рисуется на нуле — проверено отдельным опытом: квадрат внутри
сдвинутого на 100 контейнера остался внизу окна. Поэтому все экраны
этого приложения держат координаты абсолютными, а у ряда чата в
разметке вообще нет вложенных виджетов: аватар, тексты, галочки и
значки — это инструкции canvas плюс текстуры шрифта (core.text). Такой
ряд скроллится вместе со списком как обычно.
"""
import os

from kivy.core.text import Label as CoreLabel
from kivy.factory import Factory
from kivy.graphics import Color, Line, Rectangle, RoundedRectangle
from kivy.metrics import dp
from kivy.properties import (BooleanProperty, ListProperty, NumericProperty,
                             ObjectProperty, StringProperty)
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget

from ui.anim import PressButton

MOCK_W, MOCK_H = 408.0, 874.0          # холст макета (Face ID.svg)
STAGE_W, STAGE_H = 450.0, 920.0        # холст сцены приложения

# --- цвета макета ----------------------------------------------------------- #
VIOLET = "#4B2FE0"                     # кнопка «+» и активная вкладка
PINK = "#F0447C"                       # счётчик новых сообщений
GREY_TEXT = "#474747"                  # превью прочитанного чата
DARK_TEXT = "#272727"                  # превью непрочитанного
LINE_GREY = "#C5C5C5"                  # разделитель ряда
TINT = "#F3F1FF"                       # подложка закреплённых чатов
CREAM = "#FFFBF7"                      # фон экрана

# --- нижняя панель ---------------------------------------------------------- #
# Плашка в макете: 360x60 в (24, 780) -> в сцене x 26.5, y 35.8,
# размер 397.1 x 63.2, радиус 31.6.
PANEL = (26.5, 35.8, 397.1, 63.2)
PANEL_RADIUS = 31.6
# Подписи панели: кегль один на все четыре — в макете так же.
# «Поиск» -> 40, «Чаты» -> 32, «Группы» -> 49, «Настройки» -> 69
# (макетные ширины 40, 32, 48, 67).
CAPTION_BASE = 42.0
CAPTION_SIZE = 13.0

# --- геометрия ряда ---------------------------------------------------------- #
# Все значения — из Face ID.svg (408x874), переведены в сцену 450x920.
# Координаты считаются ОТ НИЗА РЯДА: так список скроллится и не зависит
# от того, какой ряд первый. В скобках — координаты макета.
# Пересчитать: .venv312\\Scripts\\python.exe _measure_mock.py
ROW_H = 88.4                           # шаг ряда (макет 84 -> 88.4)
ROW_W = 450
AVATAR_SIZE = (75.0, 71.6)             # макет 68x68 -> 75.0 x 71.6
AVATAR_POS = (13.2, 9.0)               # макет 12, 246 (низ аватара)
# Инициалы стоят по центру аватара: центр букв в макете (41.7, 207.6),
# в сцене (46.0, 698.0) — на 4.7 левее центра аватара, ровно как в макете.
INITIALS_CENTER = (46.0, 698.0)
# Базовые линии текстов ряда 1 (макет 196.21 / 229.97 / 195.27), переведённые
# в сцену и отсчитанные от низа ряда (652.1):
NAME_BASELINE = 61.4
PREVIEW_BASELINE = 25.8
TIME_BASELINE = 62.4
NAME_LEFT = 100.0                      # макет 91.2 (измерено по чернилам)
PREVIEW_LEFT = 102.0                   # макет 92.6
TIME_RIGHT = 424.0                     # макет 385.8 (правый край времени)
DIVIDER_LEFT = 94.9                    # макет 86
# Значки. Галочки в макете стоят на одной линии со ВРЕМЕНем, слева от
# него (серые 28x20 в x 315, фиолетовые 34x25 в x 309), а не под
# текстом превью.
PIN_POS, PIN_SIZE = (404.8, 19.5), (33.1, 31.6)          # макет 367,206
BADGE_POS, BADGE_SIZE = (407.0, 20.5), (27.6, 26.3)      # макет 369,294
TICK_POS, TICK_SIZE = (347.4, 56.3), (30.9, 21.0)        # макет 315,347
TICK_BIG_POS, TICK_BIG_SIZE = (340.8, 55.3), (37.5, 26.3)  # макет 309,429
BADGE_SIZE_WIDE = 32.0                  # счётчик от двух цифр (макет 29)
# Кегли подобраны по ширине текста тем же шрифтом, каким он рисуется в
# приложении (_probe_type.py — по текстурам Kivy, не по PIL: у PIL и Kivy
# разная метрика, и кегль из PIL в приложении даёт текст уже макетного).
NAME_SIZE = 21.0                       # «Иван Иванов» -> 136 при макетных 137
PREVIEW_SIZE = 17.0                     # «Hello, Vinograd!» -> 125 при 129
TIME_SIZE = 16.0                        # «19:36» -> 41 при 43
INITIALS_SIZE = 23.0                    # «ИИ» -> 34 при макетных 34
BADGE_TEXT_SIZE = 16

# Доля высоты текстуры, приходящаяся на нижний выносной элемент: текст
# ставим по базовой линии, а текстура включает и выносные.
# У SF Pro Text выносной элемент — примерно 0.21 кегля, а текстура при
# кегле 21 выше 26, то есть доля 0.17. При 0.24 весь текст садился ниже
# макета на 3..4 пикселя.
DESCENT = 0.17

FONT_NAME = "SFPro"


def hex_rgba(color: str, alpha: float = 1.0):
    """'#RRGGBB' -> (r, g, b, alpha) долями — для canvas."""
    color = color.lstrip("#")
    red, green, blue = (int(color[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    return red, green, blue, alpha


ICON_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "assets", "images", "chats")
_icon_cache = {}
# Текстуры текста: ключ -> текстура. Инициалы и подписи в списке чатов
# повторяются на каждом ряду, без кэша список заметно подтормаживает.
_TEXT_CACHE = {}


def _icon_texture(source: str):
    """Текстура иконки из assets/images/chats (с кэшем: перерисовка частая).

    ФИЛЬТР — не украшение, а условие резкости
    -----------------------------------------
    Иконки в файлах крупные (150..194 пикселя), а на экране занимают
    около 50: их приходится уменьшать втрое. При соседней выборке
    (NEAREST) такое уменьшение выглядит как лесенка — иконки «пикселятся»,
    хотя сами файлы качественные. Линейная выборка с мип-уровнями
    усредняет соседние пиксели и даёт гладкий край.

    Ставить фильтры надо ЯВНО: CoreImage(path, mipmap=True) просит
    мип-уровни, но сам проставляет min_filter и mag_filter в None — а
    при None мип-уровни не используются, и всё остаётся как было.
    """
    if not source:
        return None
    path = os.path.join(ICON_DIR, os.path.basename(source))
    if not os.path.exists(path):
        return None
    if path not in _icon_cache:
        from kivy.core.image import Image as CoreImage
        texture = CoreImage(path, mipmap=True).texture
        # mipmap у текстуры только для чтения — мип-уровни уже собраны
        # самим CoreImage. Задаём, какими выборками к ним идти.
        texture.min_filter = "linear_mipmap_linear"
        texture.mag_filter = "linear"
        texture.wrap = "clamp_to_edge"
        _icon_cache[path] = texture
    return _icon_cache[path]


def mock_x(value: float) -> float:
    """Координата макета по горизонтали -> координата сцены."""
    return value * STAGE_W / MOCK_W


def mock_y(value: float) -> float:
    """Координата макета по вертикали -> координата сцены."""
    return value * STAGE_H / MOCK_H


class ChatRow(Widget):
    """Один чат в списке: аватар, имя, последнее сообщение, время, значки.

    Всё содержимое — инструкции canvas: так ряд не зависит от того,
    как Kivy складывает координаты вложенных виджетов, и одинаково
    выглядит в списке, в поиске и в чате.
    """

    peer_name = StringProperty("")
    preview = StringProperty("")
    stamp = StringProperty("")
    initials = StringProperty("")
    avatar_source = StringProperty("")
    unread = NumericProperty(0)
    pinned = BooleanProperty(False)
    mine = BooleanProperty(False)
    read = BooleanProperty(False)
    press_tint = NumericProperty(0.0)

    on_release = ObjectProperty(None, allownone=True)   # кем открывать чат

    # Что делать при нажатии: приходит снаружи (ui/screens.py), потому что
    # событие on_release тут же переопределено под касание.
    __events__ = ("on_release",)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (dp(ROW_W), dp(ROW_H))
        self._texts = []          # core-подписи живут, пока живёт ряд
        self._texture_updates = []
        self._touch_pressed = False   # нажали на ряд (без grab, см. on_touch_down)
        for source in ("status_pin", "status_sent", "status_read"):
            pass                    # текстуры подтягиваются в _redraw
        self.bind(pos=self._redraw, size=self._redraw,
                  peer_name=self._redraw, preview=self._redraw,
                  stamp=self._redraw, unread=self._redraw,
                  pinned=self._redraw, mine=self._redraw, read=self._redraw,
                  initials=self._redraw, avatar_source=self._redraw,
                  press_tint=self._redraw)

    # -- текст в canvas ------------------------------------------------------ #

    def _texture(self, text, font_size, color, bold=False, align="left"):
        """Текстура строки текста: та же логика, что у Label, но в canvas.

        Текстура рисуется белым, а цвет задаёт Color при отрисовке: иначе
        серый текст темнел бы вдвое (#474747 поверх белой текстуры даёт
        #232323).

        Текстуры кэшируются по (текст, кегль, жирность, выравнивание):
        при прокрутке списка один и тот же ряд перерисовывается десятки
        раз, и без кэша это самый дорогой вызов на экране.
        """
        if not text:
            return None, 0
        key = (text, round(font_size, 1), bold, align)
        texture = _TEXT_CACHE.get(key)
        if texture is None:
            label = CoreLabel(text=text, font_size=font_size,
                              font_name=FONT_NAME, color=(1, 1, 1, 1),
                              bold=bold, halign=align, anchor_x=align,
                              anchor_y="baseline")
            label.refresh()
            _TEXT_CACHE[key] = label.texture
            texture = label.texture
        return texture, texture.height

    # -- рисование ----------------------------------------------------------- #

    def _redraw(self, *_):
        self.canvas.clear()
        self._texts = []
        left, bottom = self.x, self.y
        if not self.width:
            return

        with self.canvas:
            # Подложка закреплённых (#F3F1FF 50%) — в макете она ровно в
            # высоту верхних рядов, поэтому красится здесь.
            if self.pinned:
                Color(rgba=hex_rgba(TINT, 0.5))
                Rectangle(pos=self.pos, size=self.size)

            # Лёгкая подсветка нажатия — как в Телеграме
            if self.press_tint:
                Color(rgba=(0, 0, 0, 0.05 * self.press_tint))
                Rectangle(pos=self.pos, size=self.size)

            # Аватар: круг с личным градиентом, поверх инициалы
            avatar_w, avatar_h = dp(AVATAR_SIZE[0]), dp(AVATAR_SIZE[1])
            avatar_x = left + dp(AVATAR_POS[0])
            avatar_y = bottom + dp(AVATAR_POS[1])
            if self.avatar_source:
                Color(rgba=(1, 1, 1, 1))
                Rectangle(source=self.avatar_source,
                          pos=(avatar_x, avatar_y),
                          size=(avatar_w, avatar_h))
            if self.initials:
                texture, height = self._texture(self.initials,
                                                dp(INITIALS_SIZE),
                                                "#FDFCFF", bold=False,
                                                align="center")
                if texture is not None:
                    # Центр инициалов — точка из макета, а не середина
                    # текстуры: в макете буквы сбиты чуть влево.
                    Color(rgba=hex_rgba("#FDFCFF"))
                    Rectangle(
                        texture=texture,
                        pos=(left + dp(INITIALS_CENTER[0]) - texture.width / 2,
                             bottom + dp(INITIALS_CENTER[1])
                             - height * DESCENT),
                        size=texture.size)

            # Имя — чёрным, как в макете
            texture, height = self._texture(self.peer_name, dp(NAME_SIZE),
                                            "#000000", bold=True)
            if texture is not None:
                Color(rgba=(0, 0, 0, 1))
                Rectangle(texture=texture,
                          pos=(left + dp(NAME_LEFT),
                               bottom + dp(NAME_BASELINE) - height * DESCENT),
                          size=texture.size)

            # Время — по правому краю
            stamp_texture, stamp_height = self._texture(
                self.stamp, dp(TIME_SIZE), "#000000", align="right")
            if stamp_texture is not None:
                Color(rgba=(0, 0, 0, 1))
                Rectangle(texture=stamp_texture,
                          pos=(left + dp(TIME_RIGHT) - stamp_texture.width,
                               bottom + dp(TIME_BASELINE)
                               - stamp_height * DESCENT),
                          size=stamp_texture.size)

            # Превью: у непрочитанного чата текст темнее (макет)
            tone = DARK_TEXT if self.unread else GREY_TEXT
            texture, height = self._texture(self.preview, dp(PREVIEW_SIZE), tone)
            if texture is not None:
                Color(rgba=hex_rgba(tone))
                Rectangle(texture=texture,
                          pos=(left + dp(PREVIEW_LEFT),
                               bottom + dp(PREVIEW_BASELINE) - height * DESCENT),
                          size=texture.size)

            # Галочка статуса своего сообщения: на линии со временем, слева
            # от него — серым «отправлено» (28x20), фиолетовым «прочитано»
            # (34x25). Ровно так в макете.
            if self.mine and not self.unread:
                if self.read:
                    self._icon("status_read.png", left + dp(TICK_BIG_POS[0]),
                               bottom + dp(TICK_BIG_POS[1]), TICK_BIG_SIZE)
                else:
                    self._icon("status_sent.png", left + dp(TICK_POS[0]),
                               bottom + dp(TICK_POS[1]), TICK_SIZE)

            # Закрепление
            if self.pinned:
                self._icon("status_pin.png", left + dp(PIN_POS[0]),
                           bottom + dp(PIN_POS[1]), PIN_SIZE)

            # Счётчик новых: круг на одну цифру, овал на две
            if self.unread:
                self._badge(left, bottom)

            # Разделитель #C5C5C5 — от края аватара до правого края
            Color(rgba=hex_rgba(LINE_GREY))
            Line(points=[left + dp(DIVIDER_LEFT), bottom, left + self.width, bottom],
                 width=dp(1))

    def _icon(self, name, x, y, size):
        """Значок из assets/images/chats как текстура в canvas."""
        texture = _icon_texture(name)
        if texture is None:
            return
        Color(rgba=(1, 1, 1, 1))
        Rectangle(texture=texture, pos=(x, y), size=size)

    def _badge(self, left, bottom):
        """Плашка со счётчиком новых сообщений.

        В макете 25x25 на одну цифру (макет 369,294) и 29x25 на две
        (макет 365,630) — ширина растёт вместе с числом знаков, высота
        остаётся. Правый край плашки в макете один и тот же: 434.5 в
        сцене (макет 394) — и у короткой, и у длинной.
        """
        digits = "99+" if self.unread >= 100 else str(int(self.unread))
        texture, height = self._texture(digits, dp(BADGE_TEXT_SIZE), "#FFFFFF",
                                        bold=True, align="center")
        text_w = texture.width if texture else dp(BADGE_SIZE[0])
        width = text_w + dp(BADGE_SIZE[0]) / 3      # запас по бокам
        height_badge = dp(BADGE_SIZE[1])
        # правый край плашки — 434.5 в сцене, как в макете
        x = left + dp(BADGE_POS[0]) + dp(BADGE_SIZE[0]) - width
        y = bottom + dp(BADGE_POS[1])
        Color(rgba=hex_rgba(PINK))
        RoundedRectangle(pos=(x, y), size=(width, height_badge),
                         radius=[height_badge / 2, ])
        if texture is not None:
            Color(rgba=hex_rgba("#FFFFFF"))
            Rectangle(texture=texture,
                      pos=(x + (width - texture.width) / 2,
                           y + (height_badge - height) / 2),
                      size=texture.size)

    # -- нажатие ------------------------------------------------------------- #

    def on_touch_down(self, touch):
        """Запоминаем нажатие на ряду.

        Без touch.grab(self) и проверки grab_current: касание перехватывает
        ScrollView (он забирает его раньше списка), и grab_current достаётся
        ему, а не ряду — тогда ряд не открывался бы никогда.
        """
        if not self.collide_point(*touch.pos):
            return False
        from ui.anim import Animation
        self._touch_pressed = True
        Animation.cancel_all(self, "press_tint")
        Animation(press_tint=1.0, d=0.07, t="out_quad").start(self)
        return True

    def on_touch_up(self, touch):
        from ui.anim import Animation
        Animation.cancel_all(self, "press_tint")
        Animation(press_tint=0.0, d=0.26, t="out_back").start(self)
        if not self._touch_pressed:
            return False
        self._touch_pressed = False
        # Отпустили прямо над рядом — открываем чат.
        if self.collide_point(*touch.pos) and self.on_release is not None:
            self.on_release()
        return True


Factory.register("ChatRow", cls=ChatRow)


class ChatList(ScrollView):
    """Прокручиваемый список чатов.

    Обычный ScrollView перехватывает касание для прокрутки и до детей
    оно не доходит: ряд чата не получал ни нажатия, ни отпускания, и
    чат не открывался. Поэтому сначала касание отдаётся рядам, а если
    палец повёл — списку (тогда это прокрутка, а не нажатие).
    """

    DRAG_THRESHOLD = 10.0      # пикселей окна, с которых считаем перетаскивание

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._row_press = None

    def on_touch_down(self, touch):
        self._row_press = None
        for child in self.children:
            if child.dispatch('on_touch_down', touch):
                self._row_press = touch
                return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if self._row_press is touch:
            moved = abs(touch.x - touch.ox) + abs(touch.y - touch.oy)
            if moved < self.DRAG_THRESHOLD:
                return True
            # Палец повёл — это прокрутка. Отпускаем ряд и отдаём
            # касание списку.
            self._row_press = None
            for child in self.children:
                child.dispatch('on_touch_up', touch)
            ScrollView.on_touch_down(self, touch)
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if self._row_press is touch:
            self._row_press = None
            for child in self.children:
                if child.dispatch('on_touch_up', touch):
                    return True
            return True
        return super().on_touch_up(touch)


Factory.register("ChatList", cls=ChatList)


class ChatPane(Widget):
    """Полноэкранная панель одной вкладки (Поиск, Группы).

    Панели занимают весь экран и лежат ПОВЕРХ списка чатов, поэтому
    скрытая панель не должна мешать нажатиям. В Kivy у отключённого
    виджета on_touch_down возвращает True, и маршрутизация на этом
    останавливается: невидимая панель молча съедала касания — не работали
    ни строки чатов, ни кнопка «+». Здесь скрытая панель пропускает
    касание дальше, а видимая ведёт себя как обычный виджет.
    """

    def on_touch_down(self, touch):
        if self.disabled or self.opacity < 0.01:
            return False
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if self.disabled or self.opacity < 0.01:
            return False
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if self.disabled or self.opacity < 0.01:
            return False
        return super().on_touch_up(touch)


Factory.register("ChatPane", cls=ChatPane)


# UnreadBadge удалён: счётчик новых рисует сам ряд (ChatRow._badge), и там
# он уже по координатам макета — круг на одну цифру, овал на две. Отдельный
# виджет с собственным позиционированием всё равно расходился бы с макетом.


class NavItem(Widget):
    """Пункт нижней панели: иконка и подпись.

    Иконка и подпись рисуются в canvas самого пункта — по той же причине,
    что и ряд чата (см. шапку модуля). Активная вкладка фиолетовая
    (#4B2FE0), остальные чёрные; цвет не переключается рывком, а плавно
    едет к фиолетовому через `active_t`. Лупа «Поиска» в макете нарисована
    линиями, а не картинкой — так и рисуем.

    Пункт лежит в отдельном слое поверх стекла (ui/kv/home.kv), а не
    рядом с плашкой и не внутри неё: слой объявлен последним, поэтому
    иконки всегда сверху стекла, и это не зависит от порядка строк в
    разметке — раньше плашку надо было специально ставить раньше
    кнопок, и стоило переставить строки, как «Поиск» снова начинал
    открывать «Настройки». Внутрь плашки пункт положить нельзя: Kivy не
    пересчитывает координаты касания для детей контейнера со смещением,
    и пальцем в пункт не попасть.

    Иконка и подпись стоят на координатах МАКЕТА (сцена 450x920), и
    пересчитывать их не нужно: слой начинается в нуле, поэтому координаты
    макета попадают на свои места и в рисунке, и в нажатии.
    """

    __events__ = ("on_release",)

    caption = StringProperty("")
    active_t = NumericProperty(0.0)
    active = BooleanProperty(False)
    press_tint = NumericProperty(0.0)
    # Размер иконки и её положение — из макета (у каждой вкладки своё):
    #   Поиск      лупа: круг (72, 800) r 8 и ручка до (59, 813)
    #   Чаты      38x38 в (139, 785) -> x 153.3 y 53.7
    #   Группы    44x44 в (226, 782) -> x 249.3 y 50.5
    #   Настройки 34x34 в (322, 787) -> x 355.1 y 55.8
    icon_size = NumericProperty(41.9)      # макет 38x38
    icon_x = NumericProperty(153.3)        # макет 139
    icon_y = NumericProperty(53.7)         # макет 785 (низ иконки)
    caption_x = NumericProperty(173.0)     # центр подписи, макет 157..189
    caption_size = NumericProperty(13.0)   # один на все подписи
    magnifier = BooleanProperty(False)     # лупа рисуется линиями (в макете)
    idle_source = StringProperty("")
    active_source = StringProperty("")

    # Лупа «Поиска» в макете: круг (72, 800) r 8 и ручка (66, 806)->(59, 813)
    GLASS = (79.4, 77.9, 8.8)             # центр и радиус в сцене
    GLASS_HANDLE = ((72.8, 71.5), (65.2, 64.2))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Зона нажатия — четверть плашки, а не весь ряд: пункты стоят
        # друг на друге, и при одинаковых границах верхний перехватывал бы
        # касания всех — «Поиск» открывал «Настройки». Размер здесь —
        # только для попадания пальцем, рисунок всё равно рисуется по
        # координатам макета.
        self.size_hint = (None, None)
        self.size = (dp(99.3), dp(63.2))
        self._pressed = False
        self._labels = []
        # Перерисовываем при смене любого влияющего на рисунок свойства:
        # иначе, например, magnifier=True после caption не отразился бы —
        # лупа так и осталась бы ненарисованной.
        self.bind(pos=self._redraw, size=self._redraw, active_t=self._redraw,
                  press_tint=self._redraw,
                  icon_size=self._redraw, icon_x=self._redraw,
                  icon_y=self._redraw, caption_x=self._redraw,
                  caption_size=self._redraw, caption=self._redraw,
                  magnifier=self._redraw)

    def on_release(self, *args):
        """Обработчик по умолчанию — его требует объявленное on_release."""
        return None

    def set_icon(self, idle_source: str, active_source: str) -> None:
        """Картинки для обычного и активного состояния."""
        self.idle_source = idle_source
        self.active_source = active_source
        self._redraw()

    def on_active(self, *_):
        from ui import anim
        anim.fade_to(self, "active_t", 1.0 if self.active else 0.0,
                     duration=0.18)

    # -- нажатие ------------------------------------------------------------- #
    # Своё состояние вместо ButtonBehavior: там отпускание проверяет
    # «touch.grab_current is self», а захват в этой сборке Kivy работает
    # не так, и кнопка молча не нажималась.

    def _animate_press(self, value, duration, transition):
        from kivy.animation import Animation
        Animation.cancel_all(self, "press_tint")
        Animation(press_tint=value, d=duration, t=transition).start(self)

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            self._pressed = False
            return False
        self._pressed = True
        self._animate_press(1.0, 0.07, "out_quad")
        return True

    def on_touch_up(self, touch):
        self._animate_press(0.0, 0.26, "out_back")
        pressed, self._pressed = self._pressed, False
        if not pressed or not self.collide_point(*touch.pos):
            return False
        self.dispatch("on_release")
        return True

    # -- рисунок ------------------------------------------------------------- #

    def _redraw(self, *_):
        self.canvas.clear()
        self._labels = []
        if not self.width:
            return
        # Активная вкладка едет к фиолетовому, под нажатием темнеет —
        # так же, как кнопка «+» на плашке стекла.
        tint = self.active_t
        press = self.press_tint
        # Цвет ровно как в макете: чёрный, а фиолетовый неактивный пункт
        # не «серый» (серый получается, если подмешать белый).
        rgba = (0.294 * tint, 0.184 * tint, 0.878 * tint, 1)
        ink = (rgba[0] * (1 - 0.25 * press),
               rgba[1] * (1 - 0.25 * press),
               rgba[2] * (1 - 0.25 * press), 1)
        # Иконка и подпись стоят на своих местах макета (сцена 450x920), а
        # не по центру пункта: в макете пункты смещены друг относительно
        # друга, и зона нажатия у пункта своя (см. __init__).
        icon_x = dp(self.icon_x)
        icon_y = dp(self.icon_y)
        size = dp(self.icon_size)

        with self.canvas:
            if self.magnifier:
                # Лупа нарисована линиями — ровно как в макете
                Color(rgba=ink)
                Line(circle=(dp(self.GLASS[0]), dp(self.GLASS[1]),
                             dp(self.GLASS[2])), width=dp(3.2), cap="round")
                (x1, y1), (x2, y2) = self.GLASS_HANDLE
                Line(points=[dp(x1), dp(y1), dp(x2), dp(y2)],
                     width=dp(3.2), cap="round")
            else:
                source = self.active_source if self.active else self.idle_source
                texture = _icon_texture(source)
                if texture is not None:
                    # Под нажатием иконка чуть гаснет — иначе нажатие на
                    # прозрачной кнопке не видно совсем.
                    Color(rgba=(1 - 0.25 * press, 1 - 0.25 * press,
                                1 - 0.25 * press, 1))
                    Rectangle(texture=texture, pos=(icon_x, icon_y),
                              size=(size, size))

            if self.caption:
                label = CoreLabel(
                    text=self.caption, font_size=dp(self.caption_size),
                    font_name=FONT_NAME, color=(1, 1, 1, 1),
                    halign="center", anchor_x="center")
                label.refresh()
                self._labels.append(label)
                # Цвет задаёт Color, а не текстура: иначе серый был бы
                # вдвое темнее (см. ChatRow._texture).
                Color(rgba=ink)
                Rectangle(texture=label.texture,
                          pos=(dp(self.caption_x) - label.texture.width / 2,
                               dp(CAPTION_BASE)
                               - label.texture.height * DESCENT),
                          size=label.texture.size)


Factory.register("NavItem", cls=NavItem)