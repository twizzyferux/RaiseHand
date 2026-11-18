# -*- coding: utf-8 -*-
"""Демо-данные чатов: контакты, истории, непрочитанные."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Message:
    id: str = ""
    text: str = ""
    time: str = ""
    mine: bool = False
    image: Optional[str] = None
    date: Optional[str] = None
    read: bool = True  # для исходящих: прочитано собеседником
    reply_to_id: Optional[str] = None
    reply_preview: str = ""
    edited: bool = False
    deleted: bool = False
    pending: bool = False  # в оффлайн-очереди
    # для групп: кто написал (у своих можно не заполнять)
    sender_nick: str = ""
    sender_seed: str = ""
    sender_first: str = ""
    sender_last: str = ""

    def __post_init__(self) -> None:
        # Без id правка неотличима от новой отправки (пустая строка = falsy).
        if not self.id:
            self.id = uuid.uuid4().hex[:12]
        if not self.sender_seed and self.sender_nick:
            self.sender_seed = self.sender_nick.lower()


@dataclass
class Contact:
    id: str
    name: str
    first: str
    last: str
    seed: str
    status: str = "в сети"
    bio: str = ""  # описание, которое поставил сам пользователь
    is_teacher: bool = False
    is_admin: bool = False
    is_banned: bool = False
    pinned: bool = False
    muted: bool = False
    unread: int = 0
    messages: list[Message] = field(default_factory=list)

    @property
    def display_name(self) -> str:
        """Локальный alias из prefs, иначе имя профиля."""
        try:
            from core import prefs

            alias = (prefs.get_contact_alias(self.id) or "").strip()
            if alias:
                return alias
        except Exception:
            pass
        return self.name or f"{self.first} {self.last}".strip() or self.id

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
            bio="10Б · люблю алгебру и чай с лимоном",
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
            bio="Мемы и физика. Не пиши после 23:00",
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
            bio="Готовлюсь к олимпиаде ✨",
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
                Message(text="Ахахахах", time="Пн", mine=True, read=False),
            ],
        ),
    ]


FAVORITES_ID = "favorites"


def ensure_favorites() -> Contact:
    """Личный чат «Избранное» — заметки только для себя."""
    existing = get_contact(FAVORITES_ID)
    if existing is not None:
        return existing
    fav = Contact(
        id=FAVORITES_ID,
        name="Избранное",
        first="Избранное",
        last="",
        seed="favorites",
        status="только вы · заметки",
        bio="Личные заметки. Сообщения остаются только у вас.",
        pinned=True,
        unread=0,
        messages=[
            Message(
                text="Сюда можно сохранять мысли, ссылки и напоминания — никто кроме вас их не увидит.",
                time="сейчас",
                mine=True,
                read=True,
            ),
        ],
    )
    CONTACTS.insert(0, fav)
    return fav


# единый runtime-store
CONTACTS: list[Contact] = _build_contacts()


def get_contact(cid: str) -> Optional[Contact]:
    for c in CONTACTS:
        if c.id == cid:
            return c
    return None


ensure_favorites()


def set_contact_local_name(cid: str, alias: str) -> Optional[Contact]:
    """Локальное имя контакта (только у вас)."""
    from core import prefs

    c = get_contact(cid)
    if c is None:
        return None
    prefs.set_contact_alias(cid, alias)
    return c


def media_messages(cid: str) -> list[Message]:
    """Фото/картинки из личного чата."""
    c = get_contact(cid)
    if c is None:
        return []
    return [m for m in c.messages if m.image and not m.deleted and not m.date]


def text_messages(cid: str, *, limit: int = 40) -> list[Message]:
    c = get_contact(cid)
    if c is None:
        return []
    real = [m for m in c.messages if not m.date and not m.deleted and (m.text or m.image)]
    return list(reversed(real[-limit:]))


def shared_groups_for(contact: Contact) -> list[Group]:
    """Группы, где встречаются вы и этот контакт (по seed/имени в истории)."""
    seed = (contact.seed or "").lower()
    first = (contact.first or "").strip().lower()
    out: list[Group] = []
    for g in GROUPS:
        hit = False
        for m in g.messages:
            if m.date or m.mine:
                continue
            if seed and (m.sender_seed or "").lower() == seed:
                hit = True
                break
            if first and (m.sender_first or "").strip().lower() == first:
                hit = True
                break
        if hit:
            out.append(g)
    return out


def contact_id_for_public_id(public_id: str) -> str:
    return f"u:{(public_id or '').strip()}"


def ensure_user_contact(
    *,
    public_id: str,
    name: str,
    first: str,
    last: str,
    status: str = "в сети",
    is_teacher: bool = False,
    is_admin: bool = False,
) -> Contact:
    """Контакт из найденного аккаунта — для чата и списка."""
    pid = (public_id or "").strip()
    cid = contact_id_for_public_id(pid)
    existing = get_contact(cid)
    if existing is not None:
        if name:
            existing.name = name
        if first:
            existing.first = first
        if last:
            existing.last = last
        if status:
            existing.status = status
        existing.is_teacher = bool(is_teacher)
        existing.is_admin = bool(is_admin)
        return existing
    contact = Contact(
        id=cid,
        name=name or pid,
        first=first or (name[:1] if name else "?"),
        last=last or "",
        seed=pid.lower() or cid,
        status=status or "в сети",
        is_teacher=bool(is_teacher),
        is_admin=bool(is_admin),
        messages=[],
    )
    CONTACTS.insert(0, contact)
    return contact


def sorted_contacts() -> list[Contact]:
    return sorted(CONTACTS, key=lambda c: (0 if c.pinned else 1, 0 if c.unread else 1, c.name))


def sorted_contacts_for_ui() -> list[Contact]:
    """Если есть реальные контакты (u:ID) — показываем их; иначе демо.
    «Избранное» всегда в списке.
    """
    ensure_favorites()
    all_c = sorted_contacts()
    fav = [c for c in all_c if c.id == FAVORITES_ID]
    real = [c for c in all_c if str(c.id).startswith("u:")]
    rest = real if real else [c for c in all_c if c.id != FAVORITES_ID]
    # избранное сверху (pinned уже учитывается в sorted_contacts)
    seen = {c.id for c in fav}
    return fav + [c for c in rest if c.id not in seen]


def mark_read(cid: str) -> None:
    c = get_contact(cid)
    if c:
        c.unread = 0


def toggle_pin(cid: str) -> Optional[bool]:
    c = get_contact(cid)
    if c is None:
        return None
    # «Избранное» всегда закреплено
    if c.id == FAVORITES_ID:
        c.pinned = True
        return True
    c.pinned = not c.pinned
    return c.pinned


def toggle_mute(cid: str) -> Optional[bool]:
    c = get_contact(cid)
    if c is None or c.id == FAVORITES_ID:
        return None
    c.muted = not c.muted
    return c.muted


def is_muted(cid: str) -> bool:
    c = get_contact(cid)
    return bool(c and c.muted)


def delete_chat(cid: str) -> bool:
    """Удалить чат из списка (не «Избранное»)."""
    global CONTACTS
    if cid == FAVORITES_ID:
        return False
    before = len(CONTACTS)
    CONTACTS[:] = [c for c in CONTACTS if c.id != cid]
    return len(CONTACTS) < before


def add_message(
    cid: str,
    text: str = "",
    *,
    mine: bool = True,
    image: Optional[str] = None,
    reply_to_id: Optional[str] = None,
    pending: bool = False,
    msg_id: Optional[str] = None,
) -> Optional[Message]:
    c = get_contact(cid)
    text = (text or "").strip()
    if not c or (not text and not image):
        return None
    reply_preview = ""
    if reply_to_id:
        for old in c.messages:
            if old.id == reply_to_id:
                reply_preview = (old.text or ("Фото" if old.image else ""))[:60]
                break
    m = Message(
        id=msg_id or uuid.uuid4().hex[:12],
        text=text,
        time="сейчас",
        mine=mine,
        image=image,
        read=False,
        reply_to_id=reply_to_id,
        reply_preview=reply_preview,
        pending=pending,
    )
    c.messages.append(m)
    if not mine:
        c.unread += 1
    return m


def _messages_of(cid: str) -> Optional[list[Message]]:
    c = get_contact(cid)
    if c is not None:
        return c.messages
    g = get_group(cid)
    if g is not None:
        return g.messages
    return None


def get_message(cid: str, msg_id: str) -> Optional[Message]:
    msgs = _messages_of(cid)
    if not msgs:
        return None
    for m in msgs:
        if m.id == msg_id:
            return m
    return None


def edit_message(cid: str, msg_id: str, text: str) -> Optional[Message]:
    m = get_message(cid, msg_id)
    if not m or m.deleted or not m.mine:
        return None
    m.text = (text or "").strip()
    m.edited = True
    return m


def delete_message(cid: str, msg_id: str) -> Optional[Message]:
    m = get_message(cid, msg_id)
    if not m:
        return None
    m.deleted = True
    m.text = ""
    m.image = None
    return m


def page_messages(cid: str, *, limit: int = 30, offset: int = 0) -> list[Message]:
    """Пагинация: offset от конца истории (0 = самые свежие)."""
    c = get_contact(cid)
    if not c:
        return []
    real = [m for m in c.messages if not m.date]
    if offset >= len(real):
        return []
    # с конца: [-offset-limit : -offset or None]
    end = len(real) - offset
    start = max(0, end - limit)
    return real[start:end]


def older_available(cid: str, loaded: int) -> bool:
    c = get_contact(cid)
    if not c:
        return False
    real = [m for m in c.messages if not m.date]
    return loaded < len(real)


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
    questions_count: int = 0  # из экрана вопросов (пока демо-значение)
    messages: list[Message] = field(default_factory=list)

    @property
    def status(self) -> str:
        return f"{self.members} участников"

    @property
    def last_time(self) -> str:
        for m in reversed(self.messages):
            if m.date:
                continue
            return m.time
        return self.time

    @property
    def live_preview(self) -> str:
        for m in reversed(self.messages):
            if m.date:
                continue
            if m.image:
                return "Фото"
            nick = (m.sender_nick + ": ") if (m.sender_nick and not m.mine) else ("" if not m.mine else "Вы: ")
            t = (m.text or "").replace("\n", " ")
            body = t[:40] + ("…" if len(t) > 40 else "")
            return f"{nick}{body}" if body else (nick.strip(": ") or "")
        return self.preview


def _gm(text: str, time: str, nick: str, seed: str, first: str, last: str = "", *, mine: bool = False) -> Message:
    return Message(
        text=text,
        time=time,
        mine=mine,
        sender_nick="" if mine else nick,
        sender_seed="" if mine else seed,
        sender_first="" if mine else first,
        sender_last="" if mine else last,
        read=True if mine else True,
    )


def _build_groups() -> list[Group]:
    g1_msgs = [
        _gm("Напоминаю: собрание в 15:00", "08:00", "Анна", "a1", "Анна", "Смирнова"),
        _gm("Буду", "08:02", "Дима", "d5", "Дима", "Орлов"),
        _gm("Я тоже", "08:03", "Мария", "m3", "Мария", "Козлова"),
        _gm("Ок, тогда в актовом", "08:05", "Анна", "a1", "Анна", "Смирнова"),
        Message(date="Сегодня"),
        _gm("Кто сдал реферат?", "18:30", "Елена В.", "e6", "Елена", "Ворон"),
        _gm("Я скинул вчера", "18:35", "Никита", "n8", "Никита", "Романов"),
        _gm("Сейчас доделаю и пришлю", "18:40", "Вы", "me", "Я", "", mine=True),
    ]
    g2_msgs = [
        _gm("Кто понял 3 задачу?", "14:00", "Мария", "m3", "Мария", "Козлова"),
        _gm("Там через интеграл", "14:05", "Иван", "u2", "Иван", "Петров"),
        _gm("Я скинул решение в чат", "14:10", "Вы", "me", "Я", "", mine=True),
        _gm("ДЗ на пятницу", "16:30", "Елена В.", "e6", "Елена", "Ворон"),
        _gm("Уже в дневнике", "17:12", "Анна", "a1", "Анна", "Смирнова"),
    ]
    g3_msgs = [
        _gm("Собрание в четверг в 18:00", "15:40", "Ольга", "olga", "Ольга", "К."),
        _gm("Подтвердите присутствие", "16:00", "Ольга", "olga", "Ольга", "К."),
        _gm("Буду", "16:05", "Ирина", "ira", "Ирина", "П."),
    ]
    g4_msgs = [
        _gm("Кто понял 4 задачу?", "15:10", "Дима", "d5", "Дима", "Орлов"),
        _gm("Разберём на перемене", "15:20", "Мария", "m3", "Мария", "Козлова"),
        _gm("Ок", "15:30", "Вы", "me", "Я", "", mine=True),
    ]
    g5_msgs = [
        _gm("Новое слово недели: resilient", "14:00", "Kate", "kate", "Kate", "L."),
        _gm("Сделаем карточки?", "14:18", "Анна", "a1", "Анна", "Смирнова"),
    ]
    g6_msgs = [
        _gm("Тренировка завтра в 16:00", "12:20", "Коля", "kolya", "Коля", "С."),
        _gm("Мяч возьму", "12:44", "Дима", "d5", "Дима", "Орлов"),
    ]
    g7_msgs = [
        _gm("Регистрация до пятницы", "10:50", "Елена В.", "e6", "Елена", "Ворон"),
        _gm("Я записался", "11:02", "Иван", "u2", "Иван", "Петров"),
    ]
    g8_msgs = [
        _gm("Кто видел ключи?", "вчера", "Саша", "sasha", "Саша", "Т."),
        _gm("У вахты лежали", "вчера", "Макс", "maks", "Макс", "В."),
    ]

    def _g(gid, name, members, seed, unread=0, pinned=False, messages=None, questions=0):
        msgs = messages or []
        preview = ""
        time = ""
        for m in reversed(msgs):
            if m.date:
                continue
            time = m.time
            if m.mine:
                preview = f"Вы: {(m.text or '')[:40]}"
            elif m.sender_nick:
                preview = f"{m.sender_nick}: {(m.text or '')[:40]}"
            else:
                preview = (m.text or "")[:48]
            break
        return Group(
            gid, name, members, seed,
            preview=preview, time=time, unread=unread, pinned=pinned,
            questions_count=questions, messages=msgs,
        )

    return [
        _g("g1", "Класс 10Б", 28, "g10b", unread=5, pinned=True, messages=g1_msgs, questions=7),
        _g("g2", "Физика · 10Б", 14, "gphy", unread=12, messages=g2_msgs, questions=12),
        _g("g3", "Родители 10Б", 31, "gpar", messages=g3_msgs, questions=2),
        _g("g4", "Математика", 18, "gmath", unread=3, messages=g4_msgs, questions=5),
        _g("g5", "Английский клуб", 22, "geng", messages=g5_msgs, questions=3),
        _g("g6", "Спорт · футбол", 16, "gsport", unread=1, messages=g6_msgs, questions=1),
        _g("g7", "Олимпиада", 9, "goly", messages=g7_msgs, questions=4),
        _g("g8", "Общежитие 2", 41, "gdorm", messages=g8_msgs),
    ]


GROUPS: list[Group] = _build_groups()


def sorted_groups() -> list[Group]:
    return sorted(GROUPS, key=lambda g: (0 if g.pinned else 1, 0 if g.unread else 1, g.name))


def get_group(gid: str) -> Optional[Group]:
    for g in GROUPS:
        if g.id == gid:
            return g
    return None


def mark_group_read(gid: str) -> None:
    g = get_group(gid)
    if g:
        g.unread = 0


def add_group_message(
    gid: str,
    text: str = "",
    *,
    mine: bool = True,
    image: Optional[str] = None,
    reply_to_id: Optional[str] = None,
    pending: bool = False,
    msg_id: Optional[str] = None,
    sender_nick: str = "",
    sender_seed: str = "",
    sender_first: str = "",
    sender_last: str = "",
) -> Optional[Message]:
    g = get_group(gid)
    text = (text or "").strip()
    if not g or (not text and not image):
        return None
    reply_preview = ""
    if reply_to_id:
        for old in g.messages:
            if old.id == reply_to_id:
                reply_preview = (old.text or ("Фото" if old.image else ""))[:60]
                break
    m = Message(
        id=msg_id or uuid.uuid4().hex[:12],
        text=text,
        time="сейчас",
        mine=mine,
        image=image,
        read=False,
        reply_to_id=reply_to_id,
        reply_preview=reply_preview,
        pending=pending,
        sender_nick="" if mine else (sender_nick or "Участник"),
        sender_seed="" if mine else (sender_seed or sender_nick or "user"),
        sender_first="" if mine else (sender_first or sender_nick or "?"),
        sender_last="" if mine else sender_last,
    )
    g.messages.append(m)
    if not mine:
        g.unread += 1
    return m


def page_group_messages(gid: str, *, limit: int = 30, offset: int = 0) -> list[Message]:
    g = get_group(gid)
    if not g:
        return []
    real = [m for m in g.messages if not m.date]
    if offset >= len(real):
        return []
    end = len(real) - offset
    start = max(0, end - limit)
    return real[start:end]


def older_group_available(gid: str, loaded: int) -> bool:
    g = get_group(gid)
    if not g:
        return False
    real = [m for m in g.messages if not m.date]
    return loaded < len(real)
