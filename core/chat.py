"""Контакты и сообщения.

Переписка в data/messenger.db. Для мгновенной доставки UI использует
page.pubsub; этот модуль — слой хранения + пагинация.
"""

from __future__ import annotations

from typing import List, Optional

from core import auth, database as db
from core import rate_limit
from core.uploads import UploadError, is_image, save_upload


class ChatError(Exception):
    """Ошибка, текст которой можно показать пользователю."""


PAGE_SIZE = 30


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


def send_message(
    sender_id: int,
    receiver_id: int,
    body: str = "",
    *,
    attachment_path: str = "",
    reply_to_id: Optional[int] = None,
    rate_key: Optional[str] = None,
) -> dict:
    body = (body or "").strip()
    attachment_path = (attachment_path or "").strip()
    if not body and not attachment_path:
        raise ChatError("Сообщение пустое")

    try:
        rate_limit.check(
            rate_key or f"msg:{sender_id}",
            limit=30,
            window_sec=60,
            block_sec=30,
            action="отправка сообщений",
        )
    except rate_limit.RateLimitError as exc:
        raise ChatError(str(exc)) from exc

    att_type = ""
    stored_att = ""
    if attachment_path:
        try:
            stored_att = save_upload(attachment_path, subdir="chat")
        except UploadError as exc:
            raise ChatError(str(exc)) from exc
        att_type = "image" if is_image(stored_att) else "file"

    msg_id = db.execute(
        """INSERT INTO messages
           (sender_id, receiver_id, body, attachment_path, attachment_type, reply_to_id)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (sender_id, receiver_id, body, stored_att or None, att_type or None, reply_to_id),
    )
    row = db.query_one("SELECT * FROM messages WHERE id = ?", (msg_id,))
    return dict(row) if row else {"id": msg_id}


def get_dialog(
    user_a: int,
    user_b: int,
    *,
    limit: int = PAGE_SIZE,
    offset: int = 0,
) -> List[dict]:
    """Страница сообщений: сначала свежие (ORDER BY id DESC), наружу — по возрастанию."""
    rows = db.query_all(
        """SELECT * FROM messages
           WHERE is_deleted = 0
             AND ((sender_id = ? AND receiver_id = ?)
               OR (sender_id = ? AND receiver_id = ?))
           ORDER BY id DESC
           LIMIT ? OFFSET ?""",
        (user_a, user_b, user_b, user_a, limit, offset),
    )
    return [dict(row) for row in reversed(rows)]


def count_dialog(user_a: int, user_b: int) -> int:
    row = db.query_one(
        """SELECT COUNT(*) AS n FROM messages
           WHERE is_deleted = 0
             AND ((sender_id = ? AND receiver_id = ?)
               OR (sender_id = ? AND receiver_id = ?))""",
        (user_a, user_b, user_b, user_a),
    )
    return int(row["n"]) if row else 0


def get_message(message_id: int) -> Optional[dict]:
    row = db.query_one("SELECT * FROM messages WHERE id = ?", (message_id,))
    return dict(row) if row else None


def edit_message(message_id: int, editor_id: int, new_body: str) -> dict:
    new_body = (new_body or "").strip()
    if not new_body:
        raise ChatError("Текст пустой")
    row = get_message(message_id)
    if row is None or row.get("is_deleted"):
        raise ChatError("Сообщение не найдено")
    if int(row["sender_id"]) != int(editor_id):
        raise ChatError("Можно редактировать только свои сообщения")
    db.execute(
        """UPDATE messages
           SET body = ?, edited_at = datetime('now')
           WHERE id = ?""",
        (new_body, message_id),
    )
    return get_message(message_id) or {}


def delete_message(message_id: int, actor_id: int) -> None:
    row = get_message(message_id)
    if row is None:
        raise ChatError("Сообщение не найдено")
    if int(row["sender_id"]) != int(actor_id) and int(row["receiver_id"]) != int(actor_id):
        raise ChatError("Нет доступа к сообщению")
    db.execute(
        "UPDATE messages SET is_deleted = 1, body = '', attachment_path = NULL WHERE id = ?",
        (message_id,),
    )


def mark_read(reader_id: int, partner_id: int) -> None:
    db.execute(
        "UPDATE messages SET is_read = 1 WHERE receiver_id = ? AND sender_id = ?",
        (reader_id, partner_id),
    )


def unread_count(user_id: int, partner_id: Optional[int] = None) -> int:
    if partner_id is None:
        row = db.query_one(
            "SELECT COUNT(*) AS n FROM messages WHERE receiver_id = ? AND is_read = 0 AND is_deleted = 0",
            (user_id,),
        )
    else:
        row = db.query_one(
            """SELECT COUNT(*) AS n FROM messages
               WHERE receiver_id = ? AND sender_id = ? AND is_read = 0 AND is_deleted = 0""",
            (user_id, partner_id),
        )
    return row["n"]


def last_message(user_a: int, user_b: int) -> Optional[dict]:
    row = db.query_one(
        """SELECT * FROM messages
           WHERE is_deleted = 0
             AND ((sender_id = ? AND receiver_id = ?) OR (sender_id = ? AND receiver_id = ?))
           ORDER BY id DESC LIMIT 1""",
        (user_a, user_b, user_b, user_a),
    )
    return dict(row) if row else None


def is_pinned(owner_id: int, peer_id: int) -> bool:
    row = db.query_one(
        "SELECT pinned FROM chats WHERE owner_id = ? AND peer_id = ?",
        (owner_id, peer_id),
    )
    return bool(row and row["pinned"])


def set_pinned(owner_id: int, peer_id: int, pinned: bool) -> None:
    db.execute(
        """INSERT INTO chats (owner_id, peer_id, pinned) VALUES (?, ?, ?)
           ON CONFLICT(owner_id, peer_id)
           DO UPDATE SET pinned = excluded.pinned""",
        (owner_id, peer_id, 1 if pinned else 0),
    )


def _short_time(created_at: str) -> str:
    text = (created_at or "").strip()
    if " " in text:
        text = text.split(" ", 1)[1]
    return text[:5]


def chat_list(owner_id: int) -> List[dict]:
    peers: dict = {}
    for row in db.query_all(
            """SELECT CASE WHEN sender_id = ? THEN receiver_id ELSE sender_id END AS peer,
                      MAX(id) AS last_id
               FROM messages
               WHERE (sender_id = ? OR receiver_id = ?) AND is_deleted = 0
               GROUP BY peer""",
            (owner_id, owner_id, owner_id)):
        peers[row["peer"]] = row["last_id"]

    for row in db.query_all(
            "SELECT contact_id AS peer FROM contacts WHERE owner_id = ?",
            (owner_id,)):
        peers.setdefault(row["peer"], 0)

    items = []
    for peer_id, last_id in peers.items():
        person = auth.get_user_by_id(peer_id)
        if person is None or person.id == owner_id:
            continue
        last = db.query_one("SELECT * FROM messages WHERE id = ?", (last_id,)) if last_id else None
        unread = unread_count(owner_id, peer_id)
        preview = ""
        if last:
            if last.get("is_deleted"):
                preview = ""
            elif last.get("attachment_path") and not last.get("body"):
                preview = "Фото" if last.get("attachment_type") == "image" else "Файл"
            else:
                preview = last.get("body") or ""
        items.append({
            "user": person,
            "preview": preview,
            "time": _short_time(last["created_at"] if last else ""),
            "mine": bool(last and last["sender_id"] == owner_id),
            "read": bool(last and last["sender_id"] == owner_id and last["is_read"]),
            "unread": unread,
            "pinned": is_pinned(owner_id, peer_id),
            "last_id": last_id or 0,
        })

    items.sort(key=lambda item: (not item["pinned"], -item["last_id"]))
    return items


def list_classes() -> List[dict]:
    rows = db.query_all(
        "SELECT class_name, school_name, invite_code FROM classes ORDER BY class_name")
    return [dict(row) for row in rows]


def join_class(user_id: int, invite_code: str) -> str:
    row = auth.find_class(invite_code)
    db.execute(
        "UPDATE users SET class_name = ?, school_name = ? WHERE id = ?",
        (row["class_name"], row["school_name"], user_id))
    return row["class_name"]
