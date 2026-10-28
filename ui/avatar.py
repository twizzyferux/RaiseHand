# -*- coding: utf-8 -*-
"""Аватар с градиентом пользователя.

Круг с личным градиентом и инициалами поверх. Если пользователь
загрузил свою картинку — показываем её, иначе рисуем градиент.
"""
from kivy.properties import BooleanProperty, NumericProperty
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.widget import Widget

from core import gradients


class GradientAvatar(Widget):
    """Аватар: своя картинка или личный градиент с инициалами.

    У пользователя каждый раз один и тот же градиент — он считается из
    его ID (см. core/gradients.py), поэтому не «прыгает» между запусками.
    Инициалы не дублируются в разметке: аватар сам решает, что показать.

    Кегль и начертание инициалов настраиваются: на разных экранах они
    разные (в списке чатов макет требует тонкие и крупные, на остальных
    — полужирные и компактные).
    """

    # доля кегля от стороны аватара и жирность инициалов
    initials_ratio = NumericProperty(0.36)
    initials_bold = BooleanProperty(True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._initials = ""
        # fit_mode вместо deprecated keep_ratio/allow_stretch (Kivy 2.3+)
        self._picture = Image(mipmap=True, fit_mode="contain")
        self._label = Label(markup=False, halign="center", valign="middle",
                            color=(1, 1, 1, 1), bold=True)
        super().add_widget(self._picture)
        super().add_widget(self._label)
        self.bind(pos=self._sync, size=self._sync)
        self._sync()

    # -- что показывать ---------------------------------------------------- #

    def set_user(self, user, initials=None):
        """Показать пользователя: своя картинка важнее градиента.

        getattr, а не точечный доступ: сюда иногда передают заготовки
        без части полей (например, черновик на шаге регистрации).
        """
        if user is None:
            self._picture.source = ""
            self._initials = ""
            self._label.text = ""
            return

        first = getattr(user, "first_name", "") or ""
        last = getattr(user, "last_name", "") or ""
        picture = getattr(user, "avatar_path", None)
        seed = (getattr(user, "public_id", "") or
                getattr(user, "nickname", "") or str(getattr(user, "id", 0)))

        self._initials = (initials if initials is not None
                          else gradients.initials_for(first, last))
        self._picture.source = picture or gradients.avatar_path(seed)
        self._label.text = "" if picture else self._initials
        self._sync()

    def _sync(self, *_):
        self._picture.pos = self.pos
        self._picture.size = self.size
        self._label.pos = self.pos
        self._label.size = self.size
        # инициалы — примерно 36% от стороны аватара: на 36% буквы
        # не вылезают за круг, а на 40% двузначные уже тесновато
        self._label.font_size = self.width * self.initials_ratio
        self._label.bold = self.initials_bold
