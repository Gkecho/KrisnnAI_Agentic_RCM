# ruff: noqa: E501  (regex tables and phrase pools read better on one line)
"""The transcript coder for the live encounter stream: rules first, AI only as a checked second opinion.

`krisnnai.live.reader.read` turns any visit note into a `Reading`. This module works on that reading: it suggests an E/M code, the
procedure / lab / imaging / therapy codes with units and diagnosis pointers, and the ICD-10 diagnoses from the catalog. Then the
exception-only policy of ADR-0002 decides the route:

  * every deterministic check passes and the policy is on  -> auto-accepted "by policy" (a 10% sample still goes to a coder)
  * any check fails, the policy is off, or a cap is reached   -> routed to a coder WITH the reason

The seven original checks are kept (signed, baseline, status, one_diagnosis, depth, mue, ncci). Four more are added when they apply:
laterality required, time documented for timed services, procedure documentation, and "uncertainty" (anything the reader could not
interpret ALWAYS routes to a coder). `reader="rules+ai"` additionally asks `krisnnai.live.ai_reader.AiReader` for a proposal; the AI can
add suggestions or raise a disagreement but never overrides the rules, and a disagreement is an uncertainty.

Demo tenant only. The policy is off by default; the answer key lives in `transcripts.py` and this module never imports it.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import date

from krisnnai.agents.a4_coding import config as a4
from krisnnai.agents.a4_coding import rules as a4rules
from krisnnai.agents.a5_prevention.config import DEFAULT_MUE, DEFAULT_NCCI
from krisnnai.live import catalog
from krisnnai.live.ai_reader import AiReader
from krisnnai.live.reader import Reading, ServiceHit, read

CHRONIC = {"I10", "E11.9"}  # kept for callers of the old module; the live test is `Condition.chronic` in the catalog
PROCEDURE_FAMILIES = ("procedure", "injection")  # billed with an E/M these need a modifier 25 decision
READERS = ("rules", "rules+ai")


@dataclass
class Extraction:
    """The old shape of a reading, kept for callers of `extract`."""

    elements: set[str]
    hpi_components: int
    systems: int
    status: str  # new | established | unknown
    diagnoses: list[tuple[str, str]]
    signed: bool


def extract(text: str, signed: bool) -> Extraction:
    rd = read(text, signed)
    return Extraction(rd.elements, len(rd.hpi), len(rd.systems), rd.status, [(c.icd10, c.name) for c in rd.diagnoses], rd.signed)


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
    cpt: str  # the E/M code; for a visit with only timed therapy or the like, the first service code
    dx: list[tuple[str, str]]
    elements: list[str]
    checks: list[Check]
    route: str  # auto | coder
    reason: str  # why it went to a coder; "" for auto
    approval: str  # "policy:<id>" for auto; "pending:coder" while a person has to decide
    note: str = ""
    procedures: list[dict] = field(default_factory=list)  # service lines: cpt, units, modifiers, dx pointers, status, evidence
    uncertainties: list[str] = field(default_factory=list)  # what the reader could not interpret
    flags: list[str] = field(default_factory=list)  # worth a coder's attention but not a reason to stop (e.g. an unspecified code)
    reader: str = "rules"
    ai: dict = field(default_factory=dict)  # what the AI layer proposed, accepted, rejected (empty when it did not run)

    def to_dict(self) -> dict:
        d = self.__dict__.copy()
        d["checks"] = [c.__dict__ for c in self.checks]
        return d


REASON_OF = {"signed": "unsigned", "baseline": "missing_plan", "status": "status_unclear", "one_diagnosis": "two_problems",
             "depth": "thin_chronic", "mue": "unit_limit", "ncci": "code_pair", "laterality": "laterality_missing",
             "time_documented": "time_missing", "procedure_documented": "procedure_not_documented", "uncertainty": "reader_uncertain",
             "visit_kind": "visit_kind", "indication": "missing_necessity"}  # fmt: skip


HIGH_MARKERS = re.compile(r"reviewed (?:the )?(?:outside )?(?:records|results)|risk of (?:hospital )?admission|hospitali[sz]ation", re.I)
INDICATION_RE = re.compile(r"indication\s*:|reason for (?:this|the)|because|due to|to (?:evaluate|assess|rule out|look for|check for|investigate|exclude)|concern(?:ed)? (?:for|about)|r/o|rule out|suspect", re.I)
WEAK_INDICATION_RE = re.compile(r"routine screening|to be thorough|just in case|for completeness", re.I)


def _em_level(rd: Reading, text: str, family: str) -> str:
    """The office visit code by how deep the documentation is (a demo convention, not the AMA tables): straightforward, low, moderate, high."""
    base = a4rules.supported_level(family, rd.elements)  # 99213/99214 or 99203/99204
    low, mid = a4.FAMILIES[family]
    hi = "99215" if family == "established" else "99205"
    st = "99212" if family == "established" else "99202"
    if base == mid:
        return hi if HIGH_MARKERS.search(text) else mid
    return st if len(rd.hpi) <= 1 and len(rd.systems) <= 1 else low


def _missing_indication(rd: Reading, text: str) -> list[str]:
    """Tests and images that need a stated reason (catalog `needs_indication`) where the note gives none, or only a weak one."""
    out = []
    low = text.lower()
    for s in rd.services:
        c = catalog.service_by_cpt(s.cpt)
        if not (c and c.needs_indication):
            continue
        i = low.find(s.evidence.lower()[:40])
        window = text[i: i + len(s.evidence) + 170] if i >= 0 else s.evidence
        if not INDICATION_RE.search(window) or WEAK_INDICATION_RE.search(window):
            out.append(s.name)
    return out


def _unsigned_why(rd: Reading) -> str:
    """Why a note counts as unsigned: three different things can cause it, and the fix is different for each."""
    why = []
    if not rd.signed_flag:
        why.append("the record marks the note unsigned (the 'note is signed' box, or the '# unsigned' label)" + (", although the transcript has a signature line" if rd.signature_present else ""))
    if rd.unsigned_wording:
        why.append("the transcript itself says the note is unsigned or pending signature")
    elif not rd.signature_present:
        why.append("the transcript has no signature line (for example 'Signed electronically by Dr. Name')")
    return "the note is not signed: " + "; and ".join(why) if why else "the note is not signed"


def _letters(n: int) -> list[str]:
    return [chr(ord("A") + i) for i in range(min(n, 12))]


def _lines(rd: Reading) -> list[dict]:
    """One service line per catalog service found, with units, modifiers and the diagnosis pointers."""
    dx = rd.diagnoses
    out = []
    for s in rd.services:
        pointers = _letters(len(dx))[:1]
        for i, h in enumerate(dx[:12]):
            c = catalog.condition_by_icd(h.icd10)
            if c and any(re.search(rf"(?<![a-z]){re.escape(k)}", s.evidence, re.I) for k in c.keywords):
                pointers = [chr(ord("A") + i)]
                break
        mods = {"left": ["LT"], "right": ["RT"], "bilateral": ["50"]}.get(s.laterality, []) if s.needs_laterality else []
        out.append({"cpt": s.cpt, "name": s.name, "family": s.family, "units": s.units, "minutes": s.minutes, "modifiers": mods,
                    "dx_pointers": pointers if dx else [], "laterality": s.laterality, "status": s.status, "source": s.source,
                    "evidence": s.evidence})  # fmt: skip
    return out


def _checks(rd: Reading, cpt: str, lines: list[dict], em_billed: bool, text: str = "") -> list[Check]:
    dx = rd.diagnoses
    first = catalog.condition_by_icd(dx[0].icd10) if dx else None
    chronic = bool(dx) and (dx[0].chronic or (first.chronic if first else False))
    docs_low = em_billed and cpt in ("99212", "99213", "99202", "99203")
    elements = rd.elements
    status_ok = rd.status != "unknown" or not em_billed
    kinds = sorted({k for h in dx if (c := catalog.condition_by_icd(h.icd10)) and (k := c.visit_kind)} | {s.family for s in rd.services if s.family in ("preventive", "emergency")})
    checks = [
        Check("signed", rd.signed, "the note is signed" if rd.signed else _unsigned_why(rd)),
        Check("baseline", set(a4.BASELINE) <= elements, "assessment and plan documented" if set(a4.BASELINE) <= elements
              else f"missing: {', '.join(e for e in a4.BASELINE if e not in elements)}"),  # fmt: skip
        Check("status", status_ok, f"patient is {rd.status}" if rd.status != "unknown"
              else ("no E/M code is billed, so new or established does not matter" if status_ok
                    else "the transcript never says whether the patient is new or established")),  # fmt: skip
        Check("one_diagnosis", len(dx) == 1, f"{len(dx)} diagnosis found"),
        Check("depth", not (chronic and docs_low), "documentation fits the problem" if not (chronic and docs_low)
              else "a chronic-condition follow-up is documented as a minor visit"),  # fmt: skip
    ]
    if kinds:
        checks.insert(1, Check("visit_kind", False, f"a {' and '.join(kinds)} visit is coded from the patient's age band or the emergency level, which a coder decides"))
    mue_map = dict(DEFAULT_MUE)
    over = [f"{ln['cpt']}: {ln['units']} units, limit {mue_map.get(ln['cpt'], 1)}" for ln in lines if ln["units"] > mue_map.get(ln["cpt"], 1)]
    if not lines:
        limit = mue_map.get(cpt or "99213", 1)
        checks.append(Check("mue", 1 <= limit, f"1 unit, limit {limit}"))
    else:
        checks.append(Check("mue", not over, "; ".join(over) if over else "every line is within its unit limit"))
    codes = ([cpt] if em_billed and cpt else []) + [ln["cpt"] for ln in lines]
    pairs = [f"{a} with {b}" for a, b, _ in DEFAULT_NCCI if a in codes and b in codes]
    em_proc = em_billed and any(ln["family"] in PROCEDURE_FAMILIES + ("therapy",) for ln in lines)
    if len(codes) <= 1:
        checks.append(Check("ncci", True, "one procedure line, so no pair of codes to conflict"))
    elif pairs or em_proc:
        why = ([f"code pair listed in the edit table: {', '.join(pairs)}"] if pairs else []) + (
            ["an E/M code with a procedure on the same day: a coder decides on modifier 25"] if em_proc else [])
        checks.append(Check("ncci", False, "; ".join(why)))
    else:
        checks.append(Check("ncci", True, f"{len(codes)} codes, no listed pair conflicts"))

    # ---- checks added for procedures, laterality, time and reader uncertainty: present only when they apply
    needs_lat = [h for h in dx if h.needs_laterality] + [s for s in rd.services if s.needs_laterality]
    if needs_lat:
        missing = [getattr(h, "name", "") for h in needs_lat if h.laterality not in ("left", "right", "bilateral")]
        checks.append(Check("laterality", not missing, "side (left, right or bilateral) documented" if not missing
                            else f"side not documented for: {', '.join(missing)}"))  # fmt: skip
    timed = [s for s in rd.services if s.needs_time]
    if timed:
        bad = [s.name for s in timed if not s.minutes or s.units < 1]
        checks.append(Check("time_documented", not bad, "minutes documented" if not bad else f"minutes missing or too few for: {', '.join(bad)}"))
    if lines:
        problems = []
        if not dx:
            problems.append("no diagnosis to point to")
        problems += [f"{ln['name']} is only ordered, not documented as done" for ln in lines if ln["status"] == "ordered" and ln["family"] in PROCEDURE_FAMILIES + ("therapy",)]
        checks.append(Check("procedure_documented", not problems, "each service has evidence and a diagnosis" if not problems else "; ".join(problems)))
    no_ind = _missing_indication(rd, text)
    if no_ind:
        checks.append(Check("indication", False, f"no clear reason (medical necessity) is stated for: {', '.join(no_ind)}"))
    if rd.uncertainties:
        shown = "; ".join(rd.uncertainties[:3]) + (f"; and {len(rd.uncertainties) - 3} more" if len(rd.uncertainties) > 3 else "")
        checks.append(Check("uncertainty", False, f"the reader could not interpret: {shown}"))
    return checks


def _reason(failed: list[Check], rd: Reading) -> str:
    first = failed[0].name
    if first == "baseline" and "plan" in rd.elements and "assessment" not in rd.elements:
        return "missing_assessment"
    if first == "one_diagnosis" and not rd.diagnoses:
        return "no_diagnosis"
    return REASON_OF.get(first, first)


def _sampled(visit_id: str, policy: Policy) -> bool:
    h = int(hashlib.sha256(f"{policy.seed}:{visit_id}".encode()).hexdigest(), 16)
    return (h % 10_000) < int(policy.sample_rate * 10_000)


@dataclass
class Coder:
    policy: Policy = field(default_factory=Policy)
    per_day: dict[str, int] = field(default_factory=dict)
    reader: str = "rules"  # "rules" | "rules+ai" (an AI proposal, validated by the rules; see ai_reader.py)
    ai: AiReader | None = None

    def __post_init__(self) -> None:
        if self.reader not in READERS:
            raise ValueError(f"reader must be one of {READERS}, not {self.reader!r}")

    def read(self, text: str, signed: bool) -> Reading:
        rd = read(text, signed)
        if self.reader == "rules+ai":
            if self.ai is None:
                self.ai = AiReader()
            rd = self.ai.apply(text, rd)
        return rd

    def code(self, visit_id: str, text: str, signed: bool, day: date) -> CodingRecord:
        rd = self.read(text, signed)
        dx = [(h.icd10, h.name) for h in rd.diagnoses]
        lines = _lines(rd)
        therapy_only = bool(lines) and all(ln["family"] == "therapy" for ln in lines) and len(rd.hpi) < 2 and not rd.systems  # a therapy session; with a full visit note it is a visit plus therapy
        em_billed = not therapy_only
        family = {"new": "new", "established": "established"}.get(rd.status, "established")
        cpt = _em_level(rd, text, family) if rd.status != "unknown" and em_billed else ""
        if not em_billed:
            cpt = lines[0]["cpt"]
        checks = _checks(rd, cpt or "99213", lines, em_billed, text)
        failed = [c for c in checks if not c.ok]
        flags = [f"{h.icd10} is an unspecified code ({h.name}); a coder may be able to document more" for h in rd.diagnoses if h.unspecified]
        flags += [f"not coded: {n}" for n in rd.notes]
        base = {"visit_id": visit_id, "day": day.isoformat(), "cpt": cpt, "dx": dx, "elements": sorted(rd.elements), "checks": checks,
                "procedures": lines, "uncertainties": list(rd.uncertainties), "flags": flags, "reader": self.reader, "ai": dict(rd.ai)}  # fmt: skip
        if failed:
            return CodingRecord(**base, route="coder", reason=_reason(failed, rd), approval="pending:coder",
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


__all__ = ["CHRONIC", "Check", "Coder", "CodingRecord", "Extraction", "Policy", "ServiceHit", "extract"]
