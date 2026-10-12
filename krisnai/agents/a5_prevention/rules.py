"""A5 deterministic pre-release checks (rule 6: rules first). Pure functions over a claim snapshot dict.

Each returns a RuleResult (result True = the check passed). Nothing here edits a code or a claim (rule 4).
The snapshot carries the rule data it needs (filing days, NCCI pairs, MUE limits), so a decision record is
self-contained. Eligibility on the date of service and authorization units need 270/271 and authorization data that
the repo does not have yet, so they are reported as not evaluated rather than guessed.
"""

from __future__ import annotations

from collections import Counter
from datetime import date, timedelta
from itertools import combinations

from krisnai.agents.a5_prevention.config import FILING_WARN_DAYS
from krisnai.engine import RuleResult

NOT_EVALUATED = ("eligibility_on_dos", "auth_units")


def required_fields(c: dict) -> RuleResult:
    missing = []
    if not c["service_date"]:
        missing.append("service_date")
    if not c["lines"]:
        missing.append("lines")
    if not c["diagnoses"]:
        missing.append("diagnoses")
    for ln in c["lines"]:
        if not ln["cpt"]:
            missing.append(f"line {ln['line_number']} cpt")
        if not ln["diagnosis_pointer"]:
            missing.append(f"line {ln['line_number']} diagnosis_pointer")
    return RuleResult("required_fields", not missing, ", ".join(missing) or "all present")


def duplicate_claim(c: dict) -> RuleResult:
    dupes = c["duplicates"]
    detail = f"same patient, payer, date and codes as {dupes}" if dupes else "none"
    return RuleResult("duplicate_claim", not dupes, detail)


def timely_filing(c: dict) -> RuleResult:
    if not c["service_date"]:
        return RuleResult("timely_filing", False, "no service date to count from")
    days = c["filing_days"]
    deadline = date.fromisoformat(c["service_date"]) + timedelta(days=days)
    left = (deadline - date.fromisoformat(c["as_of"])).days
    return RuleResult("timely_filing", left >= FILING_WARN_DAYS, f"{left} days left of {days} (deadline {deadline})")


def ncci_without_modifier(c: dict) -> RuleResult:
    hits = []
    for a, b in combinations(c["lines"], 2):
        if a["service_date"] != b["service_date"]:
            continue
        indicator = c["ncci"].get("|".join(sorted((a["cpt"], b["cpt"]))))
        if indicator is None:
            continue
        if indicator == "0":
            hits.append(f"{a['cpt']}+{b['cpt']} (never together)")
        elif not (a["modifiers"] or b["modifiers"]):
            hits.append(f"{a['cpt']}+{b['cpt']} (no modifier)")
    return RuleResult("ncci_pair", not hits, "; ".join(hits) or "no conflicting pair")


def mue_units(c: dict) -> RuleResult:
    units: Counter = Counter()
    for ln in c["lines"]:
        units[(ln["cpt"], ln["service_date"])] += int(float(ln["units"]))
    over = [
        f"{cpt} {u}>{c['mue'][cpt]}" for (cpt, _), u in sorted(units.items()) if cpt in c["mue"] and u > c["mue"][cpt]
    ]
    return RuleResult("mue_units", not over, "; ".join(over) or "within limits")


def run_all(c: dict) -> list[RuleResult]:
    return [required_fields(c), duplicate_claim(c), timely_filing(c), ncci_without_modifier(c), mue_units(c)]
