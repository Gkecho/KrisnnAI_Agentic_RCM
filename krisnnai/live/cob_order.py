# ruff: noqa: E501
"""Coverage-order review: does the order the front desk entered look right?

The system never decides who pays first, and never changes the order. It reads the order entered in the EMR and raises a finding
where a well-known rule points the other way. A finding goes to the front desk as a coordination-of-benefits review (the same
Gatekeeper gap as "another payer says it is primary"); the person confirms with the patient or the payer.

Rules here are general COB knowledge for a first demo and must be confirmed by the client's compliance team and each payer:
  * Medicaid pays last, after every other coverage.
  * Medicare listed first while another plan exists: Medicare is primary only if there is no current-work employer plan, or the
    employer is small (about 20 employees by age, 100 by disability). Employment and employer size are not in the EMR: a person confirms.
  * A person's own employer plan normally comes before a plan held through a spouse or parent.
  * Child on two parents' plans: the parent whose birthday (month and day) falls first in the year is primary. A court order overrides this.
  * Workers' compensation or auto insurance pays first when the visit is for that injury.
  * The same payer and member twice is a duplicate entry.
The payer type is guessed from the payer's name (demo only); a real build would use the payer master. Demo data is synthetic.
"""

from __future__ import annotations

from datetime import date

from krisnnai.live.insurance import Policy

MEDICAID, MEDICARE, INJURY, COMMERCIAL = "medicaid", "medicare", "injury", "commercial"
KEYWORDS = (("MEDICAID", MEDICAID), ("MEDICARE", MEDICARE), ("WORKERS", INJURY), ("WORK COMP", INJURY), ("AUTO", INJURY))


def kind_of(pol: Policy) -> str:
    text = f"{pol.payer_name} {pol.payer_code}".upper()
    return next((k for word, k in KEYWORDS if word in text), COMMERCIAL)


def _birthday(dob: str) -> tuple[int, int] | None:
    try:
        d = date.fromisoformat(dob[:10])
    except ValueError:
        return None
    return d.month, d.day


def check_order(policies: list[Policy]) -> list[dict]:
    """Findings about the order entered. `policies` is primary first, as the front desk entered them. Empty = nothing to review."""
    out: list[dict] = []

    def add(rule: str, pol: Policy, detail: str) -> None:
        out.append({"rule": rule, "payer": pol.payer_code, "order": pol.label, "detail": detail})

    if len(policies) < 2:
        return out  # one coverage has no order to get wrong
    kinds = [kind_of(p) for p in policies]
    for i, (p, k) in enumerate(zip(policies, kinds, strict=True)):
        later = kinds[i + 1 :]
        if k == MEDICAID and any(x != MEDICAID for x in later):
            add("medicaid_last", p, f"{p.payer_name} is Medicaid but is listed before another coverage; Medicaid normally pays last")
        if k == MEDICARE and i == 0 and any(x == COMMERCIAL for x in later):
            add("medicare_first", p, f"{p.payer_name} is listed first while another plan exists; confirm current employment and employer size before treating Medicare as primary")
        if k == INJURY and i > 0:
            add("injury_first", p, f"{p.payer_name} (workers' compensation or auto) pays first when the visit is for that injury; confirm the reason for the visit")
    own = [i for i, p in enumerate(policies) if p.relationship == "self" and kinds[i] == COMMERCIAL]
    dep = [i for i, p in enumerate(policies) if p.relationship in ("spouse", "child") and kinds[i] == COMMERCIAL]
    if own and dep and min(dep) < min(own):
        p = policies[min(dep)]
        add("own_plan_first", p, f"{p.payer_name} is held through a {p.relationship} but is listed before the patient's own plan; the patient's own employer plan normally comes first")
    kids = [p for p in policies if p.relationship == "child" and kind_of(p) == COMMERCIAL and _birthday(p.holder_dob)]
    if len(kids) >= 2:
        first, second = kids[0], kids[1]
        if _birthday(second.holder_dob) < _birthday(first.holder_dob):
            add("birthday_rule", first, f"for a child on both parents' plans the parent whose birthday comes first in the year is primary; {second.payer_name} (policyholder {second.holder_first} {second.holder_last}) looks earlier than {first.payer_name}. A court order can override this")
    seen: set[tuple[str, str]] = set()
    for p in policies:
        if (p.payer_code, p.member) in seen:
            add("duplicate_policy", p, f"{p.payer_name} member {p.member} is entered more than once")
        seen.add((p.payer_code, p.member))
    return out
