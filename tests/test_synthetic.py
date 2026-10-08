"""M0 tests: the synthetic set is well-formed, internally consistent, deterministic and PHI-free."""

from __future__ import annotations

import csv
import re
from collections import Counter
from decimal import Decimal
from pathlib import Path

import pytest

from tests.fixtures import make_synthetic as ms


@pytest.fixture(scope="module")
def synth(tmp_path_factory) -> tuple[Path, dict[str, list[Path]]]:
    out = tmp_path_factory.mktemp("synthetic")
    return out, ms.generate(out, seed=123, n_claims=500)


def segments(path: Path) -> list[list[str]]:
    text = path.read_text(encoding="ascii")
    assert text.startswith("ISA*") and text[3] == "*"
    return [s.strip().split("*") for s in text.split("~") if s.strip()]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def all_x12(files) -> list[Path]:
    return [p for kind in ("837", "835", "999", "277ca") for p in files[kind]]


def test_expected_file_set(synth):
    out, files = synth
    assert len(files["837"]) == len(files["999"]) == len(files["277ca"]) == len(ms.PAYERS) == 4
    assert files["835"]
    assert {p.name for p in files["csv"]} == {"fee_schedule.csv", "visits.csv", "ground_truth.csv"}


@pytest.mark.parametrize("kind", ["837", "835", "999", "277ca"])
def test_envelopes_are_valid(synth, kind):
    _, files = synth
    for path in files[kind]:
        segs = segments(path)
        isa, gs, st = segs[0], segs[1], segs[2]
        assert len(path.read_text().split("~")[0]) + 1 == 106  # fixed-width ISA incl. terminator
        assert isa[0] == "ISA" and gs[0] == "GS" and st[0] == "ST"
        assert segs[-1] == ["IEA", "1", isa[13]]
        assert segs[-2] == ["GE", "1", gs[6]]
        se = segs[-3]
        assert se[0] == "SE" and se[2] == st[2]
        assert int(se[1]) == len(segs) - 4  # ST..SE inclusive = total - ISA, GS, GE, IEA


def test_control_numbers_unique_across_files(synth):
    _, files = synth
    isa13 = [segments(p)[0][13] for p in all_x12(files)]
    assert len(isa13) == len(set(isa13))


def test_999_acknowledges_its_837(synth):
    _, files = synth
    gs06_837 = {p.name.split("_")[1]: segments(p)[1][6] for p in files["837"]}
    for path in files["999"]:
        ak1 = next(s for s in segments(path) if s[0] == "AK1")
        assert ak1[2] == gs06_837[path.name.split("_")[1]]


def claims_in_837(files) -> dict[str, dict]:
    found = {}
    for path in files["837"]:
        for s in segments(path):
            if s[0] == "CLM":
                found[s[1]] = {"billed": Decimal(s[2])}
    return found


def clps_in_835(files) -> dict[str, dict]:
    found = {}
    for path in files["835"]:
        cas = []
        for s in segments(path):
            if s[0] == "CLP":
                found[s[1]] = {"status": s[2], "billed": Decimal(s[3]), "paid": Decimal(s[4]),
                               "pr": Decimal(s[5]), "carcs": [], "file": path, "lines": []}  # fmt: skip
                cas = found[s[1]]["carcs"]
            elif s[0] == "SVC":
                found[next(reversed(found))]["lines"].append(Decimal(s[3]))
            elif s[0] == "CAS" and cas is not None:
                cas.extend(s[2::2])
    return found


def test_claims_count_and_payers(synth):
    _, files = synth
    assert len(claims_in_837(files)) == 500


def test_835_claims_exist_in_837_and_balance(synth):
    _, files = synth
    c837, c835 = claims_in_837(files), clps_in_835(files)
    assert set(c835) <= set(c837)
    for cid, clp in c835.items():
        assert clp["billed"] == c837[cid]["billed"]
        assert clp["paid"] == sum(clp["lines"], Decimal("0"))


def test_835_bpr_equals_sum_of_claim_payments(synth):
    _, files = synth
    for path in files["835"]:
        segs = segments(path)
        bpr = next(s for s in segs if s[0] == "BPR")
        paid = sum((Decimal(s[4]) for s in segs if s[0] == "CLP"), Decimal("0"))
        assert Decimal(bpr[2]) == paid


def test_ground_truth_shape_and_mix(synth):
    out, _ = synth
    gt = read_csv(out / "ground_truth.csv")
    kinds = Counter(r["issue_type"] for r in gt)
    assert set(kinds) == {"denial", "timely_filing", "underpayment", "rejection", "unbilled_visit"}
    assert all(n >= 5 for n in kinds.values())
    assert len({r["issue_id"] for r in gt}) == len(gt)
    assert {r["status"] for r in gt} == {"recoverable", "structural"}
    assert all(Decimal(r["expected_amount"]) > 0 for r in gt)
    # timely filing is always structural; each denial row carries a CARC
    assert all(r["status"] == "structural" for r in gt if r["issue_type"] == "timely_filing")
    assert all(r["carc"] for r in gt if r["issue_type"] in ("denial", "timely_filing"))


def test_planted_denials_appear_in_835(synth):
    out, files = synth
    c835 = clps_in_835(files)
    for r in read_csv(out / "ground_truth.csv"):
        if r["issue_type"] in ("denial", "timely_filing"):
            clp = c835[r["claim_id"]]
            assert clp["status"] == "4" and clp["paid"] == 0
            assert r["carc"] in clp["carcs"]


def test_planted_underpayments_match_fee_schedule(synth):
    out, files = synth
    c835 = clps_in_835(files)
    fees = {(r["payer_id"], r["cpt"]): Decimal(r["allowed_amount"])
            for r in read_csv(out / "fee_schedule.csv")}  # fmt: skip
    units = {}
    for path in files["837"]:
        cid = None
        for s in segments(path):
            if s[0] == "CLM":
                cid, units[cid] = s[1], []
            elif s[0] == "SV1":
                units[cid].append((s[1].split(":")[1], int(s[4])))
    for r in read_csv(out / "ground_truth.csv"):
        if r["issue_type"] != "underpayment":
            continue
        cpt, n = units[r["claim_id"]][int(r["line_no"]) - 1]
        allowed = fees[(r["payer_id"], cpt)] * n
        expected = allowed - (allowed * ms.PATIENT_SHARE).quantize(ms.CENTS, ms.ROUND_HALF_UP)
        line_paid = c835[r["claim_id"]]["lines"][int(r["line_no"]) - 1]
        assert expected - line_paid == Decimal(r["expected_amount"])


def test_rejections_have_no_835_but_a_277ca_rejection(synth):
    out, files = synth
    c835 = clps_in_835(files)
    rejected = set()
    for path in files["277ca"]:
        trn = None
        for s in segments(path):
            if s[0] == "TRN":
                trn = s[2]
            elif s[0] == "STC" and s[1].startswith("A3"):
                rejected.add(trn)
    planted = {
        r["claim_id"] for r in read_csv(out / "ground_truth.csv") if r["issue_type"] == "rejection"
    }
    assert rejected == planted and planted.isdisjoint(c835)


def test_unbilled_visits_have_no_claim(synth):
    out, files = synth
    visits = read_csv(out / "visits.csv")
    planted = {
        r["visit_id"]
        for r in read_csv(out / "ground_truth.csv")
        if r["issue_type"] == "unbilled_visit"
    }
    assert planted == {v["visit_id"] for v in visits}
    # visits are separate from the billed set: no visit id looks like a claim id
    assert not any(v["visit_id"] in claims_in_837(files) for v in visits)


def test_deterministic_for_same_seed(tmp_path):
    a = ms.generate(tmp_path / "a", seed=7, n_claims=60)
    b = ms.generate(tmp_path / "b", seed=7, n_claims=60)
    for kind in a:
        assert [p.name for p in a[kind]] == [p.name for p in b[kind]]
        for pa, pb in zip(a[kind], b[kind], strict=True):
            assert pa.read_bytes() == pb.read_bytes()


def test_different_seed_differs(tmp_path):
    ms.generate(tmp_path / "a", seed=7, n_claims=60)
    ms.generate(tmp_path / "b", seed=8, n_claims=60)
    assert (tmp_path / "a/ground_truth.csv").read_bytes() != (
        tmp_path / "b/ground_truth.csv"
    ).read_bytes()


def test_small_run_still_has_every_issue_type(tmp_path):
    ms.generate(tmp_path, seed=1, n_claims=40)
    kinds = {r["issue_type"] for r in read_csv(tmp_path / "ground_truth.csv")}
    assert kinds == {"denial", "timely_filing", "underpayment", "rejection", "unbilled_visit"}


def test_no_real_looking_phi(synth):
    """All identifiers are visibly synthetic: SYN-prefixed names/ids, fake 555 phones."""
    _, files = synth
    for path in all_x12(files):
        for s in segments(path):
            if s[0] == "NM1" and s[1] in ("IL", "QC"):
                assert s[3].startswith("SYNLAST") and s[4].startswith("SYNFIRST")
                assert s[9].startswith("SYNM")
            if s[0] == "NM1" and s[1] == "85":
                assert s[9].startswith("1999999")
            if s[0] == "PER":
                assert re.fullmatch(r"555\d{7}", s[4])


def test_money_is_two_decimals(synth):
    out, _ = synth
    for r in read_csv(out / "ground_truth.csv"):
        assert re.fullmatch(r"\d+\.\d{2}", r["expected_amount"])
