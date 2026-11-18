# -*- coding: utf-8 -*-
"""Вопросы группы: лайки, дедуп похожих формулировок, рейтинг + Gemini."""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Optional

# локальный порог после нормализации (третью→3 и т.п.)
SIMILARITY_THRESHOLD = 0.74
# кандидаты для ИИ: мягкий порог
AI_CANDIDATE_THRESHOLD = 0.45

_NUM_WORDS = {
    "ноль": "0", "нулевой": "0",
    "один": "1", "одна": "1", "одно": "1", "первую": "1", "первый": "1",
    "первое": "1", "первая": "1", "первой": "1", "первого": "1",
    "два": "2", "две": "2", "вторую": "2", "второй": "2", "второе": "2",
    "вторая": "2", "второго": "2",
    "три": "3", "третью": "3", "третий": "3", "третье": "3", "третья": "3",
    "третьей": "3", "третьего": "3", "третьим": "3",
    "четыре": "4", "четвёртую": "4", "четвертую": "4", "четвёртый": "4",
    "четвертый": "4", "четвёртое": "4", "четвертое": "4",
    "пять": "5", "пятую": "5", "пятый": "5", "пятое": "5", "пятая": "5",
    "шесть": "6", "шестую": "6", "шестой": "6",
    "семь": "7", "седьмую": "7", "седьмой": "7",
    "восемь": "8", "восьмую": "8", "восьмой": "8",
    "девять": "9", "девятую": "9", "девятый": "9",
    "десять": "10", "десятую": "10", "десятый": "10",
}

_STOP = {
    "пожалуйста", "подскажите", "скажите", "вопрос", "можно", "ли",
    "как", "что", "где", "когда", "из", "в", "на", "по", "к", "и", "а",
}


@dataclass
class Question:
    id: str
    text: str
    likes: int = 1
    liked_by_me: bool = False
    author_count: int = 1
    answer_text: str = ""
    answer_by: str = ""  # имя учителя
    answered: bool = False

    def __post_init__(self) -> None:
        if not self.id:
            self.id = uuid.uuid4().hex[:12]
        if self.answer_text and not self.answered:
            self.answered = True


_STORE: dict[str, list[Question]] = {}


def _norm(text: str) -> str:
    t = (text or "").lower().replace("ё", "е").strip()
    t = re.sub(r"[^\w\sа-яa-z0-9]", " ", t, flags=re.IGNORECASE)
    parts: list[str] = []
    for w in t.split():
        w = _NUM_WORDS.get(w, w)
        if w in _STOP:
            continue
        # домашка / дз / домашней
        if w.startswith("домаш"):
            w = "дз"
        if w.startswith("задач"):
            w = "задача"
        parts.append(w)
    # стабильный порядок: числа рядом с «задача»
    return " ".join(parts)


def _token_set(text: str) -> set[str]:
    return set(_norm(text).split())


def similarity(a: str, b: str) -> float:
    na, nb = _norm(a), _norm(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    seq = SequenceMatcher(None, na, nb).ratio()
    sa, sb = _token_set(a), _token_set(b)
    if not sa or not sb:
        return seq
    jacc = len(sa & sb) / max(1, len(sa | sb))
    # числа обязаны совпасть, если есть в обоих
    nums_a = {t for t in sa if t.isdigit()}
    nums_b = {t for t in sb if t.isdigit()}
    if nums_a and nums_b and nums_a != nums_b:
        return min(seq, jacc) * 0.5
    return max(seq, 0.55 * seq + 0.45 * jacc)


def _ensure_demo(group_id: str) -> None:
    if group_id in _STORE:
        return
    demos = {
        "g1": [
            ("Как решить задачу 3 из домашки?", 14, True),
            ("Когда контрольная по алгебре?", 9, False),
            ("Можно сдать реферат позже?", 6, False),
            ("Где найти презентацию к уроку?", 4, False),
            ("Будет ли собрание в пятницу?", 2, False),
        ],
        "g2": [
            ("Объясните формулу из §4", 11, False),
            ("Как считать интеграл в 3 задаче?", 8, True),
            ("Нужен ли калькулятор на зачёте?", 3, False),
        ],
        "g4": [
            ("Как доказать теорему из тетради?", 7, False),
            ("Что будет на самостоятельной?", 5, True),
        ],
    }
    rows = demos.get(group_id) or [
        ("Есть ли доп. материалы?", 3, False),
        ("Когда следующий урок?", 2, False),
    ]
    built: list[Question] = []
    for t, likes, liked in rows:
        built.append(
            Question(
                id=uuid.uuid4().hex[:10],
                text=t,
                likes=likes,
                liked_by_me=liked,
                author_count=max(1, likes // 3),
            )
        )
    # демо-ответ учителя на топ-вопрос
    if group_id == "g1" and built:
        built[0].answer_text = (
            "Разберите пример на стр. 42: сначала приведите подобные, "
            "затем выразите x. Если застрянете — напишите в чат."
        )
        built[0].answer_by = "Елена В."
        built[0].answered = True
    _STORE[group_id] = built


def _merge_into(dst: Question, src: Question) -> None:
    dst.likes += src.likes
    dst.author_count += src.author_count
    dst.liked_by_me = dst.liked_by_me or src.liked_by_me
    # ответ учителя сохраняем (не затираем пустым)
    if src.answered and src.answer_text:
        if not dst.answered or not dst.answer_text:
            dst.answer_text = src.answer_text
            dst.answer_by = src.answer_by
            dst.answered = True


def consolidate(group_id: str) -> None:
    """Склеить уже попавшие дубликаты (локальная нормализация; ИИ — при добавлении)."""
    _ensure_demo(group_id)
    items = list(_STORE.get(group_id) or [])
    if len(items) < 2:
        return
    kept: list[Question] = []
    for q in items:
        matched: Optional[Question] = None
        for k in kept:
            if similarity(q.text, k.text) >= SIMILARITY_THRESHOLD:
                matched = k
                break
        if matched is not None:
            _merge_into(matched, q)
        else:
            kept.append(q)
    _STORE[group_id] = kept


def list_ranked(group_id: str) -> list[Question]:
    consolidate(group_id)
    items = list(_STORE.get(group_id) or [])
    items.sort(key=lambda q: (-q.likes, q.text.lower()))
    return items


def count_for_group(group_id: str) -> int:
    return len(list_ranked(group_id))


def find_similar(group_id: str, text: str, *, use_ai: bool = True) -> Optional[Question]:
    _ensure_demo(group_id)
    items = list(_STORE.get(group_id) or [])
    best: Optional[Question] = None
    best_score = 0.0
    for q in items:
        s = similarity(text, q.text)
        if s >= SIMILARITY_THRESHOLD and s > best_score:
            best, best_score = q, s
    if best is not None:
        return best

    if not use_ai:
        return None
    try:
        from core import ai_similarity

        if not ai_similarity.available() or not items:
            return None
        # в ИИ отдаём все (для группы обычно мало) или топ по мягкому скору
        scored = sorted(
            ((similarity(text, q.text), q) for q in items),
            key=lambda x: -x[0],
        )
        candidates = [q for s, q in scored if s >= AI_CANDIDATE_THRESHOLD] or [
            q for _, q in scored[:8]
        ]
        idx = ai_similarity.find_same_question_index(text, [q.text for q in candidates])
        if idx is not None:
            return candidates[idx]
    except Exception:
        return None
    return None


def add_or_like(group_id: str, text: str) -> tuple[Question, bool]:
    text = (text or "").strip()
    if not text:
        raise ValueError("Пустой вопрос")
    _ensure_demo(group_id)
    existing = find_similar(group_id, text, use_ai=True)
    if existing is not None:
        existing.likes += 1
        existing.author_count += 1
        if not existing.liked_by_me:
            existing.liked_by_me = True
        return existing, True
    q = Question(
        id=uuid.uuid4().hex[:10],
        text=text,
        likes=1,
        liked_by_me=False,
        author_count=1,
    )
    _STORE.setdefault(group_id, []).append(q)
    return q, False


def toggle_like(group_id: str, question_id: str) -> Optional[Question]:
    _ensure_demo(group_id)
    for q in _STORE.get(group_id) or []:
        if q.id != question_id:
            continue
        if q.liked_by_me:
            q.liked_by_me = False
            q.likes = max(1, q.likes - 1)
        else:
            q.liked_by_me = True
            q.likes += 1
        return q
    return None


def set_answer(
    group_id: str,
    question_id: str,
    answer: str,
    *,
    teacher_name: str = "Учитель",
) -> Optional[Question]:
    """Ответ учителя на вопрос (виден всем ученикам)."""
    answer = (answer or "").strip()
    if not answer:
        raise ValueError("Пустой ответ")
    _ensure_demo(group_id)
    for q in _STORE.get(group_id) or []:
        if q.id != question_id:
            continue
        q.answer_text = answer
        q.answer_by = teacher_name or "Учитель"
        q.answered = True
        return q
    return None


def clear_answer(group_id: str, question_id: str) -> Optional[Question]:
    _ensure_demo(group_id)
    for q in _STORE.get(group_id) or []:
        if q.id != question_id:
            continue
        q.answer_text = ""
        q.answer_by = ""
        q.answered = False
        return q
    return None


def sync_group_count(group_id: str) -> int:
    n = count_for_group(group_id)
    try:
        from flet_app import chat_data

        g = chat_data.get_group(group_id)
        if g is not None:
            g.questions_count = n
    except Exception:
        pass
    return n


def ai_status() -> str:
    try:
        from core import ai_similarity

        return "gemini" if ai_similarity.available() else "local"
    except Exception:
        return "local"
