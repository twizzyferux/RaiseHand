# -*- coding: utf-8 -*-
"""Экран чатов по макету «проект/проект экран/основной экран чаты».

Макет пришёл четырьмя вырезками Figma: «основной интерфейс» (шапка с
заголовком и круглой кнопкой «+»), «чаты (закреп)», «чаты (не закреп)»
и «панель управления». Холст макета — 404x874, сцена приложения —
450x920, поэтому каждая координата переведена:

    x_сцены = x_макета * 450 / 404
    y_сцены = y_макета * 920 / 874

Геометрия ряда, шапки и панели — здесь, потому что ряд рисуется целиком
в своём canvas (см. почему ниже).

ПОЧЕМУ РЯД РИСУЕТСЯ САМ, А НЕ ЧЕРЕЗ ДЕТЕЙ-WIDGETОВ
-------------------------------------------------
В этой версии Kivy содержимое виджета не смещается вместе с ним: если
родитель стоит на (0, 100), а ребёнок на (0, 0), ребёнок всё равно
рисуется на нуле (проверено опытом _exp3.py — красный квадрат внутри
сдвинутого контейнера остался внизу окна). Поэтому все экраны этого
приложения держат координаты абсолютными, а у ряда чата в разметке
вообще нет вложенных виджетов: аватар, тексты, галочки и значки — это
инструкции canvas плюс текстуры шрифта (core.text). Такой ряд скроллится
вместе со списком как обычно.
"""
import os

from kivy.core.text import Label as CoreLabel
from kivy.factory import Factory
from kivy.graphics import Color, Ellipse, Line, Rectangle, RoundedRectangle
from kivy.metrics import dp
from kivy.properties import (BooleanProperty, NumericProperty, ObjectProperty,
                             StringProperty)
from kivy.uix.widget import Widget

from ui.anim import PressButton

MOCK_W, MOCK_H = 404.0, 874.0          # холст макета
STAGE_W, STAGE_H = 450.0, 920.0        # холст сцены приложения

# --- цвета макета ----------------------------------------------------------- #
VIOLET = "#4B2FE0"                     # кнопка «+» и активная вкладка
PINK = "#F0447C"                       # счётчик новых сообщений
GREY_TEXT = "#474747"                  # превью прочитанного чата
DARK_TEXT = "#272727"                  # превью непрочитанного
LINE_GREY = "#C5C5C5"                  # разделитель ряда
TINT = "#F3F1FF"                       # подложка закреплённых чатов
CREAM = "#FFFBF7"                      # фон экрана

# --- геометрия ряда (координаты сцены, посчитаны из макета) ---------------- #
ROW_H = 94                             # макет 84 -> 94 (450x920 против 404x874)
ROW_W = 450
AVATAR_SIZE = 76                       # макет 68 -> 76
AVATAR_POS = (10, 8)                   # макет 9, 8
NAME_LEFT = 98                         # макет 88
NAME_BASELINE = 66                     # макет 27.6 сверху ряда
PREVIEW_BASELINE = 29                  # макет 63.2 сверху ряда
TIME_BASELINE = 66                     # макет 26.6 сверху ряда
TIME_RIGHT = 428                       # макет 383
DIVIDER_LEFT = 92                      # макет 83
PIN_POS, PIN_SIZE = (405, 38), (33, 32)
BADGE_HEIGHT = 26
TICK_SIZE = (31, 21)                   # макет 28x20
TICK_GAP = 14                          # макет 13
NAME_SIZE = 22.5                       # макет 19.3
PREVIEW_SIZE = 18                      # макет 15.5
TIME_SIZE = 17                         # макет 14.5
BADGE_SIZE = 16
# Инициалы в макете на 33% стороны аватара: у букв SF Pro cap-height
# равен 0.714 кегля, значит кегль = 0.33 / 0.714.
INITIALS_RATIO = 0.462

# Доля высоты текстуры, приходящаяся на нижний выносной элемент: текст
# ставим по базовой линии, а текстура включает и выносные.
DESCENT = 0.24

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
    """Текстура иконки из assets/images/chats (с кэшем: перерисовка частая)."""
    if not source:
        return None
    path = os.path.join(ICON_DIR, os.path.basename(source))
    if not os.path.exists(path):
        return None
    if path not in _icon_cache:
        from kivy.core.image import Image as CoreImage
        _icon_cache[path] = CoreImage(path).texture
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
            if self.avatar_source:
                Color(rgba=(1, 1, 1, 1))
                Rectangle(source=self.avatar_source,
                          pos=(left + dp(AVATAR_POS[0]), bottom + dp(AVATAR_POS[1])),
                          size=(dp(AVATAR_SIZE), dp(AVATAR_SIZE)))
            if self.initials:
                texture, height = self._texture(
                    self.initials, dp(AVATAR_SIZE) * INITIALS_RATIO,
                    "#FDFCFF", bold=False, align="center")
                if texture is not None:
                    # Центр инициалов — центр АВАТАРА, а не ряда
                    Color(rgba=hex_rgba("#FDFCFF"))
                    Rectangle(texture=texture,
                              pos=(left + dp(AVATAR_POS[0])
                                   + (dp(AVATAR_SIZE) - texture.width) / 2,
                                   bottom + dp(AVATAR_POS[1])
                                   + (dp(AVATAR_SIZE) - height) / 2),
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

            # Время — по правому краю, на одной базовой линии с именем
            texture, height = self._texture(self.stamp, dp(TIME_SIZE),
                                            "#000000", align="right")
            if texture is not None:
                Color(rgba=(0, 0, 0, 1))
                Rectangle(texture=texture,
                          pos=(left + dp(TIME_RIGHT) - texture.width,
                               bottom + dp(TIME_BASELINE) - height * DESCENT),
                          size=texture.size)

            # Превью: у непрочитанного чата текст темнее (макет)
            tone = DARK_TEXT if self.unread else GREY_TEXT
            texture, height = self._texture(self.preview, dp(PREVIEW_SIZE), tone)
            if texture is not None:
                Color(rgba=hex_rgba(tone))
                Rectangle(texture=texture,
                          pos=(left + dp(NAME_LEFT),
                               bottom + dp(PREVIEW_BASELINE) - height * DESCENT),
                          size=texture.size)

                # Галочка своего сообщения: серым «отправлено»,
                # фиолетовым «прочитано» — сразу за текстом
                if self.mine and not self.unread:
                    source = "status_read.png" if self.read else "status_sent.png"
                    self._icon(source,
                               left + dp(NAME_LEFT) + texture.width + dp(TICK_GAP),
                               bottom + dp(PREVIEW_BASELINE) + 3, TICK_SIZE)

            # Закрепление
            if self.pinned:
                self._icon("status_pin.png", left + dp(PIN_POS[0]),
                           bottom + dp(PIN_POS[1]), PIN_SIZE)

            # Счётчик новых: круг на одну цифру, овал на две
            if self.unread:
                self._badge(bottom)

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

    def _badge(self, bottom):
        """Плашка со счётчиком новых сообщений."""
        digits = "99+" if self.unread >= 100 else str(int(self.unread))
        texture, height = self._texture(digits, dp(BADGE_SIZE), "#FFFFFF",
                                        bold=True, align="center")
        width = max(dp(BADGE_HEIGHT), (texture.width if texture else 0) + dp(12))
        x = self.x + self.width - dp(20) - width
        y = bottom + dp(PIN_POS[1])
        Color(rgba=hex_rgba(PINK))
        RoundedRectangle(pos=(x, y), size=(width, dp(BADGE_HEIGHT)),
                         radius=[dp(BADGE_HEIGHT) / 2, ])
        if texture is not None:
            Color(rgba=hex_rgba("#FFFFFF"))
            Rectangle(texture=texture,
                      pos=(x + (width - texture.width) / 2,
                           y + (dp(BADGE_HEIGHT) - height) / 2),
                      size=texture.size)

    # -- нажатие ------------------------------------------------------------- #

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return False
        from ui.anim import Animation
        touch.grab(self)
        Animation.cancel_all(self, "press_tint")
        Animation(press_tint=1.0, d=0.07, t="out_quad").start(self)
        return True

    def on_touch_up(self, touch):
        from ui.anim import Animation
        Animation.cancel_all(self, "press_tint")
        Animation(press_tint=0.0, d=0.26, t="out_back").start(self)
        if touch.grab_current is self:
            touch.ungrab(self)
            if self.collide_point(*touch.pos) and self.on_release is not None:
                self.on_release()
        return True


Factory.register("ChatRow", cls=ChatRow)


class UnreadBadge(Widget):
    """Плашка со счётчиком: та же отрисовка, что в ряду, но отдельным
    виджетом — для мест, где ряд не подходит (например, в поиске)."""

    count = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (dp(BADGE_HEIGHT), dp(BADGE_HEIGHT))
        self.bind(count=self._redraw, pos=self._redraw, size=self._redraw)

    def show(self, count: int) -> None:
        self.count = count or 0
        self.opacity = 1 if self.count else 0

    def _redraw(self, *_):
        self.canvas.clear()
        count = int(self.count)
        if not count:
            self.opacity = 0
            return
        digits = "99+" if count >= 100 else str(count)
        label = CoreLabel(text=digits, font_size=dp(BADGE_SIZE),
                          font_name=FONT_NAME, color=(1, 1, 1, 1), bold=True)
        label.refresh()
        width = max(self.height, label.texture.width + dp(12))
        self.width = width
        with self.canvas:
            Color(rgba=hex_rgba(PINK))
            RoundedRectangle(pos=self.pos, size=self.size,
                             radius=[self.height / 2, ])
            Color(rgba=(1, 1, 1, 1))
            Rectangle(texture=label.texture,
                      pos=(self.x + (width - label.texture.width) / 2,
                           self.y + (self.height - label.texture.height) / 2),
                      size=label.texture.size)


Factory.register("UnreadBadge", cls=UnreadBadge)


class NavItem(PressButton):
    """Пункт нижней панели: иконка и подпись.

    Иконка и подпись рисуются в canvas самого пункта — по той же причине,
    что и ряд чата (см. шапку модуля). Активная вкладка фиолетовая
    (#4B2FE0), остальные чёрные; цвет не переключается рывком, а плавно
    едет к фиолетовому через `active_t`. Лупа «Поиска» в макете нарисована
    линиями, а не картинкой — так и рисуем.
    """

    caption = StringProperty("")
    active_t = NumericProperty(0.0)
    active = BooleanProperty(False)
    icon_size = NumericProperty(42.0)      # сторона иконки (у каждой своя)
    magnifier = BooleanProperty(False)      # рисовать лупу линиями
    idle_source = StringProperty("")
    active_source = StringProperty("")

    ICON_TOP = 47                          # макет: иконка по центру плашки
    CAPTION_TOP = 17
    CAPTION_SIZE = 12

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (dp(100), dp(63))
        self.background_normal = ""
        self.background_down = ""
        self.background_color = 0, 0, 0, 0
        self.border = 0, 0, 0, 0
        self._labels = []
        self.bind(pos=self._redraw, size=self._redraw, active_t=self._redraw,
                  icon_size=self._redraw, caption=self._redraw)

    def set_icon(self, idle_source: str, active_source: str) -> None:
        """Картинки для обычного и активного состояния."""
        self.idle_source = idle_source
        self.active_source = active_source
        self._redraw()

    def on_active(self, *_):
        from ui import anim
        anim.fade_to(self, "active_t", 1.0 if self.active else 0.0,
                     duration=0.18)

    def _redraw(self, *_):
        self.canvas.clear()
        self._labels = []
        if not self.width:
            return
        size = dp(self.icon_size)
        icon_x = self.x + (self.width - size) / 2
        icon_y = self.y + dp(self.ICON_TOP)
        tint = self.active_t

        with self.canvas:
            if self.magnifier:
                # Лупа из макета: круг 72,36 r8 и ручка 66,42 -> 59,49
                Color(rgba=(0.294 * tint, 0.184 * tint, 0.878 * tint, 1))
                Line(circle=(icon_x + size / 2 + dp(2), icon_y + dp(8.9),
                             dp(8.9)), width=dp(3.4), cap="round")
                Line(points=[icon_x + size / 2 - dp(2.8), icon_y + dp(17.4),
                             icon_x + size / 2 - dp(11), icon_y + dp(25.8)],
                     width=dp(3.4), cap="round")
            else:
                source = self.active_source if self.active else self.idle_source
                texture = _icon_texture(source)
                if texture is not None:
                    Color(rgba=(1, 1, 1, 1))
                    Rectangle(texture=texture, pos=(icon_x, icon_y),
                              size=(size, size))

            if self.caption:
                label = CoreLabel(
                    text=self.caption, font_size=dp(self.CAPTION_SIZE),
                    font_name=FONT_NAME, color=(1, 1, 1, 1),
                    halign="center", anchor_x="center")
                label.refresh()
                self._labels.append(label)
                # Цвет задаёт Color, а не текстура: иначе серый был бы
                # вдвое темнее (см. ChatRow._texture).
                Color(rgba=(0.294 * tint, 0.184 * tint, 0.878 * tint, 1))
                Rectangle(texture=label.texture,
                          pos=(self.x + (self.width - label.texture.width) / 2,
                               self.y + dp(self.CAPTION_TOP)),
                          size=label.texture.size)


Factory.register("NavItem", cls=NavItem)