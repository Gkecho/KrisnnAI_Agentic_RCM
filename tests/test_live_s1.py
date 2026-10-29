"""S1 of the live encounter stream, without Docker: the payer sim, the live clearinghouse world, the billing guard.

The 837P fixture was written by OpenEMR's own generator for a synthetic patient (see docs/plan_live_encounter_stream.md).
"""

import json
import subprocess
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from krisnnai.ingest import p837, r835
from krisnnai.ingest.x12 import read_transactions
from krisnnai.integrations.openemr import billing
from krisnnai.live.payer import PayerSim
from krisnnai.live.world import LiveWorld
from krisnnai.synthea import x12out

FIXTURE = Path(__file__).parent / "fixtures" / "openemr_837p_synthetic.x12"
TODAY = date(2026, 10, 21)
ROOT = Path(__file__).resolve().parents[1] / "krisnnai"


def _text() -> str:
    return FIXTURE.read_text(encoding="utf-8")


def _payer(**kw) -> PayerSim:
    return PayerSim("SYNAETNA", "SYNAETNA Demo Payer", **kw)


def test_our_parser_reads_openemrs_837():
    rec = p837.parse(read_transactions(_text())[0], "s")[0]
    assert rec.total_charge == Decimal("110.00") and [ln.cpt for ln in rec.lines] == ["99213"]
    assert rec.payer_name.startswith("SYNAETNA") and rec.provider_npi == "1999999984"


def test_the_payer_pays_the_fee_schedule_less_coinsurance():
    p = _payer()
    claim = p.to_sim_claims(_text(), TODAY)[0]
    d = p.decide(claim, date(2026, 11, 7))
    assert d.outcome == "paid" and claim.scenario == "clean"
    assert (claim.billed, claim.paid, claim.pr) == (Decimal("110.00"), Decimal("72.00"), Decimal("18.00"))


def test_a_configured_denial_comes_back_as_carc_50_in_the_835():
    p = _payer(deny={"99213": "50"})
    claim = p.to_sim_claims(_text(), TODAY)[0]
    d = p.decide(claim, date(2026, 11, 7))
    text = x12out.write_835(claim.payer, date(2026, 11, 7), [claim], 7001)
    assert d.outcome == "denied" and claim.paid == 0
    r835.parse(read_transactions(text)[0], "s")  # our own parser reads it without complaint
    assert f"CLP*{claim.claim_id}*4*" in text and "CAS*CO*50*110~" in text


def test_the_live_world_accepts_a_well_formed_claim_and_queues_it_for_the_payer():
    w = LiveWorld(_payer(), TODAY)
    c999, c277, results = w.accept_claims(_text(), TODAY)
    assert results[0]["ok"] and len(w.accepted) == 1 and "IK5*A" in c999 and "STC*A2" in c277


def test_a_technical_problem_is_a_clearinghouse_rejection_not_a_payer_denial():
    w = LiveWorld(_payer(), TODAY)
    broken = _text().replace("PI*SYNAETNA", "PI*")
    c999, c277, results = w.accept_claims(broken, TODAY)
    assert not results[0]["ok"] and "payer id" in results[0]["reason"]
    assert not w.accepted and w.rejected, "a rejected claim never reaches the payer"
    assert "IK5*R" in c999 and "STC*A3" in c277


def test_eligibility_follows_what_the_payer_enrolled():
    w = LiveWorld(_payer(), TODAY)
    w.payer.enrol("SYNLV00001")
    w.payer.enrol("SYNLV00002", active=False)
    assert w.eligibility("SYNAETNA", "SYNLV00001", TODAY).active
    assert not w.eligibility("SYNAETNA", "SYNLV00002", TODAY).active
    assert not w.eligibility("SYNAETNA", "NOBODY", TODAY).found


def test_a_charge_needs_an_approval_record_and_content():
    ch = billing.Charge(1, 2, "M", "SYNAETNA", "P", [("J02.9", "x")], [("99213", "v", 1, "110.00")])
    with pytest.raises(billing.BillingError, match="approval"):
        billing.charge_and_837(ch, " ", runner=lambda *a, **k: pytest.fail("must not reach docker"))
    with pytest.raises(billing.BillingError, match="payer id"):
        billing.charge_and_837(billing.Charge(1, 2, "M", "", "P", [("J02.9", "x")], []), "policy:p")


def test_the_billing_writer_only_targets_our_container_and_fails_cleanly_when_it_is_down():
    calls = []

    def runner(*args, stdin=None):
        calls.append(args)
        return subprocess.CompletedProcess(args, 1, "", "no such container")

    ch = billing.Charge(1, 2, "M", "SYNAETNA", "P", [("J02.9", "x")], [("99213", "v", 1, "110.00")])
    with pytest.raises(billing.BillingError, match="not reachable"):
        billing.charge_and_837(ch, "policy:p", runner=runner)
    assert billing.CONTAINER in " ".join(calls[0]) and billing.CONTAINER == "krisnnai-openemr-openemr-1"


def test_the_billing_writer_returns_the_837_that_openemr_wrote():
    def runner(*args, stdin=None):
        out = json.dumps({"x12": _text(), "log": ""}) if args[0] == "exec" else ""
        return subprocess.CompletedProcess(args, 0, out, "")

    ch = billing.Charge(51, 1635, "M", "SYNAETNA", "P", [("J02.9", "x")], [("99213", "v", 1, "110.00")])
    assert billing.charge_and_837(ch, "policy:demo")["x12"].startswith("ISA")


def test_no_agent_or_bot_can_see_the_payer_simulator():
    """The payer's rules reach the agents only as X12 files and portal pages, never as an import."""
    offenders = []
    for folder in ("agents", "engine", "integrations/clearinghouse/bots.py", "integrations/portal"):
        base = ROOT / folder
        for f in ([base] if base.is_file() else base.rglob("*.py")):
            if "krisnnai.live" in f.read_text(encoding="utf-8"):
                offenders.append(str(f.relative_to(ROOT)))
    assert offenders == []


def _openemr_up() -> bool:
    try:
        import httpx

        return httpx.get("http://127.0.0.1:8300/apis/default/fhir/metadata", timeout=5).status_code == 200
    except Exception:  # noqa: BLE001
        return False


@pytest.mark.slow
@pytest.mark.skipif(not _openemr_up(), reason="the local OpenEMR is not running")
def test_s1_one_denied_encounter_end_to_end(tmp_path):
    from krisnnai.live.s1 import run_s1

    res = run_s1(Path("out/openemr"), tmp_path / "s1", date(2026, 10, 21), log=lambda *_: None)
    sm = res.summary
    assert sm["engine_status"] == "ok" and sm["files_failed"] == 0 and sm["payer_outcome"] == "denied"
    assert [c["agent"] for c in sm["cards_for_this_claim"]] == ["a8_denial"]
    assert sm["claim"] == f"{sm['patient_pid']}-{sm['encounter']}", "the card traces back to the OpenEMR encounter"
    assert not list((tmp_path / "s1" / "inbox").glob("truth*")), "the payer's decision never enters the engine's inbox"
