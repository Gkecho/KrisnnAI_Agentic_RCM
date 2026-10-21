# ruff: noqa: E501
"""S8 of the live encounter stream: the bots reply to the payer's reply (corrected claims, appeals, disputes, records), with FakeEmr and in-process servers."""

import csv
import json
import re
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from krisnai.knowledge import Book
from krisnai.knowledge.book import Rule
from krisnai.knowledge.demo import DEMO, PAYER, demo_book
from krisnai.live import score
from krisnai.live.emr import FakeEmr
from krisnai.live.payer import Decision
from krisnai.live.payer_replies import ReplySim
from krisnai.live.responder import APPROVAL_RE, RemitView, Responder, break_837, read_remit
from krisnai.live.stream import SimulatedCrash, Stream, StreamConfig, run_stream
from krisnai.synthea.types import PayerInfo, Person, SimClaim, SimLine

CFG = dict(count=40, engine=False, bots=False, serve=False, replies=True, deny_rate=0.4, deviation_rate=0.5, pend_rate=0.3, reject_rate=0.3)
quiet = lambda *_: None  # noqa: E731


def cfg(**kw) -> StreamConfig:
    return StreamConfig(**{**CFG, **kw})


def events(out: Path) -> list[dict]:
    return [json.loads(ln) for ln in (out / "events.jsonl").read_text("utf-8").splitlines()]


def state(out: Path) -> dict:
    return json.loads((out / "state.json").read_text("utf-8"))


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    out = tmp_path_factory.mktemp("s8") / "r"
    summary = run_stream(out, cfg(), FakeEmr(), log=quiet)
    return out, summary


# ---------------------------------------------------------------------------------------------------- every kind is sent and answered
def test_every_reply_kind_is_sent_and_the_payer_answers_it(run):
    out, s = run
    sent = s["replies"]["sent"]
    assert {"corrected_claim", "appeal", "dispute", "records"} <= set(sent), sent
    st = state(out)["enc"]
    for e in st.values():
        for r in e.get("rounds", []):
            assert r["answered"], f"{e['claim']} round {r['round']} was never answered"
        assert e["stage"] in ("settled", "patient_balance", "review", "pending_coder"), (e["claim"], e["stage"])
    kinds = {r["answer"]["kind"] for e in st.values() for r in e.get("rounds", []) if r.get("answer")}
    assert {"appeal", "dispute", "records", "corrected_claim"} <= kinds
    steps = {e["step"] for e in events(out)}
    assert {"8 reply: appeal", "8 reply: corrected claim", "8 reply: dispute", "8 reply: records", "8 reply: answer", "8 reply: review"} <= steps


def test_a_claim_stopped_at_the_coder_is_untouched(run):
    out, _ = run
    waiting = [e for e in state(out)["enc"].values() if e["stage"] == "pending_coder"]
    assert waiting and all(not e.get("rounds") and not e.get("billed_on") for e in waiting)


def test_the_truth_file_for_first_decisions_keeps_its_columns(run):
    from krisnai.live.payer import TRUTH_COLUMNS

    out, _ = run
    assert (out / "truth.csv").read_text("utf-8").splitlines()[0].split(",") == TRUTH_COLUMNS
    assert (out / "truth_replies.csv").exists()


# ---------------------------------------------------------------------------------------------------- the published rules
def _decision(deviation: str, carc: str, i: int) -> Decision:
    info = PayerInfo("SYNAETNA", "SYNAETNA Demo Payer", Decimal("1"), 14)
    c = SimClaim(f"C{i}", info, "1234567893", Person("M", "L", "F", date(1980, 1, 1), "F"), date(2026, 3, 2), ["J029"], [SimLine("99213", 1, Decimal("110.00"), Decimal("0"))], date(2026, 3, 3))
    return Decision(c, "denied", "x", carc, deviation, "paid" if deviation else "", "", False, date(2026, 3, 3), date(2026, 3, 17))


def test_an_appeal_that_cites_a_real_contradiction_is_overturned_far_more_often():
    sim = ReplySim(7, {"99213": "90.00"})
    n = 600
    real = sum(sim.answer(_decision("stale_version", "197", i), "appeal", 1, cites_rule=True).outcome == "overturned" for i in range(n)) / n
    ordinary = sum(sim.answer(_decision("", "197", i), "appeal", 1, cites_rule=False).outcome == "overturned" for i in range(n)) / n
    wrong_cite = sum(sim.answer(_decision("", "197", i), "appeal", 1, cites_rule=True).outcome == "overturned" for i in range(n)) / n
    assert real > 0.8 and ordinary < 0.45 and real > ordinary + 0.4
    assert wrong_cite <= ordinary + 0.08, "citing a rule the payer did not really contradict does not help"


def test_the_reply_answer_depends_only_on_seed_claim_and_round():
    a = ReplySim(7, {"99213": "90.00"}).answer(_decision("", "50", 1), "appeal", 1)
    b = ReplySim(7, {"99213": "90.00"}).answer(_decision("", "50", 1), "appeal", 1)
    assert a == b


def test_the_responder_finds_a_denial_that_contradicts_the_published_rule_and_cites_it():
    r = Responder(demo_book())
    ctx = {"claim_id": "1-1", "payer_id": PAYER, "member": "M", "dos": "2025-06-02", "cpt": "97110", "cpts": ["97110"], "lines": [("97110", 1, Decimal("80"))], "active_271": True, "notified": "2026-03-01"}
    f = r.contradiction(ctx, "197", date(2026, 3, 2))
    assert f and f.rule_id == "pa-97110" and f.version == 1 and "NOT required" in f.ground
    assert r.contradiction({**ctx, "dos": "2026-06-02"}, "197", date(2026, 3, 2)) is None, "in 2026 the rule does require authorization: the denial is consistent"
    f2 = r.contradiction({**ctx, "cpt": "99213", "dos": "2026-03-02"}, "31", date(2026, 3, 5))
    assert f2 and "271" in f2.ground
    assert r.contradiction({**ctx, "active_271": False}, "27", date(2026, 3, 5)) is None, "coverage really lapsed: nothing to appeal"
    remit = RemitView("1-1", "4", Decimal(110), Decimal(0), Decimal(0), Decimal(0), "197", "PCN1")
    plan = r.plan_after_remit(ctx, remit, date(2026, 3, 5), 1, [], {"97110": "80.00"})
    assert plan.kind == "appeal" and plan.finding["rule_id"] == "pa-97110" and "pa-97110 v1" in plan.reason
    assert "published rule excerpt: pa-97110 v1" in plan.evidence["attachments"]
    letter = Responder.appeal_letter(ctx, plan)
    assert "NOT required" in letter and "stub generator" in letter


def test_the_scorecard_counts_the_responders_recognitions(run):
    out, s = run
    ev = [e for e in events(out) if e["step"] == "8 reply: recognized"]
    assert ev, "at least one denial contradicted the published rules in this run"
    rec = score._recognitions(out)
    truth = list(csv.DictReader((out / "truth.csv").read_text("utf-8").splitlines()))
    sec = score.replies_section(state(out), truth, rec)
    assert sec["recognized_true"] >= 1 and sec["enabled"] and sec["settled"] == s["replies"]["settled"]
    assert sec["sent_by_kind"] == s["replies"]["sent"]


# ---------------------------------------------------------------------------------------------------- deadlines
def _short_book(window: int) -> Book:
    b = Book()
    for rid, fam, basis, content in (("appeal-short", "denial_appeal", "denial_notification_date", {"window_days": window, "day_count": "calendar", "inclusive": False}),
                                     ("corrected-short", "billing", "service_date", {"corrected_claim_window_days": 400, "day_count": "calendar", "inclusive": False})):
        b.add(Rule(rule_id=rid, version=1, payer=PAYER, family=fam, effective_from=date(2025, 1, 1), date_basis=basis, source=DEMO, content=content, active_from=date(2025, 1, 1)))
    return b


def test_an_expired_route_escalates_to_a_person_and_the_book_gap_does_too():
    ctx = {"claim_id": "1-1", "payer_id": PAYER, "member": "M", "dos": "2026-03-02", "cpt": "99213", "cpts": ["99213"], "lines": [("99213", 1, Decimal("110"))], "active_271": True, "notified": "2026-03-17"}
    remit = RemitView("1-1", "4", Decimal(110), Decimal(0), Decimal(0), Decimal(0), "50", "PCN1")
    late = Responder(_short_book(5)).plan_after_remit(ctx, remit, date(2026, 3, 25), 1, [], {})
    assert late.kind == "review" and "deadline passed" in late.reason and late.approval.startswith("none")
    ontime = Responder(_short_book(5)).plan_after_remit(ctx, remit, date(2026, 3, 19), 1, [], {})
    assert ontime.kind == "appeal" and ontime.deadline["due"] == "2026-03-22"
    nobook = Responder(Book()).plan_after_remit(ctx, remit, date(2026, 3, 19), 1, [], {})
    assert nobook.kind == "review" and "cannot give" in nobook.reason


def test_nothing_is_sent_after_the_deadline_in_a_run(tmp_path):
    out = tmp_path / "r"
    s = Stream(cfg(count=20, reject_rate=0.0), out, FakeEmr(), quiet)
    s.responder = Responder(_short_book(1))  # an appeal is due one day after the denial; the bots need three days to get it approved
    s.run()
    ev = events(out)
    assert not [e for e in ev if e["step"] == "8 reply: appeal" and e["outcome"] == "sent"]
    assert not list((out / "replies").glob("*appeal*")) if (out / "replies").exists() else True
    rev = [e for e in ev if e["step"] == "8 reply: review"]
    assert any("deadline passed" in e["detail"] for e in rev) and all("nothing sent" in e["detail"] for e in rev)


# ---------------------------------------------------------------------------------------------------- corrected claims
def _segs(text: str, prefix: str) -> list[str]:
    return [s for s in text.replace("\n", "").split("~") if s.startswith(prefix)]


def test_a_corrected_claim_never_changes_a_cpt_or_an_icd10_code(run):
    out, _ = run
    corrected = sorted((out / "claims").glob("*.c*.837"))
    assert len(corrected) >= 3
    for f in corrected:
        cid = f.name.split(".c")[0]
        orig = (out / "claims" / f"{cid}.837").read_text("utf-8")
        new = f.read_text("utf-8")
        assert _segs(new, "SV1*") == _segs(orig, "SV1*"), "procedure codes are untouched"
        assert _segs(new, "HI*") == _segs(orig, "HI*"), "diagnosis codes are untouched"
        clm = _segs(new, "CLM*")[0].split("*")
        assert clm[5].split(":")[2] == "7" and _segs(new, "REF*F8*")
        segs = [s for s in new.replace("\n", "").split("~") if s]
        st = next(i for i, s in enumerate(segs) if s.startswith("ST*"))
        se = next(i for i, s in enumerate(segs) if s.startswith("SE*"))
        assert segs[se].split("*")[1] == str(se - st + 1), "the segment count in SE is right"


def test_a_correction_for_a_code_problem_goes_to_a_person_instead():
    r = Responder(demo_book())
    ctx = {"claim_id": "1-1", "payer_id": PAYER, "member": "M", "dos": "2026-03-02", "cpt": "99213", "cpts": ["99213"], "lines": [("99213", 1, Decimal("110"))], "active_271": True, "notified": "2026-03-17"}
    for carc in ("4", "11", "18", "29", "999"):
        remit = RemitView("1-1", "4", Decimal(110), Decimal(0), Decimal(0), Decimal(0), carc, "P")
        plan = r.plan_after_remit(ctx, remit, date(2026, 3, 18), 1, [], {})
        assert plan.kind == "review", (carc, plan.kind)
    # coverage and missing information are corrected once, then the next step is an appeal or a person
    remit = RemitView("1-1", "4", Decimal(110), Decimal(0), Decimal(0), Decimal(0), "16", "P")
    first = r.plan_after_remit(ctx, remit, date(2026, 3, 18), 1, [], {})
    assert first.kind == "corrected_claim" and first.trigger == "denial"
    again = r.plan_after_remit(ctx, remit, date(2026, 3, 30), 2, [{"plan": first.to_dict()}], {})
    assert again.kind != "corrected_claim"


def test_the_corrected_837_fixes_only_what_the_clearinghouse_rejected(run):
    out, _ = run
    fx = [f for f in (out / "claims").glob("*.sent.837")]
    assert fx
    for f in fx:
        cid = f.name.split(".sent")[0]
        pristine = (out / "claims" / f"{cid}.837").read_text("utf-8")
        fixed = (out / "claims" / f"{cid}.c1.837").read_text("utf-8")
        assert _segs(fixed, "SV1*") == _segs(pristine, "SV1*") and _segs(fixed, "HI*") == _segs(pristine, "HI*")
        assert _segs(fixed, "NM1*PR*") == _segs(pristine, "NM1*PR*")


# ---------------------------------------------------------------------------------------------------- approvals and the daily cap
def test_every_action_carries_an_approval_label_and_the_evidence_it_used(run):
    out, _ = run
    recs = [json.loads(ln) for ln in (out / "decision_records.jsonl").read_text("utf-8").splitlines()]
    acts = [r for r in recs if r["action_type"] in ("corrected_claim", "appeal", "dispute", "records") and r["result"] == "sent"]
    assert acts
    for r in acts:
        assert APPROVAL_RE.match(r["approver"]), r["approver"]
        assert r["mode"] == "demo-live" and r["rules_fired"]
    assert all("person:simulated" in r["approver"] and "(demo)" in r["approver"] for r in acts if r["action_type"] in ("appeal", "dispute"))
    assert all(r["approver"] is None for r in recs if r["action_type"] == "review")
    keys = [r["event_key"] for r in recs]
    assert len(keys) == len(set(keys)), "one decision record per action"
    appeals = [r for r in acts if r["action_type"] == "appeal"]
    assert all(r["action_payload"]["deadline"]["rule"] for r in appeals)


def test_nothing_is_ever_written_off_or_refunded_by_the_bots(run):
    out, _ = run
    allowed = {"corrected_claim", "appeal", "dispute", "records"}
    kinds = {r["plan"]["kind"] for e in state(out)["enc"].values() for r in e.get("rounds", [])}
    assert kinds <= allowed
    text = (out / "events.jsonl").read_text("utf-8") + (out / "decision_records.jsonl").read_text("utf-8")
    assert "write_off" not in text.replace("write_off_review", "") and "refund" not in text.lower()
    q = [json.loads(ln) for ln in (out / "review_queue.jsonl").read_text("utf-8").splitlines()]
    assert q and all(x["reason"] for x in q)


def test_the_daily_cap_holds_and_a_deferred_reply_is_not_lost(tmp_path):
    out = tmp_path / "r"
    s = Stream(cfg(count=30, reject_rate=0.0), out, FakeEmr(), quiet)
    s.reply_policy.daily_cap = 2
    s.run()
    sent = [e for e in events(out) if e["step"].startswith("8 reply: ") and e["outcome"] == "sent"]
    per_day: dict[str, int] = {}
    for e in sent:
        per_day[e["day"]] = per_day.get(e["day"], 0) + 1
    assert per_day and max(per_day.values()) <= 2
    assert [e for e in events(out) if e["step"] == "8 reply: deferred"]
    assert all(e["stage"] in ("settled", "patient_balance", "review", "pending_coder") for e in state(out)["enc"].values())


# ---------------------------------------------------------------------------------------------------- rejections
def test_reject_rate_injects_rejections_that_end_in_a_corrected_claim(run):
    out, _ = run
    ev = events(out)
    rejected = {e["subject"] for e in ev if e["step"] == "5 clearinghouse" and e["outcome"] == "rejected"}
    assert len(rejected) >= 3
    fixed = {e["subject"] for e in ev if e["step"] == "8 reply: corrected claim" and e["outcome"] == "sent"}
    assert rejected <= fixed
    st = {e["claim"]: e for e in state(out)["enc"].values() if e.get("claim")}
    for c in rejected:
        assert st[c]["stage"] not in ("rejected", "new"), (c, st[c]["stage"])
        assert st[c]["rounds"][0]["plan"]["trigger"] == "rejection" and st[c]["rounds"][0]["plan"]["approval"].startswith("policy:")
    truth = {r["claim_id"] for r in csv.DictReader((out / "truth.csv").read_text("utf-8").splitlines())}
    assert rejected <= truth, "after the fix the payer decided every one"
    assert list((out / "inbox").glob("999_*_c1.999")) and list((out / "inbox").glob("277CA_*_c1.277ca"))


def test_without_the_replies_switch_a_rejected_claim_stays_rejected(tmp_path):
    out = tmp_path / "r"
    s = run_stream(out, cfg(replies=False, count=30, reject_rate=0.3), FakeEmr(), log=quiet)
    assert s["stages"].get("rejected", 0) >= 1 and not (out / "replies").exists() and not (out / "decision_records.jsonl").exists()
    assert "replies" not in s and not (out / "truth_replies.csv").exists()


def test_break_837_makes_the_clearinghouse_reject_it(tmp_path):
    from krisnai.live.payer import PayerSim
    from krisnai.live.world import LiveWorld

    out = tmp_path / "r"
    run_stream(out, cfg(count=4, replies=False, reject_rate=0.0), FakeEmr(), log=quiet)
    text = next((out / "claims").glob("*.837")).read_text("utf-8")
    for kind, why in (("payer_id", "payer id is empty"), ("diagnosis", "no diagnosis")):
        w = LiveWorld(PayerSim("SYNAETNA", "SYNAETNA Demo Payer"), date(2026, 10, 21))
        _, _, res = w.accept_claims(break_837(text, kind), date(2026, 10, 25))
        assert not res[0]["ok"] and why in res[0]["reason"]
    w = LiveWorld(PayerSim("SYNAETNA", "SYNAETNA Demo Payer"), date(2026, 10, 21))
    assert w.accept_claims(text, date(2026, 10, 25))[2][0]["ok"]


# ---------------------------------------------------------------------------------------------------- the money
def test_reconciliation_ties_out_with_second_remits_and_cash_stays_zero(run):
    out, s = run
    led = score.reconcile(out)
    assert led["tie_out_mismatches"] == [] and led["duplicate_claims"] == 0
    assert led["second_remits_read"] >= 5
    assert Decimal(led["remitted_total"]) == Decimal(led["remitted_by_payer"]) + Decimal(led["remitted_by_replies"])
    truth = list(csv.DictReader((out / "truth.csv").read_text("utf-8").splitlines()))
    assert Decimal(led["remitted_by_payer"]) == sum((Decimal(r["paid"]) for r in truth), Decimal(0)), "the first remits still tie to truth.csv"
    rt = list(csv.DictReader((out / "truth_replies.csv").read_text("utf-8").splitlines()))
    assert Decimal(led["remitted_by_replies"]) == sum((Decimal(r["paid"]) for r in rt), Decimal(0))
    assert led["cash_collected"] == "0.00"
    assert led["awaiting_remit"] == [], "every billed claim has its first remit"


def test_a_second_remit_that_disagrees_with_the_reply_truth_is_flagged(run, tmp_path):
    out, _ = run
    import shutil

    copy = tmp_path / "c"
    shutil.copytree(out, copy)
    f = sorted((copy / "inbox").glob("835_*-R*.835"))[0]
    cid = f.name[4:-4]
    text = f.read_text("utf-8")
    m = re.search(rf"CLP\*{re.escape(cid)}\*(\d)\*([\d.]+)\*([\d.]+)\*", text)
    f.write_text(text.replace(m.group(0), f"CLP*{cid}*{m.group(1)}*{m.group(2)}*999*"), encoding="utf-8")
    assert [x["claim"] for x in score.reconcile(copy)["tie_out_mismatches"]] == [cid]


def test_the_reply_truth_is_deterministic_and_the_remit_reader_reads_what_was_written(run, tmp_path):
    out, _ = run
    other = tmp_path / "again"
    run_stream(other, cfg(), FakeEmr(), log=quiet)
    assert (other / "truth_replies.csv").read_text("utf-8") == (out / "truth_replies.csv").read_text("utf-8")
    f = sorted((out / "inbox").glob("835_*-R1.835"))[0]
    v = read_remit(f.read_text("utf-8"), f.name[4:-4])
    assert v is not None and v.claim_id.endswith("-R1")


# ---------------------------------------------------------------------------------------------------- kill and resume
def _sig(out: Path) -> dict:
    st = state(out)
    return {
        "truth": (out / "truth.csv").read_text("utf-8"), "replies": (out / "truth_replies.csv").read_text("utf-8"),
        "stages": {k: e["stage"] for k, e in st["enc"].items()}, "rounds": {k: [(r["round"], r["plan"]["kind"], r["sent_on"], r["answered"]) for r in e.get("rounds", [])] for k, e in st["enc"].items()},
        "files": sorted(p.name for d in ("inbox", "claims", "replies") if (out / d).exists() for p in (out / d).glob("*") if p.suffix != ".csv"),
    }  # fmt: skip


def test_a_run_killed_at_several_points_neither_repeats_a_reply_nor_loses_a_claim(tmp_path):
    c = cfg(count=18, reject_rate=0.2)
    ref_emr = FakeEmr()
    ref = Stream(c, tmp_path / "ref", ref_emr, quiet)
    ref.run()
    total = ref.mutations
    want = _sig(tmp_path / "ref")
    assert total > 100
    for n, frac in enumerate((0.1, 0.35, 0.5, 0.62, 0.75, 0.9, 0.99)):
        crash_at = max(1, int(total * frac))
        out = tmp_path / f"run{n}"
        emr = FakeEmr()
        with pytest.raises(SimulatedCrash):
            run_stream(out, c, emr, log=quiet, crash_after=crash_at)
        run_stream(out, c, emr, log=quiet)  # the restart
        assert emr.counts() == ref_emr.counts()
        assert _sig(out) == want, f"crash at mutation {crash_at}"
        keys = [e["key"] for e in events(out)]
        assert len(keys) == len(set(keys)), "no event twice"
        recs = [json.loads(ln)["event_key"] for ln in (out / "decision_records.jsonl").read_text("utf-8").splitlines()]
        assert len(recs) == len(set(recs)), "no decision record twice"
        assert state(out)["reply_per_day"] == state(tmp_path / "ref")["reply_per_day"], "the daily count is not double counted"


# ---------------------------------------------------------------------------------------------------- off means off
def test_with_replies_off_nothing_changes(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    sa = run_stream(a, StreamConfig(count=14, per_day=5, engine=False, bots=False, serve=False), FakeEmr(), log=quiet)
    sb = run_stream(b, StreamConfig(count=14, per_day=5, engine=False, bots=False, serve=False, replies=False, reject_rate=0.0), FakeEmr(), log=quiet)
    assert sa == sb and "replies" not in sa
    assert not (a / "replies").exists() and not (a / "decision_records.jsonl").exists()
    assert not [e for e in events(a) if e["step"].startswith("8 reply")]
    assert "reply_per_day" not in state(a)
    assert score.replies_section(state(a), list(csv.DictReader((a / "truth.csv").read_text("utf-8").splitlines())), set())["sent_by_kind"] == {}


def _openemr_up() -> bool:
    return False


@pytest.mark.slow
def test_with_the_real_engine_the_second_remits_and_acknowledgements_load_without_trouble(tmp_path):
    out = tmp_path / "r"
    s = run_stream(out, StreamConfig(count=12, per_day=6, deviation_rate=0.5, deny_rate=0.4, pend_rate=0.3, reject_rate=0.2, replies=True, bots=False, serve=False), FakeEmr(), log=quiet)
    assert s["replies"]["sent"]
    assert not [e for e in events(out) if e["step"] == "8 agents" and e["outcome"] == "problem"]
    sc = score.score(out)
    assert sc["replies"]["enabled"] and sc["ledger"]["tie_out_mismatches"] == [] and sc["ledger"]["cash_collected"] == "0.00"
