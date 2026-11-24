"""Регистрация, вход, пароли и генерация ID.

Пароль никогда не хранится открытым текстом: bcrypt (passlib).
Старые PBKDF2-записи продолжают приниматься и при входе переписываются в bcrypt.

ID пользователя:
    ученик  -> только цифры, например 4820193
    учитель -> U + цифры, например U4820193
    админ   -> A + цифры (позже смогут задать свой ID в админке)
"""

from __future__ import annotations

import re
import secrets
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from core import database as db
from core.config import rule
from core.ids import (
    generate_nickname,
    generate_public_id as build_public_id,
    normalize_public_id,
)
from core.models import RoleCode
from core.security import (
    hash_password,
    needs_rehash,
    verify_password as security_verify_password,
)

ROLE_STUDENT = RoleCode.STUDENT.value
ROLE_TEACHER = RoleCode.TEACHER.value
ROLE_ADMIN = RoleCode.ADMIN.value

# Обратная совместимость для старых импортов.
PBKDF2_ITERATIONS = 200_000


class AuthError(Exception):
    """Ошибка, текст которой можно прямо показать пользователю."""


# «Поле не трогать» — нужно там, где пустое значение значит удаление.
KEEP = object()


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
    is_banned: bool = False
    terms_accepted: bool = False
    terms_version: str = ""
    terms_accepted_at: Optional[str] = None
    inactive_delete_months: int = 12
    last_active_at: Optional[str] = None

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def display_name(self) -> str:
        """Имя и фамилия (ник — отдельно, через nickname / @handle)."""
        name = self.full_name
        if name:
            return name
        if self.nickname:
            return self.nickname
        return self.public_id or "Пользователь"

    @property
    def is_teacher(self) -> bool:
        return self.role == ROLE_TEACHER

    @property
    def is_admin(self) -> bool:
        return self.role == ROLE_ADMIN

    @property
    def is_student(self) -> bool:
        return self.role == ROLE_STUDENT

    @property
    def is_fully_verified(self) -> bool:
        if self.is_admin:
            return True
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
        is_banned=bool(_opt_int(row, "is_banned") or 0),
        terms_accepted=bool(_opt_int(row, "terms_accepted") or 0),
        terms_version=(_opt(row, "terms_version") or "") or "",
        terms_accepted_at=_opt(row, "terms_accepted_at"),
        inactive_delete_months=_opt_int(row, "inactive_delete_months") or 12,
        last_active_at=_opt(row, "last_active_at"),
    )


def _opt(row, key: str) -> Optional[str]:
    """Значение колонки, которой может не быть в старых базах."""
    try:
        return row[key]
    except (IndexError, KeyError):
        return None


def _opt_int(row, key: str) -> Optional[int]:
    try:
        val = row[key]
    except (IndexError, KeyError):
        return None
    if val is None:
        return None
    try:
        return int(val)
    except Exception:
        return None


# --------------------------------------------------------------------------- #
#  Пароли
# --------------------------------------------------------------------------- #

def verify_password(password: str, password_hash: str, salt_hex: str = "") -> bool:
    return security_verify_password(password, password_hash, salt_hex)


def validate_password(password: str, repeat: str) -> None:
    min_len = rule("min_password_length")
    if len(password) < min_len:
        raise AuthError(f"Пароль должен быть не короче {min_len} символов")
    if password != repeat:
        raise AuthError("Пароли не совпадают")


def _role_id(role: str) -> Optional[int]:
    row = db.query_one("SELECT id FROM roles WHERE code = ?", (role,))
    return int(row["id"]) if row is not None else None


def _public_id_exists(candidate: str) -> bool:
    return db.query_one("SELECT 1 FROM users WHERE public_id = ?", (candidate,)) is not None


def _nickname_exists(candidate: str, user_id: Optional[int] = None) -> bool:
    row = db.query_one(
        """SELECT id FROM users
           WHERE py_upper(nickname) = py_upper(?) AND id != ?""",
        (candidate, user_id if user_id is not None else -1),
    )
    return row is not None


# --------------------------------------------------------------------------- #
#  Генерация ID / ника
# --------------------------------------------------------------------------- #

def generate_public_id(role: str) -> str:
    """Уникальный public_id с учётом занятых значений в БД."""
    return build_public_id(role, exists=_public_id_exists)


make_public_id = generate_public_id


def make_unique_nickname(first_name: str = "", last_name: str = "",
                         public_id: str = "", user_id: Optional[int] = None) -> str:
    return generate_nickname(
        first_name,
        last_name,
        public_id=public_id,
        exists=lambda nick: _nickname_exists(nick, user_id=user_id),
    )


# --------------------------------------------------------------------------- #
#  Регистрация
# --------------------------------------------------------------------------- #

def _validate_name(first_name: str, last_name: str) -> None:
    if len(first_name.strip()) < 2 or len(last_name.strip()) < 2:
        raise AuthError("Введите имя и фамилию (минимум 2 символа)")
    if any(ch.isdigit() for ch in first_name + last_name):
        raise AuthError("В имени и фамилии не может быть цифр")


def _validate_nickname(nickname: str, user_id: Optional[int] = None) -> None:
    min_len = rule("nickname_min_length")
    nickname = (nickname or "").strip()
    if len(nickname) < min_len:
        raise AuthError(f"Ник должен быть не короче {min_len} символов")
    if not re.fullmatch(r"[A-Za-z0-9_.]+", nickname):
        raise AuthError(
            "Ник только латиницей: английские буквы, цифры, _ и . (без пробелов)"
        )
    if _nickname_exists(nickname, user_id=user_id):
        raise AuthError("Такой ник уже занят")


def register_student(first_name: str, last_name: str,
                     password: str, password_repeat: str,
                     nickname: str = "",
                     contact_type: Optional[str] = None,
                     contact_value: Optional[str] = None,
                     city: str = "",
                     class_name: str = "",
                     school_name: str = "",
                     auto_nickname: bool = True) -> User:
    """Создать ученика. Пустой ник → сгенерировать уникальный (если auto_nickname)."""
    first_name, last_name = first_name.strip(), last_name.strip()
    _validate_name(first_name, last_name)
    nickname = (nickname or "").strip()
    if nickname:
        _validate_nickname(nickname)
    elif not auto_nickname:
        nickname = None
    validate_password(password, password_repeat)
    return _create_user(
        ROLE_STUDENT, first_name, last_name, nickname or None, password,
        contact_type=contact_type, contact_value=contact_value,
        city=city, class_name=class_name, school_name=school_name,
        auto_nickname=auto_nickname,
    )


def register_teacher(first_name: str, last_name: str,
                     password: str, password_repeat: str,
                     auto_nickname: bool = True) -> User:
    first_name, last_name = first_name.strip(), last_name.strip()
    _validate_name(first_name, last_name)
    validate_password(password, password_repeat)
    return _create_user(
        ROLE_TEACHER, first_name, last_name, None, password,
        auto_nickname=auto_nickname,
    )


def register_admin(first_name: str, last_name: str,
                   password: str, password_repeat: str,
                   nickname: str = "") -> User:
    """Создать админа (обычно из скрипта/консоли, не из UI регистрации)."""
    first_name, last_name = first_name.strip(), last_name.strip()
    _validate_name(first_name, last_name)
    nickname = (nickname or "").strip() or None
    if nickname:
        _validate_nickname(nickname)
    validate_password(password, password_repeat)
    return _create_user(
        ROLE_ADMIN, first_name, last_name, nickname, password,
        auto_nickname=True,
    )


def _create_user(role: str, first_name: str, last_name: str,
                 nickname: Optional[str], password: str,
                 contact_type: Optional[str] = None,
                 contact_value: Optional[str] = None,
                 city: str = "",
                 class_name: str = "",
                 school_name: str = "",
                 auto_nickname: bool = True) -> User:
    password_hash, salt = hash_password(password)
    public_id = generate_public_id(role)
    if not nickname and auto_nickname:
        nickname = make_unique_nickname(first_name, last_name, public_id=public_id)
    role_fk = _role_id(role)
    user_id = db.execute(
        """INSERT INTO users (public_id, role, role_id, first_name, last_name, nickname,
                              password_hash, password_salt,
                              contact_type, contact_value, contact_verified,
                              city, class_name, school_name)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (public_id, role, role_fk, first_name, last_name, nickname, password_hash, salt,
         contact_type, contact_value, 1 if contact_value else 0,
         city, class_name, school_name),
    )
    return get_user_by_id(user_id)


def _normalize_invite_code(raw: str) -> str:
    """6 символов: A–Z и цифры (тире/пробелы убираем, регистр → upper)."""
    return "".join(
        ch for ch in (raw or "").upper() if ("A" <= ch <= "Z") or ch.isdigit()
    )


def create_class_invite(teacher_id: int, class_name: str, school_name: str = "") -> str:
    """Учитель создаёт класс — уникальный 6-символьный код (латиница + цифры)."""
    class_name = (class_name or "").strip()
    school_name = (school_name or "").strip()
    if len(class_name) < 1:
        raise AuthError("Укажите название класса")
    # без O/0 и I/1 — меньше путаницы при ручном вводе
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    for _ in range(40):
        code = "".join(secrets.choice(alphabet) for _ in range(6))
        exists = db.query_one(
            """SELECT id FROM classes
               WHERE upper(replace(replace(invite_code, '-', ''), ' ', '')) = ?""",
            (code,),
        )
        if exists:
            continue
        db.execute(
            """INSERT INTO classes (invite_code, class_name, school_name, teacher_id)
               VALUES (?, ?, ?, ?)""",
            (code, class_name, school_name, teacher_id),
        )
        return code
    raise AuthError("Не удалось создать код, попробуйте ещё раз")


def list_teacher_classes(teacher_id: int) -> list:
    return db.query_all(
        "SELECT * FROM classes WHERE teacher_id = ? ORDER BY id DESC",
        (teacher_id,),
    )


def find_class(invite_code: str):
    """Код приглашения -> строка таблицы classes (class_name, school_name)."""
    code = _normalize_invite_code(invite_code)
    if not code:
        raise AuthError("Введите код приглашения")
    if len(code) != 6:
        raise AuthError("Код класса — 6 символов (латиница и цифры)")
    row = db.query_one(
        """SELECT * FROM classes
           WHERE upper(replace(replace(invite_code, '-', ''), ' ', '')) = ?""",
        (code,),
    )
    if row is None:
        raise AuthError("Код не найден — узнайте его у учителя или в чате класса")
    return row


# --------------------------------------------------------------------------- #
#  Вход
# --------------------------------------------------------------------------- #

def login(login_value: str, password: str) -> User:
    """Войти можно по ID, по нику или по почте/телефону."""
    login_value = login_value.strip()
    lookup = normalize_public_id(login_value)
    row = db.query_one(
        """SELECT * FROM users
           WHERE public_id = ?
              OR py_upper(nickname) = py_upper(?)
              OR contact_value = ?""",
        (lookup, login_value, login_value),
    )
    if row is None:
        raise AuthError("Пользователь не найден")
    try:
        if int(row["is_banned"] or 0):
            raise AuthError("Аккаунт заблокирован")
    except (IndexError, KeyError):
        pass
    if not verify_password(password, row["password_hash"], row["password_salt"] or ""):
        raise AuthError("Неверный пароль")
    # Мягкая миграция PBKDF2 -> bcrypt при успешном входе.
    if needs_rehash(row["password_hash"]):
        new_hash, new_salt = hash_password(password)
        db.execute(
            "UPDATE users SET password_hash = ?, password_salt = ? WHERE id = ?",
            (new_hash, new_salt, row["id"]),
        )
    return row_to_user(row)


# --------------------------------------------------------------------------- #
#  Согласие, неактивность, удаление аккаунта
# --------------------------------------------------------------------------- #

INACTIVE_MONTH_CHOICES = (3, 6, 12, 18, 24)


def _add_months(moment: datetime, months: int) -> datetime:
    month_index = moment.month - 1 + int(months)
    year = moment.year + month_index // 12
    month = month_index % 12 + 1
    leap = year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
    month_days = [31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    day = min(moment.day, month_days[month - 1])
    return moment.replace(year=year, month=month, day=day)


def record_terms(user_id: int, version: str) -> User:
    """Записать в профиль, что человек принял конкретную версию правил."""
    version = (version or "").strip() or "2026-11-24"
    db.execute(
        """UPDATE users
           SET terms_accepted = 1,
               terms_version = ?,
               terms_accepted_at = datetime('now')
           WHERE id = ?""",
        (version, user_id),
    )
    user = get_user_by_id(user_id)
    if user is None:
        raise AuthError("Аккаунт не найден")
    return user


def set_inactive_delete_months(user_id: int, months: int) -> User:
    months = int(months)
    if months not in INACTIVE_MONTH_CHOICES:
        raise AuthError("Срок можно выбрать от 3 месяцев до 2 лет")
    db.execute(
        "UPDATE users SET inactive_delete_months = ? WHERE id = ?",
        (months, user_id),
    )
    user = get_user_by_id(user_id)
    if user is None:
        raise AuthError("Аккаунт не найден")
    return user


def touch_last_active(user_id: int) -> None:
    db.execute(
        "UPDATE users SET last_active_at = datetime('now') WHERE id = ?",
        (user_id,),
    )


def inactivity_due(user: User) -> bool:
    """Срок вышел, если человек не открывал приложение дольше выбранного периода."""
    raw = (user.last_active_at or "").strip()
    if not raw:
        return False
    try:
        seen = datetime.strptime(raw[:19], "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return False
    months = int(user.inactive_delete_months or 12)
    if months not in INACTIVE_MONTH_CHOICES:
        months = 12
    return datetime.utcnow() >= _add_months(seen, months)


def delete_account(user_id: int) -> None:
    """Удалить аккаунт и связанные строки. Чужие классы учителя остаются без владельца."""
    db.execute("DELETE FROM reports WHERE reporter_id = ?", (user_id,))
    db.execute("UPDATE classes SET teacher_id = NULL WHERE teacher_id = ?", (user_id,))
    db.execute("DELETE FROM users WHERE id = ?", (user_id,))


# --------------------------------------------------------------------------- #
#  Чтение и изменение профиля
# --------------------------------------------------------------------------- #

def get_user_by_id(user_id: int) -> Optional[User]:
    return row_to_user(db.query_one("SELECT * FROM users WHERE id = ?", (user_id,)))


def find_by_public_id(public_id: str) -> Optional[User]:
    public_id = normalize_public_id(public_id)
    return row_to_user(db.query_one("SELECT * FROM users WHERE public_id = ?", (public_id,)))


def search_users(
    query: str,
    *,
    exclude_user_id: Optional[int] = None,
    limit: int = 8,
) -> list[User]:
    """Живой поиск по public_id (префикс) + ник/имя. Без Enter — по мере ввода."""
    raw = (query or "").strip()
    if not raw:
        return []
    q = normalize_public_id(raw)
    if len(q) < 1:
        return []
    limit = max(1, min(int(limit), 20))
    id_prefix = f"{q}%"
    # Имя/ник — только от 2 символов; одна буква (U/A) = только ID-префикс
    soft_ok = len(q) >= 2
    soft = f"%{q}%" if soft_ok else q  # не сматчит лишнего, если soft_ok=False
    name_prefix = f"{q}%" if soft_ok else "__never__"
    nick_like = soft if soft_ok else "__never__"
    rows = db.query_all(
        """
        SELECT * FROM users
        WHERE (
            public_id LIKE ? COLLATE NOCASE
            OR IFNULL(nickname, '') LIKE ? COLLATE NOCASE
            OR first_name LIKE ? COLLATE NOCASE
            OR last_name LIKE ? COLLATE NOCASE
        )
          AND (? IS NULL OR id != ?)
        ORDER BY
          CASE
            WHEN public_id LIKE ? COLLATE NOCASE THEN 0
            WHEN IFNULL(nickname, '') LIKE ? COLLATE NOCASE THEN 1
            ELSE 2
          END,
          length(public_id),
          first_name,
          last_name
        LIMIT ?
        """,
        (
            id_prefix,
            nick_like,
            name_prefix,
            name_prefix,
            exclude_user_id,
            exclude_user_id,
            id_prefix,
            f"{q}%",
            limit,
        ),
    )
    out: list[User] = []
    for row in rows:
        user = row_to_user(row)
        if user is not None:
            out.append(user)
    return out


def list_accounts(*, exclude_user_id: Optional[int] = None, limit: int = 200) -> list[User]:
    """Аккаунты приложения, кроме текущего пользователя."""
    limit = max(1, min(int(limit), 400))
    rows = db.query_all(
        """
        SELECT * FROM users
        WHERE (? IS NULL OR id != ?)
        ORDER BY first_name, last_name, public_id
        LIMIT ?
        """,
        (exclude_user_id, exclude_user_id, limit),
    )
    out: list[User] = []
    for row in rows:
        user = row_to_user(row)
        if user is not None and not user.is_banned:
            out.append(user)
    return out


def _digits(value: str) -> str:
    return "".join(ch for ch in (value or "") if ch.isdigit())


def find_by_phone(raw: str) -> Optional[User]:
    """Найти аккаунт по номеру. Сравниваются последние 10 цифр."""
    digits = _digits(raw)
    if len(digits) < 6:
        return None
    tail = digits[-10:]
    rows = db.query_all(
        """
        SELECT * FROM users
        WHERE contact_value IS NOT NULL AND trim(contact_value) != ''
        """
    )
    for row in rows:
        user = row_to_user(row)
        if user is None or user.is_banned:
            continue
        stored = _digits(user.contact_value or "")
        if not stored:
            continue
        if stored == digits or stored.endswith(tail) or digits.endswith(stored[-10:]):
            return user
    return None


def change_password(user_id: int, new_password: str, repeat: str) -> None:
    """Смена пароля БЕЗ ввода старого — так описано в задании."""
    validate_password(new_password, repeat)
    password_hash, salt = hash_password(new_password)
    db.execute(
        "UPDATE users SET password_hash = ?, password_salt = ? WHERE id = ?",
        (password_hash, salt, user_id),
    )


def update_profile(
    user_id: int,
    nickname=KEEP,
    *,
    first_name=KEEP,
    last_name=KEEP,
    contact_value=KEEP,
    contact_type=KEEP,
    avatar_path: Optional[str] = None,
    status_text=KEEP,
) -> User:
    """Обновить профиль: имя, ник, телефон/контакт, описание."""
    user = get_user_by_id(user_id)
    if user is None:
        raise AuthError("Пользователь не найден")

    if first_name is not KEEP or last_name is not KEEP:
        fn = user.first_name if first_name is KEEP else str(first_name or "").strip()
        ln = user.last_name if last_name is KEEP else str(last_name or "").strip()
        _validate_name(fn, ln)
        if fn != user.first_name:
            db.execute("UPDATE users SET first_name = ? WHERE id = ?", (fn, user_id))
        if ln != user.last_name:
            db.execute("UPDATE users SET last_name = ? WHERE id = ?", (ln, user_id))

    if nickname is not KEEP:
        value = (nickname or "").strip() or None
        if value != user.nickname:
            if value:
                _validate_nickname(value, user_id=user_id)
            db.execute("UPDATE users SET nickname = ? WHERE id = ?", (value, user_id))

    if contact_value is not KEEP:
        cv = (str(contact_value).strip() if contact_value is not None else "") or None
        ct = user.contact_type
        if contact_type is not KEEP:
            ct = (str(contact_type).strip() if contact_type else None) or None
        elif cv and not ct:
            # грубая эвристика: цифры → phone, иначе email
            digits = sum(ch.isdigit() for ch in (cv or ""))
            ct = "phone" if digits >= 7 else "email"
        db.execute(
            "UPDATE users SET contact_value = ?, contact_type = ? WHERE id = ?",
            (cv, ct, user_id),
        )

    if avatar_path is not None:
        db.execute("UPDATE users SET avatar_path = ? WHERE id = ?", (avatar_path, user_id))

    if status_text is not KEEP:
        bio = "" if status_text is None else str(status_text).strip()
        if len(bio) > 280:
            raise AuthError("Описание слишком длинное (макс. 280 символов)")
        db.execute("UPDATE users SET status_text = ? WHERE id = ?", (bio, user_id))

    return get_user_by_id(user_id)
