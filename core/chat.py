"""Контакты и сообщения.

Важно: сейчас переписка хранится в локальной базе data/messenger.db, то есть
общаться могут аккаунты на одном устройстве (этого достаточно для школьного
проекта и для демонстрации). Чтобы сделать настоящий обмен по сети, нужно
вынести эти же функции на сервер (например, FastAPI + WebSocket) — структура
таблиц при этом не меняется.
"""

from typing import List, Optional

from core import auth, database as db


class ChatError(Exception):
    """Ошибка, текст которой можно показать пользователю."""


def add_contact(owner_id: int, public_id: str) -> auth.User:
    other = auth.find_by_public_id(public_id)
    if other is None:
        raise ChatError("Пользователь с таким ID не найден")
    if other.id == owner_id:
        raise ChatError("Нельзя добавить самого себя")
    db.execute("INSERT OR IGNORE INTO contacts (owner_id, contact_id) VALUES (?, ?)",
               (owner_id, other.id))
    db.execute("INSERT OR IGNORE INTO contacts (owner_id, contact_id) VALUES (?, ?)",
               (other.id, owner_id))
    return other


def list_contacts(owner_id: int) -> List[auth.User]:
    rows = db.query_all(
        """SELECT u.* FROM contacts c
           JOIN users u ON u.id = c.contact_id
           WHERE c.owner_id = ?
           ORDER BY u.first_name""",
        (owner_id,),
    )
    return [auth.row_to_user(row) for row in rows]


def send_message(sender_id: int, receiver_id: int, body: str) -> None:
    body = body.strip()
    if not body:
        raise ChatError("Сообщение пустое")
    db.execute("INSERT INTO messages (sender_id, receiver_id, body) VALUES (?, ?, ?)",
               (sender_id, receiver_id, body))


def get_dialog(user_a: int, user_b: int, limit: int = 200) -> List[dict]:
    rows = db.query_all(
        """SELECT * FROM messages
           WHERE (sender_id = ? AND receiver_id = ?)
              OR (sender_id = ? AND receiver_id = ?)
           ORDER BY id DESC LIMIT ?""",
        (user_a, user_b, user_b, user_a, limit),
    )
    return [dict(row) for row in reversed(rows)]


def mark_read(reader_id: int, partner_id: int) -> None:
    db.execute("UPDATE messages SET is_read = 1 WHERE receiver_id = ? AND sender_id = ?",
               (reader_id, partner_id))


def unread_count(user_id: int, partner_id: Optional[int] = None) -> int:
    if partner_id is None:
        row = db.query_one("SELECT COUNT(*) AS n FROM messages WHERE receiver_id = ? AND is_read = 0",
                           (user_id,))
    else:
        row = db.query_one(
            "SELECT COUNT(*) AS n FROM messages WHERE receiver_id = ? AND sender_id = ? AND is_read = 0",
            (user_id, partner_id))
    return row["n"]


def last_message(user_a: int, user_b: int) -> Optional[dict]:
    row = db.query_one(
        """SELECT * FROM messages
           WHERE (sender_id = ? AND receiver_id = ?) OR (sender_id = ? AND receiver_id = ?)
           ORDER BY id DESC LIMIT 1""",
        (user_a, user_b, user_b, user_a),
    )
    return dict(row) if row else None


# --------------------------------------------------------------------------- #
#  Список чатов (как в макете «основной экран чаты»)
# --------------------------------------------------------------------------- #

def is_pinned(owner_id: int, peer_id: int) -> bool:
    row = db.query_one(
        "SELECT pinned FROM chats WHERE owner_id = ? AND peer_id = ?",
        (owner_id, peer_id),
    )
    return bool(row and row["pinned"])


def set_pinned(owner_id: int, peer_id: int, pinned: bool) -> None:
    """Закрепить или открепить чат."""
    db.execute(
        """INSERT INTO chats (owner_id, peer_id, pinned) VALUES (?, ?, ?)
           ON CONFLICT(owner_id, peer_id)
           DO UPDATE SET pinned = excluded.pinned""",
        (owner_id, peer_id, 1 if pinned else 0))


def _short_time(created_at: str) -> str:
    """Время сообщения в виде «19:36»."""
    text = (created_at or "").strip()
    if " " in text:                       # SQLite отдаёт «2026-10-08 19:36:12»
        text = text.split(" ", 1)[1]
    return text[:5]


def chat_list(owner_id: int) -> List[dict]:
    """Чаты для главного экрана: закреплённые сверху, остальные по свежести.

    В каждом словаре — всё, что нужно ряду в списке: человек, последнее
    сообщение, время, прочитано ли моё сообщение и сколько новых.
    """
    peers: dict = {}

    # с кем есть переписка: берём последнее сообщение по каждому собеседнику
    for row in db.query_all(
            """SELECT CASE WHEN sender_id = ? THEN receiver_id ELSE sender_id END AS peer,
                      MAX(id) AS last_id
               FROM messages
               WHERE sender_id = ? OR receiver_id = ?
               GROUP BY peer""",
            (owner_id, owner_id, owner_id)):
        peers[row["peer"]] = row["last_id"]

    # контакты без сообщений тоже показываем — пустой чат
    for row in db.query_all(
            "SELECT contact_id AS peer FROM contacts WHERE owner_id = ?",
            (owner_id,)):
        peers.setdefault(row["peer"], 0)

    items = []
    for peer_id, last_id in peers.items():
        person = auth.get_user_by_id(peer_id)
        if person is None or person.id == owner_id:
            continue
        last = db.query_one("SELECT * FROM messages WHERE id = ?", (last_id,)) \
            if last_id else None
        unread = unread_count(owner_id, peer_id)
        items.append({
            "user": person,
            "preview": (last["body"] if last else ""),
            "time": _short_time(last["created_at"] if last else ""),
            "mine": bool(last and last["sender_id"] == owner_id),
            "read": bool(last and last["sender_id"] == owner_id and last["is_read"]),
            "unread": unread,
            "pinned": is_pinned(owner_id, peer_id),
            "last_id": last_id or 0,
        })

    items.sort(key=lambda item: (not item["pinned"], -item["last_id"]))
    return items


# --------------------------------------------------------------------------- #
#  Классы (вкладка «Группы»)
# --------------------------------------------------------------------------- #

def list_classes() -> List[dict]:
    """Все учебные классы: название, школа и код для входа."""
    rows = db.query_all(
        "SELECT class_name, school_name, invite_code FROM classes ORDER BY class_name")
    return [dict(row) for row in rows]


def join_class(user_id: int, invite_code: str) -> str:
    """Присоединиться к классу по коду. Возвращает название класса."""
    row = auth.find_class(invite_code)        # код проверяется там же
    db.execute(
        "UPDATE users SET class_name = ?, school_name = ? WHERE id = ?",
        (row["class_name"], row["school_name"], user_id))
    return row["class_name"]
