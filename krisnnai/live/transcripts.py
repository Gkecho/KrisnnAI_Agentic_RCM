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
    reason: str = ""  # for "coder": missing_plan | two_problems | status_unclear | unsigned | thin_chronic (generate_wide adds missing_laterality | missing_time | missing_necessity)
    # Added for generate_wide (all optional; `generate()` leaves them at their defaults):
    services: tuple[str, ...] = ()  # every CPT a correct reading finds, the visit code first
    dx_all: tuple[str, ...] = ()  # every ICD-10 a correct reading finds, the first being the main one
    problems: tuple[str, ...] = ()  # documentation defects built into the note (a coder must see them)
    pressure: tuple[str, ...] = ()  # payer-side pressure points the claim creates (needs_auth, no_auth_on_file, bundle_pair, late_billing, ...)
    status: str = ""  # new | established | "" (emergency and preventive notes do not say) | unclear when the note never says
    laterality: str = ""  # LT | RT | "" (not needed, or not documented)
    minutes: int = 0  # documented minutes of the timed service (0 when none or not documented)
    units: int = 1  # billable units of the timed service (15-minute units follow the 8-minute rule), 1 otherwise
    auth_on_file: bool | None = None  # None: no authorization needed in the story; True or False: the practice did or did not obtain one
    lapsed: bool = False  # the patient's coverage has lapsed
    other_primary: bool = False  # the patient has other insurance that is primary
    bill_delay_days: int = 0  # the claim is held this long after the visit before it is sent (late billing)
    duplicate_of: int = 0  # 1-based number of the earlier visit this one repeats (same patient, day and services)


@dataclass
class Visit:
    visit_id: str
    member: str
    visit_type: str
    text: str
    signed: bool
    expected: Expected | None = None  # the answer key; a transcript someone typed in has none
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


# ====================================================================================================== generate_wide (S6)
# Visits across the whole catalog, with a configurable, independent mix of documentation defects and payer-side pressure.
DEFAULT_MIX: dict[str, float] = {
    # documentation defects (at most one per visit; each only where it can happen)
    "missing_plan": 0.03, "two_problems": 0.03, "status_unclear": 0.025, "unsigned": 0.03, "thin_chronic": 0.04,
    "missing_laterality": 0.30, "missing_time": 0.15, "missing_necessity": 0.12,  # (these three only where the visit has a side, a timed service, or a test to justify)
    # payer-side pressure (each drawn independently, so several can meet in one visit)
    "auth_service": 0.10,  # a service that payers often put behind prior authorization (MRI, CT, therapy series)
    "auth_on_file": 0.60,  # ... and the share of those where the practice obtained the authorization
    "bundle_pair": 0.07,  # two codes payers commonly bundle
    "necessity_mismatch": 0.04,  # a test whose usual supporting diagnosis is not the visit's diagnosis
    "old_dos": 0.04,  # the claim is sent late (60 to 120 days after the visit)
    "duplicate": 0.03,  # the same patient, day and services as an earlier visit
    "lapsed": 0.05, "other_primary": 0.03,
    "new_patient": 0.25,
}  # fmt: skip
SPECIALTY_WEIGHT = {"primary care": 3.0, "emergency": 0.7}  # everything else weighs 1.0
LEGACY_COMPLAINT = {"J02.9": COMPLAINT["sore_throat"], "M54.50": COMPLAINT["back_pain"], "N39.0": COMPLAINT["uti"], "I10": COMPLAINT["hypertension"],
                    "E11.9": COMPLAINT["diabetes_followup"], "R05.9": COMPLAINT["new_cough"], "M25.569": "my {side} knee has been hurting"}  # fmt: skip
LEGACY_SERVICES = {"J02.9": ("87880",), "M54.50": ("72100",), "N39.0": ("81002", "87086"), "I10": ("80053",), "E11.9": ("83036", "80053"),
                   "R05.9": ("71046",), "M25.569": ("73560",)}  # fmt: skip
PART = {"M25.569": "knee", "M25.519": "shoulder", "M17.9": "knee", "S93.409A": "ankle", "M79.609": "arm", "S61.419A": "hand", "H66.90": "ear"}
AUTH_CONDITIONS = ("M54.16", "M17.9", "M54.2", "R51.9", "S06.0X0A")
AUTH_SERVICES = ("72148", "70450", "97110", "97112", "97140", "97530")
NECESSITY_TESTS = ("83036", "93000", "84443", "80061", "71046", "94010")
EM = {("established", "straight"): "99212", ("established", "low"): "99213", ("established", "moderate"): "99214", ("established", "high"): "99215",
      ("new", "straight"): "99202", ("new", "low"): "99203", ("new", "moderate"): "99204", ("new", "high"): "99205"}  # fmt: skip
DEPTH = {"straight": (1, 1), "low": (2, 1), "moderate": (4, 3), "high": (4, 3)}  # (HPI components, exam systems)

OPENING = {
    "new": ["Provider: Is this your first visit with us? Patient: Yes, this is my first time here.",
            "Provider: Welcome, I do not see a chart for you. Are you new to the practice? Patient: Yes, I am a new patient.",
            "Provider: Thanks for coming in. Have you been seen at this office? Patient: No, I have never been seen here."],
    "established": ["Provider: You were last here a few months ago, correct? Patient: Yes, that is right, I am a returning patient.",
                    "Provider: Good to see you again. When were you last here? Patient: My last visit was back in the spring.",
                    "Provider: Welcome back. Patient: Thanks, I am a returning patient and was last seen by you in the summer."],
    "unclear": ["Provider: Good morning, let us get started.", "Provider: Come on in and have a seat.", "Provider: Hello, how are you today? Patient: Fine, thanks."],
    "emergency": ["Provider: You are being seen in the emergency department. Tell me what happened tonight.",
                  "Provider: I am the emergency physician on call. The nurse tells me you came in a short while ago."],
}
HPI_WIDE = {
    "onset": ["It started after a long trip.", "It began suddenly one morning.", "It started slowly.", "It began last weekend."],
    "duration": ["It has been going on for three days.", "I have had it for about two weeks.", "It has lasted over a week.", "It has been there for several months."],
    "severity": ["It is about a 6 out of 10.", "I would say it is moderate.", "It is severe at night.", "It is mild but constant."],
    "location": ["It is mostly in my lower back.", "I feel it in my chest.", "It is on the left side.", "I feel it in my throat."],
    "associated": ["I also have a bit of fever.", "Along with it I feel fatigue.", "I also have had some chills.", "I also notice a headache."],
    "modifying": ["It gets worse when I lie down.", "It is worse when I move.", "It is better with rest.", "It gets worse at night."],
}  # fmt: skip
EXAM_WIDE = {
    "primary care": ["Throat shows mild erythema without exudate.", "Neck is supple, no lymph nodes felt.", "Lungs are clear to auscultation.", "Heart has a regular rate and rhythm.",
                     "Abdomen is soft and not tender.", "Ears show clear canals and normal drums.", "Skin is warm and dry without rash.", "Extremities show no edema."],
    "orthopedics": ["Back has no spinal tenderness.", "Extremities show full strength and intact sensation.", "Skin over the joint is intact without redness.", "Neck has mild paraspinal tenderness."],
    "cardiology": ["Heart has a regular rate and rhythm with no murmur.", "Lungs are clear to auscultation.", "Extremities show trace edema.", "Neck has no jugular distension."],
    "pulmonology": ["Lungs show scattered wheezes.", "Throat is clear.", "Heart has a regular rate and rhythm.", "Neck shows no accessory muscle use."],
    "dermatology": ["Skin shows the lesion described, without surrounding redness.", "Extremities show no other lesions.", "Neck has no lymph nodes felt.", "Back skin is clear."],
    "mental health": ["Mental status: alert and oriented, mood low, thought process linear.", "Heart has a regular rate and rhythm.", "Neck is supple.", "Eyes are clear and tracking."],
    "obstetrics and gynecology": ["Abdomen is soft and not tender.", "Heart has a regular rate and rhythm.", "Back has no spinal tenderness.", "Lungs are clear to auscultation."],
    "pediatrics": ["Ears show clear canals and normal drums.", "Throat is mildly red.", "Lungs are clear to auscultation.", "Heart has a regular rate and rhythm.", "Abdomen is soft and not tender."],
    "emergency": ["Neck is supple with no tenderness.", "Lungs are clear to auscultation.", "Heart has a regular rate and rhythm.", "Abdomen is soft and not tender.",
                  "Skin is warm and pink.", "Extremities show good pulses.", "Eyes track normally."],
}  # fmt: skip
PLAN_WIDE = ["We will start treatment today and I will see you back in two weeks.", "I will prescribe medication and order labs; follow up in one month.",
             "Rest, fluids, and return in a week if it is not better.", "Continue current medicines, recheck in three months, call sooner if it worsens.",
             "We will adjust the dose today and see you back in six weeks."]  # fmt: skip
ASSESS_TAIL = ["", "", ", stable", ", not at goal", ", improving", ", with a flare"]
INDICATION = ["Indication: {kw}, to look for the cause.", "The reason for this is ongoing {kw}.", "Ordered because of persistent {kw}."]
INDICATION_WEAK = ["Indication: routine screening.", "Ordered to be thorough."]
DRUGS = ["ketorolac", "ceftriaxone", "diphenhydramine", "methylprednisolone"]


def _kw(rng: random.Random, words: tuple[str, ...], default: str) -> str:
    return rng.choice(words) if words else default


def _service_sentence(rng: random.Random, svc, *, side: str, part: str, minutes: int, indication: str) -> str:  # noqa: ANN001
    kw = _kw(rng, svc.keywords, svc.name.lower())
    where = f" on the {side} {part}" if side else ""
    if svc.cpt == "96372":
        return f"I gave an injection of {rng.choice(DRUGS)} in the office today."
    if svc.family == "lab":
        text = rng.choice([f"We will check a {kw} today.", f"Orders: {kw}.", f"I am ordering a {kw} today."])
    elif svc.family == "imaging":
        text = rng.choice([f"I am ordering a {kw}{where}.", f"Orders: {kw}{where}.", f"We will get a {kw}{where} today."])
        text += f" {indication}" if indication else ""
    elif svc.family == "injection":
        text = rng.choice([f"{kw.capitalize()} done today{where}.", f"We gave the {kw}{where} after verbal consent.", f"Procedure: {kw}{where}."])
    elif svc.needs_time:
        if minutes:
            text = rng.choice([f"Treatment today: {kw}, {minutes} minutes.", f"We spent {minutes} minutes on {kw}.", f"{kw.capitalize()} for {minutes} minutes."])
        else:
            text = rng.choice([f"We did {kw} today.", f"Today's treatment was {kw}."])
    else:
        text = rng.choice([f"Procedure performed today: {kw}{where}.", f"We did a {kw} in the office today{where}.", f"Procedure note: {kw}{where} completed without complication."])
        text += f" {indication}" if indication and svc.needs_indication else ""
    return text


def _pick_condition(rng: random.Random, only: tuple[str, ...] = ()):  # noqa: ANN202
    from krisnnai.live.catalog import CONDITIONS

    pool = [c for c in CONDITIONS if not only or c.icd10 in only]
    weights = [SPECIALTY_WEIGHT.get(c.specialty, 1.0) for c in pool]
    return rng.choices(pool, weights=weights, k=1)[0]


def generate_wide(seed: int = 7, n: int = 100, start: date = date(2026, 10, 24), mix: dict[str, float] | None = None) -> list[Visit]:
    """`n` visits over the whole catalog (see catalog.py), deterministic for a seed. `mix` overrides `DEFAULT_MIX` per key; every key
    is an independent chance per visit, so the share of problem visits varies with the seed and the mix (it is not a fixed 20%).
    Each visit's `expected` says what a correct reading is and which problems and payer pressure points the story contains."""
    from krisnnai.knowledge.demo import SUPPORT
    from krisnnai.live.catalog import COMMON_BUNDLES, CONDITIONS, service_by_cpt

    m = {**DEFAULT_MIX, **(mix or {})}
    out: list[Visit] = []
    for i in range(1, n + 1):
        rng = random.Random(f"wide:{seed}:{i}")
        flags = {k: rng.random() < p for k, p in m.items() if k not in ("auth_on_file",)}  # a fixed draw order: the mix changes the odds, not which draw is used

        # ---- the story: condition, status, level, services
        cond = _pick_condition(rng)
        bundle: tuple[str, str] | None = None
        auth_cpt = ""
        if flags["bundle_pair"]:
            bundle = rng.choice(COMMON_BUNDLES)
            fit = tuple(c.icd10 for c in CONDITIONS if bundle[0] in (c.services or LEGACY_SERVICES.get(c.icd10, ())))
            if fit:
                cond = _pick_condition(rng, fit)
        elif flags["auth_service"]:
            cond = _pick_condition(rng, AUTH_CONDITIONS)
            choices = [s for s in (cond.services or LEGACY_SERVICES.get(cond.icd10, ())) if s in AUTH_SERVICES]
            auth_cpt = rng.choice(choices) if choices else "72148"
        kind = cond.visit_kind
        status = "" if kind == "emergency" else ("new" if rng.random() < (0.15 if kind == "preventive" else m["new_patient"]) else "established")
        if bundle and bundle[1] == "99213":
            status = "established"
        level = "moderate" if cond.chronic else "low"
        r = rng.random()
        if bundle and bundle[1] == "99213":
            level = "low"
        elif not cond.chronic and r < 0.12:
            level = "straight"
        elif cond.chronic and r < 0.12:
            level = "high"
        elif not cond.chronic and r < 0.22:
            level = "moderate"
        if kind == "emergency":
            em = rng.choices(["99283", "99284", "99285"], weights=[5, 3.5, 1.5])[0]
            level = {"99283": "moderate", "99284": "high", "99285": "high"}[em]
        elif kind == "preventive":
            em = "99393" if cond.age == "child" else ("99385" if status == "new" else rng.choice(["99395", "99396"]))
            if cond.icd10 == "Z23":  # a vaccine-only visit is a nurse visit
                em = "99211"
        else:
            em = EM[(status, level)]
        if cond.icd10 == "Z23":
            level = "straight"
        typical = cond.services or LEGACY_SERVICES.get(cond.icd10, ())
        extra: list[str] = []
        if bundle:
            extra = [bundle[0]] + ([bundle[1]] if bundle[1] != "99213" else [])
            if bundle[1] == "99213":
                em = "99213"
        else:
            if auth_cpt:
                extra.append(auth_cpt)
            if typical and rng.random() < 0.55:
                extra.append(rng.choice(typical))
            if typical and rng.random() < 0.15:
                extra.append(rng.choice(typical))
            if flags["necessity_mismatch"]:
                bad = [c for c in NECESSITY_TESTS if not any(cond.icd10.replace(".", "").startswith(p) for p in SUPPORT[c])]
                if bad:
                    extra.append(rng.choice(bad))
        services = tuple(dict.fromkeys([em, *extra]))
        svc_objs = [s for s in (service_by_cpt(c) for c in services) if s is not None]
        timed = [s for s in svc_objs if s.needs_time]
        needs_lat = cond.needs_laterality
        side = rng.choice(["left", "right"]) if needs_lat else ""
        part = PART.get(cond.icd10, "knee")
        second = None
        has_ind = [s for s in svc_objs if s.needs_indication]

        # ---- one documentation defect at most, each only where it can happen
        defect = ""
        applicable = {
            "missing_plan": True, "two_problems": True, "status_unclear": status in ("new", "established"), "unsigned": True,
            "thin_chronic": cond.chronic and level in ("moderate", "high") and kind == "", "missing_laterality": needs_lat,
            "missing_time": bool(timed), "missing_necessity": bool(has_ind),
        }  # fmt: skip
        for key, ok in applicable.items():
            if ok and rng.random() < m.get(key, 0.0):
                defect = key
                break
        signed, plan = defect != "unsigned", defect != "missing_plan"
        hpi_n, sys_n = DEPTH[level]
        if kind == "preventive":
            hpi_n, sys_n = 3, 3
        if defect == "thin_chronic":
            hpi_n, sys_n = 2, 1
        if defect == "two_problems":
            second = _pick_condition(rng)
            while second.icd10 == cond.icd10:
                second = _pick_condition(rng)
            hpi_n, sys_n = 4, 3
        show_side = side if defect != "missing_laterality" else ""
        minutes = 0
        units = 1
        if timed:
            t = timed[0]
            lo, hi = t.time_range
            minutes = rng.randint(lo, hi)
            if t.unit == "15 minutes":
                units = max(1, (minutes + 7) // 15)
        if defect == "missing_time":
            minutes, units = 0, 0

        # ---- the text
        who = "unclear" if defect == "status_unclear" else status or "emergency"
        complaint = (cond.complaint or LEGACY_COMPLAINT.get(cond.icd10) or f"I have been having {cond.keywords[0]}").replace("{side}", show_side or "")
        complaint = complaint.replace("  ", " ")
        side_line = f" It is my {show_side} {part}." if show_side and "{side}" not in (cond.complaint or LEGACY_COMPLAINT.get(cond.icd10, "")) else ""
        comps = rng.sample(list(HPI_WIDE), hpi_n)
        hpi = " ".join(rng.choice(HPI_WIDE[c]) for c in comps)
        pool = EXAM_WIDE.get(cond.specialty, EXAM_WIDE["primary care"])
        if kind == "preventive":
            pool = EXAM_WIDE["primary care"]
        exam = " ".join(rng.sample(pool, min(sys_n, len(pool))))
        if sys_n > len(pool):
            exam += " " + " ".join(rng.sample(EXAM_WIDE["primary care"], sys_n - len(pool)))
        dx_text = (f"{show_side} " if show_side else "") + cond.keywords[0]
        assess = f"Assessment: {dx_text}{rng.choice(ASSESS_TAIL)}"
        if second is not None:
            assess += f" and {second.keywords[0]}"
        parts = ["[Synthetic visit transcript]", rng.choice(OPENING[who]),
                 f"Provider: What brings you in today? Patient: {complaint}.{side_line} {hpi}",
                 f"Provider: Let me examine you. Exam: {exam}", f"Provider: {assess}."]  # fmt: skip
        if plan:
            parts.append(f"Provider: Plan: {rng.choice(PLAN_WIDE)}")
        if level == "high" and kind != "preventive":
            parts.append("Provider: I reviewed the outside records and results, and we discussed the risk of hospital admission if this worsens.")
        ind = "" if defect == "missing_necessity" else rng.choice(INDICATION_WEAK if flags["necessity_mismatch"] else INDICATION).format(kw=cond.keywords[0])
        sentences = []
        for s in svc_objs:
            if s.family in ("em_established", "em_new", "preventive", "emergency"):
                continue
            sentences.append(_service_sentence(rng, s, side=show_side if s.needs_laterality and needs_lat else "", part=part, minutes=0 if defect == "missing_time" else (minutes if s.needs_time else 0), indication=ind))
        if sentences:
            parts.append("Provider: Procedures and orders: " + " ".join(sentences))
        if signed:
            parts.append(f"Signed electronically by {PROVIDER}.")

        # ---- the answer key
        problems = (defect,) if defect else ()
        pressure: list[str] = []
        auth_needed = bool(auth_cpt) or any(c in AUTH_SERVICES for c in services)
        auth_state: bool | None = None
        if auth_needed:
            auth_state = rng.random() < m["auth_on_file"]
            pressure += ["needs_auth"] + ([] if auth_state else ["no_auth_on_file"])
        if bundle:
            pressure.append("bundle_pair")
        if flags["necessity_mismatch"]:
            pressure.append("necessity_mismatch")
        if cond.unspecified:
            pressure.append("unspecified_dx")
        if has_ind and defect == "missing_necessity":
            pressure.append("necessity_not_documented")
        delay = rng.randint(60, 120) if flags["old_dos"] else 0
        if delay:
            pressure.append("late_billing")
        if flags["lapsed"]:
            pressure.append("coverage_lapsed")
        if flags["other_primary"]:
            pressure.append("other_primary")
        route, reason = ("coder", defect) if defect else ("auto", "")
        dx_all = (cond.icd10,) + ((second.icd10,) if second is not None else ())
        lat = ("LT" if side == "left" else "RT") if show_side else ""
        exp = Expected(em, cond.icd10, route, reason, services, dx_all, problems, tuple(pressure), "" if kind in ("emergency",) else ("unclear" if defect == "status_unclear" else status),
                       lat, minutes, units, auth_state, flags["lapsed"], flags["other_primary"], delay)  # fmt: skip
        out.append(Visit(f"SYNVW{i:05d}L1", f"SYNLW{i:05d}", f"wide_{cond.icd10}", "\n".join(parts), signed, exp, start + timedelta(days=(i - 1) // 5)))

    # ---- duplicates: a later visit repeats an earlier, clean, on-time one (same patient, day and services)
    dup_rng = random.Random(f"wide-dup:{seed}")
    for i, v in enumerate(out, start=1):
        if i > 1 and random.Random(f"wide:{seed}:{i}:dup").random() < m["duplicate"]:
            cands = [j for j in range(max(1, i - 15), i) if out[j - 1].expected.route == "auto" and not out[j - 1].expected.duplicate_of and out[j - 1].signed and out[j - 1].expected.bill_delay_days == 0 and not out[j - 1].expected.lapsed and not out[j - 1].expected.other_primary]
            if not cands:
                continue
            j = dup_rng.choice(cands)
            o = out[j - 1]
            e = o.expected
            out[i - 1] = Visit(v.visit_id, o.member, o.visit_type, o.text, True,
                               Expected(e.cpt, e.dx, "auto", "", e.services, e.dx_all, (), (*e.pressure, "duplicate"), e.status, e.laterality, e.minutes, e.units,
                                        e.auth_on_file, False, e.other_primary, 0, j), o.day)  # fmt: skip
    return out
