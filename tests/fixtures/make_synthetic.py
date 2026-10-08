"""Generate a SYNTHETIC claim set: 837P, 835, 999, 277CA, fee schedule, visits and a ground truth.

Everything here is fabricated (names, member ids, NPIs, tax ids). Output is deterministic for a
given seed. Usage:

    python -m tests.fixtures.make_synthetic --out out/synthetic --claims 500 --seed 20260630

Planted problems (listed in ground_truth.csv, one row each):
    denial          payer denied the claim with a CARC (recoverable while the appeal window is open)
    timely_filing   denied with CARC 29, always structural
    underpayment    one line paid below the fee-schedule expectation
    rejection       277CA rejected the claim, no 835 exists (fix and resubmit)
    unbilled_visit  visit in visits.csv with no 837 claim

expected_amount is the expected PAYER payment (allowed less patient share) for denials, timely
filing, rejections and unbilled visits, and the shortfall for underpayments.
Status is "recoverable" when the relevant window is still open on AS_OF, else "structural":
    denial / underpayment: AS_OF - remit (payment) date <= APPEAL_WINDOW_DAYS
    rejection / unbilled_visit: AS_OF - date of service <= TIMELY_FILING_DAYS
"""

from __future__ import annotations

import argparse
import csv
import random
from calendar import monthrange
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

AS_OF = date(2026, 6, 30)
APPEAL_WINDOW_DAYS = 180
TIMELY_FILING_DAYS = 365
PATIENT_SHARE = Decimal("0.10")
CENTS = Decimal("0.01")
BILLED_MARKUP = Decimal("1.6")

SCENARIO_MIX = {  # share of claims
    "timely_filing": Decimal("0.025"),
    "denial": Decimal("0.09"),
    "underpayment": Decimal("0.08"),
    "rejection": Decimal("0.02"),
}
UNBILLED_SHARE = Decimal("0.03")

# CARC -> a plausible RARC, purely synthetic pairing
DENIAL_CARCS = {
    "16": "MA130",
    "18": "N522",
    "50": "N115",
    "97": "N19",
    "27": "N30",
    "31": "N382",
    "197": "N54",
    "4": "N519",
}
TIMELY_FILING_CARC = "29"

CPT_BASE_FEE = {
    "99213": Decimal("92.00"),
    "99214": Decimal("130.00"),
    "99203": Decimal("120.00"),
    "99204": Decimal("180.00"),
    "97110": Decimal("38.00"),
    "97140": Decimal("35.00"),
    "90837": Decimal("140.00"),
    "93000": Decimal("22.00"),
    "71046": Decimal("55.00"),
    "85025": Decimal("12.00"),
}
MULTI_UNIT_CPTS = {"97110", "97140"}
DX_CODES = ["I10", "E119", "M545", "J069", "Z0000", "R519"]


@dataclass(frozen=True)
class Payer:
    payer_id: str
    name: str
    fee_multiplier: Decimal


PAYERS = (
    Payer("SYNPAY01", "SYNTHETIC PAYER ALPHA", Decimal("0.90")),
    Payer("SYNPAY02", "SYNTHETIC PAYER BRAVO", Decimal("1.00")),
    Payer("SYNPAY03", "SYNTHETIC PAYER CHARLIE", Decimal("1.10")),
    Payer("SYNPAY04", "SYNTHETIC PAYER DELTA", Decimal("0.95")),
)
PROVIDERS = ("1999999991", "1999999992", "1999999993")
TAX_ID = "999999999"


def money(value: Decimal) -> Decimal:
    return value.quantize(CENTS, ROUND_HALF_UP)


def fee(payer: Payer, cpt: str) -> Decimal:
    return money(CPT_BASE_FEE[cpt] * payer.fee_multiplier)


@dataclass
class Patient:
    ref: str  # synthetic member id
    last: str
    first: str
    dob: date
    sex: str
    payer: Payer


@dataclass
class Line:
    cpt: str
    units: int
    billed: Decimal
    allowed: Decimal
    pr: Decimal = Decimal("0")
    paid: Decimal = Decimal("0")
    cas: list[tuple[str, str, Decimal]] = field(default_factory=list)  # (group, reason, amount)

    @property
    def expected_pay(self) -> Decimal:
        return self.allowed - money(self.allowed * PATIENT_SHARE)


@dataclass
class Claim:
    claim_id: str
    payer: Payer
    provider_npi: str
    patient: Patient
    dos: date
    dx: list[str]
    lines: list[Line]
    scenario: str = "clean"
    carc: str = ""
    remit_date: date | None = None
    shortfall_line: int | None = None
    shortfall: Decimal = Decimal("0")

    @property
    def billed(self) -> Decimal:
        return sum((ln.billed for ln in self.lines), Decimal("0"))

    @property
    def paid(self) -> Decimal:
        return sum((ln.paid for ln in self.lines), Decimal("0"))

    @property
    def pr(self) -> Decimal:
        return sum((ln.pr for ln in self.lines), Decimal("0"))

    @property
    def payer_claim_no(self) -> str:
        return "PCN" + self.claim_id[-6:]

    @property
    def has_remit(self) -> bool:
        return self.scenario != "rejection"


@dataclass
class Visit:
    visit_id: str
    payer: Payer
    provider_npi: str
    patient: Patient
    dos: date
    cpt: str
    units: int

    @property
    def expected_pay(self) -> Decimal:
        line_allowed = fee(self.payer, self.cpt) * self.units
        return line_allowed - money(line_allowed * PATIENT_SHARE)


# ----------------------------------------------------------------------------- scenario building


def _month_end(d: date) -> date:
    return date(d.year, d.month, monthrange(d.year, d.month)[1])


def _make_line(rng: random.Random, payer: Payer, cpt: str) -> Line:
    units = rng.randint(1, 4) if cpt in MULTI_UNIT_CPTS else 1
    allowed = fee(payer, cpt) * units
    billed = money(CPT_BASE_FEE[cpt] * units * BILLED_MARKUP)
    return Line(cpt=cpt, units=units, billed=billed, allowed=allowed)


def _settle(claim: Claim) -> None:
    """Fill paid / patient responsibility / CAS adjustments for each line from the scenario."""
    for i, ln in enumerate(claim.lines):
        if claim.scenario in ("denial", "timely_filing"):
            ln.paid, ln.pr = Decimal("0"), Decimal("0")
            ln.cas = [("CO", claim.carc, ln.billed)]
            continue
        shortfall = claim.shortfall if claim.shortfall_line == i else Decimal("0")
        ln.pr = money(ln.allowed * PATIENT_SHARE)
        ln.paid = ln.allowed - ln.pr - shortfall
        ln.cas = [("CO", "45", ln.billed - ln.allowed + shortfall), ("PR", "2", ln.pr)]


def build_dataset(seed: int, n_claims: int) -> tuple[list[Claim], list[Visit]]:
    rng = random.Random(seed)
    n_patients = max(8, n_claims // 2)
    patients = [
        Patient(
            ref=f"SYNM{i:06d}",
            last=f"SYNLAST{i:04d}",
            first=f"SYNFIRST{i:04d}",
            dob=date(1940, 1, 1) + timedelta(days=rng.randint(0, 30000)),
            sex=rng.choice("MF"),
            payer=PAYERS[i % len(PAYERS)],
        )
        for i in range(1, n_patients + 1)
    ]

    counts = {k: max(1, int(n_claims * share)) for k, share in SCENARIO_MIX.items()}
    scenarios = ["clean"] * n_claims
    order = list(range(n_claims))
    rng.shuffle(order)
    pos = 0
    for name, cnt in counts.items():
        for idx in order[pos : pos + cnt]:
            scenarios[idx] = name
        pos += cnt

    first_normal, last_normal = date(2025, 10, 1), date(2026, 5, 31)
    claims: list[Claim] = []
    for i, scenario in enumerate(scenarios, start=1):
        patient = rng.choice(patients)
        if scenario == "timely_filing":
            dos = date(2025, 3, 1) + timedelta(days=rng.randint(0, 75))
            remit = date(2026, 6, 30)
        else:
            dos = first_normal + timedelta(days=rng.randint(0, (last_normal - first_normal).days))
            remit = min(_month_end(dos + timedelta(days=rng.randint(14, 35))), AS_OF)
        cpts = rng.sample(sorted(CPT_BASE_FEE), rng.randint(1, 3))
        claim = Claim(
            claim_id=f"SYNC{i:06d}",
            payer=patient.payer,
            provider_npi=rng.choice(PROVIDERS),
            patient=patient,
            dos=dos,
            dx=rng.sample(DX_CODES, rng.randint(1, 2)),
            lines=[_make_line(rng, patient.payer, c) for c in cpts],
            scenario=scenario,
            remit_date=None if scenario == "rejection" else remit,
        )
        if scenario == "denial":
            claim.carc = rng.choice(sorted(DENIAL_CARCS))
        elif scenario == "timely_filing":
            claim.carc = TIMELY_FILING_CARC
        elif scenario == "underpayment":
            claim.shortfall_line = rng.randrange(len(claim.lines))
            target = claim.lines[claim.shortfall_line]
            pct = Decimal(rng.randint(15, 40)) / 100
            claim.shortfall = max(Decimal("1.00"), money(target.expected_pay * pct))
        _settle(claim)
        claims.append(claim)

    visits: list[Visit] = []
    for j in range(1, max(1, int(n_claims * UNBILLED_SHARE)) + 1):
        patient = rng.choice(patients)
        cpt = rng.choice(sorted(CPT_BASE_FEE))
        visits.append(
            Visit(
                visit_id=f"SYNV{j:05d}",
                payer=patient.payer,
                provider_npi=rng.choice(PROVIDERS),
                patient=patient,
                dos=date(2025, 4, 15) + timedelta(days=rng.randint(0, 410)),
                cpt=cpt,
                units=rng.randint(1, 3) if cpt in MULTI_UNIT_CPTS else 1,
            )
        )
    return claims, visits


# ----------------------------------------------------------------------------------- X12 writing


def _seg(*elements: object) -> str:
    parts = [str(e) for e in elements]
    while parts and parts[-1] == "":
        parts.pop()
    return "*".join(parts)


def _amt(value: Decimal) -> str:
    text = f"{value:.2f}"
    return text[:-3] if text.endswith(".00") else text


def _envelope(
    *,
    gs_code: str,
    gs_version: str,
    st_code: str,
    st_version: str,
    body: list[str],
    ctrl: int,
    sender: str,
    receiver: str,
    when: date,
) -> str:
    """Wrap a transaction body (segments after ST, before SE) in ISA/GS/ST ... SE/GE/IEA."""
    isa = _seg(
        "ISA", "00", " " * 10, "00", " " * 10,
        "ZZ", sender.ljust(15), "ZZ", receiver.ljust(15),
        when.strftime("%y%m%d"), "1200", "^", "00501", f"{ctrl:09d}", "0", "T", ":",
    )  # fmt: skip
    st = _seg("ST", st_code, "0001", st_version)
    se = _seg("SE", len(body) + 2, "0001")
    gs = _seg("GS", gs_code, sender, receiver, when.strftime("%Y%m%d"), "1200", ctrl, "X", gs_version)
    segs = [isa, gs, st, *body, se, _seg("GE", 1, ctrl), _seg("IEA", 1, f"{ctrl:09d}")]
    return "".join(s + "~\n" for s in segs)


def write_837(payer: Payer, claims: list[Claim], ctrl: int) -> str:
    body = [
        _seg("BHT", "0019", "00", f"SYN837{ctrl}", AS_OF.strftime("%Y%m%d"), "1200", "CH"),
        _seg("NM1", "41", "2", "SYNTHETIC CLINIC", "", "", "", "", "46", "SYNSENDER"),
        _seg("PER", "IC", "SYNTHETIC BILLING", "TE", "5550000000"),
        _seg("NM1", "40", "2", payer.name, "", "", "", "", "46", payer.payer_id),
        _seg("HL", 1, "", "20", 1),
        _seg("NM1", "85", "2", "SYNTHETIC CLINIC", "", "", "", "", "XX", PROVIDERS[0]),
        _seg("N3", "100 SYNTHETIC WAY"),
        _seg("N4", "TESTVILLE", "TX", "750010000"),
        _seg("REF", "EI", TAX_ID),
    ]
    for hl, c in enumerate(claims, start=2):
        p = c.patient
        body += [
            _seg("HL", hl, 1, "22", 0),
            _seg("SBR", "P", "18", "", "", "", "", "", "", "CI"),
            _seg("NM1", "IL", "1", p.last, p.first, "", "", "", "MI", p.ref),
            _seg("N3", "100 SYNTHETIC WAY"),
            _seg("N4", "TESTVILLE", "TX", "750010000"),
            _seg("DMG", "D8", p.dob.strftime("%Y%m%d"), p.sex),
            _seg("NM1", "PR", "2", payer.name, "", "", "", "", "PI", payer.payer_id),
            _seg("CLM", c.claim_id, _amt(c.billed), "", "", "11:B:1", "Y", "A", "Y", "Y"),
            _seg("HI", *[("ABK" if i == 0 else "ABF") + ":" + dx for i, dx in enumerate(c.dx)]),
            _seg("NM1", "82", "1", "SYNRENDER", "SYNPROV", "", "", "", "XX", c.provider_npi),
        ]
        for n, ln in enumerate(c.lines, start=1):
            body += [
                _seg("LX", n),
                _seg("SV1", f"HC:{ln.cpt}", _amt(ln.billed), "UN", ln.units, "", "", "1"),
                _seg("DTP", "472", "D8", c.dos.strftime("%Y%m%d")),
            ]
    return _envelope(
        gs_code="HC", gs_version="005010X222A1", st_code="837", st_version="005010X222A1",
        body=body, ctrl=ctrl, sender="SYNSENDER", receiver=payer.payer_id, when=AS_OF,
    )  # fmt: skip


def write_999(payer: Payer, ctrl_837: int, ctrl: int) -> str:
    body = [
        _seg("AK1", "HC", ctrl_837, "005010X222A1"),
        _seg("AK2", "837", "0001", "005010X222A1"),
        _seg("IK5", "A"),
        _seg("AK9", "A", 1, 1, 1),
    ]
    return _envelope(
        gs_code="FA", gs_version="005010X231A1", st_code="999", st_version="005010X231A1",
        body=body, ctrl=ctrl, sender=payer.payer_id, receiver="SYNSENDER", when=AS_OF,
    )  # fmt: skip


def write_277ca(payer: Payer, claims: list[Claim], ctrl: int) -> str:
    body = [
        _seg("BHT", "0085", "08", f"SYN277{ctrl}", AS_OF.strftime("%Y%m%d"), "1200", "TH"),
        _seg("HL", 1, "", "20", 1),
        _seg("NM1", "PR", "2", payer.name, "", "", "", "", "PI", payer.payer_id),
        _seg("HL", 2, 1, "21", 1),
        _seg("NM1", "41", "2", "SYNTHETIC CLINIC", "", "", "", "", "46", "SYNSENDER"),
        _seg("HL", 3, 2, "19", 1),
        _seg("NM1", "85", "2", "SYNTHETIC CLINIC", "", "", "", "", "XX", PROVIDERS[0]),
    ]
    for hl, c in enumerate(claims, start=4):
        status = "A3:21:PR" if c.scenario == "rejection" else "A2:20:PR"  # A3 = returned/rejected
        p = c.patient
        body += [
            _seg("HL", hl, 3, "22", 0),
            _seg("NM1", "IL", "1", p.last, p.first, "", "", "", "MI", p.ref),
            _seg("TRN", "2", c.claim_id),
            _seg("STC", status, AS_OF.strftime("%Y%m%d"), "WQ", _amt(c.billed)),
            _seg("REF", "1K", c.payer_claim_no),
            _seg("DTP", "472", "D8", c.dos.strftime("%Y%m%d")),
        ]
    return _envelope(
        gs_code="HN", gs_version="005010X214", st_code="277", st_version="005010X214",
        body=body, ctrl=ctrl, sender=payer.payer_id, receiver="SYNSENDER", when=AS_OF,
    )  # fmt: skip


def write_835(payer: Payer, remit_date: date, claims: list[Claim], ctrl: int) -> str:
    total = sum((c.paid for c in claims), Decimal("0"))
    ymd = remit_date.strftime("%Y%m%d")
    body = [
        _seg("BPR", "I", _amt(total), "C", "ACH", "CCP", "01", "999999999", "DA", "000000001",
             "1999999999", "", "01", "999999999", "DA", "000000002", ymd),
        _seg("TRN", "1", f"TRC{payer.payer_id[-2:]}{ymd}", "1999999999"),
        _seg("DTM", "405", ymd),
        _seg("N1", "PR", payer.name, "PI", payer.payer_id),
        _seg("N1", "PE", "SYNTHETIC CLINIC", "XX", PROVIDERS[0]),
    ]  # fmt: skip
    for n, c in enumerate(claims, start=1):
        denied = c.scenario in ("denial", "timely_filing")
        p = c.patient
        body += [
            _seg("LX", n),
            _seg("CLP", c.claim_id, 4 if denied else 1, _amt(c.billed), _amt(c.paid),
                 _amt(c.pr), "12", c.payer_claim_no, "11", 1),
            _seg("NM1", "QC", "1", p.last, p.first, "", "", "", "MI", p.ref),
            _seg("DTM", "232", c.dos.strftime("%Y%m%d")),
        ]  # fmt: skip
        for ln in c.lines:
            body.append(_seg("SVC", f"HC:{ln.cpt}", _amt(ln.billed), _amt(ln.paid), "", ln.units))
            body.append(_seg("DTM", "472", c.dos.strftime("%Y%m%d")))
            for group in ("CO", "PR"):
                items = [(r, a) for g, r, a in ln.cas if g == group and a != 0]
                if items:
                    flat = [x for r, a in items for x in (r, _amt(a))]
                    body.append(_seg("CAS", group, *flat))
            body.append(_seg("AMT", "B6", _amt(ln.allowed if not denied else Decimal("0"))))
            if c.scenario == "denial":
                body.append(_seg("LQ", "HE", DENIAL_CARCS[c.carc]))
    return _envelope(
        gs_code="HP", gs_version="005010X221A1", st_code="835", st_version="005010X221A1",
        body=body, ctrl=ctrl, sender=payer.payer_id, receiver="SYNSENDER", when=remit_date,
    )  # fmt: skip


# ------------------------------------------------------------------------------- ground truth


def ground_truth_rows(claims: list[Claim], visits: list[Visit]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    def add(issue_type, claim_id, visit_id, line_no, payer, cpt, carc, amount, status, why):
        rows.append(
            {
                "issue_id": f"GT{len(rows) + 1:04d}",
                "issue_type": issue_type,
                "claim_id": claim_id,
                "visit_id": visit_id,
                "line_no": line_no,
                "payer_id": payer.payer_id,
                "cpt": cpt,
                "carc": carc,
                "expected_amount": f"{amount:.2f}",
                "status": status,
                "reason": why,
            }
        )

    for c in claims:
        if c.scenario in ("denial", "timely_filing"):
            amount = sum((ln.expected_pay for ln in c.lines), Decimal("0"))
            age = (AS_OF - c.remit_date).days
            open_window = c.scenario == "denial" and age <= APPEAL_WINDOW_DAYS
            why = (
                "CARC 29 timely filing loss"
                if c.scenario == "timely_filing"
                else f"denied {age}d before AS_OF, appeal window {APPEAL_WINDOW_DAYS}d"
            )
            add(c.scenario, c.claim_id, "", "", c.payer, "", c.carc, amount,
                "recoverable" if open_window else "structural", why)  # fmt: skip
        elif c.scenario == "underpayment":
            ln = c.lines[c.shortfall_line]
            age = (AS_OF - c.remit_date).days
            add("underpayment", c.claim_id, "", c.shortfall_line + 1, c.payer, ln.cpt, "45",
                c.shortfall, "recoverable" if age <= APPEAL_WINDOW_DAYS else "structural",
                f"paid {age}d before AS_OF, appeal window {APPEAL_WINDOW_DAYS}d")  # fmt: skip
        elif c.scenario == "rejection":
            amount = sum((ln.expected_pay for ln in c.lines), Decimal("0"))
            age = (AS_OF - c.dos).days
            add("rejection", c.claim_id, "", "", c.payer, "", "", amount,
                "recoverable" if age <= TIMELY_FILING_DAYS else "structural",
                f"277CA rejected, DOS {age}d before AS_OF, filing limit {TIMELY_FILING_DAYS}d")  # fmt: skip
    for v in visits:
        age = (AS_OF - v.dos).days
        add("unbilled_visit", "", v.visit_id, "", v.payer, v.cpt, "", v.expected_pay,
            "recoverable" if age <= TIMELY_FILING_DAYS else "structural",
            f"visit never billed, DOS {age}d before AS_OF, filing limit {TIMELY_FILING_DAYS}d")  # fmt: skip
    return rows


GROUND_TRUTH_COLUMNS = [
    "issue_id", "issue_type", "claim_id", "visit_id", "line_no", "payer_id", "cpt", "carc",
    "expected_amount", "status", "reason",
]  # fmt: skip


def _write_csv(path: Path, columns: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def generate(out_dir: Path, seed: int = 20260630, n_claims: int = 500) -> dict[str, list[Path]]:
    """Write the full synthetic set into out_dir and return the files by kind."""
    out_dir.mkdir(parents=True, exist_ok=True)
    claims, visits = build_dataset(seed, n_claims)
    written: dict[str, list[Path]] = {k: [] for k in ("837", "835", "999", "277ca", "csv")}
    ctrl = 1000

    def put(kind: str, name: str, text: str) -> None:
        path = out_dir / name
        path.write_text(text, encoding="ascii", newline="")
        written[kind].append(path)

    for payer in PAYERS:
        mine = [c for c in claims if c.payer == payer]
        ctrl += 1
        put("837", f"837P_{payer.payer_id}.x12", write_837(payer, mine, ctrl))
        put("999", f"999_{payer.payer_id}.x12", write_999(payer, ctrl, ctrl + 1000))
        put("277ca", f"277CA_{payer.payer_id}.x12", write_277ca(payer, mine, ctrl + 2000))
        by_remit: dict[date, list[Claim]] = {}
        for c in mine:
            if c.has_remit:
                by_remit.setdefault(c.remit_date, []).append(c)
        for remit_date in sorted(by_remit):
            ctrl += 1
            put("835", f"835_{payer.payer_id}_{remit_date:%Y%m%d}.x12",
                write_835(payer, remit_date, by_remit[remit_date], ctrl + 3000))  # fmt: skip

    fee_rows = [
        {"payer_id": p.payer_id, "cpt": cpt, "modifier": "", "allowed_amount": f"{fee(p, cpt):.2f}",
         "effective_date": "2025-01-01"}
        for p in PAYERS for cpt in sorted(CPT_BASE_FEE)
    ]  # fmt: skip
    visit_rows = [
        {"visit_id": v.visit_id, "payer_id": v.payer.payer_id, "provider_npi": v.provider_npi,
         "patient_ref": v.patient.ref, "dos": v.dos.isoformat(), "cpt": v.cpt, "units": v.units}
        for v in visits
    ]  # fmt: skip
    for name, cols, rows in (
        ("fee_schedule.csv", ["payer_id", "cpt", "modifier", "allowed_amount", "effective_date"], fee_rows),
        ("visits.csv", ["visit_id", "payer_id", "provider_npi", "patient_ref", "dos", "cpt", "units"], visit_rows),
        ("ground_truth.csv", GROUND_TRUTH_COLUMNS, ground_truth_rows(claims, visits)),
    ):  # fmt: skip
        _write_csv(out_dir / name, cols, rows)
        written["csv"].append(out_dir / name)
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--out", type=Path, default=Path("out/synthetic"))
    parser.add_argument("--claims", type=int, default=500)
    parser.add_argument("--seed", type=int, default=20260630)
    args = parser.parse_args()
    files = generate(args.out, args.seed, args.claims)
    print(f"Wrote {sum(len(v) for v in files.values())} files to {args.out}")


if __name__ == "__main__":
    main()
