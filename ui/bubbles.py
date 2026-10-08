# -*- coding: utf-8 -*-
"""Пузыри на стартовом экране: рисуются по макету и мягко покачиваются.

Отдельным модулем, потому что это единственный «живой фон», который
реально используется: прежний DecorBackground с 24 видами формул
остался в проекте, но не подключался ни на одном экране.

Движение идёт по синусоиде — у каждого пузыря своя амплитуда, период
и фаза, поэтому они не ходят строем. Покачивание включается, когда
заходим на стартовый экран, и выключается при уходе: на других
экранах пустая работа не крутится.
"""
import math

from kivy.clock import Clock
from kivy.factory import Factory
from kivy.graphics import Color, Ellipse, RoundedRectangle
from kivy.metrics import dp
from kivy.uix.widget import Widget

# Каждый пузырь: (цвет, x, y, кружки-хвостики [(x, y, диаметр)],
#                 амплитуда, период, фаза)
# Координаты — как в макете (единицы холста 450x920).
WELCOME_BUBBLES = [
    ((0.655, 0.545, 0.98, 1), 56, 172, [(44, 147, 25), (34, 127, 20), (29, 110, 15)],
     9.0, 7.4, 0.0),
    ((0.502, 0.749, 1.0, 1), 276, 152, [(393, 129, 20), (406, 113, 15)],
     11.0, 8.6, 1.9),
    ((1.0, 0.561, 0.671, 1), 141, 125, [(134, 110, 15)],
     8.0, 6.2, 3.4),
    ((0.549, 0.878, 0.69, 1), 230, 79, [(218, 54, 25), (208, 34, 20), (203, 17, 15)],
     10.0, 9.1, 5.0),
    ((1.0, 0.541, 0.502, 1), 44, 64, [(159, 37, 25), (174, 17, 20)],
     7.0, 5.6, 2.2),
    ((1.0, 0.69, 0.486, 1), 247, 34, [(367, 17, 15)],
     8.5, 6.9, 4.4),
]

BUBBLE_W, BUBBLE_H, BUBBLE_R = 127, 39, 19.5

TWO_PI = 2 * math.pi


class WelcomeDecor(Widget):
    """Цветные «пузыри» внизу стартового экрана."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Для каждого пузыря: список (инструкция, x, исходный y),
        # амплитуда в пикселях, угловая скорость и фаза.
        # Скорость (2*pi/период) считается один раз, а не каждый кадр.
        self._groups = []
        self._time = 0.0
        self._event = None
        self._build()

    def _build(self):
        with self.canvas:
            for color, x, y, dots, amp, period, phase in WELCOME_BUBBLES:
                Color(rgba=color)
                parts = [(RoundedRectangle(pos=(dp(x), dp(y)),
                                           size=(dp(BUBBLE_W), dp(BUBBLE_H)),
                                           radius=[dp(BUBBLE_R), ]), dp(x), dp(y))]
                for cx, cy, d in dots:
                    parts.append((Ellipse(pos=(dp(cx), dp(cy)),
                                          size=(dp(d), dp(d))), dp(cx), dp(cy)))
                self._groups.append((parts, dp(amp), TWO_PI / period, phase))

    # -- движение ------------------------------------------------------------ #

    def start_floating(self):
        if self._event is None:
            self._event = Clock.schedule_interval(self._tick, 1 / 60)

    def stop_floating(self):
        if self._event is not None:
            self._event.cancel()
            self._event = None
        self._time = 0.0
        self._place(0.0)

    def _tick(self, dt):
        self._time += dt
        self._place(self._time)

    def _place(self, t):
        """Смещает каждый пузырь по синусоиде — плавно, без рывков.

        У всех частей одного пузыря сдвиг общий, поэтому синус считается
        один раз на пузырь, а не на каждую кружку.
        """
        for parts, amp, speed, phase in self._groups:
            shift = math.sin(speed * t + phase) * amp
            for instruction, x, base_y in parts:
                instruction.pos = (x, base_y + shift)


Factory.register("WelcomeDecor", cls=WelcomeDecor)
