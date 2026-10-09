"""M2 tests: X12 ingestion end to end on the synthetic set (round trip, idempotency, failures, PHI, tenants)."""

from __future__ import annotations

import csv
import re
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import Session

import krisnai.model as m
from krisnai import cli
from krisnai.ingest import hashing, r835
from krisnai.ingest.loader import ingest_file, ingest_path
from krisnai.ingest.x12 import X12Error, read_transactions
from krisnai.model import Base, tenant_session
from tests.fixtures import make_synthetic as ms

SALT = "unit-test-salt"
N_CLAIMS = 150


def make_engine(path: Path):
    eng = create_engine(f"sqlite:///{path}")

    @event.listens_for(eng, "connect")
    def _fk(conn, _):
        conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(eng)
    with Session(eng) as s:
        s.add_all([m.Tenant(name="A", patient_salt_key="SALT_A"), m.Tenant(name="B", patient_salt_key="SALT_B")])
        s.commit()
    return eng


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    root = tmp_path_factory.mktemp("m2")
    files = ms.generate(root / "data", seed=99, n_claims=N_CLAIMS)
    eng = make_engine(root / "db.sqlite")
    results = ingest_path(eng, 1, root / "data", SALT)
    return {"root": root, "data": root / "data", "files": files, "engine": eng, "results": results}


def count(eng, model, tenant=1):
    with tenant_session(eng, tenant) as s:
        return s.scalar(select(func.count()).select_from(model))


def total(eng, column, tenant=1):
    with tenant_session(eng, tenant) as s:
        return s.scalar(select(func.sum(column))) or Decimal("0")


def segs(path: Path, sid: str):
    return [x.split("*") for x in path.read_text().split("~") if x.strip().startswith(sid + "*")]


def read_csv(path):
    with path.open(newline="") as fh:
        return list(csv.DictReader(fh))


# ----------------------------------------------------------------------------- round trip


def test_every_file_loaded_without_failures(world):
    statuses = {r.status for r in world["results"]}
    assert statuses == {"loaded"}, [r for r in world["results"] if r.status != "loaded"]
    assert (
        len(world["results"]) == sum(len(v) for v in world["files"].values()) - 1
    )  # ground truth skipped (visits.csv is loaded since M5)


def test_row_counts_equal_what_the_generator_wrote(world):
    eng, f = world["engine"], world["files"]
    sv1 = sum(len(segs(p, "SV1")) for p in f["837"])
    clp = sum(len(segs(p, "CLP")) for p in f["835"])
    svc = sum(len(segs(p, "SVC")) for p in f["835"])
    assert count(eng, m.Claim) == N_CLAIMS == sum(len(segs(p, "CLM")) for p in f["837"])
    assert count(eng, m.ClaimLine) == sv1
    assert count(eng, m.Remit) == clp
    assert count(eng, m.RemitLine) == svc
    assert count(eng, m.Payment) == len(f["835"])
    assert count(eng, m.Ack999) == 4
    assert count(eng, m.Ack277Ca) == N_CLAIMS
    assert count(eng, m.Payer) == 4 and count(eng, m.Provider) >= 1
    assert count(eng, m.FeeSchedule) == 4 * len(ms.CPT_BASE_FEE)
    events = N_CLAIMS + clp + len(f["835"]) + 4 + N_CLAIMS
    assert count(eng, m.Event) == events


def test_money_reconciles_to_the_files(world):
    eng, f = world["engine"], world["files"]
    assert total(eng, m.Claim.total_charge) == sum(Decimal(s[2]) for p in f["837"] for s in segs(p, "CLM"))
    assert total(eng, m.Remit.total_paid) == sum(Decimal(s[4]) for p in f["835"] for s in segs(p, "CLP"))
    assert total(eng, m.Payment.payment_amount) == sum(Decimal(s[2]) for p in f["835"] for s in segs(p, "BPR"))
    assert total(eng, m.RemitLine.paid) == total(eng, m.Remit.total_paid)
    # every line balances: charge = paid + all adjustments
    with tenant_session(eng, 1) as s:
        for line in s.scalars(select(m.RemitLine)):
            adj = sum(a.amount for a in s.scalars(select(m.Adjustment).where(m.Adjustment.remit_line_id == line.id)))
            assert line.charge == line.paid + adj, line.id


def test_ground_truth_denials_and_underpayments_are_visible_in_the_database(world):
    eng = world["engine"]
    gt = read_csv(world["data"] / "ground_truth.csv")
    with tenant_session(eng, 1) as s:
        for row in gt:
            if row["issue_type"] in ("denial", "timely_filing"):
                remit = s.scalars(select(m.Remit).where(m.Remit.claim_submitter_id == row["claim_id"])).one()
                assert remit.claim_status_code == "4" and remit.total_paid == 0
                adj = s.scalars(select(m.Adjustment).where(m.Adjustment.remit_id == remit.id)).all()
                assert {a.reason_code for a in adj} == {row["carc"]} and {a.group_code for a in adj} == {"CO"}
            elif row["issue_type"] == "rejection":
                ack = s.scalars(select(m.Ack277Ca).where(m.Ack277Ca.claim_submitter_id == row["claim_id"])).one()
                assert ack.status_category == "A3"
                assert s.scalars(select(m.Remit).where(m.Remit.claim_submitter_id == row["claim_id"])).first() is None
            elif row["issue_type"] == "underpayment":
                remit = s.scalars(select(m.Remit).where(m.Remit.claim_submitter_id == row["claim_id"])).one()
                line = s.scalars(
                    select(m.RemitLine).where(
                        m.RemitLine.remit_id == remit.id, m.RemitLine.line_number == int(row["line_no"])
                    )
                ).one()
                shortfall = (
                    line.allowed_amount - (line.allowed_amount * ms.PATIENT_SHARE).quantize(ms.CENTS) - line.paid
                )
                assert shortfall == Decimal(row["expected_amount"])


def test_claim_fields_and_lineage(world):
    eng = world["engine"]
    with tenant_session(eng, 1) as s:
        claim = s.scalars(select(m.Claim).order_by(m.Claim.id)).first()
        assert claim.claim_submitter_id.startswith("SYNC") and claim.frequency_code == "1"
        assert claim.place_of_service == "11" and claim.service_date is not None
        lines = s.scalars(select(m.ClaimLine).where(m.ClaimLine.claim_id == claim.id)).all()
        assert sum(ln.charge for ln in lines) == claim.total_charge
        ev = s.get(m.Event, claim.event_id)
        assert ev.event_type == "837P.claim" and ev.source_file_id == claim.source_file_id
        assert s.scalar(select(func.count()).select_from(m.ClaimDx).where(m.ClaimDx.claim_id == claim.id)) >= 1


def test_match_links_are_left_empty_for_m3(world):
    eng = world["engine"]
    with tenant_session(eng, 1) as s:
        assert s.scalar(select(func.count()).select_from(m.Remit).where(m.Remit.claim_id.is_not(None))) == 0
        assert (
            s.scalar(select(func.count()).select_from(m.RemitLine).where(m.RemitLine.claim_line_id.is_not(None))) == 0
        )


# ----------------------------------------------------------------------------- idempotency


def test_reingesting_everything_changes_nothing(world):
    eng = world["engine"]
    before = {
        mod.__name__: count(eng, mod) for mod in (m.SourceFile, m.Event, m.Claim, m.Remit, m.Payment, m.Adjustment)
    }
    again = ingest_path(eng, 1, world["data"], SALT)
    assert {r.status for r in again} == {"skipped"}
    after = {
        mod.__name__: count(eng, mod) for mod in (m.SourceFile, m.Event, m.Claim, m.Remit, m.Payment, m.Adjustment)
    }
    assert before == after


def test_same_bytes_under_another_name_is_skipped(world, tmp_path):
    src = next(iter(world["files"]["835"]))
    copy = tmp_path / "renamed_remit.txt"
    copy.write_bytes(src.read_bytes())
    assert ingest_file(world["engine"], 1, copy, SALT).status == "skipped"


def test_resent_transactions_with_different_bytes_are_skipped_by_control_numbers(world, tmp_path):
    src = next(iter(world["files"]["835"]))
    crlf = tmp_path / "resent.x12"
    crlf.write_bytes(src.read_text().replace("~\n", "~\r\n").encode())  # new file hash, same transactions
    before = count(world["engine"], m.Event)
    res = ingest_file(world["engine"], 1, crlf, SALT)
    assert res.status == "skipped" and "control numbers" in res.reason
    assert count(world["engine"], m.Event) == before


# ------------------------------------------------------------------- failures never crash


def failing_engine(tmp_path):
    return make_engine(tmp_path / "f.sqlite")


def one_837(world) -> str:
    return world["files"]["837"][0].read_text()


@pytest.mark.parametrize(
    ("name", "mutate", "reason"),
    [
        ("truncated", lambda t: t[: len(t) // 2], "ends inside|shorter|SE|IEA|GE|open"),
        ("no_isa", lambda t: t.replace("ISA*", "XXX*", 1), "does not start with an ISA"),
        ("bad_se_count", lambda t: re.sub(r"SE\*\d+\*", "SE*9999*", t, count=1), "SE01 says 9999"),
        ("bad_amount", lambda t: re.sub(r"(CLM\*[^*]*\*)[^*]*", r"\1ABC", t, count=1), "not a valid amount"),
        ("bad_date", lambda t: re.sub(r"(DTP\*472\*D8\*)\d{8}", r"\g<1>20261345", t, count=1), "not a valid date"),
        ("empty", lambda t: "", "does not start with an ISA"),
        ("unsupported_set", lambda t: t.replace("ST*837*", "ST*270*", 1), "unsupported transaction set 270"),
        ("ge_mismatch", lambda t: re.sub(r"GE\*1\*\d+", "GE*1*5", t, count=1), "GE does not match"),
        ("iea_mismatch", lambda t: re.sub(r"IEA\*1\*\d+", "IEA*1*5", t, count=1), "IEA does not match"),
    ],
)
def test_malformed_files_are_marked_failed_with_a_reason_and_load_nothing(world, tmp_path, name, mutate, reason):
    eng = failing_engine(tmp_path)
    bad = tmp_path / f"{name}.x12"
    bad.write_text(mutate(one_837(world)))
    res = ingest_file(eng, 1, bad, SALT)
    assert res.status == "failed" and re.search(reason, res.reason), res.reason
    with tenant_session(eng, 1) as s:
        sf = s.scalars(select(m.SourceFile)).one()
        assert sf.status == "failed" and sf.failure_reason
        for model in (m.Event, m.Claim, m.ClaimLine, m.Payer, m.PatientRef):
            assert s.scalar(select(func.count()).select_from(model)) == 0, model.__name__


def test_binary_file_fails_cleanly(tmp_path):
    eng = failing_engine(tmp_path)
    bad = tmp_path / "blob.x12"
    bad.write_bytes(b"\xff\xfe\x00\x01 not text")
    assert ingest_file(eng, 1, bad, SALT).status == "failed"


def test_a_bad_file_does_not_stop_the_good_ones(world, tmp_path):
    eng = failing_engine(tmp_path)
    folder = tmp_path / "mixed"
    folder.mkdir()
    (folder / "a_bad.x12").write_text("ISA*garbage")
    (folder / "b_good.x12").write_text(one_837(world))
    res = ingest_path(eng, 1, folder, SALT)
    assert [r.status for r in res] == ["failed", "loaded"]
    assert count(eng, m.Claim) > 0


def test_missing_salt_is_a_clear_error(world, tmp_path):
    eng = failing_engine(tmp_path)
    f = tmp_path / "x.x12"
    f.write_text(one_837(world))
    with pytest.raises(ValueError, match="salt"):
        ingest_file(eng, 1, f, "")


# -------------------------------------------------------------------------- parser details


def test_other_delimiters_parse_identically(world, tmp_path):
    src = world["files"]["835"][0]
    other = tmp_path / "pipe.x12"
    other.write_text(src.read_text().replace("*", "|").replace(":", ">").replace("~", "!"))
    t1, t2 = read_transactions(src.read_text()), read_transactions(other.read_text())
    p1, r1 = r835.parse(t1[0], SALT)
    p2, r2 = r835.parse(t2[0], SALT)
    assert p1 == p2 and r1 == r2


def wrap(body: list[str]) -> str:
    return ms._envelope(
        gs_code="HP", gs_version="005010X221A1", st_code="835", st_version="005010X221A1",
        body=body, ctrl=7, sender="PAYER", receiver="SYNSENDER", when=ms.AS_OF,
    )  # fmt: skip


def test_835_multiple_cas_pairs_quantity_plb_and_remarks():
    body = [
        "BPR*I*50.00*C*ACH*CCP*01*1*DA*1*1**01*1*DA*2*20260630",
        "TRN*1*TRACE1*1999999999",
        "N1*PR*PAYER X*PI*PX1",
        "LX*1",
        "CLP*C1*1*200.00*50.00*10.00*12*PCN1*11*1",
        "NM1*QC*1*DOE*JANE****MI*MEMBER1",
        "DTM*232*20260601",
        "CAS*PR*1*10.00",
        "SVC*HC:99213:25:GT*200.00*50.00**2",
        "DTM*472*20260601",
        "CAS*CO*45*100.00**97*30.00**3*2*1",
        "AMT*B6*60.00",
        "LQ*HE*N130",
        "LQ*HE*N130",
        "LQ*HE*MA01",
        "PLB*1999999999*20260630*WO:REF9*-5.25*L6*1.00",
    ]
    tx = read_transactions(wrap(body))[0]
    pay, remits = r835.parse(tx, SALT)
    assert pay.trace_number == "TRACE1" and pay.payer_code == "PX1" and pay.amount == Decimal("50.00")
    assert [(p.reason_code, p.reference_id, p.amount) for p in pay.plb] == [
        ("WO", "REF9", Decimal("-5.25")), ("L6", None, Decimal("1.00"))
    ]  # fmt: skip
    (remit,) = remits
    assert [(a.group_code, a.reason_code, a.amount) for a in remit.adjustments] == [("PR", "1", Decimal("10.00"))]
    assert remit.patient_hash == hashing.patient_hash(SALT, "MEMBER1")
    (line,) = remit.lines
    assert line.modifiers == ["25", "GT"] and line.allowed == Decimal("60.00") and line.units == Decimal("2")
    assert [(a.reason_code, a.amount, a.quantity) for a in line.adjustments] == [
        ("45", Decimal("100.00"), None),
        ("97", Decimal("30.00"), None),
        ("3", Decimal("2"), Decimal("1")),
    ]
    assert sorted(set(line.remarks)) == [("HE", "MA01"), ("HE", "N130")]


def test_plb_and_remit_load_into_the_database(tmp_path):
    eng = failing_engine(tmp_path)
    f = tmp_path / "plb.x12"
    f.write_text(
        wrap(
            [
                "BPR*I*50.00*C*ACH*CCP*01*1*DA*1*1**01*1*DA*2*20260630",
                "TRN*1*T9*1999999999",
                "N1*PR*P*PI*PX1",
                "LX*1",
                "CLP*C1*1*200.00*50.00*10.00*12*PCN1*11*1",
                "NM1*QC*1*DOE*JANE****MI*M1",
                "SVC*HC:99213*200.00*50.00**1",
                "CAS*CO*45*140.00",
                "PLB*1999999999*20260630*WO:R1*-5.25",
            ]
        )  # fmt: skip
    )
    assert ingest_file(eng, 1, f, SALT).status == "loaded"
    with tenant_session(eng, 1) as s:
        plb = s.scalars(select(m.PlbAdjustment)).one()
        assert plb.amount == Decimal("-5.25") and plb.reason_code == "WO"
        assert s.scalars(select(m.Payment)).one().trace_number == "T9"


def test_patient_hash_is_salted_and_deterministic():
    a = hashing.patient_hash("s1", "ABC")
    assert a == hashing.patient_hash("s1", " abc ") and a != hashing.patient_hash("s2", "ABC") and len(a) == 32


def test_999_and_277ca_records(world):
    eng = world["engine"]
    with tenant_session(eng, 1) as s:
        acks = s.scalars(select(m.Ack999)).all()
        assert all(a.transaction_status == "A" and a.transaction_set == "837" for a in acks)
        cats = {a.status_category for a in s.scalars(select(m.Ack277Ca))}
        assert cats == {"A2", "A3"}


# ------------------------------------------------------------------------------- PHI & tenants


def test_no_raw_phi_anywhere_in_the_database(world):
    eng = world["engine"]
    pattern = re.compile(r"SYNLAST|SYNFIRST|SYNM\d")
    with Session(eng) as s:
        for payload in s.scalars(select(m.Event.payload)):
            assert not pattern.search(payload)
        for model in (m.PatientRef,):
            for ref in s.scalars(select(model)):
                assert isinstance(ref.ref_hash, bytes) and len(ref.ref_hash) == 32
        assert s.scalar(select(func.count()).select_from(m.PatientRef)) > 1
    raw_db = (world["root"] / "db.sqlite").read_bytes()
    assert b"SYNLAST" not in raw_db and b"SYNFIRST" not in raw_db and b"SYNM0" not in raw_db


def test_two_tenants_get_separate_data_and_separate_hashes(world, tmp_path):
    eng = world["engine"]
    folder = tmp_path / "subset"
    folder.mkdir()
    for p in (*world["files"]["837"][:1], *world["files"]["835"][:2]):
        (folder / p.name).write_bytes(p.read_bytes())
    ingest_path(eng, 2, folder, "different-salt")
    n_b = count(eng, m.Claim, tenant=2)
    assert 0 < n_b < N_CLAIMS and count(eng, m.Claim, tenant=1) == N_CLAIMS
    with tenant_session(eng, 2) as s:
        assert {c.tenant_id for c in s.scalars(select(m.Claim))} == {2}
        hashes_b = {r.ref_hash for r in s.scalars(select(m.PatientRef))}
    with tenant_session(eng, 1) as s:
        hashes_a = {r.ref_hash for r in s.scalars(select(m.PatientRef))}
    assert hashes_a.isdisjoint(hashes_b)  # same people, different salt, different hash


def test_fee_schedule_loaded_with_exact_decimals(world):
    eng = world["engine"]
    with tenant_session(eng, 1) as s:
        row = s.scalars(select(m.FeeSchedule).where(m.FeeSchedule.cpt == "99213")).first()
        assert isinstance(row.allowed_amount, Decimal) and row.effective_date.isoformat() == "2025-01-01"


def test_bad_fee_schedule_fails(tmp_path):
    eng = failing_engine(tmp_path)
    f = tmp_path / "fee_schedule.csv"
    f.write_text("payer_id,cpt,modifier,allowed_amount,effective_date\nP1,99213,,abc,2025-01-01\n")
    res = ingest_file(eng, 1, f, SALT)
    assert res.status == "failed" and "line 2" in res.reason


# ------------------------------------------------------------------------------------- CLI


def test_cli_end_to_end(world, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("KRISNAI_SALT_TEST", "cli-salt")
    url = f"sqlite:///{tmp_path / 'cli.db'}"
    base = ["--db-url", url]
    assert cli.main([*base, "init-db"]) == 0
    assert cli.main([*base, "tenant-create", "CLI Clinic", "--salt-key", "KRISNAI_SALT_TEST"]) == 0
    assert cli.main([*base, "ingest", str(world["data"]), "--tenant", "1"]) == 0
    out = capsys.readouterr().out
    assert f"{len(world['results'])} loaded, 0 skipped, 0 failed" in out
    assert cli.main([*base, "ingest", str(world["data"]), "--tenant", "1"]) == 0
    assert f"0 loaded, {len(world['results'])} skipped, 0 failed" in capsys.readouterr().out


def test_cli_requires_salt_env_and_existing_tenant(world, tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'cli2.db'}"
    monkeypatch.delenv("KRISNAI_SALT_NOPE", raising=False)
    cli.main(["--db-url", url, "init-db"])
    with pytest.raises(SystemExit, match="tenant 1 does not exist"):
        cli.main(["--db-url", url, "ingest", str(world["data"]), "--tenant", "1"])
    cli.main(["--db-url", url, "tenant-create", "T", "--salt-key", "KRISNAI_SALT_NOPE"])
    with pytest.raises(SystemExit, match="KRISNAI_SALT_NOPE"):
        cli.main(["--db-url", url, "ingest", str(world["data"]), "--tenant", "1"])


def test_x12_error_is_the_only_failure_mode_for_bad_input():
    for junk in ("", "ISA", "ISA*" + "x" * 200, "hello world"):
        with pytest.raises(X12Error):
            read_transactions(junk)


def test_visits_csv_is_loaded_hashed_and_idempotent(world):
    eng = world["engine"]
    rows = list(csv.DictReader(open(world["data"] / "visits.csv", newline="", encoding="utf8")))
    assert count(eng, m.Visit) == len(rows) > 0
    with tenant_session(eng, 1) as s:
        v = s.scalars(select(m.Visit).order_by(m.Visit.visit_ref)).first()
        assert v.visit_ref == rows[0]["visit_id"] or v.visit_ref == min(r["visit_id"] for r in rows)
        # the member id is stored only as the salted hash shared with claims and remits
        ref = s.get(m.PatientRef, v.patient_ref_id)
        assert ref.ref_hash == hashing.patient_hash(
            SALT, next(r["patient_ref"] for r in rows if r["visit_id"] == v.visit_ref)
        )
    again = ingest_path(eng, 1, world["data"] / "visits.csv", SALT)
    assert [r.status for r in again] == ["skipped"]
    assert count(eng, m.Visit) == len(rows)
