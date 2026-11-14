# -*- coding: utf-8 -*-
"""Демо-данные чатов: контакты, истории, непрочитанные."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Message:
    text: str = ""
    time: str = ""
    mine: bool = False
    image: Optional[str] = None
    date: Optional[str] = None
    read: bool = True  # для исходящих: прочитано собеседником


@dataclass
class Contact:
    id: str
    name: str
    first: str
    last: str
    seed: str
    status: str = "в сети"
    is_teacher: bool = False
    is_admin: bool = False
    is_banned: bool = False
    pinned: bool = False
    unread: int = 0
    messages: list[Message] = field(default_factory=list)

    @property
    def preview(self) -> str:
        for m in reversed(self.messages):
            if m.date:
                continue
            if m.image:
                return "Фото"
            t = (m.text or "").replace("\n", " ")
            return t[:48] + ("…" if len(t) > 48 else "")
        return ""

    @property
    def last_time(self) -> str:
        for m in reversed(self.messages):
            if m.date:
                continue
            return m.time
        return ""

    @property
    def last_mine(self) -> bool:
        for m in reversed(self.messages):
            if m.date:
                continue
            return m.mine
        return False

    @property
    def last_read(self) -> bool:
        for m in reversed(self.messages):
            if m.date:
                continue
            if m.mine:
                return m.read
            return True
        return True


def _build_contacts() -> list[Contact]:
    return [
        Contact(
            id="c1",
            name="Анна Смирнова",
            first="Анна",
            last="Смирнова",
            seed="a1",
            status="Была в 19:20",
            unread=2,
            messages=[
                Message(text="Привет! Есть конспект по алгебре?", time="18:40", mine=False),
                Message(text="Да, сейчас скину", time="18:42", mine=True, read=True),
                Message(text="Спасибо 🙏", time="18:43", mine=False),
                Message(text="Пришли конспект?", time="19:36", mine=False),
            ],
        ),
        Contact(
            id="c2",
            name="Иван Петров",
            first="Иван",
            last="Петров",
            seed="u2",
            status="Был в 16:43",
            unread=3,
            messages=[
                Message(image=None, text="", time="20:15", mine=True, read=True),  # photo filled later
                Message(text="Ахахахах", time="20:37", mine=False),
                Message(text="XAXAX он очень смешной", time="20:40", mine=True, read=True),
                Message(date="24 сентября"),
                Message(text="Ты в столовой?", time="11:23", mine=False),
                Message(text="ага", time="11:23", mine=True, read=True),
                Message(text="Ща приду, займи мне\nочередь в буфете", time="11:24", mine=False),
                Message(text="OK", time="11:25", mine=True, read=False),
                Message(text="Hello, Vinograd!", time="12:01", mine=False),
            ],
        ),
        Contact(
            id="c3",
            name="Мария Козлова",
            first="Мария",
            last="Козлова",
            seed="m3",
            status="в сети",
            unread=0,
            messages=[
                Message(text="Завтра контрольная?", time="09:10", mine=False),
                Message(text="Да, по геометрии", time="09:12", mine=True, read=True),
                Message(text="Ок, до завтра", time="09:15", mine=True, read=True),
            ],
        ),
        Contact(
            id="c4",
            name="Класс 10Б",
            first="10",
            last="Б",
            seed="c4",
            status="12 участников",
            pinned=True,
            unread=0,
            messages=[
                Message(text="Напоминание: собрание в 15:00", time="08:00", mine=False),
                Message(text="Закреплённый чат", time="08:05", mine=False),
            ],
        ),
        Contact(
            id="c5",
            name="Дима Орлов",
            first="Дима",
            last="Орлов",
            seed="d5",
            status="Был в 18:00",
            unread=1,
            messages=[
                Message(text="Го в футбол после уроков", time="17:50", mine=False),
                Message(text="Не могу, репетитор", time="17:55", mine=True, read=True),
                Message(text="Ты в столовой?", time="18:12", mine=False),
            ],
        ),
        Contact(
            id="c6",
            name="Елена В.",
            first="Елена",
            is_teacher=True,
            last="Ворон",
            seed="e6",
            status="Была вчера",
            unread=5,
            messages=[
                Message(text="Фото с линейки", time="17:05", mine=False),
            ],
        ),
        Contact(
            id="c7",
            name="Группа физика",
            first="Ф",
            last="З",
            seed="g7",
            status="8 участников",
            unread=12,
            messages=[
                Message(text="Кто понял 3 задачу?", time="14:00", mine=False),
                Message(text="Я скинул решение в чат", time="14:10", mine=True, read=True),
                Message(text="ДЗ на пятницу", time="16:30", mine=False),
            ],
        ),
        Contact(
            id="c8",
            name="Никита Р.",
            first="Никита",
            last="Романов",
            seed="n8",
            status="Был в пн",
            unread=0,
            messages=[
                Message(text="Смешной мем", time="Пн", mine=False),
                Message(text="Ахахахах", time="Пн", mine=True, read=True),
            ],
        ),
    ]


# единый runtime-store
CONTACTS: list[Contact] = _build_contacts()


def get_contact(cid: str) -> Optional[Contact]:
    for c in CONTACTS:
        if c.id == cid:
            return c
    return None


def sorted_contacts() -> list[Contact]:
    return sorted(CONTACTS, key=lambda c: (0 if c.pinned else 1, 0 if c.unread else 1, c.name))


def mark_read(cid: str) -> None:
    c = get_contact(cid)
    if c:
        c.unread = 0


def add_message(cid: str, text: str, *, mine: bool = True) -> Optional[Message]:
    c = get_contact(cid)
    if not c or not text.strip():
        return None
    m = Message(text=text.strip(), time="сейчас", mine=mine, read=False)
    c.messages.append(m)
    if not mine:
        c.unread += 1
    return m


def attach_demo_photo(path: str) -> None:
    """Подставить путь к фото в историю Ивана, если файл есть."""
    c = get_contact("c2")
    if not c:
        return
    for m in c.messages:
        if m.mine and not m.text and m.time == "20:15":
            m.image = path
            break



@dataclass
class Group:
    id: str
    name: str
    members: int
    seed: str
    preview: str = ""
    time: str = ""
    unread: int = 0
    pinned: bool = False


def _build_groups() -> list[Group]:
    return [
        Group("g1", "Класс 10Б", 28, "g10b", "Кто сдал реферат?", "18:40", unread=5, pinned=True),
        Group("g2", "Физика · 10Б", 14, "gphy", "ДЗ на пятницу в чате", "17:12", unread=12),
        Group("g3", "Родители 10Б", 31, "gpar", "Собрание в четверг", "16:05"),
        Group("g4", "Математика", 18, "gmath", "Кто понял 4 задачу?", "15:30", unread=3),
        Group("g5", "Английский клуб", 22, "geng", "Новое слово недели", "14:18"),
        Group("g6", "Спорт · футбол", 16, "gsport", "Тренировка завтра в 16:00", "12:44", unread=1),
        Group("g7", "Олимпиада", 9, "goly", "Регистрация до пятницы", "11:02"),
        Group("g8", "Общежитие 2", 41, "gdorm", "Кто видел ключи?", "вчера"),
    ]


GROUPS: list[Group] = _build_groups()


def sorted_groups() -> list[Group]:
    return sorted(GROUPS, key=lambda g: (0 if g.pinned else 1, 0 if g.unread else 1, g.name))
