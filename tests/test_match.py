"""M3 tests: claim <-> remit <-> payment matching on the synthetic set, plus planted fallback cases."""

from __future__ import annotations

import csv
import json
from datetime import datetime

import pytest
from sqlalchemy import func, select

import krisnnai.model as m
from krisnnai import cli
from krisnnai.ingest.loader import ingest_path
from krisnnai.match import run_matching
from krisnnai.model import tenant_session
from tests.fixtures import make_synthetic as ms
from tests.test_ingest import SALT, make_engine

N_CLAIMS = 120


@pytest.fixture(scope="module")
def data(tmp_path_factory):
    root = tmp_path_factory.mktemp("m3")
    ms.generate(root / "data", seed=7, n_claims=N_CLAIMS)
    return root / "data"


@pytest.fixture()
def eng(data, tmp_path):
    engine = make_engine(tmp_path / "db.sqlite")
    ingest_path(engine, 1, data, SALT)
    return engine


def ground_truth(data):
    with open(data / "ground_truth.csv", newline="", encoding="utf8") as f:
        return list(csv.DictReader(f))


def remit_for(s, claim_submitter_id):
    return s.scalars(select(m.Remit).where(m.Remit.claim_submitter_id == claim_submitter_id)).one()


def claim_for(s, claim_submitter_id):
    return s.scalars(select(m.Claim).where(m.Claim.claim_submitter_id == claim_submitter_id)).one()


def test_synthetic_matches_everything_and_records_the_rule(eng, data):
    rep = run_matching(eng, 1)
    assert rep.remits.total > 0
    assert rep.remits.rate >= 0.99 and rep.lines.rate >= 0.99
    assert rep.remits.by_method == {"clp01": rep.remits.total}
    with tenant_session(eng, 1) as s:
        assert s.scalar(select(func.count()).select_from(m.Remit).where(m.Remit.claim_id.is_(None))) == 0
        assert s.scalar(select(func.count()).select_from(m.Remit).where(m.Remit.match_method.is_(None))) == 0
        assert s.scalar(select(func.count()).select_from(m.RemitLine).where(m.RemitLine.match_method.is_(None))) == 0
        # a matched remit points at a claim with the same CLM01 and payer
        r = s.scalars(select(m.Remit)).first()
        c = s.get(m.Claim, r.claim_id)
        assert c.claim_submitter_id == r.claim_submitter_id
        assert c.payer_id == s.get(m.Payment, r.payment_id).payer_id


def test_ground_truth_claims_with_and_without_a_remit(eng, data):
    rep = run_matching(eng, 1)
    rejected = {g["claim_id"] for g in ground_truth(data) if g["issue_type"] == "rejection"}
    with tenant_session(eng, 1) as s:
        matched = set(s.scalars(select(m.Claim.claim_submitter_id).join(m.Remit, m.Remit.claim_id == m.Claim.id)))
        assert not (matched & rejected), "a rejected claim has no 835 and must stay without a remit"
        for g in ground_truth(data):
            if g["issue_type"] in ("denial", "timely_filing", "underpayment"):
                assert g["claim_id"] in matched, g
    assert rep.acks.rate == 1.0  # every claim has a 277CA, rejected ones included


def test_every_payment_reconciles(eng):
    rep = run_matching(eng, 1)
    assert rep.payments.payments > 0
    assert rep.payments.mismatched == []


def test_second_run_changes_nothing(eng):
    first = run_matching(eng, 1)
    second = run_matching(eng, 1)
    assert first.remits.newly_matched > 0
    assert (second.remits.newly_matched, second.lines.newly_matched, second.acks.newly_matched) == (0, 0, 0)
    assert second.remits.matched == first.remits.matched
    assert second.lines.matched == first.lines.matched


def test_fallback_rules_and_unmatched_reasons(eng):
    with tenant_session(eng, 1) as s:
        remits = list(s.scalars(select(m.Remit).order_by(m.Remit.id)))[:5]
        by_clp07, by_patient, amount_off, nothing, _ = remits
        want = {r.id: s.get(m.Claim, claim_for(s, r.claim_submitter_id).id).id for r in remits}
        by_clp07.claim_submitter_id = "NOPE1"
        by_patient.claim_submitter_id = "NOPE2"
        by_patient.payer_claim_control_number = "NOPE-PCN2"
        amount_off.claim_submitter_id = "NOPE3"
        amount_off.payer_claim_control_number = "NOPE-PCN3"
        amount_off.total_charge += 1
        nothing.claim_submitter_id = "NOPE4"
        nothing.payer_claim_control_number = "NOPE-PCN4"
        nothing.patient_ref_id = None
        ids = (by_clp07.id, by_patient.id, amount_off.id, nothing.id)
        s.commit()

    rep = run_matching(eng, 1)
    with tenant_session(eng, 1) as s:
        a, b, c, d = (s.get(m.Remit, i) for i in ids)
        assert (a.claim_id, a.match_method) == (want[ids[0]], "clp07")
        assert (b.claim_id, b.match_method) == (want[ids[1]], "patient_dos_amount")
        assert c.claim_id is None and d.claim_id is None
    assert rep.remits.unmatched_reasons == {"amount_mismatch": 1, "no_candidate": 1}
    assert rep.lines.unmatched_reasons["claim_not_matched"] >= 2


def test_two_candidate_claims_are_ambiguous_not_guessed(eng):
    with tenant_session(eng, 1) as s:
        remits = list(s.scalars(select(m.Remit).order_by(m.Remit.id)))
        target = remits[0]
        claim = claim_for(s, target.claim_submitter_id)
        twin = next(c for c in s.scalars(select(m.Claim)) if c.payer_id == claim.payer_id and c.id != claim.id)
        twin.patient_ref_id, twin.service_date, twin.total_charge = (
            claim.patient_ref_id,
            claim.service_date,
            claim.total_charge,
        )
        target.claim_submitter_id, target.payer_claim_control_number = "NOPE", "NOPE-PCN"
        target_id = target.id
        s.commit()

    rep = run_matching(eng, 1)
    with tenant_session(eng, 1) as s:
        assert s.get(m.Remit, target_id).claim_id is None
    assert rep.remits.unmatched_reasons == {"ambiguous": 1}


def test_wrong_payer_is_reported_not_matched(eng):
    with tenant_session(eng, 1) as s:
        target = s.scalars(select(m.Remit).order_by(m.Remit.id)).first()
        claim = claim_for(s, target.claim_submitter_id)
        other = s.scalars(select(m.Payer).where(m.Payer.id != claim.payer_id)).first()
        pay = s.get(m.Payment, target.payment_id)
        for r in s.scalars(select(m.Remit).where(m.Remit.payment_id == pay.id)):
            r.patient_ref_id = None
        pay.payer_id = other.id
        target.payer_claim_control_number = "NOPE-PCN"
        s.commit()
    rep = run_matching(eng, 1)
    assert rep.remits.unmatched_reasons["payer_mismatch"] >= 1


def test_as_of_before_anything_was_known_matches_nothing(eng):
    rep = run_matching(eng, 1, as_of=datetime(2000, 1, 1))
    assert rep.remits.total == 0 and rep.remits.matched == 0
    with tenant_session(eng, 1) as s:
        assert s.scalar(select(func.count()).select_from(m.Remit).where(m.Remit.claim_id.is_not(None))) == 0


def test_cross_tenant_never_links(eng, data):
    ingest_path(eng, 2, data, SALT)
    run_matching(eng, 1)
    with tenant_session(eng, 2) as s:  # tenant 2 has not been matched
        assert s.scalar(select(func.count()).select_from(m.Remit).where(m.Remit.claim_id.is_not(None))) == 0
    run_matching(eng, 2)
    for tenant in (1, 2):
        with tenant_session(eng, tenant) as s:
            claim_ids = set(s.scalars(select(m.Claim.id)))
            assert set(s.scalars(select(m.Remit.claim_id))) <= claim_ids


def test_cli_match_prints_report(eng, tmp_path, capsys):
    url = str(eng.url)
    assert cli.main(["--db-url", url, "match", "--tenant", "1", "--json"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["remits"]["rate"] >= 0.99
    assert cli.main(["--db-url", url, "match", "--tenant", "1"]) == 0
    assert "remit -> claim" in capsys.readouterr().out
