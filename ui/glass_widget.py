# -*- coding: utf-8 -*-
"""Жидкое стекло iOS на плагине kivy-garden.frostedglass.

ЧТО ЗДЕСЬ И ПОЧЕМУ
------------------
1. BlurSource — ровно один фон для размытия. Плагин берёт образец по
   ССЫЛКЕ на canvas виджета-фона, а canvas сцены (PhoneStage) содержит
   ещё и все дочерние виджеты: иконки панели, ряды чатов, кнопку «+».
   Плагин их размывает и рисует копию ПОД настоящими иконками — панель
   выглядела «раздвоенной», а вокруг иконок появлялся ореол. Тефон
   образца — отдельный виджет с одной кремовой заливкой и ничего
   больше, размывать нечего лишнего.

2. LiquidGlass — общая часть плашки и кнопки «+»: геометрия, параметры
   размытия, нажатие. Размер и blur_size нельзя передавать в
   конструктор плагина: on_size вызывается раньше, чем создан fbo_rect,
   и виджет падает с AttributeError. Поэтому создаём пустым и задаём
   размер после — отдельным вызовом setup().

3. LiquidNavBar — плашка вместе с её пунктами. Пункты объявлены в
   разметке вложенными в плашку, а не соседями: тогда они всегда
   нарисованы поверх стекла и всегда получают касание первыми, и это
   уже не зависит от порядка объявления в .kv. Раньше всё держалось на
   ручном правиле «плашку объявить раньше кнопок» — стоило переставить
   строки, и «Поиск» снова открывал «Настройки».

4. Плагин умеет только НЕ ОБНОВЛЯТЬ стекло, когда его экран не
   текущий, но не умеет его ПРЯТАТЬ: результат размытия остаётся в
   буфере и продолжает рисоваться. При уходе в настройки панель на
   секунду висела поверх них. Отсюда set_visible().

Геометрия — из макета Face ID.svg, сцена 450x920.
"""
import os

from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.metrics import dp
from kivy.properties import NumericProperty
from kivy.uix.widget import Widget
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
CREAM = (1.0, 0.984, 0.969)              # #FFFBF7 — фон экрана


class BlurSource(Widget):
    """Чистый фон для размытия: кремовая заливка и больше ничего.

    Размер и положение задаются в разметке. Заливка рисуется в
    canvas.before, чтобы плагин (он берёт canvas целиком) видел её
    первой, а не поверх содержимого сцены.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(rgba=(*CREAM, 1.0))
            self._fill = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._sync, size=self._sync)

    def _sync(self, *_):
        self._fill.pos = self.pos
        self._fill.size = self.size


class LiquidGlass(FrostedGlass):
    """Общая часть плашки и кнопки «+».

    Нажатие ведём сами, без touch.grab(): касание перехватывают другие
    виджеты (панели, ScrollView), и проверка «grab_current is self» в
    on_touch_up оказывается ложной — кнопка молча не нажимается.
    Состояние держим сами, этого достаточно.
    """

    press_tint = NumericProperty(0.0)

    __events__ = ("on_release",)

    def on_release(self, *args):
        """Заглушка: Kivy требует обработчик у объявленного события.

        Реальный обработчик задаётся в разметке (например, у кнопки «+»
        это root.new_chat()).
        """
        return None

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

    # -- нажатие ------------------------------------------------------------- #

    def _animate_press(self, value, duration, transition):
        from kivy.animation import Animation
        Animation.cancel_all(self, "press_tint")
        Animation(press_tint=value, d=duration, t=transition).start(self)

    def on_touch_down(self, touch):
        # disabled проверяем обязательно: на вкладках «Поиск» и «Группы»
        # кнопка «+» спрятана (opacity 0), но остаётся в дереве и ловит
        # касания. Без этой проверки касание в правом верхнем углу
        # нажимало невидимую кнопку и уводило на «Поиск».
        if self.disabled or not self.collide_point(*touch.pos):
            self._pressed = False
            return False
        self._pressed = True
        self._animate_press(1.0, 0.07, "out_quad")
        return True

    def on_touch_up(self, touch):
        self._animate_press(0.0, 0.26, "out_back")
        pressed, self._pressed = self._pressed, False
        # Нажатие засчитано, только если кнопка была жива в момент
        # нажатия и палец отпущен прямо над ней.
        if not pressed or self.disabled or not self.collide_point(*touch.pos):
            return False
        self.dispatch("on_release")
        return True


class LiquidNavBar(LiquidGlass):
    """Стеклянная плашка нижней панели вместе с её пунктами.

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
        self._pressed = False
        self.setup(
            pos=(dp(PANEL[0]), dp(PANEL[1])),
            size=(dp(PANEL[2]), dp(PANEL[3])),
            radius=dp(PANEL_RADIUS),
            effect=self.EFFECT,
        )


class LiquidFab(LiquidGlass):
    """Стеклянная кнопка «+» в шапке.

    Стекло сверху, а сверху стекла — фиолетовая заливка и сам плюс: в
    макете кнопка фиолетовая, и без заливки она потеряла бы фирменный
    цвет. Плагин — это FloatLayout, а не кнопка, поэтому нажатие ведём
    сами (см. LiquidGlass).
    """

    # Фиолетовый цвет задаётся НЕ своей заливкой, а overlay_color плагина.
    # Причина: плагин берёт образец фона по ССЫЛКЕ background. Свою
    # фиолетовую заливку он в образец не берёт, а рисует результат ПОВЕРХ
    # неё — круг под стеклом просто исчезал: на его месте оказывался
    # размытый фон, бледное пятно. Tint — единственный способ получить
    # фиолетовое стекло: плагин сам подкрашивает образец и рисует его
    # вместе с бликом и кромкой.
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
        self._pressed = False
        self.setup(
            pos=(dp(FAB[0]), dp(FAB[1])),
            size=(dp(FAB[2]), dp(FAB[3])),
            radius=dp(FAB_RADIUS),
            effect=self.EFFECT,
        )
        self._draw_plus()
        self.bind(pos=self._draw_plus, size=self._draw_plus)

    # -- плюс ---------------------------------------------------------------- #

    def _draw_plus(self, *_):
        """Плюс поверх стекла: макет 344.5..371.5 по X, 99..129 по Y.

        Рисуем двумя скруглёнными прямоугольниками, а не двумя Line:
        у Line концы получались разными — у горизонтальной штрихи
        выходили острыми, у вертикальной скруглёнными. Прямоугольник
        со радиусом в половину толщины даёт одинаковый торец со всех
        четырёх сторон, и размеры берутся те же, что были у линий.
        """
        self.canvas.after.clear()
        press = self.press_tint
        thickness = dp(3.3)
        half = thickness / 2
        arm_x = dp(14.9)               # по горизонтали
        arm_y = dp(15.8)               # по вертикали
        with self.canvas.after:
            Color(rgba=(1, 1, 1, 1 - 0.15 * press))
            RoundedRectangle(pos=(self.center_x - arm_x,
                                  self.center_y - half),
                             size=(arm_x * 2, thickness),
                             radius=[half, ])
            RoundedRectangle(pos=(self.center_x - half,
                                  self.center_y - arm_y),
                             size=(thickness, arm_y * 2),
                             radius=[half, ])


def attach_background(widget, background):
    """Указать стеклу, что размывать (см. BlurSource)."""
    widget.background = background
    widget.request_update()


def set_visible(widget, visible):
    """Показать или убрать стекло.

    Плагин умеет только НЕ ОБНОВЛЯТЬ стекло, когда его экран не текущий
    (свойство not_current_screen), но не умеет его ПРЯТАТЬ: результат
    размытия остаётся в буфере и продолжает рисоваться. Из-за этого
    при уходе с экрана чатов нижняя панель на секунду оставалась поверх
    настроек — её видно было как раздвоенную.

    Поэтому убираем инструкцию отрисовки из canvas и возвращаем её
    обратно. Проверено: opacity плагина не помогает — у него эффект
    добавлен прямо в canvas, и прозрачность виджета его не гасит.
    """
    effect = getattr(widget, "frosted_glass_effect", None)
    if effect is None:
        return
    children = widget.canvas.children
    if visible:
        if effect not in children:
            widget.canvas.add(effect)
            widget.request_update()
    elif effect in children:
        widget.canvas.remove(effect)