"""Operations: one row per daily or backfill run (the watermark), and the member id -> master patient id crosswalk."""

from __future__ import annotations

from sqlalchemy import Date, DateTime, Integer, LargeBinary, String, Text

from krisnai.model.base import Base, FromFile, Mapped, Scoped, col, date, datetime, scoped


class OpsRun(Scoped, Base):
    """One run of `krisnai ops daily` or `ops backfill`. The latest `ok` row is where the next run's sweeps start."""

    __tablename__ = "ops_run"
    __table_args__ = scoped(
        checks=[
            ("mode", "mode IN ('daily', 'backfill')"),
            ("gate", "gate IN ('passed', 'failed', 'skipped')"),
            ("status", "status IN ('ok', 'gated', 'failed')"),
        ],
        from_file=False,
    )

    mode: Mapped[str] = col(String(10), "ops run: daily or backfill")
    as_of: Mapped[date] = col(Date, "ops run: the date every agent was advanced to")
    go_live: Mapped[date | None] = col(Date, "ops run: backfill go-live date; cards raised on or after it are 'new'")
    started_at: Mapped[datetime] = col(DateTime, "ops run: when it started (UTC)")
    finished_at: Mapped[datetime | None] = col(DateTime, "ops run: when it finished (UTC); null while running")
    files_loaded: Mapped[int] = col(Integer, "ops run: inbox files loaded")
    files_skipped: Mapped[int] = col(Integer, "ops run: inbox files already loaded or carrying nothing new")
    files_failed: Mapped[int] = col(Integer, "ops run: inbox files that did not parse (moved to rejected)")
    events_added: Mapped[int] = col(Integer, "ops run: events added by the load and the sweeps")
    gate: Mapped[str] = col(String(10), "ops run: load gate result: passed, failed or skipped")
    status: Mapped[str] = col(String(10), "ops run: ok, gated (stopped at the gate) or failed")
    detail: Mapped[str] = col(Text, "ops run: JSON of per-step results and the summary")


class PatientCrosswalk(Scoped, FromFile, Base):
    """A member id that maps to a master patient id, both salted-hashed. Applied when a patient reference is created."""

    __tablename__ = "patient_crosswalk"
    __table_args__ = scoped(unique=[("member_hash",)])

    member_hash: Mapped[bytes] = col(LargeBinary(32), "crosswalk CSV member_id, salted SHA-256")
    master_hash: Mapped[bytes] = col(LargeBinary(32), "crosswalk CSV master_id, salted SHA-256")
