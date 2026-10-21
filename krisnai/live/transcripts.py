# ruff: noqa: E501  (regex tables and phrase pools read better on one line)
"""Synthetic visit transcripts for the live encounter stream, with an answer key.

Fifty by default, deterministic for a seed. About 20% are deliberately problematic (missing plan, two unrelated problems,
new-versus-established never stated, unsigned, thin documentation for a chronic follow-up) so the coder's routing to a
person is visible. The answer key (`Visit.expected`) is written by this generator and kept apart from the coder, which
sees only the text and the signed flag.

Everything is made up: no real patient, provider or conversation. The wording comes from small phrase pools, so a rule-based
reader is tested on variation but not on real speech; a language model would be the next step for real transcripts.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date, timedelta

PROVIDER = "Dr. Demo Provider"

# key -> (icd10, diagnosis text, family, complexity). 'high' visits (chronic follow-ups, new complex) are documented in depth.
TYPES: dict[str, tuple[str, str, str, str]] = {
    "sore_throat": ("J02.9", "acute pharyngitis", "established", "low"),
    "back_pain": ("M54.50", "low back pain", "established", "low"),
    "uti": ("N39.0", "urinary tract infection", "established", "low"),
    "hypertension": ("I10", "hypertension", "established", "high"),
    "diabetes_followup": ("E11.9", "type 2 diabetes", "established", "high"),
    "new_cough": ("R05.9", "cough", "new", "low"),
    "new_diabetes": ("E11.9", "type 2 diabetes", "new", "high"),
}
CPT = {("established", "low"): "99213", ("established", "high"): "99214", ("new", "low"): "99203", ("new", "high"): "99204"}

COMPLAINT = {
    "sore_throat": "my throat is sore and it hurts to swallow",
    "back_pain": "I have pain in my back, mostly the lower part",
    "uti": "it burns when I urinate and I keep needing to go",
    "hypertension": "I am here for my blood pressure follow-up",
    "diabetes_followup": "I am here for my diabetes follow-up",
    "new_cough": "I have a cough that will not go away",
    "new_diabetes": "my last doctor said my sugar is high and I should see someone about diabetes",
}
HPI = {  # component -> phrases (every phrase is matched by the coder's detectors, which are broader than these)
    "onset": ["It started after a long trip.", "It began suddenly one morning.", "It started slowly."],
    "duration": ["It has been going on for three days.", "I have had it for about two weeks.", "It has lasted over a week."],
    "severity": ["It is about a 6 out of 10.", "I would say it is moderate.", "It is severe at night."],
    "location": ["I feel it in my throat and my chest.", "It is mostly on the left side.", "It is in my lower back."],
    "associated": ["I also have a bit of fever.", "Along with it I feel fatigue.", "I also have had some chills."],
    "modifying": ["It gets worse when I lie down.", "It is worse when I move.", "It is better with rest."],
}
EXAM = {
    "throat": "Throat shows mild erythema without exudate.",
    "neck": "Neck is supple, no lymph nodes felt.",
    "lungs": "Lungs are clear to auscultation.",
    "heart": "Heart has a regular rate and rhythm.",
    "abdomen": "Abdomen is soft and not tender.",
    "back": "Back has no spinal tenderness.",
}
PLAN = ["We will start treatment today and I will see you back in two weeks.", "I will prescribe medication and order labs; follow up in one month.",
        "Rest, fluids, and return in a week if it is not better."]  # fmt: skip


@dataclass
class Expected:
    cpt: str
    dx: str
    route: str  # "auto" or "coder"
    reason: str = ""  # for "coder": missing_plan | two_problems | status_unclear | unsigned | thin_chronic


@dataclass
class Visit:
    visit_id: str
    member: str
    visit_type: str
    text: str
    signed: bool
    expected: Expected
    day: date = field(default_factory=lambda: date(2026, 10, 24))


def _hpi(rng: random.Random, n: int) -> str:
    comps = rng.sample(list(HPI), n)
    return " ".join(rng.choice(HPI[c]) for c in comps)


def _exam(rng: random.Random, kind: str, n: int) -> str:
    pool = {"sore_throat": ["throat", "neck", "lungs"], "uti": ["abdomen", "back", "heart"], "back_pain": ["back", "abdomen", "lungs"]}
    systems = pool.get(kind, ["heart", "lungs", "abdomen", "neck"])
    return " ".join(EXAM[s] for s in rng.sample(systems, min(n, len(systems))))


def build_text(rng: random.Random, kind: str, *, hpi: int, systems: int, plan: bool = True, status: str = "auto",
               signed: bool = True, extra_problem: str = "") -> str:  # fmt: skip
    icd, dx, family, _ = TYPES[kind]
    who = family if status == "auto" else status
    opening = {
        "new": "Provider: Is this your first visit with us? Patient: Yes, this is my first time here.",
        "established": "Provider: You were last here a few months ago, correct? Patient: Yes, that is right, I am a returning patient.",
        "unclear": "Provider: Good morning, let us get started.",
    }[who]
    parts = [
        "[Synthetic visit transcript]",
        opening,
        f"Provider: What brings you in today? Patient: {COMPLAINT[kind]}. {_hpi(rng, hpi)}",
        f"Provider: Let me examine you. Exam: {_exam(rng, kind, systems)}",
    ]
    assessment = f"Assessment: {dx}"
    if extra_problem:
        assessment += f" and {extra_problem}"
    parts.append(f"Provider: {assessment}.")
    if plan:
        parts.append(f"Provider: Plan: {rng.choice(PLAN)}")
    if signed:
        parts.append(f"Signed electronically by {PROVIDER}.")
    return "\n".join(parts)


def generate(seed: int = 7, n: int = 50, start: date = date(2026, 10, 24)) -> list[Visit]:
    """`n` visits. The first 80% are clean; the rest are problematic, spread over five failure kinds."""
    rng = random.Random(seed)
    bad_kinds = ["missing_plan", "missing_plan", "missing_plan", "two_problems", "two_problems", "status_unclear",
                 "status_unclear", "unsigned", "unsigned", "thin_chronic"]  # fmt: skip
    n_bad = round(n * 0.2)
    kinds = [bad_kinds[i % len(bad_kinds)] for i in range(n_bad)]
    order = ["clean"] * (n - n_bad) + kinds
    rng.shuffle(order)
    keys = sorted(TYPES)
    out: list[Visit] = []
    for i, tag in enumerate(order, start=1):
        kind = keys[rng.randrange(len(keys))]
        icd, dx, family, level = TYPES[kind]
        hpi, systems = (4, 3) if level == "high" else (2, 1)
        kw: dict = {}
        exp = Expected(CPT[(family, level)], icd, "auto")
        if tag == "missing_plan":
            kw["plan"] = False
            exp = Expected(exp.cpt, icd, "coder", "missing_plan")
        elif tag == "two_problems":
            kind, kw["extra_problem"] = "hypertension", "right knee pain"
            icd, dx, family, level = TYPES[kind]
            hpi, systems = 4, 3
            exp = Expected(CPT[(family, level)], icd, "coder", "two_problems")
        elif tag == "status_unclear":
            kw["status"] = "unclear"
            exp = Expected(exp.cpt, icd, "coder", "status_unclear")
        elif tag == "unsigned":
            kw["signed"] = False
            exp = Expected(exp.cpt, icd, "coder", "unsigned")
        elif tag == "thin_chronic":
            kind = rng.choice(["hypertension", "diabetes_followup"])
            icd, dx, family, level = TYPES[kind]
            hpi, systems = 2, 1  # chronic follow-up documented as a minor visit
            exp = Expected(CPT[(family, "high")], icd, "coder", "thin_chronic")
        member = f"SYNLT{i:05d}"
        text = build_text(rng, kind, hpi=hpi, systems=systems, **kw)
        out.append(Visit(f"SYNVT{i:05d}L1", member, kind, text, kw.get("signed", True), exp, start + timedelta(days=(i - 1) // 5)))
    return out
