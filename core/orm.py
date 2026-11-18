# -*- coding: utf-8 -*-
"""SQLAlchemy engine / session.

По умолчанию — SQLite рядом с приложением.
Переход на PostgreSQL: RH_DATABASE_URL=postgresql+psycopg://user:pass@host/db
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator, Optional

from sqlalchemy import create_engine, event, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from core.config import DB_PATH
from core.models import ROLE_TITLES, Base, Role, RoleCode

_engine: Optional[Engine] = None
_SessionLocal: Optional[sessionmaker[Session]] = None


def database_url() -> str:
    url = os.environ.get("RH_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if url:
        return url
    # SQLite: три слэша = абсолютный путь на Windows тоже ок через pathlib-стиль
    path = DB_PATH.replace("\\", "/")
    return f"sqlite:///{path}"


def get_engine() -> Engine:
    global _engine, _SessionLocal
    if _engine is None:
        url = database_url()
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        _engine = create_engine(url, future=True, echo=False, connect_args=connect_args)

        if url.startswith("sqlite"):

            @event.listens_for(_engine, "connect")
            def _sqlite_pragma(dbapi_conn, _connection_record):
                cursor = dbapi_conn.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

        _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, future=True)
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    get_engine()
    assert _SessionLocal is not None
    return _SessionLocal


@contextmanager
def session_scope() -> Iterator[Session]:
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def seed_roles(session: Session) -> None:
    """Гарантирует наличие трёх ролей в таблице roles."""
    existing = {row.code for row in session.scalars(select(Role)).all()}
    for code in RoleCode:
        if code in existing:
            continue
        session.add(Role(code=code, title=ROLE_TITLES[code]))
    session.flush()


def init_orm() -> None:
    """Создать таблицы ORM и заполнить роли."""
    engine = get_engine()
    Base.metadata.create_all(engine)
    with session_scope() as session:
        seed_roles(session)
