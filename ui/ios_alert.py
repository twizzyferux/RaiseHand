"""Окно в айфонском виде.

Зачем
-----
Серое окно Kivy в айфонском приложении выглядит как чужеродное
пятно: толстая рамка, кнопка во всю ширину, чужой шрифт. Системное
окно iOS выглядит как все остальные и ведёт себя так же.

ПОЧЕМУ ЭТО НЕ СИСТЕМНЫЙ АЛЕРТ, А НАРИСОВАННЫЙ
---------------------------------------------
Системный класс UIAlertController вызвать нечем, и это установлено
фактами, а не предположением.

Мост в iOS у нас - pyobjus. У него есть таблица селекторов
(protocols.py, генерируется из протоколов Objective-C), и в ней нет
НИ ОДНОГО протокола UIAlert:

  initWithTitle:message:preferredStyle:      - отсутствует
  actionWithTitle:style:handler:             - отсутствует
  presentViewController:animated:completion: - отсутствует
  safeAreaInsets                             - отсутствует

pyobjus создаёт метод только для селектора, который есть в таблице.
Нет в таблице - нет метода, обращение падает с AttributeError. На
телефоне так и вышло: "'UIAlertController' object has no attribute
'initWithTitle_message_preferredStyle_'". Тем же объясняется и то,
что безопасные отступы всегда приходили нулевыми: safeAreaInsets в
таблице тоже нет.

Поэтому окно рисуется здесь, а размеры и вид взяты из системной
спецификации iOS. Для простого окна из заголовка, текста и одной
кнопки разницы с настоящим не видно.

Размеры (в точках iOS)
----------------------
Ширина окна 270, скругление 14, высота кнопки 44. Заголовок 17
полужирный, текст 13 серый, кнопка 17 синяя #007AFF. Над кнопкой -
тонкая линия-разделитель.

ПОЧЕМУ ModalView, А НЕ ПРОСТО WIDGET В ОКНЕ
----------------------------------------
Первая версия добавляла свой виджет прямо в Window и рисовала
карточку в его canvas.before. На снимке весь экран выходил
перекошенным и задвоенным: состояние графики от карточки
оставалось на стеке и тянуло за собой следующий кадр.

ModalView делает это сам - он и есть штатный механизм Kivy для
всплывающих окон, с затемнением и стеком. Своя отрисовка поверх
него остаётся только карточкой и тремя надписями.
"""

from kivy.animation import Animation
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.metrics import dp, sp
from kivy.uix.label import Label
from kivy.uix.modalview import ModalView

# Цвета системного окна в светлом оформлении.
BG = (0.98, 0.98, 0.99, 0.97)
TITLE = (0, 0, 0, 1)
MESSAGE = (0, 0, 0, 0.6)
BUTTON = (0, 0.478, 1, 1)                # #007AFF
SEPARATOR = (0.776, 0.776, 0.784, 1)
BACKDROP = (0, 0, 0, 0.36)

# Геометрия в точках iOS.
WIDTH = 270
RADIUS = 14
PAD_X = 16
PAD_TOP = 19
PAD_BOTTOM = 19
GAP = 4
BUTTON_H = 44
# Толщина линии-разделителя. Раньше эта величина называлась так же,
# как её цвет, и цвет перебивался числом: Kivy получал вместо цвета
# число и падал.
SEPARATOR_H = 0.5

TITLE_SIZE = 17
MESSAGE_SIZE = 13
BUTTON_SIZE = 17

__all__ = ["show"]


def _window_centre():
    """Середина окна экрана.

    Считается от окна, а не от самого ModalView. ModalView центрируется
    сам и меняет свою позицию уже после того, как вёрстка окна
    посчитана, - брать его center_x значит зависеть от порядка событий:
    в одной сборке карточка вставала по центру, в другой на 175
    пикселей левее. От окна результат не зависит ни от чего.
    """
    from kivy.core.window import Window
    return Window.size[0] / 2.0, Window.size[1] / 2.0


class _Alert(ModalView):
    """Окно: затемнение от ModalView, карточка и надписи нарисованы здесь."""

    def __init__(self, title, message, button, on_close, **kwargs):
        kwargs.setdefault("size_hint", (None, None))
        kwargs.setdefault("auto_dismiss", False)
        kwargs.setdefault("background", "")
        kwargs.setdefault("background_color", (0, 0, 0, 0))
        kwargs.setdefault("overlay_color", BACKDROP)
        # border и separator_color у ModalView этой версии нет: Kivy
        # отвергает незнакомое свойство при создании. Проверено пробой.
        kwargs.pop("separator_color", None)
        kwargs.pop("border", None)
        super().__init__(**kwargs)
        self.on_close = on_close
        self.title_text = title
        self.message_text = message
        self.button_text = button
        self.card_w = dp(WIDTH)
        self._built = False
        self._build()
        self._built = True
        self._place()

    # -- построение ---------------------------------------------------------- #

    def _build(self):
        self.title_label = Label(
            text=self.title_text, markup=True, size_hint=(None, None),
            color=TITLE, bold=True, font_size=sp(TITLE_SIZE),
            halign="center", valign="middle", line_height=1.2)
        self.message_label = Label(
            text=self.message_text, markup=True, size_hint=(None, None),
            color=MESSAGE, font_size=sp(MESSAGE_SIZE),
            halign="center", valign="middle", line_height=1.3)
        self.button_label = Label(
            text=self.button_text, size_hint=(None, None),
            color=BUTTON, font_size=sp(BUTTON_SIZE),
            halign="center", valign="middle")

        with self.canvas.before:
            Color(rgba=BG)
            self._card = RoundedRectangle(pos=self.pos, size=self.size,
                                          radius=[dp(RADIUS)])
            Color(rgba=SEPARATOR)
            self._sep = Rectangle(pos=self.pos, size=(0, dp(SEPARATOR_H)))

        for widget in (self.title_label, self.message_label,
                       self.button_label):
            self.add_widget(widget)

    # -- размеры и положение ------------------------------------------------- #

    def _place(self, *_):
        """Пересчитать размеры под текст и поставить всё по центру."""
        if not self._built:
            return

        inner = self.card_w - dp(PAD_X * 2)

        self.title_label.size = (inner, self.title_label.texture_size[1])
        if self.title_label.texture_size[1] > sp(TITLE_SIZE) * 2.4:
            self.title_label.height = sp(TITLE_SIZE) * 2.4
        title_h = self.title_label.height

        self.message_label.text_size = (inner, None)
        self.message_label.texture_update()
        message_h = max(dp(0), self.message_label.texture_size[1])

        card_h = (dp(PAD_TOP) + title_h + dp(GAP) + message_h
                  + dp(PAD_BOTTOM) + dp(BUTTON_H))

        cx, cy = _window_centre()

        # Окно iOS стоит чуть выше середины экрана, а не ровно в ней.
        cy += dp(24)

        top = cy + card_h / 2.0
        y = top - dp(PAD_TOP) - title_h
        self.title_label.pos = (cx - inner / 2.0, y)
        y -= dp(GAP) + message_h
        self.message_label.pos = (cx - inner / 2.0, y)

        btn_y = cy - card_h / 2.0
        self.button_label.size = (inner, dp(BUTTON_H))
        self.button_label.pos = (cx - inner / 2.0,
                                 btn_y + (dp(BUTTON_H) - dp(BUTTON_SIZE) * 1.3)
                                 / 2.0)

        left = cx - self.card_w / 2.0
        bottom = cy - card_h / 2.0
        self._card.pos = (left, bottom)
        self._card.size = (self.card_w, card_h)
        self._card.radius = [dp(RADIUS)]

        # Разделитель над кнопкой тянется по всей ширине карточки, а не
        # по полям: так он выглядит в системном окне.
        self._sep.pos = (left, btn_y + dp(BUTTON_H))
        self._sep.size = (self.card_w, dp(SEPARATOR_H))

        # Размер самого ModalView равен карточке: за него ничего не
        # кликается и ничего не рисуется.
        self.size = (self.card_w, card_h)

    # -- ввод ---------------------------------------------------------------- #

    def on_touch_down(self, touch):
        if self.button_label.collide_point(*touch.pos):
            self.dismiss()
            return True
        # Нажатие мимо кнопки окно не закрывает: системное так же.
        return True

    def on_touch_up(self, touch):
        return True

    # -- закрытие ------------------------------------------------------------ #

    def dismiss(self, *_):
        if self.on_close is not None:
            try:
                self.on_close()
            except Exception:
                pass
        self.on_close = None
        super().dismiss()


def show(title: str, message: str, button: str = "Понятно",
         on_close=None) -> bool:
    """Показать окно в айфонском виде. Всегда True."""
    from kivy.core.window import Window

    box = _Alert(title=title, message=message, button=button,
                 on_close=on_close)

    # Вёрстка окна пересчитывается при смене размера экрана.
    #
    # Это не украшение, а необходимость: размер окна может измениться
    # уже после того, как окно сообщения создано. На ПК так и выходит -
    # размер подбирается под свободное место на экране, и это происходит
    # позже создания. Посчитанная по старому размеру вёрстка уводила
    # карточку на 175 пикселей вправо. На телефоне то же самое случится
    # при повороте экрана.
    def on_size(*_):
        box._place()

    Window.bind(size=on_size)
    box.bind(on_dismiss=lambda *_: Window.unbind(size=on_size))

    box.open()
    box._place()
    # И ещё раз на следующем кадре. Размер окна на ПК меняется уже
    # после создания окна сообщения, и порядок этих событий не
    # гарантирован: то ли привязка выше успела отработать и потом всё
    # испортил этот самый вызов, то ли наоборот. Пересчёт на кадр
    # позже выполняется после всех подмен размера и потому даёт
    # одинаковый результат при любом порядке.
    from kivy.clock import Clock
    Clock.schedule_once(lambda *_: box._place(), 0)
    # Появление как у iOS - проявление, без роста размера: рост
    # требовал пересчитывать вёрстку каждый кадр и давал перекос.
    box.opacity = 0.0
    Animation(opacity=1, d=0.18, t="out_quad").start(box)
    return True