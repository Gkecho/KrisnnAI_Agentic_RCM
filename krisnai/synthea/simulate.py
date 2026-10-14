"""A seeded payer simulator: bills Synthea bundles, plants known problems, writes X12 files and a ground truth.

Same planted problems as tests/fixtures/make_synthetic.py (denial, timely filing, underpayment, rejection, unbilled
visit), plus claims that are simply still unpaid or stuck. Payers differ in fee level and days to pay. Nothing is chosen
because it is unpaid: payment timing decides what is open at `as_of`, so a forecast made earlier can be scored fairly.
"""

from __future__ import annotations

import csv
import random
from collections import Counter
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from krisnai.synthea.crosswalk import CPT_BASE_FEE
from krisnai.synthea.documentation import CHARGE_COLUMNS, NOTE_COLUMNS, TRUTH_COLUMNS, DocPlan
from krisnai.synthea.types import (
    BILLED_MARKUP,
    PATIENT_SHARE,
    Bundle,
    PayerInfo,
    SimClaim,
    SimLine,
    SimVisit,
    money,
)
from krisnai.synthea.x12out import DENIAL_RARC, write_277ca, write_835, write_837, write_999

APPEAL_WINDOW_DAYS = 180
TIMELY_FILING_DAYS = 365
LATE_SUBMIT_DAYS = 380  # a timely-filing loss is submitted this long after the visit
SHARES = {  # share of billed claims
    "denial": Decimal("0.09"), "underpayment": Decimal("0.08"), "rejection": Decimal("0.02"),
    "timely_filing": Decimal("0.025"),
}  # fmt: skip
UNBILLED_SHARE = Decimal("0.03")
STUCK_SHARE = 0.10
TIMELY_CARC = "29"
GROUND_TRUTH_COLUMNS = [
    "issue_id", "issue_type", "claim_id", "visit_id", "line_no", "payer_id", "cpt", "carc",
    "expected_amount", "status", "reason",
]  # fmt: skip


@dataclass(frozen=True)
class RateCut:
    """From `start`, `payer_id` pays `percent` % less than the contract on `cpt` (a planted payer-wide change)."""

    payer_id: str
    cpt: str
    start: date
    percent: Decimal


def parse_rate_cut(text: str) -> RateCut:
    payer, cpt, start, percent = text.split(":")
    return RateCut(payer, cpt, date.fromisoformat(start), Decimal(percent))


def fee(payer: PayerInfo, cpt: str) -> Decimal:
    return money(CPT_BASE_FEE[cpt] * payer.fee_multiplier)


def _make_claim(b: Bundle, rng: random.Random) -> SimClaim:
    lines = [
        SimLine(cpt=cpt, units=units, billed=money(CPT_BASE_FEE[cpt] * units * BILLED_MARKUP),
                allowed=fee(b.payer, cpt) * units)
        for cpt, units in b.cpts
    ]  # fmt: skip
    submitted = b.dos + timedelta(days=rng.randint(2, 10))
    return SimClaim(b.claim_id, b.payer, b.provider_npi, b.patient, b.dos, b.dx, lines, submitted)


def _settle(c: SimClaim) -> None:
    for i, ln in enumerate(c.lines):
        if c.scenario in ("denial", "timely_filing"):
            ln.paid, ln.pr = Decimal("0"), Decimal("0")
            ln.cas = [("CO", c.carc, ln.billed)]
            continue
        short = (c.shortfall if c.shortfall_line == i else Decimal("0")) + ln.cut
        ln.pr = money(ln.allowed * PATIENT_SHARE)
        ln.paid = ln.allowed - ln.pr - short
        ln.cas = [("CO", "45", ln.billed - ln.allowed + short), ("PR", "2", ln.pr)]


def simulate(
    bundles: list[Bundle], as_of: date, seed: int, rate_cuts: list[RateCut] | None = None
) -> tuple[list[SimClaim], list[SimVisit]]:
    rng = random.Random(seed)
    order = list(range(len(bundles)))
    rng.shuffle(order)
    n_unbilled = int(len(bundles) * UNBILLED_SHARE)
    unbilled = set(order[:n_unbilled])
    visits = [
        SimVisit(f"SYNV{k:05d}", b.payer, b.provider_npi, b.patient, b.dos, b.cpts[0][0], b.cpts[0][1])
        for k, i in enumerate(sorted(unbilled), start=1)
        for b in [bundles[i]]
    ]

    claims = [_make_claim(b, rng) for i, b in enumerate(bundles) if i not in unbilled]
    claims = [c for c in claims if c.submitted <= as_of]  # not yet sent by as_of: nobody knows about it
    pool = list(range(len(claims)))
    rng.shuffle(pool)
    counts = {k: max(1, int(len(claims) * s)) for k, s in SHARES.items()} if claims else {}
    plant: dict[int, str] = {}
    for name, cnt in counts.items():
        eligible = []
        for idx in pool:
            c = claims[idx]
            if idx in plant:
                continue
            if name == "timely_filing":
                if (as_of - c.dos).days < LATE_SUBMIT_DAYS + 10:
                    continue
            elif name == "rejection":
                if c.submitted + timedelta(days=2) > as_of:
                    continue  # the 277CA that rejects it is not back yet, so nobody knows
            elif c.submitted + timedelta(days=c.payer.pay_days + 4) > as_of:
                continue  # a denial or underpayment needs a payment that already happened
            eligible.append(idx)
        for idx in eligible[:cnt]:
            plant[idx] = name

    for idx, c in enumerate(claims):
        name = plant.get(idx, "clean")
        c.scenario = name
        pay_days = c.payer.pay_days + rng.randint(-4, 4)
        if name == "timely_filing":
            c.submitted = c.dos + timedelta(days=LATE_SUBMIT_DAYS)
            c.carc = TIMELY_CARC
            c.remit_date = min(c.submitted + timedelta(days=pay_days), as_of)
        elif name == "rejection":
            c.remit_date = None
        else:
            c.remit_date = c.submitted + timedelta(days=pay_days)
            if name == "denial":
                c.carc = rng.choice(sorted(DENIAL_RARC))
            elif name == "underpayment":
                c.shortfall_line = rng.randrange(len(c.lines))
                target = c.lines[c.shortfall_line]
                c.shortfall = max(Decimal("1.00"), money(target.expected_pay * Decimal(rng.randint(15, 40)) / 100))
            elif rng.random() < STUCK_SHARE:
                c.scenario, c.remit_date = "open", None  # the payer never pays it
        if c.remit_date is not None and c.remit_date > as_of:
            c.scenario, c.remit_date = "open", None  # not paid yet at as_of
        if c.remit_date is not None and c.scenario in ("clean", "underpayment"):
            for ln in c.lines:
                for cut in rate_cuts or []:
                    if cut.payer_id == c.payer.payer_id and cut.cpt == ln.cpt and c.remit_date >= cut.start:
                        ln.cut = money(ln.allowed * cut.percent / 100)
        if c.scenario not in ("open", "rejection") or c.remit_date is not None:
            _settle(c)
    return claims, visits


def ground_truth(claims: list[SimClaim], visits: list[SimVisit], as_of: date) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    def add(kind, claim_id, visit_id, line_no, payer, cpt, carc, amount, recoverable, why):
        rows.append({
            "issue_id": f"GT{len(rows) + 1:04d}", "issue_type": kind, "claim_id": claim_id, "visit_id": visit_id,
            "line_no": line_no, "payer_id": payer.payer_id, "cpt": cpt, "carc": carc,
            "expected_amount": f"{amount:.2f}", "status": "recoverable" if recoverable else "structural", "reason": why,
        })  # fmt: skip

    for c in claims:
        if c.scenario in ("denial", "timely_filing"):
            amount = sum((ln.expected_pay for ln in c.lines), Decimal("0"))
            age = (as_of - c.remit_date).days
            if c.scenario == "timely_filing":
                add("timely_filing", c.claim_id, "", "", c.payer, "", c.carc, amount, False,
                    "CARC 29 timely filing loss")  # fmt: skip
            else:
                add("denial", c.claim_id, "", "", c.payer, "", c.carc, amount, age <= APPEAL_WINDOW_DAYS,
                    f"denied {age}d before as_of, appeal window {APPEAL_WINDOW_DAYS}d")  # fmt: skip
        elif c.scenario in ("underpayment", "clean") and c.remit_date is not None:
            age = (as_of - c.remit_date).days
            for i, ln in enumerate(c.lines):
                planted = c.shortfall if c.scenario == "underpayment" and c.shortfall_line == i else Decimal("0")
                if planted + ln.cut <= 0:
                    continue
                why = f"paid {age}d before as_of" + (", payer-wide rate cut" if ln.cut else "")
                add("underpayment", c.claim_id, "", i + 1, c.payer, ln.cpt, "45", planted + ln.cut,
                    age <= APPEAL_WINDOW_DAYS, why)  # fmt: skip
        elif c.scenario == "rejection":
            amount = sum((ln.expected_pay for ln in c.lines), Decimal("0"))
            age = (as_of - c.dos).days
            add("rejection", c.claim_id, "", "", c.payer, "", "", amount, age <= TIMELY_FILING_DAYS,
                f"277CA rejected, DOS {age}d before as_of")  # fmt: skip
    for v in visits:
        age = (as_of - v.dos).days
        add("unbilled_visit", "", v.visit_id, "", v.payer, v.cpt, "", v.expected_pay, age <= TIMELY_FILING_DAYS,
            f"visit never billed, DOS {age}d before as_of")  # fmt: skip
    return rows


def _write_csv(path: Path, columns: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=columns, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def write_dir(
    claims: list[SimClaim], visits: list[SimVisit], out_dir: Path, as_of: date, doc: DocPlan | None = None
) -> dict[str, int]:
    """Write 837 / 999 / 277CA / 835 files plus fee_schedule.csv, visits.csv, ground_truth.csv and open_ar.csv.

    With a documentation plan, visits.csv lists every billed service too, and notes.csv, charges.csv and
    doc_truth.csv are written."""
    out_dir.mkdir(parents=True, exist_ok=True)
    counts: Counter = Counter()
    ctrl = 1000
    payers = {c.payer.payer_id: c.payer for c in claims}

    def put(name: str, text: str, kind: str) -> None:
        (out_dir / name).write_text(text, encoding="ascii", newline="")
        counts[kind] += 1

    for pid in sorted(payers):
        payer = payers[pid]
        mine = [c for c in claims if c.payer.payer_id == pid]
        for day in sorted({c.submitted for c in mine}):
            batch = [c for c in mine if c.submitted == day]
            ctrl += 1
            put(f"837P_{pid}_{day:%Y%m%d}.x12", write_837(payer, batch, ctrl, day), "837")
            if day + timedelta(days=1) <= as_of:
                put(f"999_{pid}_{day:%Y%m%d}.x12", write_999(payer, ctrl, ctrl + 100000, day + timedelta(days=1)),
                    "999")  # fmt: skip
            if day + timedelta(days=2) <= as_of:
                put(f"277CA_{pid}_{day:%Y%m%d}.x12",
                    write_277ca(payer, batch, ctrl + 200000, day + timedelta(days=2)), "277ca")  # fmt: skip
        by_remit: dict[date, list[SimClaim]] = {}
        for c in mine:
            if c.has_remit and c.remit_date is not None:
                by_remit.setdefault(c.remit_date, []).append(c)
        for remit_date in sorted(by_remit):
            ctrl += 1
            put(f"835_{pid}_{remit_date:%Y%m%d}.x12", write_835(payer, remit_date, by_remit[remit_date], ctrl + 300000),
                "835")  # fmt: skip

    fee_rows = [
        {"payer_id": p.payer_id, "cpt": cpt, "modifier": "", "allowed_amount": f"{fee(p, cpt):.2f}",
         "effective_date": "2020-01-01"}
        for p in payers.values() for cpt in sorted(CPT_BASE_FEE)
    ]  # fmt: skip
    visit_rows = [
        {"visit_id": v.visit_id, "payer_id": v.payer.payer_id, "provider_npi": v.provider_npi,
         "patient_ref": v.patient.ref, "dos": v.dos.isoformat(), "cpt": v.cpt, "units": v.units}
        for v in visits
    ] if doc is None else doc.visit_rows  # fmt: skip
    open_rows = [
        {"claim_id": c.claim_id, "payer_id": c.payer.payer_id, "submitted": c.submitted.isoformat(),
         "billed": f"{c.billed:.2f}", "returned": "Y" if c.scenario == "rejection" else "N"}
        for c in claims if c.scenario in ("open", "rejection")
    ]  # fmt: skip
    for name, cols, rows in (
        ("fee_schedule.csv", ["payer_id", "cpt", "modifier", "allowed_amount", "effective_date"], fee_rows),
        ("visits.csv", ["visit_id", "payer_id", "provider_npi", "patient_ref", "dos", "cpt", "units"], visit_rows),
        ("ground_truth.csv", GROUND_TRUTH_COLUMNS, ground_truth(claims, visits, as_of)),
        ("open_ar.csv", ["claim_id", "payer_id", "submitted", "billed", "returned"], open_rows),
    ):  # fmt: skip
        _write_csv(out_dir / name, cols, rows)
        counts["csv"] += 1
    if doc is not None:
        for name, cols, rows in (
            ("notes.csv", NOTE_COLUMNS, doc.note_rows),
            ("charges.csv", CHARGE_COLUMNS, doc.charge_rows),
            ("doc_truth.csv", TRUTH_COLUMNS, doc.truth_rows),
        ):  # fmt: skip
            _write_csv(out_dir / name, cols, rows)
            counts["csv"] += 1
    return dict(counts)
