# -*- coding: utf-8 -*-
"""Поля пароля с «глазом».

ЗАЧЕМ
----
В макетах у полей пароля стоит иконка глаза: нажатие показывает
введённое, повторное — снова прячет. Без нажатия смотреть не на что:
и в макете, и в приложении человек с чужим паролем не может
перепроверить, что напечатал, и гадает по звёздочкам. В макете глаз был
просто картинкой рядом с полем — нажать на него было нельзя.

ПОЧЕМУ ЗОНА ВНУТРИ ПОЛЯ, А НЕ КНОПКА ПОВЕРХ
--------------------------------------------
TextInput перехватывает касание целиком: нажатие в любом месте поля
ставит туда курсор. Отдельная кнопка поверх потребовала бы перехвата
касаний у поля, а это ломает и вставку текста, и прокрутку. Поэтому
поле само следит за правым краем: попали в зону глаза — переключаем
видимость, не попали — ведём себя как обычное поле.

ДВА ВИДА ПОЛЯ
-------------
Поведение вынесено в примесь, потому что поля в приложении двух видов:
обычные (темы форм) и «таблетки» из макета регистрации. Оформление у
них разное, а глаз нужен одинаковый.

Рисунок глаза — из кита (assets/images/raisehand), как и остальные
иконки приложения.
"""
import os

from kivy.clock import Clock
from kivy.core.image import Image as CoreImage
from kivy.factory import Factory
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp
from kivy.properties import BooleanProperty
from kivy.uix.textinput import TextInput

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAISEHAND = os.path.join(BASE, 'assets', 'images', 'raisehand')

# Зона нажатия глаза: у правого края поля, по центру по вертикали.
# Квадрат 44x44 — минимальная удобная цель для пальца, больше самой
# иконки, чтобы по нему не надо было целиться.
EYE_ZONE = 44
EYE_ICON = 22

_cache = {}


def _texture(name):
    """Текстура иконки из assets/images/raisehand (с кэшем)."""
    path = os.path.join(RAISEHAND, os.path.basename(name))
    if not name or not os.path.exists(path):
        return None
    if path not in _cache:
        _cache[path] = CoreImage(path).texture
    return _cache[path]


def _sprite(kind):
    from core.config import sprite
    return sprite(kind)


class EyeToggleMixin:
    """Поведение глаза для любого поля ввода."""

    show_password = BooleanProperty(False)

    def _init_eye(self):
        self._eye_hit = False
        self.bind(show_password=self._sync_mask, password=self._sync_mask)
        self._sync_mask()

    # Сам глаз рисует разметка (canvas.after в theme.kv), а не код.
    # Причина проверена на регистрации учителя: когда поле рисует глаз
    # само, глаз успевает нарисоваться ДО раскладки — на старом размере
    # — и остаётся сдвинутым влево, наезжая на подсказку. Принудительная
    # перерисовка это чинила, но и она зависела от момента. В разметке
    # Kivy пересчитывает координаты сам, как только меняется right или
    # center_y, — и глаз всегда на месте.

    def _sync_mask(self, *_):
        """Маска включена всегда: показать пароль можно только глазом,
        а не случайным флагом в коде."""
        if not self.show_password and not self.password:
            self.password = True

    # -- касания ------------------------------------------------------------- #

    def _eye_box(self):
        """Прямоугольник иконки глаза в координатах поля."""
        size = dp(EYE_ICON)
        return (self.right - dp(14) - size,
                self.center_y - size / 2.0, size, size)

    def _in_eye(self, pos):
        x, y, w, h = self._eye_box()
        margin = (dp(EYE_ZONE) - max(w, h)) / 2.0
        return (x - margin <= pos[0] <= x + w + margin
                and y - margin <= pos[1] <= y + h + margin)

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            self._eye_hit = False
            return super().on_touch_down(touch)
        if self.disabled or not self._in_eye(touch.pos):
            self._eye_hit = False
            return super().on_touch_down(touch)
        self._eye_hit = True
        self.show_password = not self.show_password
        self.password = not self.show_password
        return True

    def on_touch_up(self, touch):
        if self._eye_hit:
            # Отпускание после переключения: курсор в поле не ставим.
            self._eye_hit = False
            return True
        return super().on_touch_up(touch)


class PasswordField(EyeToggleMixin, TextInput):
    """Обычное поле пароля из тем оформления."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._init_eye()


class PillPasswordField(EyeToggleMixin, TextInput):
    """Поле пароля-«таблетка» из макета регистрации."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._init_eye()


Factory.register("PasswordField", cls=PasswordField)
Factory.register("PillPasswordField", cls=PillPasswordField)