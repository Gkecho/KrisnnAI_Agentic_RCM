"""The mock clearinghouse's picture of the world: what the payers would answer, from the practice's own extract.

Deterministic. Eligibility answers follow the appointment answer key (coverage ended, other primary payer, otherwise
active at 10% coinsurance); claim status follows what the 277CA and 835 files already say; a replacement 837 is accepted
when it points at a claim that was rejected. It is a stand-in for the protocol and for payer behaviour on this book,
not a model of any real payer.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from krisnnai.integrations.clearinghouse.claim_store import PmExtract, StoredClaim
from krisnnai.ingest.x12 import X12Error, read_transactions, x12_date
from krisnnai.synthea.x12out import SENDER, _amt, _envelope, _seg

PLAN_COINSURANCE = "0.10"


@dataclass
class EligibilityAnswer:
    found: bool
    active: bool = True
    plan_end: date | None = None
    other_payer: str = ""
    copay: Decimal | None = None  # the visit copayment the plan reports (EB*B); None = the payer gives none


class MockWorld:
    def __init__(self, extract: PmExtract, truth_dir: Path | None = None, today: date | None = None):
        self.extract = extract
        self.today = today or date.today()
        self.appt_defect: dict[str, str] = {}
        if truth_dir is not None and (truth_dir / "elig_truth.csv").exists():
            with (truth_dir / "elig_truth.csv").open(encoding="utf-8") as f:
                for r in csv.DictReader(f):
                    self.appt_defect[r["appointment_id"]] = r["defect"]
        self.received_corrected: dict[str, int] = {}  # claim id -> number of replacement claims accepted
        self._ctrl = 700000

    def next_ctrl(self) -> int:
        self._ctrl += 1
        return self._ctrl

    # ------------------------------------------------------------------------------ eligibility
    def eligibility(self, payer_id: str, member_id: str, dos: date, dependent: dict | None = None) -> EligibilityAnswer:
        appt = self.extract.find_appointment(payer_id, member_id, dos)
        if appt is None:
            return EligibilityAnswer(found=False)
        defect = self.appt_defect.get(appt["appointment_id"], "")
        if defect == "coverage_inactive":
            return EligibilityAnswer(True, False, plan_end=dos - timedelta(days=30))
        if defect == "cob_other_payer":
            return EligibilityAnswer(True, True, other_payer="OTHER PRIMARY PAYER")
        return EligibilityAnswer(True, True)

    def write_271(self, payer_id: str, payer_name: str, member_id: str, last: str, first: str, dos: date,
                  ref: str, ans: EligibilityAnswer, when: date, dependent: dict | None = None) -> str:  # fmt: skip
        ctrl = self.next_ctrl()
        if dependent is not None:  # the answer is about the dependent (HL 23) under the subscriber
            return self._write_271_dependent(
                payer_id, payer_name, member_id, last, first, dos, ref, ans, when, ctrl, dependent
            )
        body = [
            _seg("BHT", "0022", "11", f"SYN271R{ctrl}", when.strftime("%Y%m%d"), "1200"),
            _seg("HL", 1, "", "20", 1),
            _seg("NM1", "PR", "2", payer_name, "", "", "", "", "PI", payer_id),
            _seg("HL", 2, 1, "21", 1),
            _seg("NM1", "1P", "2", "SYNTHETIC CLINIC", "", "", "", "", "XX", "1888888800"),
            _seg("HL", 3, 2, "22", 0),
            _seg("TRN", "2", ref, SENDER),
            _seg("NM1", "IL", "1", last, first, "", "", "", "MI", member_id),
        ]
        body += self._coverage(dos, ans)
        return _envelope("HB", "005010X279A1", "271", "005010X279A1", body, ctrl, payer_id, SENDER, when)

    @staticmethod
    def _coverage(dos: date, ans: EligibilityAnswer) -> list[str]:
        """The date and benefit lines of a 271 answer (plan dates, active or not, other payer, copay, coinsurance, deductible)."""
        body = [
            _seg("DTP", "291", "D8", dos.strftime("%Y%m%d")),
            _seg("DTP", "346", "D8", (dos - timedelta(days=365)).strftime("%Y%m%d")),
        ]
        if ans.plan_end is not None:
            body.append(_seg("DTP", "347", "D8", ans.plan_end.strftime("%Y%m%d")))
        body.append(_seg("EB", "1" if ans.active else "6", "IND", "30"))
        if ans.other_payer:
            body += [_seg("EB", "R", "IND", "30"),
                     _seg("NM1", "PR", "2", ans.other_payer, "", "", "", "", "PI", "OTHERPAY")]  # fmt: skip
        if ans.active and ans.copay is not None:
            body.append(_seg("EB", "B", "IND", "98", "", "", "", _amt(ans.copay)))
        if ans.active:
            body.append(_seg("EB", "A", "IND", "98", "", "", "", "", PLAN_COINSURANCE))
            body.append(_seg("EB", "C", "IND", "30", "", "", "29", _amt(Decimal(0))))
        return body

    def _write_271_dependent(self, payer_id: str, payer_name: str, member_id: str, last: str, first: str, dos: date,
                             ref: str, ans: EligibilityAnswer, when: date, ctrl: int, dep: dict) -> str:  # fmt: skip
        """271 for a dependent: the subscriber is named (HL 22), the coverage lines sit under the dependent (HL 23, NM1*03)."""
        body = [
            _seg("BHT", "0022", "11", f"SYN271R{ctrl}", when.strftime("%Y%m%d"), "1200"),
            _seg("HL", 1, "", "20", 1),
            _seg("NM1", "PR", "2", payer_name, "", "", "", "", "PI", payer_id),
            _seg("HL", 2, 1, "21", 1),
            _seg("NM1", "1P", "2", "SYNTHETIC CLINIC", "", "", "", "", "XX", "1888888800"),
            _seg("HL", 3, 2, "22", 1),
            _seg("NM1", "IL", "1", last, first, "", "", "", "MI", member_id),
            _seg("HL", 4, 3, "23", 0),
            _seg("TRN", "2", ref, SENDER),
            _seg("NM1", "03", "1", dep["last"], dep["first"]),
            _seg("DMG", "D8", dep["dob"] or "19700101"),
            _seg("INS", "N", dep["relation"]),
            *self._coverage(dos, ans),
        ]
        return _envelope("HB", "005010X279A1", "271", "005010X279A1", body, ctrl, payer_id, SENDER, when)

    def write_271_not_found(self, payer_id: str, payer_name: str, member_id: str, ref: str, when: date) -> str:
        """A subscriber the payer cannot find: AAA*Y**75 on the subscriber loop (no coverage line)."""
        ctrl = self.next_ctrl()
        body = [
            _seg("BHT", "0022", "11", f"SYN271R{ctrl}", when.strftime("%Y%m%d"), "1200"),
            _seg("HL", 1, "", "20", 1),
            _seg("NM1", "PR", "2", payer_name, "", "", "", "", "PI", payer_id),
            _seg("HL", 2, 1, "22", 0),
            _seg("TRN", "2", ref, SENDER),
            _seg("NM1", "IL", "1", "", "", "", "", "", "MI", member_id),
            _seg("AAA", "Y", "", "75", "C"),
        ]
        return _envelope("HB", "005010X279A1", "271", "005010X279A1", body, ctrl, payer_id, SENDER, when)

    # ---------------------------------------------------------------------------------- status
    def claim_state(self, claim_id: str) -> tuple[str, str, Decimal, str, StoredClaim | None]:
        """(category, code, paid, payer claim number, claim). Unknown claims answer E1 (not found)."""
        claim = self.extract.claims.get(claim_id)
        if claim is None:
            return "E1", "164", Decimal(0), "", None
        corrected = self.received_corrected.get(claim_id, 0) > 0
        ans = self.extract.answers.get(claim_id)
        if corrected:
            return "A2", "20", Decimal(0), ans.payer_claim_no if ans else "", claim  # accepted, in adjudication
        if ans is None:
            return "P1", "21", Decimal(0), "", claim  # received, no answer yet
        if ans.state == "rejected":
            return "A3", ans.status_code or "21", Decimal(0), ans.payer_claim_no, claim
        if ans.state == "denied":
            return "F2", "3", Decimal(0), ans.payer_claim_no, claim
        return "F1", "65" if ans.paid > 0 else "3", ans.paid, ans.payer_claim_no, claim

    # ------------------------------------------------------------------------- replacement 837
    def accept_claims(self, text: str, when: date) -> tuple[str, str, list[dict]]:
        """(999, 277CA, per-claim results) for an inbound 837. Accepts a replacement (CLM05-3 = 7) of a claim the payer
        returned; everything else is rejected with a reason, so the bot's behaviour is visible in the answers."""
        results: list[dict] = []
        gs06 = st02 = ""
        for tx in read_transactions(text):
            if tx.st01 != "837":
                raise X12Error(f"expected an 837, got {tx.st01}")
            gs06, st02 = tx.gs06, tx.st02
            for seg in tx.segments:
                if seg.id != "CLM":
                    continue
                claim_id, freq = seg[1], seg.comp(5, 3)
                known = self.extract.claims.get(claim_id)
                ans = self.extract.answers.get(claim_id)
                if known is None:
                    results.append({"claim": claim_id, "ok": False, "reason": "claim not on file"})
                elif freq != "7":
                    results.append({"claim": claim_id, "ok": False, "reason": "not a replacement claim (CLM05-3 must be 7)"})
                elif ans is None or ans.state != "rejected":
                    results.append({"claim": claim_id, "ok": False, "reason": "original claim was not returned"})
                else:
                    self.received_corrected[claim_id] = self.received_corrected.get(claim_id, 0) + 1
                    results.append({"claim": claim_id, "ok": True, "reason": "replacement accepted"})
        ok = all(r["ok"] for r in results) and bool(results)
        c999 = self.next_ctrl()
        ack = _envelope(
            "FA", "005010X231A1", "999", "005010X231A1",
            [_seg("AK1", "HC", gs06, "005010X222A1"), _seg("AK2", "837", st02, "005010X222A1"),
             _seg("IK5", "A" if ok else "R"), _seg("AK9", "A" if ok else "R", 1, 1, 1 if ok else 0)],
            c999, "SYNCH", SENDER, when,
        )  # fmt: skip
        body = [
            _seg("BHT", "0085", "08", f"SYN277R{c999}", when.strftime("%Y%m%d"), "1200", "TH"),
            _seg("HL", 1, "", "20", 1),
            _seg("NM1", "PR", "2", "MOCK PAYER", "", "", "", "", "PI", "MOCK"),
            _seg("HL", 2, 1, "21", 1),
            _seg("NM1", "41", "2", "SYNTHETIC CLINIC", "", "", "", "", "46", SENDER),
            _seg("HL", 3, 2, "19", 1),
            _seg("NM1", "85", "2", "SYNTHETIC CLINIC", "", "", "", "", "XX", "1888888800"),
        ]
        hl = 4
        for r in results:
            claim = self.extract.claims.get(r["claim"])
            body += [
                _seg("HL", hl, 3, "22", 0),
                _seg("NM1", "IL", "1", "", "", "", "", "", "MI", claim.member_id if claim else ""),
                _seg("TRN", "2", r["claim"]),
                _seg("STC", "A2:20:PR" if r["ok"] else "A3:21:PR", when.strftime("%Y%m%d"), "WQ",
                     _amt(claim.billed) if claim else "0"),
            ]
            hl += 1
        ca = _envelope("HN", "005010X214", "277", "005010X214", body, c999 + 1, "SYNCH", SENDER, when)
        return ack, ca, results


def parse_inbound_270(text: str) -> list[dict]:
    """The fields the mock needs from a 270: payer, member, names, date of service, trace."""
    out = []
    for tx in read_transactions(text):
        if tx.st01 != "270":
            raise X12Error(f"expected a 270, got {tx.st01}")
        payer_id = payer_name = ""
        cur = None
        in_dep = False
        for seg in tx.segments:
            if seg.id == "NM1" and seg[1] == "PR":
                payer_name, payer_id = seg[3], seg[9]
            elif seg.id == "NM1" and seg[1] == "IL":
                cur = {"payer_id": payer_id, "payer_name": payer_name, "member": seg[9], "last": seg[3],
                       "first": seg[4], "dos": None, "ref": "", "dependent": None}  # fmt: skip
                out.append(cur)
            elif seg.id == "NM1" and seg[1] == "03" and cur is not None:
                cur["dependent"] = {"last": seg[3], "first": seg[4], "dob": "", "relation": ""}
                in_dep = True
            elif seg.id == "DMG" and in_dep and cur is not None:
                cur["dependent"]["dob"] = seg[2]
            elif seg.id == "INS" and in_dep and cur is not None:
                cur["dependent"]["relation"] = seg[2]
            elif seg.id == "TRN" and seg[1] == "1" and cur is None:
                pass
            elif seg.id == "DTP" and seg[1] == "291" and cur is not None:
                cur["dos"] = x12_date(seg[3], "270 DTP*291")
        refs = [s[2] for s in tx.segments if s.id == "TRN" and s[1] == "1"]
        for rec, ref in zip(out, refs):
            rec["ref"] = ref
    if not out:
        raise X12Error("270 has no subscriber")
    return out


def parse_inbound_276(text: str) -> list[dict]:
    out = []
    for tx in read_transactions(text):
        if tx.st01 != "276":
            raise X12Error(f"expected a 276, got {tx.st01}")
        payer_id = ""
        cur = None
        for seg in tx.segments:
            if seg.id == "NM1" and seg[1] == "PR":
                payer_id = seg[9]
            elif seg.id == "NM1" and seg[1] == "IL":
                cur = {"payer_id": payer_id, "member": seg[9], "claim": "", "payer_claim_no": ""}
                out.append(cur)
            elif seg.id == "TRN" and seg[1] == "1" and cur is not None:
                cur["claim"] = seg[2]
            elif seg.id == "REF" and seg[1] == "1K" and cur is not None:
                cur["payer_claim_no"] = seg[2]
    if not out:
        raise X12Error("276 has no subscriber")
    return out
