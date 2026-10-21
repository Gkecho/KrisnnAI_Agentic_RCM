# ruff: noqa: E501
"""S3 of the live encounter stream: a seeded payer simulator that reads the Knowledge Book, deviates on purpose, and keeps a truth log."""

from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from krisnai.integrations.portal.bots import claim_status_bot
from krisnai.knowledge.demo import PAYER, demo_book
from krisnai.live.payer import PayerConfig, PayerSim
from krisnai.live.world import LiveWorld
from krisnai.synthea.types import PayerInfo, Person, SimClaim, SimLine
from tests.test_portal import PASSWORD, USER, driver_for

FIXTURE = Path(__file__).parent / "fixtures" / "openemr_837p_synthetic.x12"
NOW = date(2026, 10, 21)
INFO = PayerInfo(PAYER, "SYNAETNA Demo Payer", Decimal("1"), 14)


def claim(i: int, cpt: str = "99213", dos: date = date(2026, 3, 2), member: str | None = None) -> SimClaim:
    p = Person(member or f"SYNM{i:05d}", f"LAST{i}", "Synthetic", date(1980, 1, 1), "F")
    return SimClaim(f"C{i:05d}", INFO, "1999999984", p, dos, ["J029"], [SimLine(cpt, 1, Decimal("110.00"), Decimal("0"))], date(2026, 3, 3))


def sim(**kw) -> PayerSim:
    cfg = PayerConfig(**{k: kw.pop(k) for k in list(kw) if k in PayerConfig.__dataclass_fields__})
    return PayerSim(PAYER, "SYNAETNA Demo Payer", config=cfg, book=kw.pop("book", demo_book()), **kw)


def run(seed: int, n: int = 300, order=None, **kw) -> PayerSim:
    p = sim(seed=seed, pend_rate=0.1, deny_rate=0.15, deviation_rate=0.25, **kw)
    ids = list(range(n)) if order is None else order
    for i in ids:
        p.adjudicate(claim(i, cpt=["99213", "97110", "99214"][i % 3], dos=date(2025, 12, 10) if i % 2 else date(2026, 3, 2)), date(2026, 3, 3))
    return p


def rows(p: PayerSim) -> list[dict]:
    import csv
    import io

    return list(csv.DictReader(io.StringIO(p.truth_csv())))


def test_the_same_seed_gives_a_byte_identical_truth_log_whatever_the_order():
    a, b = run(7).truth_csv(), run(7).truth_csv()
    assert a == b and run(8).truth_csv() != a
    assert run(7, order=list(reversed(range(300)))).truth_csv() == a, "per-claim random streams, so arrival order does not matter"


def test_with_no_deviation_rate_the_payer_always_does_what_it_published():
    p = sim(seed=3, deny_rate=0.2, pend_rate=0.2)
    for i in range(200):
        p.adjudicate(claim(i, "97110", date(2026, 3, 2)), date(2026, 3, 3))
    assert not [r for r in rows(p) if r["deviation"]]


def test_the_deviation_rate_is_respected_and_every_deviation_contradicts_what_was_published():
    out = rows(run(7, n=600))
    dev = [r for r in out if r["deviation"]]
    assert 0.12 <= len(dev) / len(out) <= 0.32, len(dev) / len(out)
    assert {r["deviation"] for r in dev} >= {"wrong_denial", "stale_version", "unpublished_rule", "underpay_off_schedule"}
    for r in dev:
        assert r["published"] == "paid" and r["outcome"] in ("denied", "underpaid"), r


def test_the_payer_follows_the_book_a_2026_therapy_visit_needs_an_authorization_and_a_2025_one_does_not():
    p = sim(seed=1)
    d26 = p.adjudicate(claim(1, "97110", date(2026, 3, 2)), date(2026, 3, 3))
    d25 = p.adjudicate(claim(2, "97110", date(2025, 12, 10)), date(2026, 3, 3))
    assert (d26.outcome, d26.carc, d26.deviation) == ("denied", "197", "") and "prior authorization required" in d26.published_reason
    assert (d25.outcome, d25.deviation) == ("paid", "")
    p.grant_auth("SYNM00003", "97110")
    assert p.adjudicate(claim(3, "97110", date(2026, 3, 2)), date(2026, 3, 3)).outcome == "paid"


def test_a_stale_version_deviation_applies_a_rule_that_was_not_in_force_and_only_where_a_rule_changed():
    p = sim(seed=5, deviation_rate=1.0)
    for i in range(400):
        p.adjudicate(claim(i, ["99213", "97110"][i % 2], date(2025, 12, 10)), date(2026, 3, 3))
    out = rows(p)
    stale = [r for r in out if r["deviation"] == "stale_version"]
    assert stale and all(r["carc"] == "197" and r["published"] == "paid" for r in stale)
    assert all(int(r["claim_id"][1:]) % 2 == 1 for r in stale), "only 97110 has a rule that changed between years"


def test_a_pended_claim_shows_a_records_request_until_its_remit_date_then_the_final_answer():
    p = sim(seed=2, pend_rate=1.0)
    c = claim(1)
    d = p.adjudicate(c, date(2026, 3, 3))
    assert d.pended and d.remit_date == date(2026, 3, 3) + timedelta(days=35)
    cat, _, paid, _, reason, records = p.status("C00001", date(2026, 3, 20))
    assert (cat, paid, records) == ("P1", 0, True) and "Records requested" in reason
    cat2, _, paid2, _, _, rec2 = p.status("C00001", d.remit_date)
    assert cat2 == "F1" and paid2 == Decimal("72.00") and not rec2


def test_remits_come_due_once_in_claim_order_and_not_early():
    p = sim(seed=2)
    for i in (3, 1, 2):
        p.adjudicate(claim(i), date(2026, 3, 3))
    assert p.remits_due(date(2026, 3, 10)) == []
    due = p.remits_due(date(2026, 3, 17))
    assert [d.claim.claim_id for d in due] == ["C00001", "C00002", "C00003"]
    assert p.remits_due(date(2026, 3, 30)) == []


def test_an_underpayment_pays_less_than_the_schedule_and_says_so_in_the_truth_log():
    p = sim(seed=9, deviation_rate=1.0)
    out = []
    for i in range(80):
        d = p.adjudicate(claim(i, "99213", date(2026, 3, 2)), date(2026, 3, 3))
        if d.deviation == "underpay_off_schedule":
            out.append(d)
    assert out
    for d in out:
        assert d.claim.paid < Decimal("72.00") and d.outcome == "underpaid"


def _world(**kw) -> LiveWorld:
    p = sim(seed=4, **kw)
    p.enrol("SYNLV00051")
    return LiveWorld(p, NOW)


def test_a_clearinghouse_rejection_never_reaches_the_payer_and_a_denial_is_a_different_thing():
    w = _world(deny={"99213": "50"})
    text = FIXTURE.read_text(encoding="utf-8")
    _, _, ok = w.accept_claims(text, NOW)
    claim_id = ok[0]["claim"]
    d = w.payer.adjudicate(w.accepted[0], NOW)
    _, _, bad = w.accept_claims(text.replace("PI*SYNAETNA", "PI*"), NOW)
    assert not bad[0]["ok"] and bad[0]["claim"] in w.rejected
    assert list(w.payer.cases) == [claim_id] and d.outcome == "denied"
    assert [r["claim_id"] for r in rows(w.payer)] == [claim_id], "the truth log holds payer decisions only, not clearinghouse rejections"


def test_the_portal_bot_reads_the_payers_live_state_as_the_clock_moves(tmp_path):
    w = _world(pend_rate=1.0, deny_rate=1.0)
    w.accept_claims(FIXTURE.read_text(encoding="utf-8"), NOW)
    c = w.accepted[0]
    d = w.payer.adjudicate(c, NOW)
    assert d.pended and d.outcome == "denied"
    driver, _ = driver_for(w)
    first = claim_status_bot(driver, USER, PASSWORD, [c.claim_id], tmp_path / "e1")[0]
    assert first.outcome == "read" and first.status == "Pending: in review" and "Records requested" in first.reason
    assert first.records_requested is True
    w.advance(d.remit_date)
    driver2, _ = driver_for(w)
    last = claim_status_bot(driver2, USER, PASSWORD, [c.claim_id], tmp_path / "e2")[0]
    assert last.status == "Finalized: denied" and last.paid == "0.00" and not last.records_requested


def test_the_status_bots_view_of_an_unknown_claim_is_not_found():
    w = _world()
    assert w.claim_state("NOPE")[0] == "E1"
