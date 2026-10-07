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
