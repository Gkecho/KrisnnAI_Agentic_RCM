# ruff: noqa: E501
"""How the payer simulator answers a REPLY from our bots (S8). A stand-in written for the demo, NOT a model of any real payer.

The first decision is PayerSim's. When our side replies (a corrected claim, an appeal, an underpayment dispute, a records
submission) this module decides the answer. Like PayerSim it is seeded and replayable: the answer depends only on
(seed, claim id, round) and on what the reply says, never on the order claims arrive in.

  corrected claim   accepted and paid, or denied again. Fixing the real problem (coverage re-verified, the missing information
                    added) pays far more often than a claim that was denied for a reason a correction cannot touch.
  appeal            upheld or overturned. The chance of an overturn depends on the denial category, and jumps when the appeal
                    cites a REAL contradiction of the payer's own published rule (the payer deviated), because there the payer
                    is wrong; citing a rule that was not really contradicted helps less than not citing one.
  dispute           an underpayment dispute is accepted in full, in part, or refused. Fee-schedule evidence matters.
  records           a records submission resolves a pend (a 277CA acknowledgement; the payment date does not move).

Second remits are written with a distinct claim id `<claim>-R<round>` carrying only what that round paid, so the first remit is
never counted twice. The truth rows for replies are a SEPARATE file (`truth_replies.csv`); `truth.csv` is untouched.
"""

from __future__ import annotations

import csv
import hashlib
import io
import random
from dataclasses import asdict, dataclass
from datetime import date
from decimal import Decimal

from krisnnai.agents.a8_denial.routing import DEFAULT_ROUTES
from krisnnai.live.payer import COINSURANCE, Decision, money
from krisnnai.synthea.types import SimClaim, SimLine

REPLY_TRUTH_COLUMNS = ["claim_id", "reply_id", "round", "kind", "sent", "answer_date", "outcome", "carc", "billed", "allowed", "paid",
                       "patient_resp", "deviation_in_play", "cites_rule", "rule_really_contradicted", "p_good", "approval"]  # fmt: skip
ANSWER_DAYS = {"corrected_claim": 14, "appeal": 21, "dispute": 14, "records": 2}
CATEGORY = {carc: cat for carc, cat, *_ in DEFAULT_ROUTES}
DEVIATION_DENIALS = ("wrong_denial", "stale_version", "unpublished_rule")
APPEAL_BASE = {"authorization": 0.30, "bundling": 0.25, "medical_necessity": 0.30, "coverage": 0.25, "coding": 0.20, "missing_information": 0.35}
REAL_CONTRADICTION_P = 0.90  # a payer deviation, cited correctly


@dataclass
class ReplyClaim(SimClaim):
    """A claim carrying one round's money. It reports the ORIGINAL payer claim number (CLP07), so the engine's matcher links the second remit to the original claim."""

    pcn: str = ""

    @property
    def payer_claim_no(self) -> str:
        return self.pcn


def reply_id(claim_id: str, round_no: int) -> str:
    return f"{claim_id}-R{round_no}"


@dataclass
class ReplyAnswer:
    claim_id: str
    reply_id: str
    round: int
    kind: str  # corrected_claim | appeal | dispute | records
    outcome: str  # paid | denied | overturned | upheld | accepted_full | accepted_part | refused | pend_resolved
    carc: str
    reason: str
    p_good: float  # the chance of a good outcome the rule table gave this reply (shown in the truth file)
    billed: str
    allowed: str
    paid: str
    patient_resp: str
    answer_days: int
    deviation_in_play: str
    cites_rule: bool
    rule_really_contradicted: bool

    @property
    def paid_out(self) -> bool:
        return self.outcome in ("paid", "overturned", "accepted_full", "accepted_part")

    def to_dict(self) -> dict:
        return asdict(self)


class ReplySim:
    def __init__(self, seed: int, fees: dict[str, str]):
        self.seed, self.fees = seed, fees

    def _rng(self, claim_id: str, round_no: int) -> random.Random:
        return random.Random(int(hashlib.sha256(f"{self.seed}:reply:{claim_id}:{round_no}".encode()).hexdigest(), 16))

    def _expected_allowed(self, claim: SimClaim) -> Decimal:
        return sum((money(min(Decimal(self.fees.get(ln.cpt, str(ln.billed))) * ln.units, ln.billed)) for ln in claim.lines), Decimal(0))

    def answer(self, d: Decision, kind: str, round_no: int, *, carc: str = "", cites_rule: bool = False, fee_evidence: bool = False,
               shortfall_allowed: Decimal = Decimal(0), info_fixed: bool = True) -> ReplyAnswer:  # fmt: skip
        """The payer's answer to one reply. `d` is the payer's own first decision (it knows the truth); the reply says only what our side said."""
        claim = d.claim
        u1 = self._rng(claim.claim_id, round_no).random()
        carc = carc or d.carc
        cat = CATEGORY.get(carc, "other")
        really = d.deviation in DEVIATION_DENIALS and cites_rule
        base = dict(claim_id=claim.claim_id, reply_id=reply_id(claim.claim_id, round_no), round=round_no, kind=kind, carc=carc,
                    answer_days=ANSWER_DAYS[kind], deviation_in_play=d.deviation, cites_rule=cites_rule, rule_really_contradicted=really)  # fmt: skip
        zero = Decimal(0)

        def build(outcome: str, reason: str, p: float, billed: Decimal, allowed: Decimal, pr: Decimal) -> ReplyAnswer:
            paid = allowed - pr
            return ReplyAnswer(outcome=outcome, reason=reason, p_good=round(p, 3), billed=str(billed), allowed=str(allowed), paid=str(paid),
                               patient_resp=str(pr), **base)  # fmt: skip

        if kind == "records":
            return build("pend_resolved", "records received; the pend is closed and the claim continues to adjudication", 1.0, zero, zero, zero)
        if kind == "corrected_claim":
            if cat == "coverage":
                p = 0.90 if d.deviation == "wrong_denial" else (0.20 if carc == "27" else 0.60)
            elif cat == "missing_information":
                p = 0.85 if info_fixed else 0.10
            else:
                p = 0.60 if info_fixed else 0.10
            if u1 < p:
                allowed = self._expected_allowed(claim)
                return build("paid", "corrected claim accepted and paid per the fee schedule", p, claim.billed, allowed, money(allowed * COINSURANCE))
            return build("denied", f"corrected claim denied again (CARC {carc})", p, claim.billed, zero, zero)
        if kind == "appeal":
            base_p = APPEAL_BASE.get(cat, 0.20)
            p = REAL_CONTRADICTION_P if really else (base_p * 0.8 if cites_rule else base_p)
            if u1 < p:
                allowed = self._expected_allowed(claim)
                why = "overturned: the payer's own published rule did not support the denial" if really else "overturned on review"
                return build("overturned", why, p, claim.billed, allowed, money(allowed * COINSURANCE))
            return build("upheld", f"denial upheld (CARC {carc}) on review", p, claim.billed, zero, zero)
        # dispute
        real_underpay = d.deviation == "underpay_off_schedule"
        if real_underpay and fee_evidence:
            full, part = 0.60, 0.25
        elif real_underpay:
            full, part = 0.20, 0.20
        else:
            full, part = 0.05, 0.10
        if u1 < full:
            return build("accepted_full", "dispute accepted in full: the contract rate applies", full, shortfall_allowed, shortfall_allowed, money(shortfall_allowed * COINSURANCE))
        if u1 < full + part:
            half = money(shortfall_allowed / 2)
            return build("accepted_part", "dispute accepted in part", full + part, shortfall_allowed, half, money(half * COINSURANCE))
        return build("refused", "dispute refused: the payer stands by its allowed amount", full + part, shortfall_allowed, zero, zero)

    # ------------------------------------------------------------------------------------------------ the second-round paper
    def remit_claim(self, d: Decision, ans: ReplyAnswer) -> SimClaim:
        """A SimClaim carrying only this round's money, for x12out.write_835 (claim id `<claim>-R<n>`)."""
        c = d.claim
        billed, allowed, pr = Decimal(ans.billed), Decimal(ans.allowed), Decimal(ans.patient_resp)
        if ans.kind == "dispute":
            ln = SimLine(c.lines[0].cpt, 1, billed, allowed, pr, allowed - pr, [("CO", "45", billed - allowed), ("PR", "2", pr)])
            lines, scenario, carc = [ln], "clean", ""
        elif ans.paid_out:
            lines = [SimLine(x.cpt, x.units, x.billed, Decimal(0)) for x in c.lines]
            for ln in lines:  # spread the round's allowed amount over the lines in proportion to billed
                ln.allowed = money(allowed * ln.billed / sum((x.billed for x in lines), Decimal(0)))
            if sum((ln.allowed for ln in lines), Decimal(0)) != allowed:
                lines[-1].allowed += allowed - sum((ln.allowed for ln in lines), Decimal(0))
            for ln in lines:
                ln.pr = money(ln.allowed * COINSURANCE)
                ln.paid = ln.allowed - ln.pr
                ln.cas = [("CO", "45", ln.billed - ln.allowed), ("PR", "2", ln.pr)]
            scenario, carc = "clean", ""
        else:
            lines = [SimLine(x.cpt, x.units, x.billed, Decimal(0), Decimal(0), Decimal(0), [("CO", ans.carc, x.billed)]) for x in c.lines]
            scenario, carc = "denial", ans.carc
        if ans.outcome == "refused":
            lines[0].cas = [("CO", "45", billed)]
        out = ReplyClaim(ans.reply_id, c.payer, c.provider_npi, c.patient, c.dos, list(c.dx), lines, c.submitted, scenario, carc, pcn=c.payer_claim_no)
        return out


def truth_csv(rows: list[dict]) -> str:
    """One row per answered reply, sorted by reply id. `rows` come from the run state; deterministic for the same seed and claims."""
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=REPLY_TRUTH_COLUMNS, lineterminator="\n")
    w.writeheader()
    for r in sorted(rows, key=lambda x: x["reply_id"]):
        w.writerow({k: r.get(k, "") for k in REPLY_TRUTH_COLUMNS})
    return buf.getvalue()


def truth_row(ans: dict, sent: date | str, answer_date: date | str, approval: str) -> dict:
    return {"claim_id": ans["claim_id"], "reply_id": ans["reply_id"], "round": ans["round"], "kind": ans["kind"], "sent": str(sent), "answer_date": str(answer_date),
            "outcome": ans["outcome"], "carc": ans["carc"], "billed": ans["billed"], "allowed": ans["allowed"], "paid": ans["paid"], "patient_resp": ans["patient_resp"],
            "deviation_in_play": ans["deviation_in_play"], "cites_rule": int(ans["cites_rule"]), "rule_really_contradicted": int(ans["rule_really_contradicted"]),
            "p_good": ans["p_good"], "approval": approval}  # fmt: skip
