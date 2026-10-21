# ruff: noqa: E501  (regex tables and phrase pools read better on one line)
"""The transcript coder for the live encounter stream: rules first, no model.

It reads a visit transcript and a signed flag, extracts the named note elements, and suggests an E/M code and one
diagnosis. Then the exception-only policy of ADR-0002 decides the route:

  * every deterministic check passes and the policy is on  -> auto-accepted "by policy" (a 10% sample still goes to a coder)
  * any check fails, the policy is off, or a cap is reached   -> routed to a coder WITH the reason

Demo tenant only. The policy is off by default; the answer key lives in `transcripts.py` and this module never imports it.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import date

from krisnai.agents.a4_coding import config as a4
from krisnai.agents.a4_coding import rules as a4rules
from krisnai.agents.a5_prevention.config import DEFAULT_MUE

# ---------------------------------------------------------------------------------------------------- extraction
HPI_PATTERNS = {
    "onset": r"\b(started|began|onset|since)\b",
    "duration": r"\bfor (about |over )?(\w+ )?(hours?|days?|weeks?|months?)\b|\bover (a|the past|the last) (\w+ )?(week|month|day)",
    "severity": r"\b\d+ out of (10|ten)\b|\b(mild|moderate|severe)\b",
    "location": r"\b(left|right|lower|upper) (side|back|knee|chest|abdomen)\b|\b(in|on) my (\w+ )?(throat|back|chest|abdomen|side)\b",
    "associated": r"\b(also|along with|with some|plus)\b[^.]{0,40}\b(fever|nausea|cough|fatigue|dizz\w+|headache|chills)\b",
    "modifying": r"\b(worse when|better with|worse at|relieved by|gets worse|improves with)\b",
}
SYSTEMS = ("throat", "neck", "lungs", "heart", "abdomen", "skin", "back", "extremities", "eyes", "ears")
DX = {  # keyword pattern -> (icd10, text)
    r"pharyngitis|sore throat": ("J02.9", "Acute pharyngitis, unspecified"),
    r"low back pain|back pain": ("M54.50", "Low back pain, unspecified"),
    r"urinary tract infection|\buti\b": ("N39.0", "Urinary tract infection, site not specified"),
    r"hypertension|high blood pressure": ("I10", "Essential (primary) hypertension"),
    r"diabetes": ("E11.9", "Type 2 diabetes mellitus without complications"),
    r"\bcough\b": ("R05.9", "Cough, unspecified"),
    r"knee pain": ("M25.569", "Pain in unspecified knee"),
}
CHRONIC = {"I10", "E11.9"}  # a follow-up for these is expected to be documented in depth
NEW_RE = re.compile(r"first (time|visit)|new patient|never been seen|not been here before", re.I)
EST_RE = re.compile(r"last (here|seen|visit)|returning patient", re.I)


@dataclass
class Extraction:
    elements: set[str]
    hpi_components: int
    systems: int
    status: str  # new | established | unknown
    diagnoses: list[tuple[str, str]]
    signed: bool


def _section(text: str, start: str, end: str | None) -> str:
    m = re.search(start, text, re.I)
    if not m:
        return ""
    rest = text[m.end():]
    if end:
        e = re.search(end, rest, re.I)
        rest = rest[: e.start()] if e else rest
    return rest


def extract(text: str, signed: bool) -> Extraction:
    hpi = _section(text, r"what brings you in", r"\bexam\b")
    n_hpi = sum(1 for p in HPI_PATTERNS.values() if re.search(p, hpi, re.I))
    exam = _section(text, r"\bexam:", r"assessment")
    systems = sum(1 for s in SYSTEMS if re.search(rf"\b{s}\b", exam, re.I))
    assess = _section(text, r"assessment:", r"\bplan\b|signed")
    dx, seen = [], set()
    for pat, (code, name) in DX.items():
        if re.search(pat, assess, re.I) and code not in seen:
            seen.add(code)
            dx.append((code, name))
    els: set[str] = set()
    if len(assess.split()) >= 2 and dx:
        els.add("assessment")
    after = _section(text, r"assessment:", None)
    if re.search(r"\bplan\s*:|\b(prescribe|follow up|return in|refer)\b", after, re.I):
        els.add("plan")
    if n_hpi >= 3:
        els.add("history_detailed")
    if systems >= 2:
        els.add("exam_expanded")
    status = "new" if NEW_RE.search(text) else "established" if EST_RE.search(text) else "unknown"
    return Extraction(els, n_hpi, systems, status, dx, signed and bool(re.search(r"signed electronically", text, re.I)))


# ---------------------------------------------------------------------------------------------------- the decision
@dataclass(frozen=True)
class Policy:
    """ADR-0002. Off by default. `sample_rate` of auto-accepts go to a coder anyway; `daily_cap` stands in for the unbuilt kill switch."""

    policy_id: str = "demo-exception-only-v1"
    enabled: bool = False
    sample_rate: float = 0.10
    daily_cap: int = 40
    seed: int = 7


@dataclass
class Check:
    name: str
    ok: bool
    detail: str


@dataclass
class CodingRecord:
    visit_id: str
    day: str
    cpt: str
    dx: list[tuple[str, str]]
    elements: list[str]
    checks: list[Check]
    route: str  # auto | coder
    reason: str  # why it went to a coder; "" for auto
    approval: str  # "policy:<id>" for auto; "pending:coder" while a person has to decide
    note: str = ""

    def to_dict(self) -> dict:
        d = self.__dict__.copy()
        d["checks"] = [c.__dict__ for c in self.checks]
        return d


REASON_OF = {"signed": "unsigned", "baseline": "missing_plan", "status": "status_unclear", "one_diagnosis": "two_problems",
             "depth": "thin_chronic"}  # fmt: skip


def _checks(ex: Extraction, cpt: str) -> list[Check]:
    chronic = bool(ex.diagnoses) and ex.diagnoses[0][0] in CHRONIC
    docs_low = cpt in ("99213", "99203")
    mue = dict(DEFAULT_MUE).get(cpt, 1)
    return [
        Check("signed", ex.signed, "the note is signed" if ex.signed else "the note is not signed"),
        Check("baseline", set(a4.BASELINE) <= ex.elements, "assessment and plan documented" if set(a4.BASELINE) <= ex.elements
              else f"missing: {', '.join(e for e in a4.BASELINE if e not in ex.elements)}"),  # fmt: skip
        Check("status", ex.status != "unknown", f"patient is {ex.status}" if ex.status != "unknown"
              else "the transcript never says whether the patient is new or established"),  # fmt: skip
        Check("one_diagnosis", len(ex.diagnoses) == 1, f"{len(ex.diagnoses)} diagnosis found"),
        Check("depth", not (chronic and docs_low), "documentation fits the problem" if not (chronic and docs_low)
              else "a chronic-condition follow-up is documented as a minor visit"),  # fmt: skip
        Check("mue", 1 <= mue, f"1 unit, limit {mue}"),
        Check("ncci", True, "one procedure line, so no pair of codes to conflict"),
    ]


def _sampled(visit_id: str, policy: Policy) -> bool:
    h = int(hashlib.sha256(f"{policy.seed}:{visit_id}".encode()).hexdigest(), 16)
    return (h % 10_000) < int(policy.sample_rate * 10_000)


@dataclass
class Coder:
    policy: Policy = field(default_factory=Policy)
    per_day: dict[str, int] = field(default_factory=dict)

    def code(self, visit_id: str, text: str, signed: bool, day: date) -> CodingRecord:
        ex = extract(text, signed)
        family = {"new": "new", "established": "established"}.get(ex.status, "established")
        cpt = a4rules.supported_level(family, ex.elements) if ex.status != "unknown" else ""
        checks = _checks(ex, cpt or "99213")
        failed = [c for c in checks if not c.ok]
        base = {"visit_id": visit_id, "day": day.isoformat(), "cpt": cpt, "dx": ex.diagnoses[:1] if len(ex.diagnoses) == 1 else ex.diagnoses,
                "elements": sorted(ex.elements), "checks": checks}  # fmt: skip
        if failed:
            first = failed[0].name
            return CodingRecord(**base, route="coder", reason=REASON_OF.get(first, first), approval="pending:coder",
                                note="; ".join(c.detail for c in failed))  # fmt: skip
        if not self.policy.enabled:
            return CodingRecord(**base, route="coder", reason="policy_off", approval="pending:coder",
                                note="every check passed, but auto-accept is switched off")  # fmt: skip
        if _sampled(visit_id, self.policy):
            return CodingRecord(**base, route="coder", reason="qa_sample", approval="pending:coder",
                                note="every check passed; sampled for a coder's quality check")  # fmt: skip
        used = self.per_day.get(day.isoformat(), 0)
        if used >= self.policy.daily_cap:
            return CodingRecord(**base, route="coder", reason="daily_cap_reached", approval="pending:coder",
                                note=f"cap of {self.policy.daily_cap} auto-accepts a day reached")  # fmt: skip
        self.per_day[day.isoformat()] = used + 1
        return CodingRecord(**base, route="auto", reason="", approval=f"policy:{self.policy.policy_id}",
                            note="every deterministic check passed")  # fmt: skip
