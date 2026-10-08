"""Подтверждение аккаунта через почту или телефон.

Как это работает:
 1. create_code(...) — генерирует 6-значный код, кладёт его в таблицу verification
    и «отправляет».
 2. Отправка:
      * если в config/settings.json включён блок "email" — код реально уходит
        письмом по SMTP;
      * иначе (режим "dev_mode": true) код просто пишется в data/outbox.log
        и возвращается в приложение, чтобы его было видно на экране.
        Это удобно для защиты проекта: интернет и SMS-шлюз не нужны.
 3. check_code(...) — проверяет код, отмечает аккаунт подтверждённым.
"""

import random
import re
import smtplib
from datetime import datetime, timedelta
from email.message import EmailMessage
from typing import Optional

from core import database as db
from core.config import OUTBOX_PATH, SETTINGS, rule

CHANNEL_EMAIL = "email"
CHANNEL_PHONE = "phone"

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-zА-Яа-я]{2,}$")
PHONE_RE = re.compile(r"^\+?\d{10,15}$")


class VerificationError(Exception):
    """Ошибка, текст которой можно показать пользователю."""


def validate_target(channel: str, target: str) -> str:
    target = target.strip().replace(" ", "")
    if channel == CHANNEL_EMAIL:
        if not EMAIL_RE.match(target):
            raise VerificationError("Некорректная почта, пример: ivan@mail.ru")
    else:
        if not PHONE_RE.match(target):
            raise VerificationError("Некорректный номер, пример: +79001234567")
    return target


def _generate_code() -> str:
    length = rule("code_length")
    return "".join(str(random.randint(0, 9)) for _ in range(length))


def create_code(user_id: int, channel: str, target: str) -> str:
    """Создаёт код и отправляет его. Возвращает код (в dev-режиме он показывается)."""
    target = validate_target(channel, target)
    code = _generate_code()
    expires_at = datetime.now() + timedelta(minutes=rule("code_lifetime_minutes"))

    db.execute("UPDATE verification SET used = 1 WHERE user_id = ? AND used = 0", (user_id,))
    db.execute(
        "INSERT INTO verification (user_id, channel, target, code, expires_at) VALUES (?, ?, ?, ?, ?)",
        (user_id, channel, target, code, expires_at.strftime("%Y-%m-%d %H:%M:%S")),
    )
    db.execute("UPDATE users SET contact_type = ?, contact_value = ?, contact_verified = 0 WHERE id = ?",
               (channel, target, user_id))

    _deliver(channel, target, code)
    return code


def _deliver(channel: str, target: str, code: str) -> None:
    text = f"Код подтверждения: {code}"
    if channel == CHANNEL_EMAIL and SETTINGS["email"].get("enabled"):
        _send_email(target, text)
    elif channel == CHANNEL_PHONE and SETTINGS["sms"].get("enabled"):
        # Сюда можно вставить вызов любого SMS-сервиса (SMS.ru, Twilio и т.п.).
        _write_outbox(channel, target, text + "  [SMS-провайдер не настроен]")
    else:
        _write_outbox(channel, target, text)


def _write_outbox(channel: str, target: str, text: str) -> None:
    line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {channel} -> {target}: {text}\n"
    with open(OUTBOX_PATH, "a", encoding="utf-8") as f:
        f.write(line)


def _send_email(target: str, text: str) -> None:
    cfg = SETTINGS["email"]
    message = EmailMessage()
    message["Subject"] = "Подтверждение аккаунта"
    message["From"] = cfg["from_address"] or cfg["login"]
    message["To"] = target
    message.set_content(text)
    try:
        if cfg.get("use_ssl", True):
            server = smtplib.SMTP_SSL(cfg["smtp_host"], cfg["smtp_port"], timeout=15)
        else:
            server = smtplib.SMTP(cfg["smtp_host"], cfg["smtp_port"], timeout=15)
            server.starttls()
        with server:
            server.login(cfg["login"], cfg["password"])
            server.send_message(message)
    except Exception as exc:  # noqa: BLE001 — показываем пользователю понятную ошибку
        raise VerificationError(f"Не удалось отправить письмо: {exc}") from exc


def check_code(user_id: int, code: str) -> None:
    row = db.query_one(
        """SELECT * FROM verification
           WHERE user_id = ? AND used = 0
           ORDER BY id DESC LIMIT 1""",
        (user_id,),
    )
    if row is None:
        raise VerificationError("Код не запрашивался. Нажмите «Отправить код»")
    if datetime.strptime(row["expires_at"], "%Y-%m-%d %H:%M:%S") < datetime.now():
        raise VerificationError("Срок действия кода истёк, запросите новый")
    # разделители не важны: код могли вставить из буфера обмена
    # как «123 456» или «123-456»
    entered = "".join(ch for ch in code if ch.isalnum()).upper()
    if entered != row["code"].strip().upper():
        raise VerificationError("Неверный код")

    db.execute("UPDATE verification SET used = 1 WHERE id = ?", (row["id"],))
    db.execute("UPDATE users SET contact_verified = 1 WHERE id = ?", (user_id,))


def last_code(user_id: int) -> Optional[str]:
    """Только для dev-режима: показать последний код прямо в приложении."""
    if not SETTINGS.get("dev_mode"):
        return None
    row = db.query_one(
        "SELECT code FROM verification WHERE user_id = ? AND used = 0 ORDER BY id DESC LIMIT 1",
        (user_id,),
    )
    return row["code"] if row else None
