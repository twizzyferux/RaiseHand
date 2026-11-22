"""Подтверждение аккаунта через почту или телефон.

Как это работает:
 1. create_code / send_registration_code — генерирует код, сохраняет в БД и отправляет.
 2. Отправка:
      * email.enabled + SMTP/SendGrid (креды из settings или env RH_SMTP_*);
      * sms.enabled + SMS.ru;
      * иначе при dev_mode — только data/outbox.log;
      * иначе — ошибка «отправка не настроена».
 3. check_code / check_registration_code — серверная проверка (клиент код не хранит).
"""

from __future__ import annotations

import random
import re
import smtplib
from datetime import datetime, timedelta
from email.message import EmailMessage
from typing import Optional

from core import database as db
from core import rate_limit
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
    length = int(rule("code_length") or 6)
    return "".join(str(random.randint(0, 9)) for _ in range(length))


def _normalize_code(code: str) -> str:
    return "".join(ch for ch in (code or "") if ch.isalnum()).upper()


def _expires_at() -> str:
    minutes = int(rule("code_lifetime_minutes") or 10)
    return (datetime.now() + timedelta(minutes=minutes)).strftime("%Y-%m-%d %H:%M:%S")


def email_ready() -> bool:
    """Есть рабочий email-провайдер с учётами."""
    cfg = SETTINGS.get("email") or {}
    if not cfg.get("enabled"):
        return False
    provider = (cfg.get("provider") or "smtp").lower()
    if provider == "sendgrid":
        return bool(cfg.get("sendgrid_api_key") and (cfg.get("from_address") or cfg.get("login")))
    return bool(cfg.get("login") and cfg.get("password") and cfg.get("smtp_host"))


def sms_ready() -> bool:
    cfg = SETTINGS.get("sms") or {}
    return bool(cfg.get("enabled") and cfg.get("api_key"))


def create_code(user_id: int, channel: str, target: str) -> None:
    """Создаёт код для существующего пользователя и отправляет. Код клиенту не отдаём."""
    target = validate_target(channel, target)
    try:
        rate_limit.check(
            f"verify:{channel}:{target.lower()}",
            limit=5,
            window_sec=600,
            block_sec=300,
            action="отправка кода",
        )
        rate_limit.check(
            f"verify:user:{user_id}",
            limit=8,
            window_sec=600,
            block_sec=300,
            action="отправка кода",
        )
    except rate_limit.RateLimitError as exc:
        raise VerificationError(str(exc)) from exc

    code = _generate_code()
    db.execute("UPDATE verification SET used = 1 WHERE user_id = ? AND used = 0", (user_id,))
    db.execute(
        "INSERT INTO verification (user_id, channel, target, code, expires_at) VALUES (?, ?, ?, ?, ?)",
        (user_id, channel, target, code, _expires_at()),
    )
    db.execute(
        "UPDATE users SET contact_type = ?, contact_value = ?, contact_verified = 0 WHERE id = ?",
        (channel, target, user_id),
    )
    _deliver(channel, target, code)


def send_registration_code(channel: str, target: str) -> None:
    """Код до создания пользователя: в registration_codes + доставка. Код клиенту не отдаём."""
    target = validate_target(channel, target)
    try:
        rate_limit.check(
            f"verify:{channel}:{target.lower()}",
            limit=5,
            window_sec=600,
            block_sec=300,
            action="отправка кода",
        )
    except rate_limit.RateLimitError as exc:
        raise VerificationError(str(exc)) from exc

    code = _generate_code()
    # погасить предыдущие неиспользованные коды на этот контакт
    db.execute(
        "UPDATE registration_codes SET used = 1 WHERE channel = ? AND lower(target) = lower(?) AND used = 0",
        (channel, target),
    )
    db.execute(
        "INSERT INTO registration_codes (channel, target, code, expires_at) VALUES (?, ?, ?, ?)",
        (channel, target, code, _expires_at()),
    )
    _deliver(channel, target, code)


def check_registration_code(channel: str, target: str, code: str) -> None:
    """Серверная проверка кода регистрации. При успехе помечает код использованным."""
    target = validate_target(channel, target)
    entered = _normalize_code(code)
    if not entered:
        raise VerificationError("Введите код подтверждения")

    row = db.query_one(
        """SELECT * FROM registration_codes
           WHERE channel = ? AND lower(target) = lower(?) AND used = 0
           ORDER BY id DESC LIMIT 1""",
        (channel, target),
    )
    if row is None:
        raise VerificationError("Код не запрашивался. Нажмите «Получить код»")
    if datetime.strptime(row["expires_at"], "%Y-%m-%d %H:%M:%S") < datetime.now():
        raise VerificationError("Срок действия кода истёк, запросите новый")
    if entered != str(row["code"]).strip().upper():
        raise VerificationError("Неверный код")

    db.execute("UPDATE registration_codes SET used = 1 WHERE id = ?", (row["id"],))


def _deliver(channel: str, target: str, code: str) -> None:
    text = f"Код подтверждения RaiseHand: {code}"
    email_cfg = SETTINGS.get("email") or {}
    if channel == CHANNEL_EMAIL and email_cfg.get("enabled"):
        if not email_ready():
            raise VerificationError(
                "Email включён, но не настроен. Для SendGrid нужен API-ключ "
                "(email.sendgrid_api_key или RH_SENDGRID_API_KEY), "
                "для SMTP — login/password."
            )
        provider = (email_cfg.get("provider") or "smtp").lower()
        if provider == "sendgrid":
            _send_email_sendgrid(target, text)
            _write_outbox(channel, target, text + "  [отправлено через SendGrid]")
        else:
            _send_email(target, text)
            _write_outbox(channel, target, text + "  [отправлено по SMTP]")
    elif channel == CHANNEL_PHONE and (SETTINGS.get("sms") or {}).get("enabled"):
        if not sms_ready():
            raise VerificationError("SMS включён, но api_key не задан.")
        _send_sms(target, text)
        _write_outbox(channel, target, text + "  [отправлено по SMS]")
    elif SETTINGS.get("dev_mode"):
        _write_outbox(channel, target, text + "  [dev: провайдер выключен]")
    else:
        raise VerificationError(
            "Отправка кода не настроена. Нужен email (SMTP/SendGrid) или SMS."
        )


def _write_outbox(channel: str, target: str, text: str) -> None:
    line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {channel} -> {target}: {text}\n"
    with open(OUTBOX_PATH, "a", encoding="utf-8") as f:
        f.write(line)


def _send_email(target: str, text: str) -> None:
    cfg = SETTINGS["email"]
    message = EmailMessage()
    message["Subject"] = "Подтверждение аккаунта RaiseHand"
    message["From"] = cfg.get("from_address") or cfg.get("login")
    message["To"] = target
    message.set_content(text)
    try:
        if cfg.get("use_ssl", True):
            server = smtplib.SMTP_SSL(cfg["smtp_host"], int(cfg.get("smtp_port") or 465), timeout=15)
        else:
            server = smtplib.SMTP(cfg["smtp_host"], int(cfg.get("smtp_port") or 587), timeout=15)
            server.starttls()
        with server:
            server.login(cfg["login"], cfg["password"])
            server.send_message(message)
    except Exception as exc:  # noqa: BLE001 — понятная ошибка пользователю
        raise VerificationError(f"Не удалось отправить письмо: {exc}") from exc


def _send_email_sendgrid(target: str, text: str) -> None:
    """Альтернатива SMTP: SendGrid Web API v3."""
    cfg = SETTINGS.get("email") or {}
    api_key = cfg.get("sendgrid_api_key") or cfg.get("api_key") or ""
    if not api_key:
        raise VerificationError("SendGrid: укажите email.sendgrid_api_key или RH_SENDGRID_API_KEY")
    from_addr = cfg.get("from_address") or cfg.get("login") or ""
    if not from_addr:
        raise VerificationError("SendGrid: укажите email.from_address или RH_SMTP_FROM")
    import json
    import urllib.error
    import urllib.request

    payload = {
        "personalizations": [{"to": [{"email": target}]}],
        "from": {"email": from_addr},
        "subject": "Подтверждение аккаунта RaiseHand",
        "content": [{"type": "text/plain", "value": text}],
    }
    req = urllib.request.Request(
        "https://api.sendgrid.com/v3/mail/send",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            if resp.status not in (200, 202):
                raise VerificationError(f"SendGrid HTTP {resp.status}")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        raise VerificationError(f"SendGrid: {exc.code} {body}") from exc
    except Exception as exc:
        raise VerificationError(f"Не удалось отправить через SendGrid: {exc}") from exc


def _send_sms(target: str, text: str) -> None:
    """Отправка SMS. Сейчас: SMS.ru (api_id в settings)."""
    cfg = SETTINGS.get("sms", {})
    provider = (cfg.get("provider") or "smsru").lower()
    api_key = cfg.get("api_key") or ""
    if not api_key:
        raise VerificationError("SMS не настроен: укажите api_key в config/settings.json")
    phone = target.lstrip("+")
    try:
        import json
        import urllib.parse
        import urllib.request

        if provider in ("smsru", "sms.ru"):
            data = urllib.parse.urlencode(
                {
                    "api_id": api_key,
                    "to": phone,
                    "msg": text,
                    "json": "1",
                }
            ).encode()
            req = urllib.request.Request("https://sms.ru/sms/send", data=data)
            with urllib.request.urlopen(req, timeout=15) as resp:
                body = json.loads(resp.read().decode())
            if str(body.get("status")) != "OK":
                raise VerificationError(f"SMS.ru: {body.get('status_text') or body}")
        else:
            raise VerificationError(f"SMS-провайдер «{provider}» не поддержан. Используйте smsru.")
    except VerificationError:
        raise
    except Exception as exc:
        raise VerificationError(f"Не удалось отправить SMS: {exc}") from exc


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
    entered = _normalize_code(code)
    if entered != str(row["code"]).strip().upper():
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
