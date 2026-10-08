"""Declarative base, column helpers and the tenant-scoping mixin for the core data model.

Conventions (see docs/adr/0001-event-sourcing-and-tenant-keys.md):
- Every table except `tenant` carries `tenant_id`; every table except `tenant` and `source_file`
  also carries `source_file_id` and `loaded_at`.
- Every table has a surrogate `id` plus UNIQUE (tenant_id, id) so children can reference their
  parent with a composite (tenant_id, parent_id) foreign key. A child can therefore never point
  at another tenant's parent row.
- Money is DECIMAL(18,2), units DECIMAL(9,2), dates are DATE. No floats, no date strings.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    MetaData,
    Numeric,
    Text,
    UniqueConstraint,
)
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql.expression import FunctionElement

NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

PK = BigInteger().with_variant(Integer, "sqlite")  # SQLite only autoincrements INTEGER keys
Money = Numeric(18, 2)
Units = Numeric(9, 2)

__all__ = [
    "Base", "Scoped", "UtcNow", "col", "fk", "scoped", "date", "datetime", "Decimal", "Money", "Units", "PK",
    "Mapped", "mapped_column", "BigInteger", "CheckConstraint",
]  # fmt: skip


@compiles(Date, "mssql")
def _mssql_date(_type, _compiler, **_kw) -> str:
    return "DATE"  # an offline dialect (no server version) would otherwise fall back to DATETIME


@compiles(DateTime, "mssql")
def _mssql_datetime(_type, _compiler, **_kw) -> str:
    return "DATETIME2(0)"


@compiles(Text, "mssql")
def _mssql_text(_type, _compiler, **_kw) -> str:
    return "NVARCHAR(MAX)"  # TEXT is deprecated on SQL Server


class UtcNow(FunctionElement):
    """Server-side UTC timestamp default."""

    type = DateTime()
    inherit_cache = True


@compiles(UtcNow)
def _utcnow_default(_element, _compiler, **_kw) -> str:
    return "CURRENT_TIMESTAMP"  # SQLite / generic: already UTC


@compiles(UtcNow, "mssql")
def _utcnow_mssql(_element, _compiler, **_kw) -> str:
    return "SYSUTCDATETIME()"


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def col(type_, src: str, **kwargs):
    """mapped_column that records where the value comes from (X12 element or derivation).

    The `src` text feeds docs/data_model.md, so every business column must have one.
    """
    return mapped_column(type_, info={"src": src}, **kwargs)


def fk(src: str, **kwargs):
    """BigInteger reference column; the composite (tenant_id, column) FK comes from `scoped`."""
    return mapped_column(BigInteger, info={"src": src}, **kwargs)


class Scoped:
    """Mixin: tenant + lineage columns shared by every tenant table except `source_file`."""

    id: Mapped[int] = mapped_column(PK, primary_key=True, autoincrement=True, sort_order=-3)
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tenant.tenant_id"), sort_order=-2
    )
    loaded_at: Mapped[datetime] = mapped_column(DateTime, server_default=UtcNow(), sort_order=100)


class FromFile:
    """Mixin: the file a row was loaded from (composite FK added by `scoped`)."""

    source_file_id: Mapped[int] = mapped_column(BigInteger, sort_order=-1)


def scoped(
    refs: Sequence[tuple[str, str]] = (),
    unique: Sequence[Sequence[str]] = (),
    checks: Sequence[tuple[str, str]] = (),
    *,
    from_file: bool = True,
) -> tuple:
    """Build __table_args__: tenant-composite FKs, UNIQUE(tenant_id, id) and extra constraints.

    refs:   (column, parent_table) pairs; each becomes FK (tenant_id, column) -> parent(tenant_id, id)
    unique: column tuples; each becomes UNIQUE (tenant_id, *columns)
    checks: (name, sql) CHECK constraints
    """
    args: list = [UniqueConstraint("tenant_id", "id")]
    if from_file:
        args.append(
            ForeignKeyConstraint(
                ["tenant_id", "source_file_id"], ["source_file.tenant_id", "source_file.id"]
            )
        )
    for column, parent in refs:
        args.append(
            ForeignKeyConstraint(["tenant_id", column], [f"{parent}.tenant_id", f"{parent}.id"])
        )
    for columns in unique:
        args.append(UniqueConstraint("tenant_id", *columns))
    for name, sql in checks:
        args.append(CheckConstraint(sql, name=name))
    return tuple(args)
