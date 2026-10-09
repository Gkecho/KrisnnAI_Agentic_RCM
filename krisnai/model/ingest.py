"""Tenant, source files and the append-only event log."""

from __future__ import annotations

from sqlalchemy import CHAR, BigInteger, DateTime, Integer, String, Text

from krisnai.model.base import (
    PK,
    Base,
    FromFile,
    Mapped,
    Scoped,
    UtcNow,
    col,
    datetime,
    mapped_column,
    scoped,
)  # fmt: skip


class Tenant(Base):
    """A client practice. Root of tenant isolation."""

    __tablename__ = "tenant"

    tenant_id: Mapped[int] = mapped_column(PK, primary_key=True, autoincrement=True)
    name: Mapped[str] = col(String(200), "client-provided practice name")
    patient_salt_key: Mapped[str] = col(
        String(100), "name of the env/secret-store key holding this tenant's patient-hash salt"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=UtcNow())


class SourceFile(Scoped, Base):
    """One ingested file. UNIQUE (tenant, sha256) makes re-ingesting the same file a no-op."""

    __tablename__ = "source_file"
    __table_args__ = scoped(unique=[("file_sha256",)], from_file=False)

    file_name: Mapped[str] = col(String(500), "file name as received (no PHI in names)")
    file_sha256: Mapped[str] = col(CHAR(64), "SHA-256 of the file bytes")
    file_type: Mapped[str] = col(String(20), "837P | 835 | 999 | 277CA | fee_schedule | visits | ar_snapshot")
    byte_size: Mapped[int] = col(BigInteger, "file size in bytes")
    status: Mapped[str] = col(String(20), "loaded | failed")
    failure_reason: Mapped[str | None] = col(String(1000), "parser error text when status = failed")


class Event(Scoped, FromFile, Base):
    """Append-only raw event: one per claim / remit / acknowledgement / row. Never updated.

    Normalized tables are rebuilt from events. A trigger on SQL Server rejects UPDATE/DELETE.
    """

    __tablename__ = "event"
    __table_args__ = scoped(unique=[("source_file_id", "isa13", "gs06", "st02", "seq_in_file")])

    event_type: Mapped[str] = col(String(40), "837P.claim | 835.remit | 999.ack | 277CA.claim_status | ...")
    isa13: Mapped[str] = col(String(9), "ISA13 interchange control number")
    gs06: Mapped[str] = col(String(9), "GS06 group control number")
    st02: Mapped[str] = col(String(9), "ST02 transaction set control number")
    seq_in_file: Mapped[int] = col(Integer, "position of this event within its transaction set")
    known_at: Mapped[datetime] = col(DateTime, "when the data became known (point-in-time key)")
    payload: Mapped[str] = col(Text, "the parsed record as JSON; patient identifiers are already hashed, so no PHI")
