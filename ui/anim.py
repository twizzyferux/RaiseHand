# -*- coding: utf-8 -*-
"""Анимации в духе Telegram.

Три вещи, которые отличают «вкусное» нажатие от стандартного:

  1. Кнопка слегка сжимается (до 96.5% от своего размера) и плавно
     темнеет, а при отпускании пружинит обратно с небольшим
     перелётом. Стандартная Kivy просто меняет картинку — здесь
     живое движение.
  2. Экраны не переключаются рывком: новый въезжает сбоку и мягко
     проявляется, старый слегка отходит и притухает.
  3. Содержимое появляется лесенкой — элемент за элементом снизу
     вверх, как в Телеграме при открытии чата.

Здесь только логика; в .kv читаются свойства `press_scale`,
`press_tint` и `active_t`, поэтому разметка остаётся чистой.
"""
from kivy.animation import Animation, AnimationTransition
from kivy.clock import Clock
from kivy.factory import Factory
from kivy.graphics import PopMatrix, PushMatrix, Scale, Translate
from kivy.metrics import dp
from kivy.properties import NumericProperty, OptionProperty
from kivy.uix.button import Button
from kivy.uix.screenmanager import TransitionBase
from kivy.uix.togglebutton import ToggleButton

# Длительности подобраны на глаз: нажатие мгновенное, отпускание пружинит.
PRESS_IN = 0.06
PRESS_OUT = 0.24
PRESS_SCALE = 0.965

TRANSITION_DURATION = 0.24
TRANSITION_SHIFT = 0.09          # насколько въезжает новый экран, доля ширины
TRANSITION_DIM = 0.45            # насколько притухает уходящий экран

FADE_IN = 0.30
FADE_OUT = 0.14
RISE = 14                        # насколько элемент приподнимается при появлении


class PressMixin:
    """Общее поведение «живой» кнопки: сжатие по центру + затемнение.

    Масштаб делается матрицей в canvas, а не изменением size: иначе
    вложенный текст остался бы на месте и «вылезал» из кнопки.
    """

    press_scale = NumericProperty(1.0)      # 1.0 — исходный размер
    press_tint = NumericProperty(0.0)       # 0 — обычный цвет, 1 — цвет нажатия
    press_min = NumericProperty(PRESS_SCALE)
    press_tint_max = NumericProperty(1.0)

    def _init_press(self):
        group = self.canvas.before
        self._press_back = Translate(0, 0)
        self._press_scale_instr = Scale(1, 1, 1, origin_x=0, origin_y=0)
        self._press_to = Translate(0, 0)
        # Матрица должна быть ПЕРВОЙ в canvas.before — иначе она
        # окажется после заливки кнопки и сжимать будет только текст.
        group.insert(0, self._press_back)
        group.insert(0, self._press_scale_instr)
        group.insert(0, self._press_to)
        group.insert(0, PushMatrix())
        with self.canvas.after:
            PopMatrix()

        self.fbind("state", self._on_press_state)
        self.bind(press_scale=self._apply_press_matrix)
        self.bind(pos=self._apply_press_matrix, size=self._apply_press_matrix)
        self._apply_press_matrix()

    def _apply_press_matrix(self, *_):
        cx, cy = self.center_x, self.center_y
        self._press_to.x = cx
        self._press_to.y = cy
        self._press_back.x = -cx
        self._press_back.y = -cy
        self._press_scale_instr.x = self.press_scale
        self._press_scale_instr.y = self.press_scale

    def _press_state_down(self):
        """Что делать при нажатии. У чекбокса переопределяется."""
        Animation.cancel_all(self, "press_scale", "press_tint")
        Animation(press_scale=self.press_min,
                  press_tint=self.press_tint_max,
                  d=PRESS_IN, t="out_quad").start(self)

    def _release(self):
        Animation.cancel_all(self, "press_scale", "press_tint")
        Animation(press_scale=1.0, press_tint=0.0,
                  d=PRESS_OUT, t="out_back").start(self)

    def _on_press_state(self, *_):
        Animation.cancel_all(self, "press_scale", "press_tint")
        if self.state == "down":
            self._press_state_down()
        else:
            self._release()


class PressButton(PressMixin, Button):
    """Кнопка с телеграммовским нажатием."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._init_press()


class PressToggle(PressMixin, ToggleButton):
    """Чекбокс: при включении делает «поп», а не просто меняет галочку."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._init_press()

    def _press_state_down(self):
        Animation.cancel_all(self, "press_scale")
        # сжатие и обратно с перелётом — как «щёлчок»
        anim = Animation(press_scale=0.86, d=0.07, t="out_quad")
        anim.bind(on_complete=lambda *_: Animation(
            press_scale=1.0, d=0.32, t="out_back").start(self))
        anim.start(self)

    def _release(self):
        Animation.cancel_all(self, "press_scale")
        Animation(press_scale=1.0, d=0.26, t="out_back").start(self)


class SlideDot(PressButton):
    """Точка-индикатор карусели.

    Цвет не переключается рывком: active_t плавно идёт от 0
    (светло-фиолетовая) к 1 (фиолетовая активная).
    """

    active_t = NumericProperty(0.0)


Factory.register("PressButton", cls=PressButton)
Factory.register("PressToggle", cls=PressToggle)
Factory.register("SlideDot", cls=SlideDot)


# --------------------------------------------------------------------------- #
#  Переходы между экранами
# --------------------------------------------------------------------------- #

class SoftSlideTransition(TransitionBase):
    """Новый экран въезжает сбоку и проявляется, старый отходит и гаснет.

    Движение короткое (0.24с) и без «отскока» — как в Телеграме,
    где переходы быстрые и не задерживают. Уходящий экран не исчезает
    совсем, а лишь притухает: так переход читается как «смена слоёв».
    """

    direction = OptionProperty("left", options=("left", "right", "up", "down"))

    def on_progress(self, p):
        mx, my = self.manager.pos
        w, h = float(self.manager.width), float(self.manager.height)
        shift = TRANSITION_SHIFT
        # out_quad — мягкое ускорение в начале, спокойное торможение в конце
        t = AnimationTransition.out_quad(p)
        new, old = self.screen_in, self.screen_out

        if self.direction == "left":            # новый въезжает справа
            new.pos = (mx + w * shift * (1 - t), my)
            old.pos = (mx - w * shift * 0.5 * t, my)
        elif self.direction == "right":         # новый въезжает слева
            new.pos = (mx - w * shift * (1 - t), my)
            old.pos = (mx + w * shift * 0.5 * t, my)
        elif self.direction == "up":
            new.pos = (mx, my + h * shift * (1 - t))
            old.pos = (mx, my - h * shift * 0.5 * t)
        else:
            new.pos = (mx, my - h * shift * (1 - t))
            old.pos = (mx, my + h * shift * 0.5 * t)

        new.opacity = min(1.0, t * 2.6)
        old.opacity = 1.0 - t * TRANSITION_DIM

    def on_complete(self):
        super().on_complete()
        for screen in (self.screen_in, self.screen_out):
            if screen is not None:
                screen.pos = self.manager.pos
                screen.opacity = 1.0


Factory.register("SoftSlideTransition", cls=SoftSlideTransition)


# --------------------------------------------------------------------------- #
#  Мелкие помощники
# --------------------------------------------------------------------------- #

def cancel(widget, name):
    """Гасить незавершённую анимацию свойства.

    Нужна там, где значение ставится напрямую: анимация Kivy живёт по
    часам и сама пишет свойство каждый кадр, поэтому не отменённая
    анимация допишет своё старое значение уже после прямой установки
    (см. HomeScreen._paint_tabs — оттуда и появлялись «случайные»
    вкладки при возврате из настроек).
    """
    Animation.cancel_all(widget, name)


def fade_to(widget, name, value, duration=FADE_IN, transition="out_quad"):
    """Плавно меняет числовое свойство виджета (цвет точки, прозрачность)."""
    cancel(widget, name)
    Animation(**{name: value}, d=duration, t=transition).start(widget)


def stagger_in(widgets, start=0.0, step=0.045, rise=RISE, duration=FADE_IN):
    """Появление содержимого лесенкой: элементы проявляются по очереди.

    Каждый элемент сначала чуть ниже своего места и прозрачный,
    затем мягко всплывает на место.
    """
    live = [w for w in widgets if w is not None]
    for index, widget in enumerate(live):
        target_y = widget.y
        Animation.cancel_all(widget, "opacity", "y")
        widget.opacity = 0
        widget.y = target_y - dp(rise)
        Clock.schedule_once(
            lambda dt, w=widget, ty=target_y: Animation(
                opacity=1, y=ty, d=duration, t="out_cubic").start(w),
            start + index * step)
    return len(live)


def swap_text(widget, apply_text, out_duration=FADE_OUT, in_duration=FADE_IN):
    """Меняет текст виджета с перекрёстным затуханием.

    Старый текст гаснет, затем подставляется новый и проявляется.
    """
    def put(*_):
        apply_text()
        widget.opacity = 0
        Animation(opacity=1, d=in_duration, t="out_quad").start(widget)

    # on_complete нельзя передать в start() — только через bind()
    fade_out = Animation(opacity=0, d=out_duration, t="in_quad")
    fade_out.bind(on_complete=put)
    fade_out.start(widget)