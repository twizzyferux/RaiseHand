"""Работа с базой данных SQLite.

Файл базы: data/messenger.db (создаётся автоматически при первом запуске).
Таблицы:
  users            — аккаунты учеников и учителей
  classes          — коды приглашений (код -> класс и школа)
  verification     — одноразовые коды подтверждения (почта / телефон)
  teacher_proofs   — подтверждение того, что человек действительно учитель
  contacts         — добавленные контакты (кого нашли по ID)
  messages         — сообщения между пользователями
"""

import sqlite3
from typing import Optional

from core.config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    public_id       TEXT    NOT NULL UNIQUE,   -- ID, по которому ищут друг друга (у учителей с 'U')
    role            TEXT    NOT NULL,          -- 'student' или 'teacher'
    first_name      TEXT    NOT NULL,
    last_name       TEXT    NOT NULL,
    nickname        TEXT,                      -- только у учеников
    password_hash   TEXT    NOT NULL,
    password_salt   TEXT    NOT NULL,
    contact_type    TEXT,                      -- 'email' или 'phone'
    contact_value   TEXT,
    contact_verified INTEGER NOT NULL DEFAULT 0,
    teacher_verified INTEGER NOT NULL DEFAULT 0,
    avatar_path     TEXT,
    status_text     TEXT DEFAULT '',
    city            TEXT DEFAULT '',           -- где учится (шаг регистрации «Где вы учитесь?»)
    class_name      TEXT DEFAULT '',
    school_name     TEXT DEFAULT '',
    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS classes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    invite_code TEXT    NOT NULL UNIQUE,   -- код, который даёт учитель ученикам
    class_name  TEXT    NOT NULL,          -- например '5А'
    school_name TEXT    NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS verification (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    channel    TEXT    NOT NULL,      -- 'email' | 'phone'
    target     TEXT    NOT NULL,      -- сам адрес или номер
    code       TEXT    NOT NULL,
    expires_at TEXT    NOT NULL,
    used       INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS teacher_proofs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL,
    platform        TEXT    NOT NULL,   -- МЭШ, Дневник.ру и т.д.
    proof_type      TEXT    NOT NULL,   -- 'code' | 'screenshot'
    proof_value     TEXT,               -- код или путь к файлу скриншота
    status          TEXT    NOT NULL DEFAULT 'pending',  -- pending | approved | rejected
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS contacts (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id      INTEGER NOT NULL,
    contact_id    INTEGER NOT NULL,
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (owner_id, contact_id),
    FOREIGN KEY (owner_id)   REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (contact_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS messages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_id   INTEGER NOT NULL,
    receiver_id INTEGER NOT NULL,
    body        TEXT    NOT NULL,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    is_read     INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (sender_id)   REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (receiver_id) REFERENCES users (id) ON DELETE CASCADE
);
"""

_connection: Optional[sqlite3.Connection] = None


def get_connection() -> sqlite3.Connection:
    """Одно соединение на всё приложение (так проще и быстрее для SQLite)."""
    global _connection
    if _connection is None:
        _connection = sqlite3.connect(DB_PATH, check_same_thread=False)
        _connection.row_factory = sqlite3.Row
        _connection.execute("PRAGMA foreign_keys = ON")
    return _connection


def init_db() -> None:
    conn = get_connection()
    conn.executescript(SCHEMA)

    # Колонки, добавленные в новых версиях: в старых базах их ещё нет.
    for statement in (
        "ALTER TABLE users ADD COLUMN city TEXT DEFAULT ''",
        "ALTER TABLE users ADD COLUMN class_name TEXT DEFAULT ''",
        "ALTER TABLE users ADD COLUMN school_name TEXT DEFAULT ''",
    ):
        try:
            conn.execute(statement)
        except sqlite3.OperationalError:
            pass  # колонка уже есть

    # Учебный код приглашения из макета: A12-3B4 -> 5А / Школа №67
    conn.execute(
        """INSERT OR IGNORE INTO classes (invite_code, class_name, school_name)
           VALUES ('A12-3B4', '5А', 'Школа №67')""")
    conn.commit()


def query_all(sql: str, params: tuple = ()) -> list:
    return get_connection().execute(sql, params).fetchall()


def query_one(sql: str, params: tuple = ()):
    return get_connection().execute(sql, params).fetchone()


def execute(sql: str, params: tuple = ()) -> int:
    conn = get_connection()
    cursor = conn.execute(sql, params)
    conn.commit()
    return cursor.lastrowid
