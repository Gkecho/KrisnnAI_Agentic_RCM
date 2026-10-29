# ruff: noqa: E501
"""Payer Knowledge Book v1: where agents look up insurance rules, with versions, effective dates and honest gaps.

Each rule is a record (payer, plan, state, service, family, effective dates, the date it is judged on, source, version), not
an uploaded document. Lookup is point in time: it answers "what did the book say on `as_of`, for an event on this date".
It never guesses. A missing rule, two rules that disagree, an unknown plan or state that matters, a missing event date or a
fact marked unknown all come back as a `Problem` naming an owner and what to ask, never as an answer.

v1 holds a small demo ruleset (see demo.py), labelled as client-confirmed demo rules, not official payer policy.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path

FAMILIES = ("coverage", "prior_auth", "medical_necessity", "billing", "denial_appeal")
DATE_BASES = ("service_date", "denial_notification_date", "claim_submission_date")
OWNER = "payer_rules_owner"


@dataclass(frozen=True)
class Source:
    kind: str  # demo | public | contract | client
    title: str
    url: str = ""


@dataclass(frozen=True)
class Rule:
    rule_id: str
    version: int
    payer: str
    family: str
    effective_from: date
    date_basis: str  # which event date the effective range is tested against
    source: Source
    content: dict
    active_from: date  # when the book began to know this version (point-in-time replay)
    effective_to: date | None = None
    plan: str = "*"
    state: str = "*"
    service: str = "*"  # a CPT, or "*" for every service
    unknown: tuple[str, ...] = ()  # content fields nobody has confirmed
    retired_on: date | None = None
    note: str = ""

    @property
    def specificity(self) -> int:
        return (self.plan != "*") + (self.state != "*") + (self.service != "*")


@dataclass(frozen=True)
class Problem:
    """Why the book will not answer. A person with this owner must supply or confirm the fact."""

    kind: str  # no_rule | conflict | unknown_fact | missing_date
    message: str
    ask: str
    owner: str = OWNER
    context: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Found:
    rule: Rule | None = None
    problem: Problem | None = None

    @property
    def ok(self) -> bool:
        return self.rule is not None


class BookError(ValueError):
    pass


def _could_apply(r: Rule, dates: dict[str, date]) -> bool:
    """False only when the event date is known and falls outside this version's effective range."""
    when = dates.get(r.date_basis)
    return when is None or (r.effective_from <= when and (r.effective_to is None or when <= r.effective_to))


class Book:
    def __init__(self) -> None:
        self.rules: list[Rule] = []

    # ------------------------------------------------------------------------------------------------ editing
    def add(self, rule: Rule) -> Rule:
        """Add a version. Old versions are kept; a new version needs the next number for its rule id."""
        if rule.family not in FAMILIES:
            raise BookError(f"unknown family {rule.family!r}")
        if rule.date_basis not in DATE_BASES:
            raise BookError(f"unknown date basis {rule.date_basis!r}")
        if rule.effective_to is not None and rule.effective_to < rule.effective_from:
            raise BookError("effective_to is before effective_from")
        have = [r.version for r in self.rules if r.rule_id == rule.rule_id]
        if rule.version != (max(have) + 1 if have else 1):
            raise BookError(f"{rule.rule_id}: the next version is {max(have) + 1 if have else 1}, not {rule.version}")
        self.rules.append(rule)
        return rule

    def retire(self, rule_id: str, version: int, on: date) -> None:
        for i, r in enumerate(self.rules):
            if r.rule_id == rule_id and r.version == version:
                self.rules[i] = Rule(**{**r.__dict__, "retired_on": on})
                return
        raise BookError(f"no such rule {rule_id} v{version}")

    def history(self, rule_id: str) -> list[Rule]:
        return sorted((r for r in self.rules if r.rule_id == rule_id), key=lambda r: r.version)

    # ------------------------------------------------------------------------------------------------ lookup
    def lookup(self, payer: str, family: str, service: str, dates: dict[str, date], as_of: date, plan: str | None = None,
               state: str | None = None) -> Found:  # fmt: skip
        """The rule in force. `dates` holds the event dates the caller knows (service_date, denial_notification_date, ...)."""
        ctx = {"payer": payer, "family": family, "service": service, "plan": plan, "state": state, "as_of": as_of.isoformat()}
        known = [r for r in self.rules if r.payer == payer and r.family == family and r.active_from <= as_of
                 and (r.retired_on is None or as_of < r.retired_on)]  # fmt: skip
        in_scope = [r for r in known if r.service in ("*", service)]
        # without a confirmed plan or state, a rule that names one cannot be ruled in or out
        unsure_scope = [r for r in in_scope if ((r.plan != "*" and plan is None) or (r.state != "*" and state is None))
                        and _could_apply(r, dates)]  # fmt: skip
        in_scope = [r for r in in_scope if (r.plan in ("*", plan)) and (r.state in ("*", state))]
        current: dict[str, Rule] = {}
        for rid in {r.rule_id for r in in_scope}:
            versions = [r for r in in_scope if r.rule_id == rid]
            basis = versions[0].date_basis
            if any(v.date_basis != basis for v in versions):
                return Found(problem=Problem("conflict", f"{rid} changes its date basis between versions",
                                             f"Confirm which event date governs {rid}", context=ctx))
            when = dates.get(basis)
            if when is None:
                return Found(problem=Problem("missing_date", f"{family} for {payer} is judged on the {basis}, which is not known",
                                             f"Supply the {basis}", context={**ctx, "needs": basis}))
            live = [v for v in versions if v.effective_from <= when]
            if not live:
                continue
            top = max(live, key=lambda v: (v.effective_from, v.version))
            if top.effective_to is None or when <= top.effective_to:
                current[rid] = top
        if not current:
            if unsure_scope:
                return Found(problem=Problem("unknown_fact", "a rule exists for a specific plan or state, which is not known",
                                             "Confirm the patient's plan and state", context=ctx))
            return Found(problem=Problem("no_rule", f"no {family} rule for {payer} / {service} in force on that date",
                                         f"Add or confirm the {family} rule for {payer}, service {service}", context=ctx))
        best = max(r.specificity for r in current.values())
        top_rules = [r for r in current.values() if r.specificity == best]
        if len(top_rules) > 1:
            ids = sorted(r.rule_id for r in top_rules)
            return Found(problem=Problem("conflict", f"rules {', '.join(ids)} overlap with equal scope",
                                         "Decide which rule applies and retire the other", context={**ctx, "rules": ids}))
        chosen = top_rules[0]
        if chosen.plan == "*" and chosen.state == "*" and unsure_scope:
            return Found(problem=Problem("unknown_fact", "a more specific plan or state rule might override this general one",
                                         "Confirm the patient's plan and state", context=ctx))
        return Found(rule=chosen)

    # ------------------------------------------------------------------------------------------------ storage
    def to_json(self) -> str:
        def enc(o):  # noqa: ANN001
            return o.isoformat() if isinstance(o, date) else list(o) if isinstance(o, tuple) else str(o)

        return json.dumps([asdict(r) for r in self.rules], default=enc, indent=1)

    @classmethod
    def from_json(cls, text: str) -> Book:
        b = cls()
        for d in json.loads(text):
            for k in ("effective_from", "effective_to", "active_from", "retired_on"):
                d[k] = date.fromisoformat(d[k]) if d.get(k) else None
            d["source"] = Source(**d["source"])
            d["unknown"] = tuple(d.get("unknown") or ())
            b.rules.append(Rule(**d))
        return b

    def save(self, path: Path) -> None:
        path.write_text(self.to_json(), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> Book:
        return cls.from_json(path.read_text(encoding="utf-8"))
