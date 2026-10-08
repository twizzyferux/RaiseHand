# -*- coding: utf-8 -*-
"""Страны и коды для ввода номера телефона.

Подсказка появляется, когда человек начинает набирать номер: кроме
кода страны нужно ещё и название — «+7» без подписи не сказать, где
это вообще.

Флагов-эмодзи здесь нет намеренно: в фирменном шрифте нет таких
знаков, и вместо флага получаются пустые квадраты.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Country:
    dial: str          # код набора, например "+7"
    name: str          # название на русском

    @property
    def label(self) -> str:
        return "%s %s" % (self.dial, self.name)


# Порядок = порядок в подсказке: сначала то, что чаще всего выбирают.
COUNTRIES = (
    Country("+7", "Россия"),
    Country("+375", "Беларусь"),
    Country("+7", "Казахстан"),
    Country("+380", "Украина"),
    Country("+996", "Киргизия"),
    Country("+374", "Армения"),
    Country("+995", "Грузия"),
    Country("+994", "Азербайджан"),
    Country("+998", "Узбекистан"),
    Country("+1", "США"),
)

BY_DIAL = {}
for _country in COUNTRIES:
    BY_DIAL.setdefault(_country.dial, _country)


def looks_like_phone(text: str) -> bool:
    """Человек набирает номер, а не почту.

    Почта отсеивается по «@», всё остальное — плюс, цифры и знаки
    номера считаем телефоном.
    """
    value = (text or "").strip()
    if not value or "@" in value:
        return False
    return all(ch.isdigit() or ch in "+- ()" for ch in value)


def dial_for(text: str) -> str:
    """Код страны, который уже набран в начале строки (если есть)."""
    value = (text or "").strip()
    if not value.startswith("+"):
        return ""
    digits = ""
    for ch in value[1:]:
        if not ch.isdigit():
            break
        digits += ch
    # ищем самый длинный подходящий код: +375 важнее, чем +3
    for length in (4, 3, 2, 1):
        candidate = "+" + digits[:length]
        if candidate in BY_DIAL:
            return candidate
    return ""