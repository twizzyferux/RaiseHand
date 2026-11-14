"""Подтверждение статуса учителя.

Учитель выбирает площадку (МЭШ, Дневник.ру, Учи.ру и т.д.) и подтверждает
себя одним из двух способов:
  * 'code'       — одноразовый код, который школа/завуч выдаёт учителю;
  * 'screenshot' — скриншот личного кабинета с этой площадки (файл копируется
                   в data/uploads/).

В учебном проекте проверка автоматическая (см. AUTO_APPROVE): заявка сразу
получает статус approved. В «настоящем» варианте заявку в статусе pending
проверял бы администратор — для этого есть функция approve()/reject().
"""

import os
import shutil
from datetime import datetime
from typing import List, Optional

from core import database as db
from core.config import SETTINGS, UPLOADS_DIR

AUTO_APPROVE = True  # поставь False, если заявки должен проверять администратор

PROOF_CODE = "code"
PROOF_SCREENSHOT = "screenshot"

# «Школьные» одноразовые коды. В реальном проекте их выдаёт администратор
# и хранит в отдельной таблице — здесь список для демонстрации.
VALID_ONE_TIME_CODES = {"UCH-2024", "TEACHER-777", "SCHOOL-1"}


class ProofError(Exception):
    """Ошибка, текст которой можно показать пользователю."""


def platforms() -> List[str]:
    return list(SETTINGS["teacher_platforms"])


def submit_code(user_id: int, platform: str, code: str) -> str:
    code = code.strip().upper()
    if platform not in platforms():
        raise ProofError("Выберите площадку из списка")
    if not code:
        raise ProofError("Введите одноразовый код")
    if AUTO_APPROVE and code not in VALID_ONE_TIME_CODES:
        raise ProofError("Такого одноразового кода нет. Пример кода: UCH-2024")
    return _save(user_id, platform, PROOF_CODE, code)


def submit_screenshot(user_id: int, platform: str, file_path: str) -> str:
    if platform not in platforms():
        raise ProofError("Выберите площадку из списка")
    if not file_path or not os.path.isfile(file_path):
        raise ProofError("Файл скриншота не выбран")
    if os.path.splitext(file_path)[1].lower() not in (".png", ".jpg", ".jpeg", ".webp"):
        raise ProofError("Скриншот должен быть картинкой: png, jpg или webp")

    name = f"proof_{user_id}_{datetime.now():%Y%m%d_%H%M%S}{os.path.splitext(file_path)[1].lower()}"
    target = os.path.join(UPLOADS_DIR, name)
    shutil.copyfile(file_path, target)
    return _save(user_id, platform, PROOF_SCREENSHOT, target)


def _save(user_id: int, platform: str, proof_type: str, value: str) -> str:
    status = "approved" if AUTO_APPROVE else "pending"
    db.execute(
        """INSERT INTO teacher_proofs (user_id, platform, proof_type, proof_value, status)
           VALUES (?, ?, ?, ?, ?)""",
        (user_id, platform, proof_type, value, status),
    )
    if status == "approved":
        db.execute("UPDATE users SET teacher_verified = 1 WHERE id = ?", (user_id,))
    return status


def last_proof(user_id: int) -> Optional[dict]:
    row = db.query_one(
        "SELECT * FROM teacher_proofs WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,)
    )
    return dict(row) if row else None


def approve(proof_id: int) -> None:
    row = db.query_one("SELECT user_id FROM teacher_proofs WHERE id = ?", (proof_id,))
    if row is None:
        raise ProofError("Заявка не найдена")
    db.execute("UPDATE teacher_proofs SET status = 'approved' WHERE id = ?", (proof_id,))
    db.execute("UPDATE users SET teacher_verified = 1 WHERE id = ?", (row["user_id"],))


def reject(proof_id: int) -> None:
    db.execute("UPDATE teacher_proofs SET status = 'rejected' WHERE id = ?", (proof_id,))


def submit_to_discord(name: str, city: str, school: str, photo_path: str) -> str:
    """Отправляет анкету (текст + фото) в Discord webhook. Возвращает id заявки."""
    import uuid
    from datetime import datetime
    from core.config import SETTINGS, OUTBOX_PATH, DATA_DIR
    import os
    import json

    app_id = uuid.uuid4().hex[:10]
    record = {
        "id": app_id,
        "name": name,
        "city": city,
        "school": school,
        "photo": photo_path,
        "status": "pending",
        "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    pending_dir = os.path.join(DATA_DIR, "teacher_apps")
    os.makedirs(pending_dir, exist_ok=True)
    with open(os.path.join(pending_dir, f"{app_id}.json"), "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)

    cfg = SETTINGS.get("discord") or {}
    url = cfg.get("webhook_url") or ""
    text = (
        f"**Анкета учителя** `#{app_id}`\n"
        f"Имя: {name}\n"
        f"Город: {city}\n"
        f"Место работы: {school}\n"
        f"Одобрите или отклоните в боте."
    )
    if not url:
        with open(OUTBOX_PATH, "a", encoding="utf-8") as f:
            f.write(f"[{record['created']}] discord teacher #{app_id}: {name}, {city}, {school}, photo={photo_path}\n")
        return app_id

    # multipart: payload_json + file
    import mimetypes
    boundary = "----RaiseHandBoundary"
    filename = os.path.basename(photo_path) or "proof.jpg"
    mime = mimetypes.guess_type(filename)[0] or "image/jpeg"
    with open(photo_path, "rb") as img:
        file_bytes = img.read()
    payload = json.dumps({"content": text}).encode()
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="payload_json"\r\n\r\n'
    ).encode() + payload + b"\r\n" + (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="files[0]"; filename="{filename}"\r\n'
        f"Content-Type: {mime}\r\n\r\n"
    ).encode() + file_bytes + f"\r\n--{boundary}--\r\n".encode()

    import urllib.request
    import urllib.error
    req = urllib.request.Request(
        url.strip(),
        data=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": "RaiseHand (https://github.com/raisehand, 1.0)",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            if resp.status not in (200, 204):
                raise RuntimeError(f"Discord {resp.status}")
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8", errors="replace")[:300]
        except Exception:
            pass
        raise RuntimeError(f"Discord {exc.code}: {detail or exc.reason}") from exc
    _post_with_buttons(app_id, name, city, school, photo_path)
    return app_id


def approval_status(app_id: str) -> str:
    """pending | approved | rejected"""
    from core.config import DATA_DIR
    import os
    import json
    path = os.path.join(DATA_DIR, "teacher_apps", f"{app_id}.json")
    if not os.path.exists(path):
        return "pending"
    with open(path, encoding="utf-8") as f:
        return json.load(f).get("status", "pending")


def _post_with_buttons(app_id: str, name: str, city: str, school: str, photo_path: str) -> None:
    """Сообщение с кнопками через токен бота (вебхук кнопки не умеет)."""
    from core.config import SETTINGS
    import json
    import os
    import urllib.request
    import urllib.error

    cfg = SETTINGS.get("discord") or {}
    token = (cfg.get("bot_token") or "").strip()
    if not token:
        return
    channel_id = str(cfg.get("channel_id") or "").strip()
    if not channel_id.isdigit():
        wh = (cfg.get("webhook_url") or "").strip()
        if wh:
            try:
                req = urllib.request.Request(wh, headers={"User-Agent": "RaiseHandBot"})
                with urllib.request.urlopen(req, timeout=15) as resp:
                    info = json.loads(resp.read().decode())
                channel_id = str(info.get("channel_id") or "")
            except Exception:
                channel_id = ""
    if not channel_id.isdigit():
        raise RuntimeError("Не удалось определить канал. Укажи discord.channel_id")

    content = (
        f"**Анкета учителя** `#{app_id}`\n"
        f"Имя: {name}\nГород: {city}\nМесто работы: {school}"
    )
    payload = {
        "content": content,
        "components": [{
            "type": 1,
            "components": [
                {"type": 2, "style": 3, "label": "Одобрить", "custom_id": f"approve:{app_id}"},
                {"type": 2, "style": 4, "label": "Отклонить", "custom_id": f"reject:{app_id}"},
            ],
        }],
    }
    url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
    # с файлом — multipart, без — json
    if photo_path and os.path.exists(photo_path):
        import mimetypes
        boundary = "----RaiseHandBtn"
        filename = os.path.basename(photo_path)
        mime = mimetypes.guess_type(filename)[0] or "image/jpeg"
        with open(photo_path, "rb") as f:
            file_bytes = f.read()
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="payload_json"\r\n'
            f"Content-Type: application/json\r\n\r\n"
        ).encode() + json.dumps(payload).encode() + b"\r\n" + (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="files[0]"; filename="{filename}"\r\n'
            f"Content-Type: {mime}\r\n\r\n"
        ).encode() + file_bytes + f"\r\n--{boundary}--\r\n".encode()
        headers = {
            "Authorization": f"Bot {token}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": "RaiseHandBot",
        }
        data = body
    else:
        headers = {
            "Authorization": f"Bot {token}",
            "Content-Type": "application/json",
            "User-Agent": "RaiseHandBot",
        }
        data = json.dumps(payload).encode()

    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            if resp.status not in (200, 201):
                raise RuntimeError(f"Discord {resp.status}")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:400]
        raise RuntimeError(f"Бот не смог отправить кнопки: {exc.code} {detail}") from exc
