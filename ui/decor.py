"""Живой фон на PNG-спрайтах. Один canvas — много объектов.

Каждый объект — DecorObject: тип (спрайт), позиция, размер, alpha, фаза.
Раз в кадр обновляем фазы и перерисовываем дочерний canvas.

Спрайты лежат в assets/images/decor/decor_<kind>.png.
Если файла нет — объект рисуется векторно (fallback внизу файла).

При изменении размера экрана новые объекты появляются в новых зонах.

Здесь же — WelcomeDecor: цветные «пузыри» внизу стартового экрана.
Они рисуются по координатам макета и мягко покачиваются вверх-вниз,
как дыхание фона.
"""
import math
import os
import random

from kivy.clock import Clock
from kivy.core.image import Image as CoreImage
from kivy.factory import Factory
from kivy.graphics import Color, Line, Ellipse, Rectangle, Canvas, RoundedRectangle
from kivy.metrics import dp
from kivy.uix.widget import Widget

from core.config import BASE_DIR

DECOR_DIR = os.path.join(BASE_DIR, "assets", "images", "decor")

DECOR_RGB = (0.72, 0.72, 0.72)

# Общая прозрачность декора: фон должен «шептать», а не спорить
# с контентом. Умножается на alpha каждого объекта.
DECOR_ALPHA = 0.55

# Длительности фаз жизненного цикла (в секундах)
FADE_IN = 1.4
HOLD_MIN, HOLD_MAX = 3.0, 6.0
FADE_OUT = 1.4
PAUSE_MIN, PAUSE_MAX = 0.8, 3.0

# Потолок количества объектов
MAX_OBJECTS = 40

# Зоны появления: (тип, (x0, y0, x1, y1)) в долях экрана.
# Центр (0.30..0.70 по X, 0.25..0.75 по Y) свободен — там кнопки и текст.
# Также чиста центрально-верхняя полоса (x 0.26..0.74, y 0.68..1.0) —
# там заголовок и логотип, декор им не мешает.
ZONES = [
    ('x2',     (0.75, 0.80, 0.90, 0.92)),
    ('pi',     (0.10, 0.82, 0.25, 0.92)),
    ('plus',   (0.32, 0.44, 0.46, 0.54)),
    ('sqrt',   (0.76, 0.74, 0.90, 0.86)),
    ('sigma',  (0.05, 0.78, 0.18, 0.90)),
    ('atom',   (0.05, 0.55, 0.25, 0.75)),
    ('dna',    (0.78, 0.45, 0.95, 0.70)),
    ('pi',     (0.05, 0.35, 0.15, 0.45)),
    ('e_mc2',  (0.80, 0.25, 0.95, 0.40)),
    ('h2o',    (0.05, 0.20, 0.20, 0.35)),
    ('co2',    (0.80, 0.10, 0.95, 0.25)),
    ('sin',    (0.30, 0.55, 0.45, 0.66)),
    ('cube',   (0.05, 0.05, 0.22, 0.22)),
    ('tri',    (0.78, 0.08, 0.92, 0.22)),
    ('circle', (0.40, 0.05, 0.55, 0.15)),
    ('x2',     (0.05, 0.66, 0.18, 0.76)),
    ('cone',   (0.30, 0.05, 0.45, 0.18)),
    ('pyramid',(0.55, 0.05, 0.70, 0.18)),
    ('sphere', (0.75, 0.30, 0.90, 0.45)),
    ('delta',  (0.15, 0.40, 0.28, 0.55)),
    ('integral',(0.52, 0.55, 0.66, 0.66)),
    ('abc',    (0.35, 0.30, 0.50, 0.45)),
    ('fma',    (0.60, 0.35, 0.75, 0.50)),
    ('ohm',    (0.10, 0.60, 0.25, 0.75)),
]

# Уникальные типы (порядок первого появления сохраняется)
KINDS = list(dict.fromkeys(kind for kind, _ in ZONES))

# Тип -> список его зон (для равномерного распределения типов)
KIND_ZONES = {}
for _kind, _bounds in ZONES:
    KIND_ZONES.setdefault(_kind, []).append(_bounds)


def sprite_path(kind):
    """Путь к PNG-спрайту объекта или '', если файла нет."""
    path = os.path.join(DECOR_DIR, "decor_%s.png" % kind)
    return path if os.path.exists(path) else ""


class DecorObject:
    """Один декоративный объект. Не виджет — просто данные."""

    def __init__(self, kind, bounds):
        self.kind = kind              # 'atom', 'dna', 'x2', ...
        self.bounds = bounds          # (x0, y0, x1, y1) — в долях
        self.x = 0.0
        self.y = 0.0
        self.size = 0.0               # в пикселях (сторона бокса)
        self.alpha = 0.0
        self.phase = 'idle'           # idle | fade_in | hold | fade_out
        self.timer = 0.0
        self.duration = 0.0

    def start_cycle(self, parent_w, parent_h, delay):
        """Начать жизненный цикл с случайной задержкой."""
        self.phase = 'idle'
        self.timer = -delay           # отрицательный timer = ещё ждём
        self.alpha = 0.0
        self._pick_random_position(parent_w, parent_h)

    def _pick_random_position(self, pw, ph):
        x0, y0, x1, y1 = self.bounds
        self.x = pw * random.uniform(x0, x1)
        self.y = ph * random.uniform(y0, y1)
        # Размер зависит от меньшей стороны экрана — спрайты не растягиваются,
        # а просто появляются крупнее/мелче на больших экранах.
        base = min(pw, ph)
        self.size = random.uniform(0.10, 0.17) * base

    def update(self, dt, pw, ph):
        """Вызывается каждый кадр."""
        self.timer += dt

        if self.phase == 'idle':
            if self.timer >= 0:
                self.phase = 'fade_in'
                self.timer = 0.0
                self.duration = FADE_IN

        elif self.phase == 'fade_in':
            # Появление — только прозрачность, объект стоит на месте
            self.alpha = min(1.0, self.timer / self.duration)
            if self.timer >= self.duration:
                self.phase = 'hold'
                self.timer = 0.0
                self.duration = random.uniform(HOLD_MIN, HOLD_MAX)
                self.alpha = 1.0

        elif self.phase == 'hold':
            # Просто стоит на месте с полной прозрачностью
            if self.timer >= self.duration:
                self.phase = 'fade_out'
                self.timer = 0.0
                self.duration = FADE_OUT

        elif self.phase == 'fade_out':
            # Затухание — только прозрачность
            self.alpha = max(0.0, 1.0 - self.timer / self.duration)
            if self.timer >= self.duration:
                self.alpha = 0.0
                self.phase = 'idle'
                self.timer = 0.0
                self.duration = 0.0
                # Меняем позицию и снова ждём
                self._pick_random_position(pw, ph)
                self.timer = -random.uniform(PAUSE_MIN, PAUSE_MAX)


class DecorBackground(Widget):
    """Один виджет — один canvas — все объекты."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._objects = []
        self._textures = {}           # kind -> GLTexture (спрайт)
        self._kind_bag = []           # перемешанная колода типов
        self._spawned = False
        self._last_size = (0, 0)
        self._target_count = 0

        # Белый фон + дочерний canvas для объектов — на одном canvas
        with self.canvas:
            # Мягкий фон #F7F9FD — не стерильный чистый белый
            self._bg_color = Color(0.969, 0.976, 0.992, 1)
            self._bg_rect = Rectangle(pos=self.pos, size=self.size)
            # Дочерний canvas: в него попадают Color/Rectangle/Ellipse,
            # созданные внутри `with self._fx:` в _redraw.
            self._fx = Canvas()

        self.bind(pos=self._on_resize, size=self._on_resize)
        Clock.schedule_interval(self._tick, 1 / 60)
        Clock.schedule_once(self._spawn, 0.1)

    def _on_resize(self, *args):
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size

    def _calculate_target_count(self, pw, ph):
        """Сколько объектов нужно для этого размера экрана.

        Зависит от корня площади: на телефоне (~10 шт), на большом
        экране больше (~24).
        """
        area = max(pw * ph, 1)
        count = int(10 * math.sqrt(area / 350_000))
        return max(4, min(count, MAX_OBJECTS))

    def _spawn(self, *args):
        if self._spawned:
            return
        if self.size[0] < 50:
            Clock.schedule_once(self._spawn, 0.1)
            return
        self._spawned = True
        self._load_textures()
        self._ensure_object_count()

    def _load_textures(self):
        """Загрузить PNG-спрайты в GL-текстуры.

        Если файла нет — kind не попадёт в self._textures и сработает
        векторный fallback (см. DRAWERS внизу файла).
        """
        for kind in KINDS:
            if kind in self._textures:
                continue
            path = sprite_path(kind)
            if not path:
                continue
            try:
                self._textures[kind] = CoreImage(path).texture
            except Exception:
                # Битый PNG — рисуем векторно, приложение не падает
                pass

    def _next_kind(self):
        """Следующий тип из перемешанной колоды.

        Гарантирует равномерное распределение: каждый тип появляется
        ровно один раз за круг, никаких кластеров из одних ×² сверху.
        """
        if not self._kind_bag:
            self._kind_bag = KINDS[:]
            random.shuffle(self._kind_bag)
        return self._kind_bag.pop()

    def _ensure_object_count(self):
        """Добавить объекты если нужно (при resize)."""
        pw, ph = self.size
        self._target_count = self._calculate_target_count(pw, ph)

        while len(self._objects) < self._target_count:
            kind = self._next_kind()
            bounds = random.choice(KIND_ZONES[kind])
            obj = DecorObject(kind, bounds)
            obj.start_cycle(pw, ph, random.uniform(0, 4))
            self._objects.append(obj)

    def _fit_size(self, tex, box):
        """Вписать спрайт в бокс `box`, сохраняя его пропорции."""
        tw, th = tex.width, tex.height
        if tw <= 0 or th <= 0:
            return box, box
        scale = box / float(max(tw, th))
        return tw * scale, th * scale

    def _tick(self, dt):
        if not self._objects:
            return
        pw, ph = self.size
        changed = False

        # При resize — добавляем новые объекты если нужно
        if self._last_size != (pw, ph):
            self._last_size = (pw, ph)
            self._ensure_object_count()
            for obj in self._objects:
                obj._pick_random_position(pw, ph)
            changed = True

        # Обновляем состояние (перерисовка нужна при смене прозрачности)
        before = tuple(round(o.alpha, 3) for o in self._objects)
        for obj in self._objects:
            obj.update(dt, pw, ph)
        after = tuple(round(o.alpha, 3) for o in self._objects)

        # Перерисовываем только если прозрачность изменилась
        if changed or before != after:
            self._redraw()

    def _redraw(self):
        # Очищаем только дочерний canvas объектов (белый фон не трогаем)
        self._fx.clear()
        with self._fx:
            for obj in self._objects:
                if obj.alpha <= 0.01:
                    continue

                # Прозрачность объекта с общим приглушением декора
                a = obj.alpha * DECOR_ALPHA
                tex = self._textures.get(obj.kind)
                if tex is not None:
                    # Спрайт: белый Color умножается на текстуру,
                    # alpha управляет общим затуханием
                    Color(1, 1, 1, a)
                    w, h = self._fit_size(tex, obj.size)
                    Rectangle(texture=tex,
                              pos=(obj.x - w / 2, obj.y - h / 2),
                              size=(w, h))
                else:
                    # Fallback: векторная отрисовка
                    drawer = DRAWERS.get(obj.kind)
                    if drawer:
                        drawer(self.canvas, obj.x, obj.y, obj.size,
                               a, obj.kind)


# ============================================================
#  ВЕКТОРНЫЙ FALLBACK — используется только если PNG-файла нет
# ============================================================

def _draw_atom(canvas, x, y, s, a, _):
    Color(*DECOR_RGB, a * 0.6)
    r = s / 2
    for ang_deg in (0, 60, 120):
        ang = math.radians(ang_deg)
        pts = []
        for i in range(0, 361, 10):
            t = math.radians(i)
            ex = r * math.cos(t)
            ey = r * 0.38 * math.sin(t)
            px = x + ex * math.cos(ang) - ey * math.sin(ang)
            py = y + ex * math.sin(ang) + ey * math.cos(ang)
            pts.extend([px, py])
        Line(points=pts, width=1.2)

    Color(*DECOR_RGB, a * 0.85)
    nr = r * 0.16
    Ellipse(pos=(x - nr, y - nr), size=(nr * 2, nr * 2))

    dot = r * 0.10
    for t_deg in (30, 150, 270):
        t = math.radians(t_deg)
        ex = r * math.cos(t)
        ey = r * 0.38 * math.sin(t)
        Ellipse(pos=(x + ex - dot, y + ey - dot), size=(dot * 2, dot * 2))


def _draw_dna(canvas, x, y, s, a, _):
    Color(*DECOR_RGB, a * 0.55)
    h = s
    w = s * 0.35
    for phase in (0, math.pi):
        pts = []
        for i in range(0, 41):
            t = i / 40
            yy = y - h / 2 + t * h
            xx = x + w * math.sin(t * 3.5 * math.pi + phase)
            pts.extend([xx, yy])
        Line(points=pts, width=1.4)

    Color(*DECOR_RGB, a * 0.4)
    for i in range(1, 10):
        t = i / 10
        yy = y - h / 2 + t * h
        x1 = x + w * math.sin(t * 3.5 * math.pi)
        x2 = x + w * math.sin(t * 3.5 * math.pi + math.pi)
        Line(points=[x1, yy, x2, yy], width=1)


def _draw_cube(canvas, x, y, s, a, _):
    Color(*DECOR_RGB, a * 0.5)
    h = s / 2
    dx = s * 0.35
    dy = s * 0.3
    p1 = (x - h, y - h)
    p2 = (x + h, y - h)
    p3 = (x + h, y + h)
    p4 = (x - h, y + h)
    p5 = (p1[0] + dx, p1[1] + dy)
    p6 = (p2[0] + dx, p2[1] + dy)
    p7 = (p3[0] + dx, p3[1] + dy)
    p8 = (p4[0] + dx, p4[1] + dy)
    Line(points=[*p1, *p2, *p3, *p4, *p1], width=1.2)
    Line(points=[*p5, *p6, *p7, *p8, *p5], width=1.2)
    Line(points=[*p1, *p5], width=1.0)
    Line(points=[*p2, *p6], width=1.0)
    Line(points=[*p3, *p7], width=1.0)
    Line(points=[*p4, *p8], width=1.0)


def _draw_x2(canvas, x, y, s, a, _):
    Color(*DECOR_RGB, a * 0.7)
    pad = s * 0.3
    Line(points=[x - pad, y - pad, x + pad, y + pad], width=1.8)
    Line(points=[x - pad, y + pad, x + pad, y - pad], width=1.8)
    Color(*DECOR_RGB, a * 0.55)
    d = s * 0.25
    bx, by = x + pad, y + pad
    Line(points=[
        bx, by,
        bx + d * 0.6, by + d * 0.4,
        bx + d * 0.6, by + d * 0.7,
        bx, by + d,
        bx - d * 0.2, by + d * 0.8,
    ], width=1.2)


def _draw_pi(canvas, x, y, s, a, _):
    Color(*DECOR_RGB, a * 0.65)
    w = s * 0.7
    h = s * 0.7
    Line(points=[x - w / 2, y + h / 2, x + w / 2, y + h / 2], width=2)
    Line(points=[x - w / 4, y + h / 2, x - w / 4, y - h / 2], width=1.8)
    Line(points=[x + w / 4, y + h / 2, x + w / 4, y - h / 2], width=1.8)


def _draw_plus(canvas, x, y, s, a, _):
    Color(*DECOR_RGB, a * 0.6)
    w = s * 0.5
    Line(points=[x - w, y, x + w, y], width=1.8)
    Line(points=[x, y - w, x, y + w], width=1.8)


def _draw_tri(canvas, x, y, s, a, _):
    Color(*DECOR_RGB, a * 0.55)
    h = s / 2
    p1 = (x, y + h)
    p2 = (x - h, y - h)
    p3 = (x + h, y - h)
    Line(points=[*p1, *p2, *p3, *p1], width=1.4)


def _draw_circle(canvas, x, y, s, a, _):
    Color(*DECOR_RGB, a * 0.55)
    r = s / 2
    Ellipse(pos=(x - r, y - r), size=(s, s))
    Color(*DECOR_RGB, a * 0.4)
    Line(points=[x, y, x + r, y], width=1)


def _draw_sqrt(canvas, x, y, s, a, _):
    Color(*DECOR_RGB, a * 0.65)
    w = s * 0.8
    h = s * 0.5
    Line(points=[x - w * 0.3, y + h * 0.3, x - w * 0.1, y + h * 0.6], width=1.8)
    Line(points=[x - w * 0.1, y + h * 0.6, x + w * 0.5, y - h * 0.4], width=1.8)
    Line(points=[x - w * 0.5, y - h * 0.2, x + w * 0.5, y - h * 0.2], width=1.8)


def _draw_sigma(canvas, x, y, s, a, _):
    Color(*DECOR_RGB, a * 0.65)
    w = s * 0.6
    h = s * 0.6
    Line(points=[
        x + w / 2, y + h / 2,
        x - w / 2, y + h / 2,
        x, y,
        x - w / 2, y - h / 2,
        x + w / 2, y - h / 2,
    ], width=1.8)


def _draw_e_mc2(canvas, x, y, s, a, _):
    Color(*DECOR_RGB, a * 0.6)
    w = s * 0.9
    h = s * 0.4
    Line(points=[x - w * 0.4, y + h / 2, x - w * 0.4, y - h / 2], width=1.8)
    Line(points=[x - w * 0.4, y + h / 2, x - w * 0.1, y + h / 2], width=1.8)
    Line(points=[x - w * 0.4, y, x - w * 0.15, y], width=1.8)
    Line(points=[x - w * 0.4, y - h / 2, x - w * 0.1, y - h / 2], width=1.8)
    Line(points=[x - w * 0.05, y + h * 0.15, x + w * 0.1, y + h * 0.15], width=1.8)
    Line(points=[x - w * 0.05, y - h * 0.15, x + w * 0.1, y - h * 0.15], width=1.8)
    Line(points=[x + w * 0.15, y - h / 2, x + w * 0.15, y + h * 0.3], width=1.8)
    Line(points=[x + w * 0.15, y + h * 0.3, x + w * 0.3, y + h * 0.1], width=1.8)
    Line(points=[x + w * 0.3, y + h * 0.1, x + w * 0.45, y + h * 0.3], width=1.8)
    Line(points=[x + w * 0.45, y + h * 0.3, x + w * 0.45, y - h / 2], width=1.8)
    Color(*DECOR_RGB, a * 0.5)
    d = s * 0.15
    bx, by = x + w * 0.5, y + h * 0.3
    Line(points=[
        bx, by,
        bx + d * 0.6, by + d * 0.4,
        bx + d * 0.6, by + d * 0.7,
        bx, by + d,
        bx - d * 0.2, by + d * 0.8,
    ], width=1.2)


def _draw_h2o(canvas, x, y, s, a, _):
    Color(*DECOR_RGB, a * 0.6)
    w = s * 0.8
    h = s * 0.4
    Line(points=[x - w * 0.4, y + h / 2, x - w * 0.4, y - h / 2], width=1.8)
    Line(points=[x - w * 0.25, y + h / 2, x - w * 0.25, y - h / 2], width=1.8)
    Line(points=[x - w * 0.4, y, x - w * 0.25, y], width=1.8)
    Color(*DECOR_RGB, a * 0.5)
    d = s * 0.12
    bx, by = x - w * 0.2, y - h * 0.3
    Line(points=[
        bx, by,
        bx + d * 0.5, by + d * 0.3,
        bx + d * 0.5, by + d * 0.6,
        bx, by + d,
        bx - d * 0.15, by + d * 0.7,
    ], width=1.0)
    Color(*DECOR_RGB, a * 0.6)
    r = h * 0.35
    Ellipse(pos=(x + w * 0.15 - r, y - r), size=(r * 2, r * 2))


def _draw_co2(canvas, x, y, s, a, _):
    Color(*DECOR_RGB, a * 0.6)
    w = s * 0.8
    h = s * 0.4
    Line(points=[x - w * 0.35, y + h / 2, x - w * 0.35, y - h / 2], width=1.8)
    Line(points=[x - w * 0.35, y + h / 2, x - w * 0.15, y + h / 2], width=1.8)
    Line(points=[x - w * 0.35, y - h / 2, x - w * 0.15, y - h / 2], width=1.8)
    r = h * 0.35
    Ellipse(pos=(x + w * 0.05 - r, y - r), size=(r * 2, r * 2))
    Color(*DECOR_RGB, a * 0.5)
    d = s * 0.12
    bx, by = x + w * 0.3, y - h * 0.3
    Line(points=[
        bx, by,
        bx + d * 0.5, by + d * 0.3,
        bx + d * 0.5, by + d * 0.6,
        bx, by + d,
        bx - d * 0.15, by + d * 0.7,
    ], width=1.0)


def _draw_sin(canvas, x, y, s, a, _):
    Color(*DECOR_RGB, a * 0.6)
    w = s * 0.7
    h = s * 0.35
    Line(points=[
        x - w * 0.3, y + h / 2,
        x - w * 0.4, y + h * 0.2,
        x - w * 0.2, y,
        x - w * 0.4, y - h * 0.2,
        x - w * 0.3, y - h / 2,
    ], width=1.8)
    Line(points=[x - w * 0.05, y - h / 2, x - w * 0.05, y + h * 0.3], width=1.8)
    Ellipse(pos=(x - w * 0.05 - 1.5, y + h * 0.4), size=(3, 3))
    Line(points=[x + w * 0.1, y - h / 2, x + w * 0.1, y + h * 0.3], width=1.8)
    Line(points=[x + w * 0.1, y + h * 0.3, x + w * 0.3, y + h * 0.1], width=1.8)
    Line(points=[x + w * 0.3, y + h * 0.1, x + w * 0.3, y - h / 2], width=1.8)


def _draw_cone(canvas, x, y, s, a, _):
    Color(*DECOR_RGB, a * 0.55)
    w = s * 0.6
    h = s * 0.7
    Ellipse(pos=(x - w / 2, y - h / 2), size=(w, h * 0.3))
    Line(points=[x - w / 2, y - h / 2 + h * 0.15, x, y + h / 2], width=1.4)
    Line(points=[x + w / 2, y - h / 2 + h * 0.15, x, y + h / 2], width=1.4)


def _draw_pyramid(canvas, x, y, s, a, _):
    Color(*DECOR_RGB, a * 0.55)
    w = s * 0.6
    h = s * 0.6
    p1 = (x, y - h / 2)
    p2 = (x + w / 2, y)
    p3 = (x, y + h / 2)
    p4 = (x - w / 2, y)
    Line(points=[*p1, *p2, *p3, *p4, *p1], width=1.4)
    top = (x, y + h * 0.8)
    Line(points=[*p1, *top], width=1.4)
    Line(points=[*p2, *top], width=1.4)
    Line(points=[*p3, *top], width=1.4)
    Line(points=[*p4, *top], width=1.4)


def _draw_sphere(canvas, x, y, s, a, _):
    Color(*DECOR_RGB, a * 0.55)
    r = s / 2
    Ellipse(pos=(x - r, y - r), size=(s, s))
    Color(*DECOR_RGB, a * 0.4)
    eq_pts = []
    for i in range(0, 361, 10):
        t = math.radians(i)
        eq_pts.extend([x + r * math.cos(t), y + r * 0.3 * math.sin(t)])
    Line(points=eq_pts, width=1)


def _draw_delta(canvas, x, y, s, a, _):
    Color(*DECOR_RGB, a * 0.65)
    w = s * 0.6
    h = s * 0.6
    Line(points=[
        x, y + h / 2,
        x - w / 2, y - h / 2,
        x + w / 2, y - h / 2,
        x, y + h / 2,
    ], width=1.8)


def _draw_integral(canvas, x, y, s, a, _):
    Color(*DECOR_RGB, a * 0.65)
    h = s * 0.7
    w = s * 0.3
    Line(points=[x + w / 2, y + h / 2, x + w * 0.3, y + h / 2], width=1.8)
    Line(points=[x + w * 0.3, y + h / 2, x, y + h * 0.2], width=1.8)
    Line(points=[x, y - h * 0.2, x - w * 0.3, y - h / 2], width=1.8)
    Line(points=[x - w * 0.3, y - h / 2, x - w / 2, y - h / 2], width=1.8)


def _draw_abc(canvas, x, y, s, a, _):
    Color(*DECOR_RGB, a * 0.55)
    w = s * 0.9
    h = s * 0.3
    Line(points=[x - w * 0.4, y - h / 2, x - w * 0.4, y + h * 0.3], width=1.5)
    Line(points=[x - w * 0.4, y + h * 0.3, x - w * 0.25, y + h * 0.1], width=1.5)
    Line(points=[x - w * 0.25, y + h * 0.1, x - w * 0.25, y - h / 2], width=1.5)
    Color(*DECOR_RGB, a * 0.4)
    d = s * 0.1
    bx, by = x - w * 0.2, y + h * 0.3
    Line(points=[
        bx, by,
        bx + d * 0.5, by + d * 0.3,
        bx + d * 0.5, by + d * 0.6,
        bx, by + d,
        bx - d * 0.15, by + d * 0.7,
    ], width=1.0)
    Color(*DECOR_RGB, a * 0.55)
    Line(points=[x - w * 0.1, y, x + w * 0.05, y], width=1.5)
    Line(points=[x - w * 0.025, y - h * 0.2, x - w * 0.025, y + h * 0.2], width=1.5)
    Line(points=[x + w * 0.1, y - h / 2, x + w * 0.1, y + h * 0.3], width=1.5)
    Line(points=[x + w * 0.1, y + h * 0.3, x + w * 0.25, y + h * 0.1], width=1.5)
    Line(points=[x + w * 0.25, y + h * 0.1, x + w * 0.25, y - h / 2], width=1.5)
    Color(*DECOR_RGB, a * 0.4)
    bx, by = x + w * 0.3, y + h * 0.3
    Line(points=[
        bx, by,
        bx + d * 0.5, by + d * 0.3,
        bx + d * 0.5, by + d * 0.6,
        bx, by + d,
        bx - d * 0.15, by + d * 0.7,
    ], width=1.0)
    Color(*DECOR_RGB, a * 0.55)
    Line(points=[x + w * 0.4, y + h * 0.15, x + w * 0.55, y + h * 0.15], width=1.5)
    Line(points=[x + w * 0.4, y - h * 0.15, x + w * 0.55, y - h * 0.15], width=1.5)


def _draw_fma(canvas, x, y, s, a, _):
    Color(*DECOR_RGB, a * 0.6)
    w = s * 0.7
    h = s * 0.35
    Line(points=[x - w * 0.35, y + h / 2, x - w * 0.35, y - h / 2], width=1.8)
    Line(points=[x - w * 0.35, y + h / 2, x - w * 0.1, y + h / 2], width=1.8)
    Line(points=[x - w * 0.35, y, x - w * 0.15, y], width=1.8)
    Line(points=[x - w * 0.05, y + h * 0.15, x + w * 0.1, y + h * 0.15], width=1.8)
    Line(points=[x - w * 0.05, y - h * 0.15, x + w * 0.1, y - h * 0.15], width=1.8)
    Line(points=[x + w * 0.15, y - h / 2, x + w * 0.15, y + h * 0.3], width=1.8)
    Line(points=[x + w * 0.15, y + h * 0.3, x + w * 0.3, y + h * 0.1], width=1.8)
    Line(points=[x + w * 0.3, y + h * 0.1, x + w * 0.45, y + h * 0.3], width=1.8)
    Line(points=[x + w * 0.45, y + h * 0.3, x + w * 0.45, y - h / 2], width=1.8)


def _draw_ohm(canvas, x, y, s, a, _):
    Color(*DECOR_RGB, a * 0.65)
    w = s * 0.5
    h = s * 0.6
    r = w / 2
    Ellipse(pos=(x - r, y - h * 0.3), size=(w, h * 0.6))
    Line(points=[x - w * 0.3, y - h * 0.3, x - w * 0.3, y - h / 2], width=1.8)
    Line(points=[x + w * 0.3, y - h * 0.3, x + w * 0.3, y - h / 2], width=1.8)


DRAWERS = {
    'atom':     _draw_atom,
    'dna':      _draw_dna,
    'cube':     _draw_cube,
    'x2':       _draw_x2,
    'pi':       _draw_pi,
    'plus':     _draw_plus,
    'tri':      _draw_tri,
    'circle':   _draw_circle,
    'sqrt':     _draw_sqrt,
    'sigma':    _draw_sigma,
    'e_mc2':    _draw_e_mc2,
    'h2o':      _draw_h2o,
    'co2':      _draw_co2,
    'sin':      _draw_sin,
    'cone':     _draw_cone,
    'pyramid':  _draw_pyramid,
    'sphere':   _draw_sphere,
    'delta':    _draw_delta,
    'integral': _draw_integral,
    'abc':      _draw_abc,
    'fma':      _draw_fma,
    'ohm':      _draw_ohm,
}


# ============================================================================
#  Пузыри на стартовом экране
# ============================================================================

# Каждый пузырь: (цвет, x, y, кружки-хвостики [(x, y, диаметр)],
#                  амплитуда покачивания, период, фаза)
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


class WelcomeDecor(Widget):
    """Цветные «пузыри» внизу стартового экрана.

    Рисуются один раз по координатам макета, а потом мягко
    покачиваются вверх-вниз: у каждого пузыря своя амплитуда, период
    и фаза, поэтому они не ходят строем. Амплитуда небольшая (7-11
    единиц), чтобы фон оставался фоном и не спорил с текстом.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._groups = []          # список (инструкции, база_y, амплитуда, период, фаза)
        self._time = 0.0
        self._event = None
        self._build()

    def _build(self):
        with self.canvas:
            for color, x, y, dots, amp, period, phase in WELCOME_BUBBLES:
                Color(rgba=color)
                bubble = RoundedRectangle(pos=(dp(x), dp(y)),
                                          size=(dp(BUBBLE_W), dp(BUBBLE_H)),
                                          radius=[dp(BUBBLE_R), ])
                circles = []
                for cx, cy, d in dots:
                    circles.append(Ellipse(pos=(dp(cx), dp(cy)),
                                           size=(dp(d), dp(d))))
                self._groups.append({
                    "instructions": [bubble] + circles,
                    "base": [dp(y)] + [dp(dy) for _, dy, _ in dots],
                    "amp": dp(amp),
                    "period": period,
                    "phase": phase,
                })

    # -- движение ------------------------------------------------------------ #

    def start_floating(self):
        if self._event is None:
            self._event = Clock.schedule_interval(self._tick, 1 / 60)

    def stop_floating(self):
        if self._event is not None:
            self._event.cancel()
            self._event = None
        self._place(0.0)

    def _tick(self, dt):
        self._time += dt
        self._place(self._time)

    def _place(self, t):
        """Смещает каждый пузырь по синусоиде — плавно, без рывков."""
        for group in self._groups:
            wave = math.sin((2 * math.pi * t / group["period"]) + group["phase"])
            shift = wave * group["amp"]
            for instr, base_y in zip(group["instructions"], group["base"]):
                instr.pos = (instr.pos[0], base_y + shift)


Factory.register("WelcomeDecor", cls=WelcomeDecor)