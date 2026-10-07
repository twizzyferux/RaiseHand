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
