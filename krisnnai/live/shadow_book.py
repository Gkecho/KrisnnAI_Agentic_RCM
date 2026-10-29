# ruff: noqa: E501
"""Shadow book: runs the real A1 Gatekeeper agent (with its decision record) on what the trigger just found.

The trigger already applies A1's rules. This adds the rest of the agent: the same appointment and the same 271 are loaded through
the normal ingest into a small local SQLite database under the work folder, a clearance event is raised for the check, and the
agent runs through the engine pipeline. The engine writes one decision record per event (rules fired, input snapshot, proposed
action, autonomy level, mode). Nothing is sent anywhere: the policy default is L0/shadow, and this database is our own file.

Only the primary policy is given to the agent (it reads one payer per appointment). The trigger's own result covers the others.
Raw member IDs are hashed by the ingest; the temporary CSV is deleted after loading. Demo data is synthetic.
"""

from __future__ import annotations

import json
import tempfile
from datetime import date, datetime, time
from hashlib import sha256
from pathlib import Path

from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session

import krisnnai.model as m
from krisnnai.agents.a1_clearance import A1ClearanceAgent
from krisnnai.agents.a1_clearance.sweep import EVENT_TYPE
from krisnnai.engine import run
from krisnnai.ingest.loader import ingest_file
from krisnnai.model import tenant_session

TENANT = 1
SALT = "krisnnai-shadow-book-demo"  # demo salt for synthetic members only
CLINIC_NPI = "1999999991"  # the demo clinic


class ShadowBook:
    def __init__(self, work: Path):
        self.dir = work / "shadow"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(f"sqlite:///{self.dir / 'book.sqlite'}")

        @event.listens_for(self.engine, "connect")
        def _fk(conn, _):  # noqa: ANN001
            conn.execute("PRAGMA foreign_keys=ON")

        m.Base.metadata.create_all(self.engine)
        with Session(self.engine) as s:
            if s.get(m.Tenant, TENANT) is None:
                s.add(m.Tenant(name="demo practice", patient_salt_key="SHADOW_SALT"))
                s.commit()

    def _has_appointment(self, ref: str) -> bool:
        with tenant_session(self.engine, TENANT) as s:
            return s.scalar(select(m.Appointment.id).where(m.Appointment.appt_ref == ref)) is not None

    def record(self, res: dict) -> dict:
        """Run A1 on one trigger result. Same event and run twice = the same record, nothing duplicated."""
        a = res["appointment"]
        if not res["checks"]:
            return {"ran": False, "why": "no insurance on file: nothing for the agent to read"}
        first = res["checks"][0]
        ref = res["event_id"]
        visit = date.fromisoformat(a["pc_eventDate"])
        as_of = date.fromisoformat(res["as_of"])
        with tempfile.TemporaryDirectory() as tmp:
            if not self._has_appointment(ref):
                csv_path = Path(tmp) / f"appointment_{sha256(ref.encode()).hexdigest()[:10]}.csv"
                csv_path.write_text(
                    "appointment_id,payer_id,provider_npi,patient_ref,appt_date,booked_on,cpt,status\n"
                    f"{ref},{first['payer']},{CLINIC_NPI},{first['member']},{visit},{min(as_of, visit)},99213,booked\n",
                    encoding="utf-8",
                )
                ingest_file(self.engine, TENANT, csv_path, SALT)
            x271 = Path(tmp) / "271.x12"
            x271.write_text(first["x12_271"], encoding="utf-8")
            ingest_file(self.engine, TENANT, x271, SALT)
        digest = sha256(f"a1trigger|{ref}|{res['kind']}|{as_of}".encode()).hexdigest()
        with tenant_session(self.engine, TENANT) as s:
            sf = s.scalar(select(m.SourceFile).where(m.SourceFile.file_sha256 == digest))
            if sf is None:
                sf = m.SourceFile(
                    file_name=f"a1trigger_{res['kind']}",
                    file_sha256=digest,
                    file_type="sweep",
                    byte_size=0,
                    status="loaded",
                )
                s.add(sf)
                s.flush()
                payload = {"appt": ref, "checkpoint_days": (visit - as_of).days, "due_on": as_of.isoformat()}
                s.add(
                    m.Event(
                        source_file_id=sf.id, event_type=EVENT_TYPE, isa13=as_of.strftime("%Y%m%d"), gs06=digest[:8],
                        st02="1", seq_in_file=1, known_at=datetime.combine(as_of, time.min),
                        payload=json.dumps(payload, sort_keys=True),
                    )
                )  # fmt: skip
                s.commit()
            ev_id = s.scalar(select(m.Event.id).where(m.Event.source_file_id == sf.id))
        out = run(self.engine, TENANT, A1ClearanceAgent(), ev_id)
        with tenant_session(self.engine, TENANT) as s:
            rec = s.get(m.DecisionRecord, out.record_id)
            return {
                "ran": True, "record_id": rec.id, "created": out.created, "outcome": rec.outcome, "action": rec.action_type,
                "level": f"L{rec.autonomy_level}", "mode": rec.mode, "confidence": str(rec.confidence) if rec.confidence is not None else None,
                "rules": [f"{r['rule']}={'ok' if r['result'] else 'FAILED'}" for r in json.loads(rec.rules_fired)],
                "patient_estimate": json.loads(rec.action_payload).get("patient_estimate"),
            }  # fmt: skip
