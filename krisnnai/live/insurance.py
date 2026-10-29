# ruff: noqa: E501
"""Read a patient's insurance records from the EMR (read-only) and put them in coverage order.

OpenEMR keeps one row per policy: type (primary, secondary, tertiary), policy number (the member id), group, the policyholder, the
dates it applies and the copay. Its FHIR Coverage resource leaves out the member id and the dates, so the policy comes from the
REST insurance record and only the payer's name and payer id come from FHIR (Coverage id = policy uuid -> payor Organization).

Reading only: nothing here writes to the EMR. Demo data is synthetic.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

ORDER = {"primary": 1, "secondary": 2, "tertiary": 3}
LABEL = {1: "primary", 2: "secondary", 3: "tertiary"}


@dataclass(frozen=True)
class Policy:
    order: int  # 1 primary, 2 secondary, 3 tertiary
    member: str  # policy number: the member id the payer knows
    payer_code: str  # the id the clearinghouse routes on (NM1*PR in the 270)
    payer_name: str
    plan: str
    group: str
    relationship: str  # self, spouse, child, other
    holder_last: str
    holder_first: str
    holder_dob: str  # YYYY-MM-DD
    begin: date | None
    end: date | None
    copay: Decimal | None

    @property
    def label(self) -> str:
        return LABEL.get(self.order, str(self.order))

    def covers(self, day: date) -> bool:
        return (self.begin is None or self.begin <= day) and (self.end is None or day <= self.end)


def _day(text: str | None) -> date | None:
    try:
        return date.fromisoformat(str(text)[:10]) if text and not str(text).startswith("0000") else None
    except ValueError:
        return None


def _money(text: str | None) -> Decimal | None:
    try:
        return Decimal(str(text)).quantize(Decimal("0.01")) if str(text or "").strip() else None
    except InvalidOperation:
        return None


class InsuranceReader:
    """`policies(patient_uuid, visit)` -> the policies in force on the visit date, primary first. Payer names are cached."""

    def __init__(self, server):  # noqa: ANN001
        self.server = server
        self._orgs: dict[str, tuple[str, str]] | None = None

    def _payers(self) -> dict[str, tuple[str, str]]:
        """Organization id -> (name, payer code), from FHIR."""
        if self._orgs is None:
            self._orgs = {}
            for o in self.server.fhir.search("Organization", page_size=None):
                ident = (o.get("identifier") or [{}])[0].get("value", "")
                self._orgs[o["id"]] = (o.get("name", ""), ident)
        return self._orgs

    def _coverage_org(self, patient_uuid: str) -> dict[str, str]:
        """Policy uuid -> payor Organization id (the Coverage resource has the same id as the policy)."""
        out = {}
        for c in self.server.fhir.search("Coverage", params={"patient": patient_uuid}, page_size=None):
            ref = ((c.get("payor") or [{}])[0].get("reference") or "").split("/")[-1]
            out[c["id"]] = ref
        return out

    def all_policies(self, patient_uuid: str) -> list[Policy]:
        rows = self.server.rest_rows(f"/patient/{patient_uuid}/insurance")
        if not rows:
            return []
        link = self._coverage_org(patient_uuid)
        orgs = self._payers()
        out = []
        for r in rows:
            name, code = orgs.get(link.get(r.get("uuid", ""), ""), ("", ""))
            out.append(
                Policy(
                    order=ORDER.get(str(r.get("type", "")).lower(), 9), member=str(r.get("policy_number") or "").strip(),
                    payer_code=code, payer_name=name, plan=r.get("plan_name") or "", group=r.get("group_number") or "",
                    relationship=r.get("subscriber_relationship") or "self", holder_last=r.get("subscriber_lname") or "",
                    holder_first=r.get("subscriber_fname") or "", holder_dob=str(r.get("subscriber_DOB") or ""),
                    begin=_day(r.get("date")), end=_day(r.get("date_end")), copay=_money(r.get("copay")),
                )
            )  # fmt: skip
        return out

    def policies(self, patient_uuid: str, visit: date) -> list[Policy]:
        """In force on the visit date; if the EMR holds two of one type (an old and a new), the one that began last wins."""
        best: dict[int, Policy] = {}
        for p in self.all_policies(patient_uuid):
            if not p.covers(visit):
                continue
            if p.order not in best or (p.begin or date.min) > (best[p.order].begin or date.min):
                best[p.order] = p
        return [best[k] for k in sorted(best)]
