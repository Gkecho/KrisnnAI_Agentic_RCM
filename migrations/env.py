"""Alembic environment. Targets SQL Server; KRISNNAI_ALEMBIC_URL overrides (used by tests)."""

import os

from alembic import context
from sqlalchemy import create_engine

import krisnnai.model  # noqa: F401  (registers all tables)
from krisnnai.config import DbSettings
from krisnnai.model.base import Base

config = context.config
target_metadata = Base.metadata


def _url() -> str:
    return os.environ.get("KRISNNAI_ALEMBIC_URL") or DbSettings.from_env().sqlalchemy_url()


def run_migrations_offline() -> None:
    # Offline (--sql) needs no server: emit T-SQL for the mssql dialect.
    url = os.environ.get("KRISNNAI_ALEMBIC_URL") or "mssql+pyodbc://"
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(_url())
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
