# -*- coding: utf-8 -*-
"""Эффект «жидкого стекла» — на плагине kivy-garden.frostedglass.

ПОЧЕМУ ПЛАГИН, А НЕ СВОИ СЛОИ
----------------------------
Свой вариант (тело + блик + затемнение + кромка) был собран вручную и
выглядел как пластиковая плашка, а не как стекло: без настоящего размытия
фона глаз считывает «нарисованный» прямоугольник. Плагин делает то, чего
не хватало ручной сборке — берёт то, что позади, размывает это по двум
осям и добавляет шум, подсветку и обводку.

ЧТО ПРИХОДИТСЯ УЧИТЫВАТЬ
------------------------
1. Размер и положение нельзя передавать в конструктор: внутри плагина
   on_size вызывается раньше, чем создаётся fbo_rect, и виджет падает с
   AttributeError. Поэтому создаём пустым и задаём размер после.
2. Плагину нужно сказать, ЧТО размывать (свойство background). Без него
   стекло показывает только шум — выглядит как серый прямоугольник.
3. Плагин один раз на весь процесс ставит Clock-подписку
   «Window.canvas.ask_update() каждый кадр». Она нужна, чтобы стекло
   жило само, но она же заставляет перерисовывать всё окно постоянно.
   Мы выставляем FG_ASK_UPDATE_CANVAS_ACTIVE заранее и обновляем стекло
   сами — только когда что-то изменилось (см. request_update).

Геометрия — из макета Face ID.svg, сцена 450x920.
"""
import os

from kivy.graphics import Color, Line
from kivy.metrics import dp
from kivy.properties import NumericProperty
from kivy_garden.frostedglass import FrostedGlass

# Плагин читает этот флаг, чтобы не вешать перерисовку окна каждый кадр.
# Ставим ДО создания первого стекла — иначе он успеет подписаться.
os.environ.setdefault("FG_ASK_UPDATE_CANVAS_ACTIVE", "1")

# --- геометрия макета (сцена 450x920) -------------------------------------- #
PANEL = (26.5, 35.8, 397.1, 63.2)        # x, y, ширина, высота плашки
PANEL_RADIUS = 31.6
FAB = (366.0, 775.0, 59.0, 58.0)        # кнопка «+»
FAB_RADIUS = 29.5
VIOLET = (0.294, 0.184, 0.878)           # #4B2FE0 — фиолетовый макета


class _GlassBase(FrostedGlass):
    """Общее для плашки и кнопки: настройка размытия и бережная сборка.

    Размер нельзя задавать в конструкторе плагина, поэтому все параметры
    применяются после создания, отдельным вызовом setup().
    """

    press_tint = NumericProperty(0.0)

    def setup(self, pos, size, radius, background=None, effect=None):
        self.size_hint = (None, None)
        # Ключевой обход: свойства ставятся после __init__, где плагин
        # уже создал свои буферы. Ни размер, ни blur_size в конструктор
        # передавать нельзя — они обрабатываются раньше fbo_rect.
        self.pos = pos
        self.size = size
        self.border_radius = [radius, ]
        for name, value in (effect or {}).items():
            setattr(self, name, value)
        if background is not None:
            self.background = background
        # Плагин считает, что его свойства меняются снаружи — говорим ему
        # пересчитать буферы под новый размер.
        self.update_effect()

    def request_update(self, *_):
        """Пересчитать стекло вручную (плагин сам обновляется не всегда)."""
        self.refresh_effect()


class GlassPanel(_GlassBase):
    """Стеклянная плашка нижней панели навигации.

    Настройки подобраны на кремовом фоне макета: стекло должно читаться
    как светлая гладкая поверхность, а не как серая пятнистая наклейка.
    Поэтому шум почти выключен — именно он давал «грязь», — а поверх
    стекла лежит лёгкий холодный отсвет вместо серого.
    """

    # Настройки задаются ПОСЛЕ создания (см. setup): их нельзя передавать
    # в конструктор — плагин обрабатывает blur_size раньше, чем создаёт
    # свои буферы, и падает.
    EFFECT = dict(
        blur_size=22,
        luminosity=1.12,
        saturation=1.10,
        noise_opacity=0.015,
        outline_width=1.1,
        outline_color=(1.0, 1.0, 1.0, 0.85),
        overlay_color=(0.96, 0.97, 1.0, 0.34),
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.setup(
            pos=(dp(PANEL[0]), dp(PANEL[1])),
            size=(dp(PANEL[2]), dp(PANEL[3])),
            radius=dp(PANEL_RADIUS),
            effect=self.EFFECT,
        )


class GlassFab(_GlassBase):
    """Стеклянная кнопка «+» в шапке.

    Стекло сверху, а сверху стекла — фиолетовая заливка и сам плюс: в
    макете кнопка фиолетовая, и без заливки она потеряла бы фирменный
    цвет. Нажатие ведём сами: плагин — это FloatLayout, а не кнопка.
    """

    __events__ = ("on_release",)

    # Фиолетовый цвет задаётся НЕ своей заливкой, а overlay_color плагина.
    # Причина: плагин берёт образец фона по ССЫЛКЕ background — это заливка
    # сцены (кремовая). Свою фиолетовую заливку он в образец не берёт, а
    # рисует результат ПОВЕРХ неё. Поэтому круг под стеклом просто исчезал:
    # на его месте оказывался размытый кремовый фон — бледное пятно.
    # Tint — единственный способ получить фиолетовое стекло: плагин сам
    # подкрашивает образец и рисует вместе с бликом и кромкой.
    EFFECT = dict(
        blur_size=14,
        luminosity=1.0,
        saturation=1.35,
        noise_opacity=0.012,
        outline_width=1.0,
        outline_color=(1.0, 1.0, 1.0, 0.85),
        overlay_color=(VIOLET[0], VIOLET[1], VIOLET[2], 0.86),
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.setup(
            pos=(dp(FAB[0]), dp(FAB[1])),
            size=(dp(FAB[2]), dp(FAB[3])),
            radius=dp(FAB_RADIUS),
            effect=self.EFFECT,
        )
        self._pressed = False
        self._draw_plus()
        self.bind(pos=self._draw_plus, size=self._draw_plus)

    # -- плюс ---------------------------------------------------------------- #

    def _draw_plus(self, *_):
        """Плюс поверх стекла: макет 344.5..371.5 по X, 99..129 по Y."""
        self.canvas.after.clear()
        press = self.press_tint
        with self.canvas.after:
            Color(rgba=(1, 1, 1, 1 - 0.15 * press))
            Line(points=[self.center_x - dp(14.9), self.center_y,
                         self.center_x + dp(14.9), self.center_y],
                 width=dp(3.3), cap="round")
            Line(points=[self.center_x, self.center_y - dp(15.8),
                         self.center_x, self.center_y + dp(15.8)],
                 width=dp(3.3), cap="round")

    # -- нажатие ------------------------------------------------------------ #

    def on_release(self, *args):
        """Обработчик по умолчанию — его требует объявленное on_release."""
        return None

    def on_touch_down(self, touch):
        """Запоминаем нажатие.

        deliberately БЕЗ touch.grab(self): касание перехватывают другие
        виджеты (панели, ScrollView), и проверка «grab_current is self» в
        on_touch_up оказывается ложной — кнопка молча не нажималась.
        Состояние держим сами, этого достаточно.
        """
        if not self.collide_point(*touch.pos):
            return False
        from ui.anim import Animation
        self._pressed = True
        Animation.cancel_all(self, "press_tint")
        Animation(press_tint=1.0, d=0.07, t="out_quad").start(self)
        return True

    def on_touch_up(self, touch):
        from ui.anim import Animation
        Animation.cancel_all(self, "press_tint")
        Animation(press_tint=0.0, d=0.26, t="out_back").start(self)
        if not self._pressed:
            return False
        self._pressed = False
        # Отпустили прямо над кнопкой — нажатие засчитано.
        if self.collide_point(*touch.pos):
            self.dispatch("on_release")
        return True


def attach_background(widget, background):
    """Указать стеклу, что размывать.

    Размывается canvas указанного виджета. В приложении за панелью и
    кнопкой «+» лежит сцена (PhoneStage): её canvas содержит кремовую
    заливку экрана.
    """
    widget.background = background
    widget.request_update()
