"""Регистрация, вход, пароли и генерация ID.

Пароль НИКОГДА не хранится в открытом виде: хранится соль и хеш PBKDF2-SHA256.
ID пользователя:
    ученик  -> 7 цифр, например 4820193
    учитель -> буква U + 7 цифр, например U4820193
"""

import hashlib
import os
import random
import re
from dataclasses import dataclass
from typing import Optional

from core import database as db
from core.config import rule

ROLE_STUDENT = "student"
ROLE_TEACHER = "teacher"

PBKDF2_ITERATIONS = 200_000


class AuthError(Exception):
    """Ошибка, текст которой можно прямо показать пользователю."""


@dataclass
class User:
    id: int
    public_id: str
    role: str
    first_name: str
    last_name: str
    nickname: Optional[str]
    contact_type: Optional[str]
    contact_value: Optional[str]
    contact_verified: bool
    teacher_verified: bool
    avatar_path: Optional[str]
    status_text: str
    city: Optional[str] = None
    class_name: Optional[str] = None
    school_name: Optional[str] = None

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def display_name(self) -> str:
        """Что показывать в профиле и в списке чатов."""
        if self.role == ROLE_STUDENT and self.nickname:
            return self.nickname
        return self.full_name

    @property
    def is_teacher(self) -> bool:
        return self.role == ROLE_TEACHER

    @property
    def is_fully_verified(self) -> bool:
        if self.is_teacher:
            return self.contact_verified and self.teacher_verified
        return self.contact_verified


def row_to_user(row) -> Optional[User]:
    if row is None:
        return None
    return User(
        id=row["id"],
        public_id=row["public_id"],
        role=row["role"],
        first_name=row["first_name"],
        last_name=row["last_name"],
        nickname=row["nickname"],
        contact_type=row["contact_type"],
        contact_value=row["contact_value"],
        contact_verified=bool(row["contact_verified"]),
        teacher_verified=bool(row["teacher_verified"]),
        avatar_path=row["avatar_path"],
        status_text=row["status_text"] or "",
        city=_opt(row, "city"),
        class_name=_opt(row, "class_name"),
        school_name=_opt(row, "school_name"),
    )


def _opt(row, key: str) -> Optional[str]:
    """Значение колонки, которой может не быть в старых базах."""
    try:
        return row[key]
    except (IndexError, KeyError):
        return None


# --------------------------------------------------------------------------- #
#  Пароли
# --------------------------------------------------------------------------- #

def hash_password(password: str, salt: Optional[bytes] = None):
    if salt is None:
        salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return digest.hex(), salt.hex()


def verify_password(password: str, password_hash: str, salt_hex: str) -> bool:
    digest, _ = hash_password(password, bytes.fromhex(salt_hex))
    return digest == password_hash


def validate_password(password: str, repeat: str) -> None:
    min_len = rule("min_password_length")
    if len(password) < min_len:
        raise AuthError(f"Пароль должен быть не короче {min_len} символов")
    if password != repeat:
        raise AuthError("Пароли не совпадают")


# --------------------------------------------------------------------------- #
#  Генерация ID
# --------------------------------------------------------------------------- #

def generate_public_id(role: str) -> str:
    digits = rule("student_id_digits")
    prefix = rule("teacher_id_prefix") if role == ROLE_TEACHER else ""
    while True:
        number = "".join(str(random.randint(0, 9)) for _ in range(digits))
        candidate = f"{prefix}{number}"
        if db.query_one("SELECT 1 FROM users WHERE public_id = ?", (candidate,)) is None:
            return candidate


# --------------------------------------------------------------------------- #
#  Регистрация
# --------------------------------------------------------------------------- #

def _validate_name(first_name: str, last_name: str) -> None:
    if len(first_name.strip()) < 2 or len(last_name.strip()) < 2:
        raise AuthError("Введите имя и фамилию (минимум 2 символа)")


def _validate_nickname(nickname: str) -> None:
    min_len = rule("nickname_min_length")
    if len(nickname) < min_len:
        raise AuthError(f"Ник должен быть не короче {min_len} символов")
    if not re.fullmatch(r"[A-Za-zА-Яа-я0-9_.]+", nickname):
        raise AuthError("В нике можно использовать только буквы, цифры, _ и .")
    if db.query_one("SELECT 1 FROM users WHERE nickname = ?", (nickname,)):
        raise AuthError("Такой ник уже занят")


def register_student(first_name: str, last_name: str,
                     password: str, password_repeat: str,
                     nickname: str = "",
                     contact_type: Optional[str] = None,
                     contact_value: Optional[str] = None,
                     city: str = "",
                     class_name: str = "",
                     school_name: str = "") -> User:
    """Создать ученика. Ник не обязателен (новый флоу регистрации его не спрашивает).

    contact_* заполняются на шаге «Подтверждение» — код уже проверен,
    поэтому contact_verified = 1.
    """
    first_name, last_name = first_name.strip(), last_name.strip()
    _validate_name(first_name, last_name)
    nickname = (nickname or "").strip()
    if nickname:
        _validate_nickname(nickname)
    else:
        nickname = None
    validate_password(password, password_repeat)
    return _create_user(ROLE_STUDENT, first_name, last_name, nickname, password,
                        contact_type=contact_type, contact_value=contact_value,
                        city=city, class_name=class_name, school_name=school_name)


def find_class(invite_code: str):
    """Код приглашения -> строка таблицы classes (class_name, school_name).

    Регистр не важен: код из макета «A12-3B4», а человек может
    набрать «a12-3b4» — сравниваем без учёта регистра.
    """
    invite_code = invite_code.strip()
    if not invite_code:
        raise AuthError("Введите код приглашения")
    row = db.query_one(
        "SELECT * FROM classes WHERE UPPER(invite_code) = ?",
        (invite_code.upper(),))
    if row is None:
        raise AuthError("Код не найден — узнайте его у учителя или в чате класса")
    return row


def register_teacher(first_name: str, last_name: str,
                     password: str, password_repeat: str) -> User:
    first_name, last_name = first_name.strip(), last_name.strip()
    _validate_name(first_name, last_name)
    validate_password(password, password_repeat)
    return _create_user(ROLE_TEACHER, first_name, last_name, None, password)


def _create_user(role: str, first_name: str, last_name: str,
                 nickname: Optional[str], password: str,
                 contact_type: Optional[str] = None,
                 contact_value: Optional[str] = None,
                 city: str = "",
                 class_name: str = "",
                 school_name: str = "") -> User:
    password_hash, salt = hash_password(password)
    public_id = generate_public_id(role)
    user_id = db.execute(
        """INSERT INTO users (public_id, role, first_name, last_name, nickname,
                              password_hash, password_salt,
                              contact_type, contact_value, contact_verified,
                              city, class_name, school_name)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (public_id, role, first_name, last_name, nickname, password_hash, salt,
         contact_type, contact_value, 1 if contact_value else 0,
         city, class_name, school_name),
    )
    return get_user_by_id(user_id)


# --------------------------------------------------------------------------- #
#  Вход
# --------------------------------------------------------------------------- #

def login(login_value: str, password: str) -> User:
    """Войти можно по ID, по нику или по почте/телефону."""
    login_value = login_value.strip()
    row = db.query_one(
        """SELECT * FROM users
           WHERE public_id = ? OR nickname = ? OR contact_value = ?""",
        (login_value.upper() if login_value[:1].upper() == "U" else login_value,
         login_value, login_value),
    )
    if row is None:
        raise AuthError("Пользователь не найден")
    if not verify_password(password, row["password_hash"], row["password_salt"]):
        raise AuthError("Неверный пароль")
    return row_to_user(row)


# --------------------------------------------------------------------------- #
#  Чтение и изменение профиля
# --------------------------------------------------------------------------- #

def get_user_by_id(user_id: int) -> Optional[User]:
    return row_to_user(db.query_one("SELECT * FROM users WHERE id = ?", (user_id,)))


def find_by_public_id(public_id: str) -> Optional[User]:
    public_id = public_id.strip()
    if public_id[:1].lower() == "u":
        public_id = "U" + public_id[1:]
    return row_to_user(db.query_one("SELECT * FROM users WHERE public_id = ?", (public_id,)))


def change_password(user_id: int, new_password: str, repeat: str) -> None:
    """Смена пароля БЕЗ ввода старого — так описано в задании."""
    validate_password(new_password, repeat)
    password_hash, salt = hash_password(new_password)
    db.execute("UPDATE users SET password_hash = ?, password_salt = ? WHERE id = ?",
               (password_hash, salt, user_id))


def update_profile(user_id: int, nickname: Optional[str] = None,
                   avatar_path: Optional[str] = None,
                   status_text: Optional[str] = None) -> User:
    user = get_user_by_id(user_id)
    if nickname is not None and nickname != user.nickname:
        _validate_nickname(nickname)
        db.execute("UPDATE users SET nickname = ? WHERE id = ?", (nickname, user_id))
    if avatar_path is not None:
        db.execute("UPDATE users SET avatar_path = ? WHERE id = ?", (avatar_path, user_id))
    if status_text is not None:
        db.execute("UPDATE users SET status_text = ? WHERE id = ?", (status_text, user_id))
    return get_user_by_id(user_id)
