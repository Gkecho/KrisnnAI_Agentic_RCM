# ruff: noqa: E501
"""S8: the bots reply to the payer's reply (demo tenant only, ADR-0003).

Given what the payer showed (a clearinghouse rejection, an 835 denial or underpayment, a records request) and the claim, this
module DECIDES the next action and builds what would be sent. It does no I/O and keeps no hidden state: the stream saves every
plan, so a killed run resumes without repeating a reply. It reads only what a client could see: the 837 it sent, the remit text,
the practice's own fee-schedule copy, the coder's saved record and the payer's PUBLISHED rules (the Knowledge Book). It never
looks at the payer simulator's hidden truth.

Rules, in order, for a denial (rules first, no model):
  1. a CODE change is never made here (rule 4): coding denials, duplicates, timely filing, unknown reasons go to a person;
  2. if the payer contradicted its own published rule (or its own 271 answer) say so and APPEAL on that ground;
  3. a correctable data or coverage problem gets ONE corrected claim (CLM05-3 = 7, same codes);
  4. otherwise an appealable denial gets an appeal packet; everything else goes to review;
  5. nothing is sent after the Knowledge Book's deadline for that route (or when the book cannot compute one): a person decides.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import date
from decimal import Decimal

from krisnai.agents.a8_denial.routing import DEFAULT_ROUTES
from krisnai.ingest.x12 import read_transactions
from krisnai.knowledge import Book
from krisnai.knowledge.deadlines import deadline
from krisnai.live.payer import money

SIM_BILLER = "person:simulated-biller (demo)"
SIM_FRONT_DESK = "person:simulated-front-desk (demo)"
SIM_APPEALS = "person:simulated-appeals-specialist (demo)"
POLICY = "policy:demo-replies-v1 (capped)"
APPROVAL_RE = re.compile(r"^(person:simulated-[a-z-]+ \(demo\)|policy:demo-replies-v1 \(capped\))$")
NO_APPROVAL = "none: waiting for a person (nothing sent)"
MAX_ROUNDS = 3  # denial replies per claim before a person must decide
ROUTES = {carc: {"category": cat, "owner": owner, "disposition": disp, "description": desc} for carc, cat, owner, disp, desc in DEFAULT_ROUTES}
SEND_DELAY = {"corrected_claim": 1, "appeal": 3, "dispute": 2, "records": 1}  # days a simulated person takes to prepare and approve


@dataclass
class ReplyPolicy:
    """The capped demo policy. The daily cap stands in for the unbuilt kill switch (ADR-0003)."""

    daily_cap: int = 25
    enabled: bool = True
    per_day: dict[str, int] = field(default_factory=dict)

    def can_send(self, day: date) -> bool:
        return self.enabled and self.per_day.get(day.isoformat(), 0) < self.daily_cap

    def took(self, day: date) -> None:
        self.per_day[day.isoformat()] = self.per_day.get(day.isoformat(), 0) + 1


@dataclass
class RemitView:
    """What an 835 says about one claim."""

    claim_id: str
    status: str  # CLP02: 1 processed as primary, 4 denied
    billed: Decimal
    paid: Decimal
    patient_resp: Decimal
    allowed: Decimal
    carc: str  # the denial reason (first CAS reason that is not 45 or a patient-responsibility group)
    payer_claim_no: str

    @property
    def denied(self) -> bool:
        return self.status == "4" or (self.paid == 0 and bool(self.carc))


def read_remit(text: str, claim_id: str) -> RemitView | None:
    cur: dict | None = None
    for tx in read_transactions(text):
        for seg in tx.segments:
            if seg.id == "CLP":
                if cur and cur["claim_id"] == claim_id:
                    break
                cur = {"claim_id": seg[1], "status": seg[2], "billed": Decimal(seg[3] or "0"), "paid": Decimal(seg[4] or "0"), "patient_resp": Decimal(seg[5] or "0"),
                       "allowed": Decimal(0), "carc": "", "payer_claim_no": seg[7]}  # fmt: skip
            elif cur is not None and cur["claim_id"] == claim_id:
                if seg.id == "CAS" and seg[1] == "CO" and seg[2] not in ("45", "") and not cur["carc"]:
                    cur["carc"] = seg[2]
                elif seg.id == "AMT" and seg[1] == "B6":
                    cur["allowed"] += Decimal(seg[2] or "0")
    return RemitView(**cur) if cur and cur["claim_id"] == claim_id else None


@dataclass
class Finding:
    """The payer contradicted what it published (or its own answer)."""

    rule_id: str
    version: int
    ground: str
    kind: str  # published_rule | own_271

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Plan:
    kind: str  # corrected_claim | appeal | dispute | records | review | settled | patient_balance
    round: int
    reason: str
    approval: str
    send_on: str = ""
    trigger: str = ""  # corrected_claim: rejection | denial
    carc: str = ""
    owner: str = ""
    finding: dict | None = None
    deadline: dict | None = None
    evidence: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def _dl(d) -> dict:  # noqa: ANN001
    return {"route": d.route, "due": d.due.isoformat(), "rule": f"{d.rule_id} v{d.version}", "days_left": d.days_left, "method": d.method}


class Responder:
    def __init__(self, book: Book | None):
        self.book = book

    # ------------------------------------------------------------------------------------------------ deadlines and rules
    def check_deadline(self, route: str, ctx: dict, as_of: date) -> tuple[dict | None, str]:
        """(deadline info, "") when the route is open on `as_of`; (info or None, why not) when expired or not computable."""
        if self.book is None:
            return None, "no Knowledge Book: the deadline cannot be computed"
        dates = {"service_date": date.fromisoformat(ctx["dos"])}
        if ctx.get("notified"):
            dates["denial_notification_date"] = date.fromisoformat(ctx["notified"])
        r = deadline(self.book, route, ctx["payer_id"], ctx["cpt"], dates, as_of)
        if not r.ok:
            return None, f"the book cannot give the {route} deadline: {r.problem.message}"
        assert r.deadline is not None
        if r.deadline.expired:
            return _dl(r.deadline), f"the {route} deadline passed on {r.deadline.due} ({r.deadline.rule_id} v{r.deadline.version})"
        return _dl(r.deadline), ""

    def contradiction(self, ctx: dict, carc: str, as_of: date) -> Finding | None:
        """Did the payer deny against its own published rule or its own eligibility answer? Only strong, checkable grounds count."""
        if self.book is None:
            return None
        dos = date.fromisoformat(ctx["dos"])
        dates = {"service_date": dos}
        if carc in ("197", "198"):
            pa = self.book.lookup(ctx["payer_id"], "prior_auth", ctx["cpt"], dates, as_of)
            if pa.ok and not pa.rule.content.get("required"):
                return Finding(pa.rule.rule_id, pa.rule.version, f"{pa.rule.rule_id} v{pa.rule.version} says prior authorization was NOT required for {ctx['cpt']} on {dos}", "published_rule")
        if carc in ("27", "31") and ctx.get("active_271") is True:
            cov = self.book.lookup(ctx["payer_id"], "coverage", ctx["cpt"], dates, as_of)
            rid, ver = (cov.rule.rule_id, cov.rule.version) if cov.ok and cov.rule.content.get("covered") else ("271", 0)
            extra = f"; {rid} v{ver} covers {ctx['cpt']}" if ver else ""
            return Finding(rid, ver, f"the payer's own 271 answered that coverage was active for the date of service{extra}", "own_271" if not ver else "published_rule")
        return None

    # ------------------------------------------------------------------------------------------------ planning
    def review_plan(self, kind_round: int, reason: str, carc: str = "", fnd: Finding | None = None, dl: dict | None = None) -> Plan:
        route = ROUTES.get(carc)
        return Plan("review", kind_round, reason, NO_APPROVAL, carc=carc, owner=(route or {}).get("owner", "billing"), finding=fnd.to_dict() if fnd else None, deadline=dl)

    def plan_after_rejection(self, ctx: dict, reason: str, day: date, round_no: int) -> Plan:
        """A clearinghouse rejection (technical): fix the data-entry field and resubmit a replacement claim."""
        if "payer id" not in reason and "diagnosis" not in reason:
            return self.review_plan(round_no, f"clearinghouse rejection '{reason}' is not a field the bot may fix")
        dl, why = self.check_deadline("corrected_claim", ctx, day)
        if why:
            return self.review_plan(round_no, why, dl=dl)
        return Plan("corrected_claim", round_no, f"fix the data-entry error and send a replacement claim ({reason})", POLICY, day.isoformat(), "rejection", deadline=dl, evidence={"rejection": reason})

    def plan_records(self, ctx: dict, day: date, round_no: int) -> Plan:
        return Plan("records", round_no, "the payer asked for medical records for this claim; send the signed note and transcript", POLICY, (day).isoformat(),
                    evidence={"attachments": ["signed note", "visit transcript", "claim copy (837)"]})  # fmt: skip

    def plan_after_remit(self, ctx: dict, remit: RemitView, day: date, round_no: int, rounds: list[dict], fees: dict[str, str], check_underpay: bool = True) -> Plan:
        """What to do about a remit. `rounds` are the replies already sent for this claim (kind, trigger, outcome)."""
        sent = [r["plan"]["kind"] + ":" + r["plan"].get("trigger", "") for r in rounds if r["plan"]["kind"] != "records"]
        n_denial_rounds = len(sent)
        if not remit.denied:
            short = self._shortfall(ctx, remit, fees) if check_underpay else Decimal(0)
            if short > 0 and not any(s.startswith("dispute") for s in sent):
                return Plan("dispute", round_no, f"paid below the contract rate: allowed {remit.allowed} against the fee schedule; dispute the difference of {short} (allowed amount)",
                            SIM_BILLER, (day).isoformat(), carc="45", evidence={"fee_schedule": {c: fees[c] for c in ctx["cpts"] if c in fees}, "allowed_on_remit": str(remit.allowed),
                                                                          "shortfall_allowed": str(short)})  # fmt: skip
            return Plan("settled", round_no, "paid; nothing left to ask the payer for", "")
        carc = remit.carc
        if n_denial_rounds >= MAX_ROUNDS:
            return self.review_plan(round_no, f"still denied (CARC {carc}) after {n_denial_rounds} replies: a person must decide", carc)
        if sent and sent[-1].startswith("appeal"):
            return self.review_plan(round_no, f"the appeal was upheld (CARC {carc}); a second-level appeal, external review or a write-off needs a person", carc)
        route = ROUTES.get(carc)
        if route is None:
            return self.review_plan(round_no, f"CARC {carc} has no route: a person must decide", carc)
        ctx = {**ctx, "notified": ctx.get("notified") or day.isoformat()}
        fnd = self.contradiction(ctx, carc, day)
        corrected_denial_done = any(s == "corrected_claim:denial" for s in sent)
        if fnd is not None:
            kind = "appeal"
        elif route["owner"] == "coding" and route["disposition"] == "correctable":
            return self.review_plan(round_no, f"CARC {carc} ({route['description']}) would need a code change; codes are never changed without a named person", carc)
        elif route["disposition"] == "correctable" and not corrected_denial_done:
            kind = "corrected_claim"
        elif route["disposition"] in ("appealable", "correctable"):
            kind = "appeal"
        else:
            return self.review_plan(round_no, f"CARC {carc} ({route['description']}): {route['disposition']}; a person decides whether to write it off", carc)
        dl, why = self.check_deadline(kind, ctx, day)
        if why:
            return self.review_plan(round_no, why, carc, fnd, dl)
        if kind == "corrected_claim":
            who = SIM_FRONT_DESK if route["category"] == "coverage" else SIM_BILLER
            what = "update the insurance details and resubmit once" if route["category"] == "coverage" else "add the missing information and resubmit once"
            return Plan(kind, round_no, f"CARC {carc} ({route['description']}): {what}", who, day.isoformat(), "denial", carc, route["owner"], deadline=dl,
                        evidence={"fields": "insurance details" if route["category"] == "coverage" else "missing information"})  # fmt: skip
        reason = f"CARC {carc} ({route['description']}): appeal" + (f" on the ground that {fnd.ground}" if fnd else " on the merits (no published rule contradicted)")
        return Plan("appeal", round_no, reason, SIM_APPEALS, day.isoformat(), carc=carc, owner=route["owner"], finding=fnd.to_dict() if fnd else None, deadline=dl,
                    evidence={"attachments": self.attachments(ctx, fnd)})  # fmt: skip

    def _shortfall(self, ctx: dict, remit: RemitView, fees: dict[str, str]) -> Decimal:
        """Allowed amount the remit is short of the contract: the practice's fee-schedule copy against the AMT*B6 on the 835."""
        exp = sum((money(min(Decimal(fees[c]) * u, b)) for c, u, b in ctx["lines"] if c in fees), Decimal(0))
        return money(exp - remit.allowed) if exp - remit.allowed > Decimal("0.01") else Decimal(0)

    # ------------------------------------------------------------------------------------------------ what is sent
    @staticmethod
    def attachments(ctx: dict, fnd: Finding | None) -> list[str]:
        out = ["claim copy (837)", "remittance advice (835)", "signed visit note", "visit transcript"]
        if ctx.get("active_271") is not None:
            out.append("eligibility response (271)")
        if fnd:
            out.append(f"published rule excerpt: {fnd.rule_id} v{fnd.version}" if fnd.version else "eligibility response (271) showing active coverage")
        return out

    @staticmethod
    def appeal_letter(ctx: dict, plan: Plan) -> str:
        """A stub letter generator (rules fill a template; no model is used and no real PHI is in it)."""
        g = (plan.finding or {}).get("ground")
        body = [f"To: {ctx['payer_id']} appeals (SIMULATED PAYER, DEMO)", f"Re: claim {ctx['claim_id']}, date of service {ctx['dos']}, member {ctx['member']}",
                f"We appeal the denial with reason code {plan.carc}.", ""]  # fmt: skip
        if g:
            body += [f"Ground: {g}.", "The denial is inconsistent with the payer's own published rule; we ask that it be overturned and the claim paid.", ""]
        else:
            body += ["Ground: the service was documented and medically appropriate; the enclosed records support payment.", ""]
        body += ["Enclosures: " + "; ".join(plan.evidence.get("attachments", [])), f"Filed {plan.send_on} within the deadline ({plan.deadline['rule']}, due {plan.deadline['due']})." if plan.deadline else "",
                 f"Approved by {plan.approval}. Draft text from a stub generator; a person approves before anything is filed."]  # fmt: skip
        return "\n".join(body) + "\n"

    @staticmethod
    def dispute_letter(ctx: dict, plan: Plan) -> str:
        ev = plan.evidence
        return (f"To: {ctx['payer_id']} payment disputes (SIMULATED PAYER, DEMO)\nRe: claim {ctx['claim_id']}, date of service {ctx['dos']}\n"
                f"The allowed amount on the remittance ({ev['allowed_on_remit']}) is below the contract fee schedule ({json.dumps(ev['fee_schedule'])}).\n"
                f"We ask for the difference of {ev['shortfall_allowed']} (allowed amount). Approved by {plan.approval}.\n")  # fmt: skip

    @staticmethod
    def corrected_837(sent: str, *, payer_claim_no: str = "", note: str = "", payer_id: str = "", dx_codes: list[str] | None = None) -> str:
        """A replacement claim (CLM05-3 = 7) from the 837 that was sent. It may fix a blank payer id or a blanked diagnosis and add a reference
        and a note. It never touches an SV1 procedure code or an existing diagnosis code."""
        segs = [s for s in sent.replace("\n", "").split("~") if s]
        out: list[str] = []
        have_hi = any(s.startswith("HI*") and len(s.split("*")) > 1 and s.split("*")[1] for s in segs)
        for s in segs:
            parts = s.split("*")
            if parts[0] == "NM1" and len(parts) > 1 and parts[1] == "PR" and payer_id:
                parts = (parts + [""] * 10)[:10]
                if not parts[9]:
                    parts[9] = payer_id
                s = "*".join(parts)
            elif parts[0] == "HI" and not have_hi:
                continue  # an empty HI segment is replaced below
            if parts[0] == "CLM":
                comp = (parts[5] if len(parts) > 5 else "11:B:1").split(":")
                comp = (comp + ["", ""])[:3]
                comp[2] = "7"
                parts = (parts + [""] * 6)[:max(len(parts), 6)]
                parts[5] = ":".join(comp)
                out.append("*".join(parts))
                out.append(f"REF*F8*{payer_claim_no or parts[1]}")
                if note:
                    out.append(f"NTE*ADD*{note[:78]}")
                if not have_hi and dx_codes:
                    out.append("HI*" + "*".join(("ABK" if i == 0 else "ABF") + ":" + c for i, c in enumerate(dx_codes)))
                continue
            out.append(s)
        # keep the envelope counts right: SE01 is the number of segments between ST and SE inclusive
        text = ""
        st = next(i for i, s in enumerate(out) if s.startswith("ST*"))
        se = next(i for i, s in enumerate(out) if s.startswith("SE*"))
        parts = out[se].split("*")
        parts[1] = str(se - st + 1)
        out[se] = "*".join(parts)
        for s in out:
            text += s + "~\n"
        return text


def break_837(text: str, kind: str) -> str:
    """Inject a technical data-entry error into an 837 for tests and the reject_rate switch: a blank payer id or a blank diagnosis."""
    segs = [s for s in text.replace("\n", "").split("~") if s]
    out: list[str] = []
    for s in segs:
        p = s.split("*")
        if kind == "payer_id" and p[0] == "NM1" and p[1] == "PR":
            p = (p + [""] * 10)[:10]
            p[9] = ""
            s = "*".join(p)
        elif kind == "diagnosis" and p[0] == "HI":
            continue
        out.append(s)
    st = next(i for i, s in enumerate(out) if s.startswith("ST*"))
    se = next(i for i, s in enumerate(out) if s.startswith("SE*"))
    q = out[se].split("*")
    q[1] = str(se - st + 1)
    out[se] = "*".join(q)
    return "".join(s + "~\n" for s in out)


