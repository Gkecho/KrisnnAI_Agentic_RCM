"""Engine factory. KRISNNAI_DB_URL (any SQLAlchemy URL, e.g. sqlite:///dev.db) overrides SQL Server."""

from __future__ import annotations

import os

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine

from krisnnai.config import DbSettings


def make_engine(url: str | None = None) -> Engine:
    url = url or os.environ.get("KRISNNAI_DB_URL") or DbSettings.from_env().sqlalchemy_url()
    engine = create_engine(url)
    if engine.dialect.name == "sqlite":

        @event.listens_for(engine, "connect")
        def _fk_on(dbapi_conn, _record):
            dbapi_conn.execute("PRAGMA foreign_keys=ON")

    return engine
