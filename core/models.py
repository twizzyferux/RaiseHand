# -*- coding: utf-8 -*-
"""SQLAlchemy-модели RaiseHand.

Сейчас движок — SQLite (data/messenger.db). Для PostgreSQL достаточно
сменить DATABASE_URL / RH_DATABASE_URL, схема моделей та же.
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class RoleCode(str, enum.Enum):
    ADMIN = "admin"
    TEACHER = "teacher"
    STUDENT = "student"


class CountryCode(str, enum.Enum):
    """Страны со школами в справочнике."""

    RF = "RF"  # Россия
    RK = "RK"  # Казахстан
    RB = "RB"  # Беларусь


ROLE_TITLES = {
    RoleCode.ADMIN: "Админ",
    RoleCode.TEACHER: "Учитель",
    RoleCode.STUDENT: "Ученик",
}


class Role(Base):
    """Роль пользователя: админ / учитель / ученик."""

    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[RoleCode] = mapped_column(
        Enum(RoleCode, name="role_code", native_enum=False, length=16),
        unique=True,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(64), nullable=False)

    users: Mapped[list["User"]] = relationship(back_populates="role_ref")

    def __repr__(self) -> str:
        return f"<Role {self.code.value}>"


class School(Base):
    """Школа из справочника РФ / РК / РБ."""

    __tablename__ = "schools"
    __table_args__ = (
        UniqueConstraint(
            "country_code", "city", "name",
            name="uq_schools_country_city_name",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    country_code: Mapped[CountryCode] = mapped_column(
        Enum(CountryCode, name="country_code", native_enum=False, length=8),
        nullable=False,
        index=True,
    )
    region: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    city: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    external_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="seed")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.now(),
        nullable=False,
    )

    users: Mapped[list["User"]] = relationship(back_populates="school")

    def __repr__(self) -> str:
        return f"<School {self.country_code.value} {self.city}: {self.name}>"


class User(Base):
    """Аккаунт: ученик, учитель или админ."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    public_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    # Строковый код роли — совместим со старой схемой SQLite.
    role: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    role_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("roles.id", ondelete="SET NULL"),
        nullable=True,
    )
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    nickname: Mapped[Optional[str]] = mapped_column(String(64), unique=True, nullable=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    # Для bcrypt/passlib соль внутри хеша; колонка оставлена ради старых PBKDF2-записей.
    password_salt: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    contact_type: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    contact_value: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    contact_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    teacher_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    avatar_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    city: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    class_name: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    school_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    school_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("schools.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.now(),
        nullable=False,
    )

    role_ref: Mapped[Optional[Role]] = relationship(back_populates="users")
    school: Mapped[Optional[School]] = relationship(back_populates="users")

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def display_name(self) -> str:
        """Имя и фамилия; ник отдельным полем."""
        name = self.full_name
        if name:
            return name
        if self.nickname:
            return self.nickname
        return self.public_id or "Пользователь"

    @property
    def is_admin(self) -> bool:
        return self.role == RoleCode.ADMIN.value

    @property
    def is_teacher(self) -> bool:
        return self.role == RoleCode.TEACHER.value

    @property
    def is_student(self) -> bool:
        return self.role == RoleCode.STUDENT.value

    def __repr__(self) -> str:
        return f"<User {self.public_id} ({self.role})>"
