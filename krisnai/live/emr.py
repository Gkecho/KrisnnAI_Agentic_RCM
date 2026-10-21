# ruff: noqa: E501
"""The EMR side of the live stream, behind one small interface so the orchestrator can be tested without Docker.

`OpenEmrPort` talks to the local demo OpenEMR (REST for writes, FHIR for the existence checks, the PHP billing helper for the
charge and the 837P). Every `ensure_*` method looks for the record before creating it, so re-running a step after a crash
never makes a duplicate. `FakeEmr` keeps the same promises in memory and writes its 837 with the repo's own X12 writer.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Protocol

from krisnai.integrations.openemr import billing, seed
from krisnai.integrations.openemr.billing import Charge
from krisnai.synthea import x12out
from krisnai.synthea.types import PayerInfo, Person, SimClaim, SimLine

PROVIDER_NPI = "1234567893"  # the demo provider OpenEMR's billing helper sets up


class EmrPort(Protocol):
    def ensure_patient(self, member: str) -> tuple[int, str]: ...

    def ensure_appointment(self, pid: int, appt_id: str, day: date, cpt: str, payer: str, booked: date) -> None: ...

    def ensure_visit(self, pid: int, puuid: str, visit_id: str, day: date, payer: str, cpt: str, note: str, transcript: str) -> int: ...

    def charge_837(self, charge: Charge, approval: str, day: date) -> str: ...

    def counts(self) -> dict[str, int]: ...


class OpenEmrPort:
    def __init__(self, server: seed._Server, runner=billing._docker):  # noqa: ANN001
        self.server = server
        self.runner = runner
        self._patients: dict[str, tuple[int, str]] = {}
        self._aid: int | None = None

    # -------------------------------------------------------------------------------------------- lookups
    def _practitioner(self) -> int:
        if self._aid is None:
            rows = self.server.rest_rows("/practitioner")
            self._aid = rows[0]["id"] if rows else 1
        return self._aid

    def ensure_patient(self, member: str) -> tuple[int, str]:
        if member not in self._patients:
            for p in self.server.rest_rows("/patient"):
                if p.get("pubpid") == member:
                    self._patients[member] = (p["pid"], p["uuid"])
                    break
        if member not in self._patients:
            body = {"fname": "Synthetic", "lname": member, "pubpid": member, "street": "100 Synthetic Way", "city": "Testville",
                    "state": "TX", "postal_code": "75001", "country_code": "US", **seed._synthetic_person(member)}  # fmt: skip
            d = self.server.rest_json("POST", "/patient", json=body)["data"]
            self._patients[member] = (d["pid"], d["uuid"])
        return self._patients[member]

    def ensure_appointment(self, pid: int, appt_id: str, day: date, cpt: str, payer: str, booked: date) -> None:
        for a in self.server.rest_rows(f"/patient/{pid}/appointment"):
            if (seed.decode(a.get("pc_title")) or {}).get("appt") == appt_id:
                return
        title = seed.encode(appt=appt_id, cpt=cpt, payer=payer, booked=booked.isoformat(), status="booked")
        self.server.rest_json("POST", f"/patient/{pid}/appointment", json={
            "pc_catid": seed.OFFICE_VISIT, "pc_title": title, "pc_hometext": "Synthetic appointment", "pc_duration": "1800",
            "pc_apptstatus": "-", "pc_eventDate": day.isoformat(), "pc_startTime": "09:00", "pc_facility": seed.FACILITY_ID,
            "pc_billing_location": seed.FACILITY_ID, "pc_aid": self._practitioner(),
        })  # fmt: skip

    def ensure_visit(self, pid: int, puuid: str, visit_id: str, day: date, payer: str, cpt: str, note: str, transcript: str) -> int:
        eno = None
        for e in self.server.rest_rows(f"/patient/{puuid}/encounter"):
            if (seed.decode(e.get("reason")) or {}).get("visit") == visit_id:
                eno = int(e["eid"])
        if eno is None:
            when = f"{day} 09:00:00"
            made = self.server.rest_json("POST", f"/patient/{puuid}/encounter", json={
                "pc_catid": seed.OFFICE_VISIT, "class_code": "AMB", "sensitivity": "normal", "date": when, "onset_date": when,
                "reason": seed.encode(visit=visit_id, cpt=cpt, units="1", payer=payer), "facility_id": seed.FACILITY_ID,
                "billing_facility": seed.FACILITY_ID, "provider_id": self._practitioner(), "referral_source": "",
            })  # fmt: skip
            eno = int(made["data"]["encounter"] if "encounter" in made.get("data", {}) else made["data"]["id"])
        have = {c.get("attachment", {}).get("title") for d in self.server.fhir.search("DocumentReference", params={"patient": puuid}, page_size=None)
                for c in d.get("content", [])}  # fmt: skip
        for name, text in ((f"note_{visit_id}.txt", note), (f"transcript_{visit_id}.txt", transcript)):
            if name not in have:
                self.server.rest_json("POST", f"/patient/{pid}/document", params={"path": seed.DOC_CATEGORY},
                                      files={"document": (name, text.encode(), "text/plain")})  # fmt: skip
        return eno

    def charge_837(self, charge: Charge, approval: str, day: date) -> str:
        return billing.charge_and_837(charge, approval, runner=self.runner)["x12"]

    def counts(self) -> dict[str, int]:
        return {"patients": len(self.server.rest_rows("/patient"))}


class FakeEmr:
    """In memory, same promises: get-or-create everywhere, an 837 written by the repo's own X12 writer."""

    def __init__(self) -> None:
        self.patients: dict[str, tuple[int, str]] = {}
        self.appointments: set[str] = set()
        self.visits: dict[str, int] = {}
        self.docs: set[str] = set()
        self.charges: dict[str, str] = {}
        self.visit_day: dict[int, date] = {}
        self.calls = 0

    def ensure_patient(self, member: str) -> tuple[int, str]:
        self.calls += 1
        return self.patients.setdefault(member, (100 + len(self.patients), f"uuid-{member}"))

    def ensure_appointment(self, pid: int, appt_id: str, day: date, cpt: str, payer: str, booked: date) -> None:
        self.calls += 1
        self.appointments.add(appt_id)

    def ensure_visit(self, pid: int, puuid: str, visit_id: str, day: date, payer: str, cpt: str, note: str, transcript: str) -> int:
        self.calls += 1
        self.docs |= {f"note_{visit_id}", f"transcript_{visit_id}"}
        eno = self.visits.setdefault(visit_id, 1000 + len(self.visits))
        self.visit_day[eno] = day
        return eno

    def charge_837(self, charge: Charge, approval: str, day: date) -> str:
        self.calls += 1
        if not approval:
            raise billing.BillingError("a charge needs an approval record")
        payer = PayerInfo(charge.payer_id, charge.payer_name, Decimal("1"), 14)
        person = Person(charge.member, charge.member, "Synthetic", date(1980, 1, 1), "F")
        lines = [SimLine(c, u, Decimal(f), Decimal("0")) for c, _, u, f in charge.lines]
        dos = self.visit_day.get(charge.encounter, day)
        claim = SimClaim(f"{charge.pid}-{charge.encounter}", payer, "1234567893", person, dos, [c.replace(".", "") for c, _ in charge.dx], lines, day)
        text = x12out.write_837(payer, [claim], 1, day)
        self.charges[claim.claim_id] = text
        return text

    def counts(self) -> dict[str, int]:
        return {"patients": len(self.patients), "visits": len(self.visits), "appointments": len(self.appointments)}
