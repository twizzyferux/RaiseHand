# -*- coding: utf-8 -*-
"""Подсказки школ по городу и стране.

Сначала ищем в таблице schools (РФ / РК / РБ), затем — в локальном
фолбэке, чтобы подсказки работали даже до запуска load_schools.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import or_, select

from core.models import CountryCode, School
from core.orm import get_session_factory, init_orm

# Неполный фолбэк, если таблица ещё пустая.
_BY_CITY = {
    "Москва": ["Школа №67", "Школа №57", "Школа №179", "Школа №1535", "Лицей «Вторая школа»", "Гимназия №1543"],
    "Санкт-Петербург": ["Школа №239", "Школа №30", "Лицей №344", "Гимназия №56", "Школа №610"],
    "Казань": ["Лицей №131", "Школа №18", "Гимназия №7", "Лицей им. Лобачевского"],
    "Новосибирск": ["СУНЦ НГУ", "Школа №162", "Гимназия №1", "Лицей №130"],
    "Екатеринбург": ["СУНЦ УрФУ", "Гимназия №9", "Школа №180", "Лицей №110"],
    "Краснодар": ["Школа №1", "Гимназия №23", "Лицей №4", "Школа №48"],
    "Нижний Новгород": ["Лицей №40", "Школа №1", "Гимназия №13"],
    "Самара": ["Школа №63", "Лицей №1", "Гимназия №1"],
    "Ростов-на-Дону": ["Школа №1", "Лицей №1", "Гимназия №36"],
    "Воронеж": ["Школа №1", "Лицей №1", "Гимназия №2"],
    "Алматы": ["НИШ ФМН Алматы", "Школа-гимназия №12", "Лицей №162"],
    "Астана": ["НИШ ХБН Астана", "Школа-лицей №48"],
    "Минск": ["Гимназия №1", "Лицей БГУ", "Гимназия №29", "СШ №50"],
}

_GENERIC = ["Школа №1", "Школа №2", "Школа №5", "Школа №10", "Гимназия №1", "Лицей №1"]

_COUNTRY_ALIASES = {
    "rf": CountryCode.RF,
    "ru": CountryCode.RF,
    "россия": CountryCode.RF,
    "rk": CountryCode.RK,
    "kz": CountryCode.RK,
    "казахстан": CountryCode.RK,
    "rb": CountryCode.RB,
    "by": CountryCode.RB,
    "беларусь": CountryCode.RB,
}


def _country(value: Optional[str]) -> Optional[CountryCode]:
    if not value:
        return None
    key = value.strip().lower()
    return _COUNTRY_ALIASES.get(key)


def _search_db(city: str, text: str, country: Optional[CountryCode], limit: int) -> list[str]:
    try:
        init_orm()
        factory = get_session_factory()
    except Exception:
        return []

    q = (text or "").strip().lower()
    city = (city or "").strip()
    with factory() as session:
        stmt = select(School.name)
        if country is not None:
            stmt = stmt.where(School.country_code == country)
        if city:
            stmt = stmt.where(School.city == city)
        if q:
            like = f"%{q}%"
            stmt = stmt.where(
                or_(
                    School.name.ilike(like),
                    School.city.ilike(like),
                    School.region.ilike(like),
                )
            )
        stmt = stmt.order_by(School.name).limit(limit)
        return list(session.scalars(stmt).all())


def _search_fallback(city: str, text: str, limit: int) -> list[str]:
    city = (city or "").strip()
    q = (text or "").strip().lower()
    pool = list(_BY_CITY.get(city, [])) + [s for s in _GENERIC if s not in _BY_CITY.get(city, [])]
    if not q:
        return pool[:limit]
    return [s for s in pool if q in s.lower()][:limit]


def search(
    city: str,
    text: str,
    limit: int = 6,
    country: Optional[str] = None,
) -> list[str]:
    """Подсказки названий школ."""
    hits = _search_db(city, text, _country(country), limit)
    if hits:
        return hits
    return _search_fallback(city, text, limit)


def list_cities(country: Optional[str] = None, limit: int = 50) -> list[str]:
    """Города, для которых есть школы в справочнике."""
    try:
        init_orm()
        factory = get_session_factory()
    except Exception:
        return sorted(_BY_CITY.keys())[:limit]

    code = _country(country)
    with factory() as session:
        stmt = select(School.city).distinct().order_by(School.city).limit(limit)
        if code is not None:
            stmt = stmt.where(School.country_code == code)
        cities = list(session.scalars(stmt).all())
    return cities or sorted(_BY_CITY.keys())[:limit]
