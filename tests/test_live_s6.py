# ruff: noqa: E501
"""S6 of the live encounter stream: the realistic world (catalog, payer network, outcomes from claim content, wide transcripts)."""

import csv
import io
from collections import Counter
from datetime import date
from decimal import Decimal

from krisnnai.knowledge.demo import network_book
from krisnnai.live.catalog import CONDITIONS, SERVICES
from krisnnai.live.emr import FakeEmr
from krisnnai.live.network import PAYER_IDS, Network
from krisnnai.live.stream import StreamConfig, run_stream
from krisnnai.live.transcripts import generate_wide
from krisnnai.synthea import x12out
from krisnnai.synthea.types import PayerInfo, Person, SimClaim, SimLine


def claim(i, cpts=("99213",), dos=date(2026, 3, 2), dx=("J029",), member=None, sub=date(2026, 3, 3)):
    p = Person(member or f"M{i:05d}", "L", "S", date(1980, 1, 1), "F")
    lines = [SimLine(c, 1, Decimal("200"), Decimal("0")) for c in cpts]
    return SimClaim(f"C{i:05d}", PayerInfo("X", "X", Decimal(1), 14), "1999999984", p, dos, list(dx), lines, sub)


def quiet(net: Network) -> Network:
    """The same payers with every random layer off, so only the published rules and the claim's facts decide."""
    return Network(net.seed, pend_rate=0.0, deny_rate=0.0, deviation_rate=0.0)


def cause(net, payer, cl, when=date(2026, 3, 3)):
    return net.payer(payer).adjudicate(cl, when)


# ---------------------------------------------------------------------------------------------- catalog
def test_catalog_sizes_uniqueness_and_keywords():
    assert len(CONDITIONS) >= 45 and len(SERVICES) >= 35
    assert len({c.icd10 for c in CONDITIONS}) == len(CONDITIONS) and len({s.cpt for s in SERVICES}) == len(SERVICES)
    for c in CONDITIONS:
        assert c.keywords and all(k == k.lower() for k in c.keywords), c.icd10
    for s in SERVICES:
        assert all(k == k.lower() for k in s.keywords), s.cpt
        if not s.family.startswith("em_") and s.family not in ("preventive", "emergency"):
            assert s.keywords, s.cpt
        if s.needs_time:
            assert s.time_range[1] >= s.time_range[0] > 0
    assert {"99213", "99214", "99203", "99204", "97110", "71046", "81002", "96372"} <= {s.cpt for s in SERVICES}
    assert {c.specialty for c in CONDITIONS} >= {"primary care", "orthopedics", "cardiology", "pulmonology", "dermatology", "mental health", "obstetrics and gynecology", "pediatrics", "emergency"}
    assert any(c.chronic for c in CONDITIONS) and any(c.unspecified for c in CONDITIONS) and any(c.needs_laterality for c in CONDITIONS)


# ---------------------------------------------------------------------------------------------- network
def test_same_seed_same_payer_picks_and_same_truth_and_a_different_seed_differs():
    def world(seed):
        net = Network(seed)
        picks = [net.pick_payer(f"v{i}") for i in range(80)]
        for i, p in enumerate(picks):
            net.payer(p).adjudicate(claim(i, ("99214", "72148") if i % 2 else ("99213",)), date(2026, 3, 3))
        return picks, "".join(net.payer(p).truth_csv() for p in PAYER_IDS)

    assert world(7) == world(7)
    assert world(7)[0] != world(8)[0]


def test_market_share_spreads_over_600_visits():
    net = Network(7)
    n = Counter(net.pick_payer(f"v{i}") for i in range(600))
    assert set(n) == set(PAYER_IDS)
    for pid, prof in net.profiles.items():
        assert abs(n[pid] / 600 - prof.share) < 0.07, (pid, n[pid])


def test_the_book_publishes_every_family_for_all_six_payers_without_conflicts():
    b = network_book()
    d25, d26 = date(2025, 6, 1), date(2026, 6, 1)
    for pid in PAYER_IDS:
        for fam in ("coverage", "prior_auth", "medical_necessity"):
            found = [b.lookup(pid, fam, s.cpt, {"service_date": d}, date(2026, 10, 1)) for s in SERVICES for d in (d25, d26)]
            assert not [f for f in found if not f.ok and f.problem.kind != "no_rule"], (pid, fam)
            if not (pid == "SYNMCARE" and fam == "prior_auth"):  # the Medicare-like payer publishes no authorization rules
                assert any(f.ok for f in found), (pid, fam)
        assert b.lookup(pid, "billing", "FILING", {"service_date": d26}, date(2026, 10, 1)).ok, pid
    ap = b.lookup("SYNCIGNA", "denial_appeal", "*", {"denial_notification_date": date(2026, 2, 1)}, date(2026, 10, 1))
    assert ap.ok and ap.rule.content["window_days"] == 120
    # a rule that changes on 2026-01-01: UNITED requires authorization for therapy only from 2026
    pa = lambda d: b.lookup("SYNUNITED", "prior_auth", "97110", {"service_date": d}, date(2026, 10, 1)).rule.content["required"]  # noqa: E731
    assert pa(d25) is False and pa(d26) is True


def test_each_kind_of_trouble_occurs_and_is_attributed_to_its_cause():
    net = quiet(Network(7))
    a, u = "SYNAETNA", "SYNUNITED"
    assert cause(net, a, claim(1, ("99214", "72148"), dx=("M5416",))).cause == "no_prior_auth"
    net.payer(a).grant_auth("M00002", "72148")
    d = cause(net, a, claim(2, ("72148",), dx=("M5416",)))
    assert d.outcome == "paid" and d.cause == "paid"
    assert cause(net, a, claim(3, ("72148",), dx=("J029",), member="M00003")).cause == "no_prior_auth"
    mc = "SYNMCARE"
    d = cause(net, mc, claim(5, ("83036",), dx=("I10",)))
    assert d.cause == "no_medical_necessity" and d.carc == "50"
    d = cause(net, mc, claim(6, ("80053", "36415")))
    assert d.cause == "bundled" and d.carc == "97"
    d = cause(net, mc, claim(7, ("99395",), dx=("Z0000",)))
    assert d.cause == "not_covered" and d.carc == "96"
    # duplicate: same patient, day and services
    cause(net, u, claim(8, ("99213",), member="MDUP"))
    d = cause(net, u, claim(9, ("99213",), member="MDUP"))
    assert d.cause == "duplicate" and d.carc == "18"
    # timely filing: SYNUNITED allows 90 days for a 2026 service
    d = cause(net, u, claim(10, dos=date(2026, 3, 2), sub=date(2026, 8, 1)), when=date(2026, 8, 1))
    assert d.cause == "timely_filing" and d.carc == "29"
    d = cause(net, "SYNBLUE", claim(11, dos=date(2026, 3, 2), sub=date(2026, 8, 1)), when=date(2026, 8, 1))
    assert d.cause == "paid"  # the same age is inside SYNBLUE's 365-day limit
    # coverage lapsed and other insurance primary
    net.payer(u).enrol("MLAPSE", False)
    assert cause(net, u, claim(12, member="MLAPSE")).carc == "27"
    net.payer(u).set_other_primary("MOTH")
    assert cause(net, u, claim(13, member="MOTH")).cause == "other_primary"
    assert cause(net, u, claim(14, member="MOTH")).carc == "22"


def test_ordinary_denials_modifier_and_missing_information_pends_and_underpayment_occur():
    net = Network(7, pend_rate=0.3, deny_rate=0.5, deviation_rate=0.0)
    sim = net.payer("SYNAETNA")
    for i in range(300):
        sim.adjudicate(claim(i, ("99213", "10060") if i % 2 else ("99213",), dx=("J029",)), date(2026, 3, 3))
    carcs = Counter(d.carc for d in sim.cases.values() if d.cause.startswith("ordinary"))
    assert {"4", "16", "50", "97"} <= set(carcs)
    assert any(d.pended for d in sim.cases.values())
    # underpayment against the fee schedule: forced by a high underpay propensity, recorded as a deviation
    n2 = Network(7, deviation_rate=0.0)
    under = n2.payer("SYNMCAID")
    object.__setattr__(under.profile, "underpay_rate", 1.0)
    d = under.adjudicate(claim(1), date(2026, 3, 3))
    full = Decimal(under.fees["99213"])
    assert d.outcome == "underpaid" and d.deviation == "underpay_off_schedule" and d.claim.lines[0].allowed < full


def test_deviations_are_a_configured_share_and_always_recorded():
    net = Network(7, deviation_rate=0.25, pend_rate=0.0, deny_rate=0.0)
    sim = net.payer("SYNCIGNA")
    for i in range(600):
        sim.adjudicate(claim(i, ("99213",)), date(2026, 3, 3))
    rows = list(csv.DictReader(io.StringIO(sim.truth_csv())))
    dev = [r for r in rows if r["deviation"]]
    assert 0.15 < len(dev) / 600 < 0.35
    assert all(d.cause.startswith("deviation:") for d in sim.cases.values() if d.deviation)
    off = Network(7, deviation_rate=0.0, pend_rate=0.0, deny_rate=0.0).payer("SYNCIGNA")
    for i in range(200):
        off.adjudicate(claim(i), date(2026, 3, 3))
    assert not [r for r in csv.DictReader(io.StringIO(off.truth_csv())) if r["deviation"]]


def test_every_carc_the_network_uses_can_be_written_into_an_835():
    for c in ("27", "22", "18", "29", "96", "97", "197", "50", "16", "4", "31"):
        assert x12out.DENIAL_RARC.get(c) or x12out.EXTRA_RARC.get(c), c


# ---------------------------------------------------------------------------------------------- transcripts
def test_generate_wide_is_deterministic_and_varied():
    a = generate_wide(7, 200)
    assert a == generate_wide(7, 200) and a != generate_wide(8, 200)
    assert len({v.expected.dx for v in a}) >= 35 and len({s for v in a for s in v.expected.services}) >= 30
    assert len({v.text.splitlines()[1] for v in a}) >= 8  # varied openings
    problems = Counter(p for v in a for p in v.expected.problems)
    assert {"missing_plan", "unsigned", "status_unclear", "two_problems", "missing_laterality", "missing_time", "missing_necessity"} <= set(problems)
    pressure = Counter(p for v in a for p in v.expected.pressure)
    assert {"needs_auth", "no_auth_on_file", "bundle_pair", "late_billing", "duplicate", "coverage_lapsed", "other_primary", "necessity_mismatch"} <= set(pressure)
    assert all(v.expected.route == "coder" for v in a if v.expected.problems)
    assert any(v.expected.laterality for v in a) and any(v.expected.units > 1 for v in a)
    # the share of problem visits is not fixed
    shares = {round(sum(bool(v.expected.problems) for v in generate_wide(s, 100)) / 100, 2) for s in range(1, 8)}
    assert len(shares) > 3
    # the mix is configurable
    clean = generate_wide(7, 100, mix={k: 0.0 for k in ("missing_plan", "two_problems", "status_unclear", "unsigned", "thin_chronic", "missing_laterality", "missing_time", "missing_necessity")})
    assert not any(v.expected.problems for v in clean)
    dups = [v for v in a if v.expected.duplicate_of]
    assert dups and all(a[v.expected.duplicate_of - 1].member == v.member and a[v.expected.duplicate_of - 1].day == v.day for v in dups)


# ---------------------------------------------------------------------------------------------- the stream
def test_a_40_visit_network_stream_completes_with_several_payers_and_outcomes(tmp_path):
    out = tmp_path / "r"
    cfg = StreamConfig(count=40, per_day=8, engine=False, bots=False, serve=False, payers="network")
    s = run_stream(out, cfg, FakeEmr(), log=lambda *_: None)
    assert s["encounters"] == 40 and s["remits_issued"] == s["stages"]["adjudicated"] > 20
    truth = list(csv.DictReader((out / "truth_payers.csv").read_text("utf-8").splitlines()))
    assert len({r["payer_id"] for r in truth}) >= 4
    assert len({r["cause"] for r in truth}) >= 3
    log = list(csv.DictReader((out / "truth.csv").read_text("utf-8").splitlines()))
    assert len(log) == len(truth) and len({r["outcome"] for r in log}) >= 2
    fee = (out / "inbox" / "fee_schedule.csv").read_text("utf-8")
    assert all(f"\n{p}," in fee for p in PAYER_IDS)
    again = run_stream(tmp_path / "r2", cfg, FakeEmr(), log=lambda *_: None)
    assert (tmp_path / "r2" / "truth.csv").read_text("utf-8") == (out / "truth.csv").read_text("utf-8") and again["payer_outcomes"] == s["payer_outcomes"]


def test_the_default_single_payer_stream_is_unchanged(tmp_path):
    out = tmp_path / "r"
    run_stream(out, StreamConfig(count=10, engine=False, bots=False, serve=False), FakeEmr(), log=lambda *_: None)
    assert not (out / "truth_payers.csv").exists()
    assert {r["payer_id"] for r in csv.DictReader((out / "inbox" / "fee_schedule.csv").read_text("utf-8").splitlines())} == {"SYNAETNA"}
