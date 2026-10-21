# ruff: noqa: E501
"""The clearinghouse's picture of the live stream: eligibility and claim intake answered from a PayerSim.

It subclasses the existing MockWorld so the same mock clearinghouse service serves it. It makes technical
checks only (envelope, claim id, payer id, diagnosis, charge, NPI): a claim that fails them is REJECTED here
and never reaches the payer, which is a different thing from a payer DENIAL later.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from krisnai.ingest.x12 import X12Error, read_transactions
from krisnai.integrations.clearinghouse.claim_store import PmExtract, StoredClaim, StoredLine
from krisnai.integrations.clearinghouse.mock_world import EligibilityAnswer, MockWorld
from krisnai.live.payer import PayerSim
from krisnai.synthea import x12out
from krisnai.synthea.types import SimClaim
from krisnai.synthea.x12out import _envelope, _seg


class LiveWorld(MockWorld):
    def __init__(self, payer: PayerSim, today: date):
        super().__init__(PmExtract(), None, today)
        self.payer = payer
        self.accepted: list[SimClaim] = []  # claims past the technical checks, waiting for the payer
        self.rejected: dict[str, str] = {}
        self.today = today

    def advance(self, day: date) -> None:
        """Move the simulation clock; status requests and the portal show what the payer would show on this day."""
        self.today = day

    def _store(self, c: SimClaim) -> None:
        p = c.patient
        self.extract.claims[c.claim_id] = StoredClaim(
            c.claim_id, c.payer.payer_id, c.payer.name, p.ref, p.last, p.first, p.dob.strftime("%Y%m%d"), p.sex, c.billed,
            c.dos, list(c.dx), c.provider_npi, [StoredLine(ln.cpt, ln.billed, str(ln.units)) for ln in c.lines])

    def claim_state(self, claim_id: str):  # noqa: ANN201
        """(category, code, paid, payer claim number, claim) as of the world's clock, from the payer's own state."""
        claim = self.extract.claims.get(claim_id)
        if claim is None:
            return "E1", "164", Decimal(0), "", None
        if claim_id in self.rejected:
            return "A3", "21", Decimal(0), "", claim
        cat, code, paid, no, _, _ = self.payer.status(claim_id, self.today)
        return cat, code, paid, no, claim

    def portal_reason(self, claim_id: str, category: str) -> tuple[str, bool] | None:
        """The reason line and whether a records request is open, for the mock portal."""
        if claim_id in self.rejected:
            return f"Returned: {self.rejected[claim_id]}", False
        if claim_id in self.payer.cases:
            _, _, _, _, reason, records = self.payer.status(claim_id, self.today)
            return reason, records
        return None

    def eligibility(self, payer_id: str, member_id: str, dos: date) -> EligibilityAnswer:
        found, active = self.payer.eligibility(member_id)
        if not found:
            return EligibilityAnswer(found=False)
        return EligibilityAnswer(True, active, plan_end=None if active else dos - timedelta(days=30))

    def _technical_check(self, claim: SimClaim, raw_payer_id: str, charge: Decimal) -> str:
        if not claim.claim_id:
            return "claim id (CLM01) is empty"
        if not raw_payer_id:
            return "payer id is empty (NM1*PR)"
        if charge <= 0:
            return "total charge is not positive"
        if not claim.dx:
            return "no diagnosis on the claim"
        if len(claim.provider_npi) != 10:
            return "billing provider NPI is not 10 digits"
        return ""

    def accept_claims(self, text: str, when: date) -> tuple[str, str, list[dict]]:
        """(999, 277CA, per-claim results) for an inbound 837. Anything well-formed is accepted for the payer."""
        try:
            txs = read_transactions(text)
        except X12Error:
            raise
        gs06 = txs[0].gs06 if txs else ""
        st02 = txs[0].st02 if txs else ""
        payer_ids = {}
        for tx in txs:
            for seg in tx.segments:
                if seg.id == "NM1" and seg[1] == "PR":
                    payer_ids = {"id": seg[9]}
        results: list[dict] = []
        sims = self.payer.to_sim_claims(text, when)
        for c in sims:
            self._store(c)
            why = self._technical_check(c, payer_ids.get("id", ""), c.billed)
            if why:
                c.scenario = "rejection"
                self.rejected[c.claim_id] = why
                results.append({"claim": c.claim_id, "ok": False, "reason": why})
            else:
                self.accepted.append(c)
                results.append({"claim": c.claim_id, "ok": True, "reason": "accepted for the payer"})
        ok = bool(results) and all(r["ok"] for r in results)
        c999 = self.next_ctrl()
        ack = _envelope(
            "FA", "005010X231A1", "999", "005010X231A1",
            [_seg("AK1", "HC", gs06, "005010X222A1"), _seg("AK2", "837", st02, "005010X222A1"),
             _seg("IK5", "A" if ok else "R"), _seg("AK9", "A" if ok else "R", 1, 1, 1 if ok else 0)],
            c999, "SYNCH", x12out.SENDER, when,
        )  # fmt: skip
        c277 = x12out.write_277ca(sims[0].payer, sims, self.next_ctrl(), when) if sims else ""
        return ack, c277, results

    def release(self, claim_id: str) -> None:
        """S8: a corrected claim for this id passed the technical checks, so it is no longer shown as rejected (idempotent)."""
        self.rejected.pop(claim_id, None)
