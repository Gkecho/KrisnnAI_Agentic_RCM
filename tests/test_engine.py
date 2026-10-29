"""M6 tests: the decision engine, proved with a dummy agent. Nothing here touches a real adapter or model."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import func, select

import krisnnai.model as m
from krisnnai.engine import (
    NO_ACTION,
    ApprovalError,
    approve,
    fingerprint,
    list_requests,
    reject,
    replay,
    run,
    set_policy,
)
from krisnnai.engine.adapters import ClearinghouseStub, TaskNoteAdapter
from krisnnai.engine.models import BaaNotApproved, StubProvider, prompt_hash
from krisnnai.model import tenant_session
from tests.fixtures.dummy_agent import TRIGGER, DummyAgent, SpyAdapter
from tests.test_ingest import make_engine

START = datetime(2026, 1, 1, 8, 0)


def add_events(engine, tenant, amounts, start=START, step_days=1):
    """Fabricated trigger events known on consecutive days. Returns their ids."""
    ids = []
    with tenant_session(engine, tenant) as s:
        sf = s.scalars(select(m.SourceFile)).first()
        if sf is None:
            sf = m.SourceFile(file_name="d.x12", file_sha256=(str(tenant) * 64)[:64], file_type="835", byte_size=1,
                              status="loaded")  # fmt: skip
            s.add(sf)
            s.flush()
        base = s.scalar(select(func.count()).select_from(m.Event))
        for i, amount in enumerate(amounts):
            e = m.Event(source_file_id=sf.id, event_type=TRIGGER, isa13="1", gs06="1", st02="1", seq_in_file=base + i + 1,
                        known_at=start + timedelta(days=step_days * (base + i)), payload=json.dumps({"amount": amount}))  # fmt: skip
            s.add(e)
            s.flush()
            ids.append(e.id)
        s.commit()
    return ids


@pytest.fixture()
def eng(tmp_path):
    return make_engine(tmp_path / "e.sqlite")


def records(engine, tenant=1):
    with tenant_session(engine, tenant) as s:
        return list(s.scalars(select(m.DecisionRecord).order_by(m.DecisionRecord.id)))


def live(engine, level, tenant=1, action="add_note", **kw):
    with tenant_session(engine, tenant) as s:
        set_policy(s, action, mode="live", autonomy_level=level, **kw)
        s.commit()


# ------------------------------------------------------------------------------------ policy and shadow


def test_default_policy_is_shadow_and_never_calls_an_adapter(eng):
    (eid,) = add_events(eng, 1, ["100.00"])
    spy = SpyAdapter()
    res = run(eng, 1, DummyAgent(), eid, adapters={"add_note": spy})
    assert res.outcome == "shadow" and spy.calls == []
    (rec,) = records(eng)
    assert (rec.mode, rec.autonomy_level, rec.execution_result) == ("shadow", 0, "shadow: not executed")


def test_shadow_mode_never_calls_adapters_even_at_level_4(eng):
    (eid,) = add_events(eng, 1, ["100.00"])
    with tenant_session(eng, 1) as s:
        set_policy(s, "add_note", mode="shadow", autonomy_level=4, max_amount=Decimal("1000"))
        s.commit()
    spy = SpyAdapter()
    assert run(eng, 1, DummyAgent(), eid, adapters={"add_note": spy}).outcome == "shadow"
    assert spy.calls == []


def test_a_denied_action_never_executes_but_is_still_recorded(eng):
    (eid,) = add_events(eng, 1, ["100.00"])
    live(eng, 4, allowed=False, max_amount=Decimal("1000"))
    spy = SpyAdapter()
    res = run(eng, 1, DummyAgent(), eid, adapters={"add_note": spy})
    assert res.outcome == "denied" and spy.calls == []
    (rec,) = records(eng)
    assert rec.outcome == "denied" and "denied by policy" in rec.execution_result


def test_a_failed_blocking_check_stops_execution(eng):
    (eid,) = add_events(eng, 1, ["100.00"])
    live(eng, 4, max_amount=Decimal("1000"))
    spy = SpyAdapter()
    res = run(eng, 1, DummyAgent(failing_blocking_rule=True), eid, adapters={"add_note": spy})
    assert res.outcome == "blocked_by_check" and spy.calls == []
    assert any(
        r["rule"] == "must_have_authorization" and not r["result"] for r in json.loads(records(eng)[0].rules_fired)
    )


def test_levels_0_to_2_never_execute(eng):
    ids = add_events(eng, 1, ["100.00"])
    for level, outcome in ((0, "observed"), (1, "assisted"), (2, "pending_approval")):
        with tenant_session(eng, 1) as s:
            s.query(m.Policy).delete()
            s.commit()
        live(eng, level)
        spy = SpyAdapter()
        agent = DummyAgent(action=f"note_l{level}")
        live(eng, level, action=f"note_l{level}")
        assert run(eng, 1, agent, ids[0], adapters={agent.action: spy}).outcome == outcome
        assert spy.calls == []


# ------------------------------------------------------------------------------- records and idempotency


def test_every_run_writes_one_complete_decision_record(eng):
    (eid,) = add_events(eng, 1, ["125.00"])
    run(eng, 1, DummyAgent(), eid)
    (rec,) = records(eng)
    assert (rec.agent_id, rec.agent_version, rec.event_id, rec.trigger_type) == ("dummy", "1.0", eid, TRIGGER)
    snap = json.loads(rec.input_snapshot)
    assert snap["lineage"]["event_ids"] == [eid] and snap["data"]["amount"] == "125.00"
    assert json.loads(rec.rules_fired)[0] == {"rule": "amount_is_positive", "result": True, "detail": ""}
    assert (rec.model_id, rec.model_version) == ("stub", "1")
    assert rec.prompt_hash == prompt_hash("write a note for 1 events")
    assert (rec.confidence, rec.materiality_amount) == (Decimal("0.95"), Decimal("125.00"))
    assert (rec.action_type, rec.mode, rec.autonomy_level) == ("add_note", "shadow", 0)
    assert rec.verification_condition and rec.verification_result == "not_run" and rec.loaded_at is not None


def test_no_action_is_still_a_recorded_run(eng):
    (eid,) = add_events(eng, 1, ["100.00"])
    assert run(eng, 1, DummyAgent(action=NO_ACTION), eid).outcome == "no_action"
    assert records(eng)[0].action_type == NO_ACTION


def test_an_event_the_agent_does_not_trigger_on_writes_nothing(eng):
    (eid,) = add_events(eng, 1, ["100.00"])
    with tenant_session(eng, 1) as s:
        s.get(m.Event, eid).event_type = "other.event"
        s.commit()
    assert run(eng, 1, DummyAgent(), eid) is None and records(eng) == []


def test_repeating_a_run_creates_no_duplicate_and_executes_once(eng):
    (eid,) = add_events(eng, 1, ["100.00"])
    live(eng, 4, max_amount=Decimal("1000"))
    spy = SpyAdapter()
    first = run(eng, 1, DummyAgent(), eid, adapters={"add_note": spy})
    again = run(eng, 1, DummyAgent(), eid, adapters={"add_note": spy})
    assert (first.created, again.created, again.record_id) == (True, False, first.record_id)
    assert len(records(eng)) == 1 and len(spy.calls) == 1


# ---------------------------------------------------------------------------------------- L3 / L4 paths


def test_level_4_runs_alone_only_within_the_cap_and_with_confidence(eng):
    ids = add_events(eng, 1, ["100.00", "500.00", "100.00"])
    live(eng, 4, max_amount=Decimal("200"))
    spy = SpyAdapter()
    ad = {"add_note": spy}
    assert run(eng, 1, DummyAgent(), ids[0], adapters=ad).outcome == "executed"
    assert run(eng, 1, DummyAgent(), ids[1], adapters=ad).outcome == "pending_approval"  # over the cap
    assert run(eng, 1, DummyAgent(confidence="0.50"), ids[2], adapters=ad).outcome == "pending_approval"  # unsure
    assert len(spy.calls) == 1
    done = records(eng)[0]
    assert done.execution_result == "spy: ran" and done.verification_result == "confirmed"


def test_level_3_waits_for_a_named_approval_then_runs_once(eng):
    (eid,) = add_events(eng, 1, ["100.00"])
    live(eng, 3, approver_role="billing_manager")
    spy = SpyAdapter()
    ad = {"add_note": spy}
    res = run(eng, 1, DummyAgent(), eid, adapters=ad)
    assert res.outcome == "pending_approval" and spy.calls == []
    (item,) = list_requests(eng, 1)
    assert (item["status"], item["approver_role"], item["action_type"]) == ("pending", "billing_manager", "add_note")

    with pytest.raises(ApprovalError, match="named approver"):
        approve(eng, 1, res.approval_id, "  ", "billing_manager", adapters=ad)
    with pytest.raises(ApprovalError, match="role"):
        approve(eng, 1, res.approval_id, "Pat", "intern", adapters=ad)
    assert spy.calls == []

    out = approve(eng, 1, res.approval_id, "Pat", "billing_manager", adapters=ad, agents={"dummy": DummyAgent()})
    assert (out["status"], out["outcome"], out["decided_by"]) == ("approved", "executed", "Pat")
    assert len(spy.calls) == 1
    rec = records(eng)[0]
    assert (rec.approver, rec.verification_result) == ("Pat", "confirmed") and rec.approved_at is not None
    with pytest.raises(ApprovalError, match="already approved"):
        approve(eng, 1, res.approval_id, "Pat", "billing_manager", adapters=ad)
    assert len(spy.calls) == 1 and list_requests(eng, 1) == []


def test_rejecting_needs_a_reason_and_never_executes(eng):
    (eid,) = add_events(eng, 1, ["100.00"])
    live(eng, 3)
    spy = SpyAdapter()
    res = run(eng, 1, DummyAgent(), eid, adapters={"add_note": spy})
    with pytest.raises(ApprovalError, match="reason"):
        reject(eng, 1, res.approval_id, "Pat", " ")
    out = reject(eng, 1, res.approval_id, "Pat", "wrong payer")
    assert (out["status"], out["outcome"], out["reason"]) == ("rejected", "rejected", "wrong payer")
    assert spy.calls == [] and records(eng)[0].execution_result == "rejected: wrong payer"
    with pytest.raises(ApprovalError, match="already rejected"):
        approve(eng, 1, res.approval_id, "Pat", adapters={"add_note": spy})


def test_a_level_2_draft_is_approved_but_not_executed(eng):
    (eid,) = add_events(eng, 1, ["100.00"])
    live(eng, 2)
    spy = SpyAdapter()
    res = run(eng, 1, DummyAgent(), eid, adapters={"add_note": spy})
    out = approve(eng, 1, res.approval_id, "Pat", adapters={"add_note": spy})
    assert out["outcome"] == "approved_draft" and spy.calls == []


def test_approval_is_refused_if_policy_was_switched_back_to_shadow(eng):
    (eid,) = add_events(eng, 1, ["100.00"])
    live(eng, 3)
    res = run(eng, 1, DummyAgent(), eid, adapters={})
    with tenant_session(eng, 1) as s:
        set_policy(s, "add_note", mode="shadow", autonomy_level=3)
        s.commit()
    with pytest.raises(ApprovalError, match="no longer allows"):
        approve(eng, 1, res.approval_id, "Pat")


# ------------------------------------------------------------------------------------- adapters and models


def test_task_note_adapter_is_disabled_by_default_and_clearinghouse_never_sends(eng):
    ids = add_events(eng, 1, ["100.00", "100.00"])
    live(eng, 4, max_amount=Decimal("1000"))
    disabled = TaskNoteAdapter()
    assert run(eng, 1, DummyAgent(), ids[0], adapters={"add_note": disabled}).outcome == "adapter_disabled"
    assert disabled.outbox == []
    enabled = TaskNoteAdapter(enabled=True)
    assert run(eng, 1, DummyAgent(), ids[1], adapters={"add_note": enabled}).outcome == "executed"
    assert enabled.outbox[0][0] == "add_note"

    live(eng, 4, action="resubmit_claim", max_amount=Decimal("1000"))
    stub = ClearinghouseStub()
    (eid,) = add_events(eng, 1, ["50.00"])
    assert (
        run(eng, 1, DummyAgent(action="resubmit_claim"), eid, adapters={"resubmit_claim": stub}).outcome == "executed"
    )
    assert (
        stub.requests
        and "stub" in records(eng)[-1].execution_result
        and "not sent" in records(eng)[-1].execution_result
    )


def test_a_missing_adapter_is_recorded_not_crashed(eng):
    (eid,) = add_events(eng, 1, ["100.00"])
    live(eng, 4, max_amount=Decimal("1000"))
    assert run(eng, 1, DummyAgent(), eid, adapters={}).outcome == "no_adapter"


class CloudModel:
    model_id = "acme-large"
    model_version = "9"

    def complete(self, prompt: str) -> str:
        return "answer"


def test_a_real_model_provider_is_refused_without_a_baa(eng):
    (eid,) = add_events(eng, 1, ["100.00"])
    with pytest.raises(BaaNotApproved):
        run(eng, 1, DummyAgent(), eid, provider=CloudModel())
    assert records(eng) == []  # nothing reached the model and nothing was recorded
    assert run(eng, 1, DummyAgent(), eid, provider=CloudModel(), baa_approved=True).created
    assert records(eng)[0].model_id == "acme-large"
    assert StubProvider().complete("x") == StubProvider().complete("x")  # the stub is deterministic


# ------------------------------------------------------------------------------------------------ replay


def test_replay_is_deterministic_and_always_shadow(eng):
    add_events(eng, 1, ["10.00", "20.00", "30.00", "40.00"])
    live(eng, 4, max_amount=Decimal("1000"))  # live L4 policy, replay must still not act
    agent = DummyAgent()
    first = replay(eng, 1, agent)
    second = replay(eng, 1, agent)
    assert [(i.event_id, i.fingerprint) for i in first] == [(i.event_id, i.fingerprint) for i in second]
    assert len(first) == 4 and len(records(eng)) == 4
    assert {i.outcome for i in first} == {"shadow"} and {r.mode for r in records(eng)} == {"shadow"}
    assert [i.known_at for i in first] == sorted(i.known_at for i in first)
    print("\nreplay fingerprints:", [i.fingerprint[:12] for i in first])


def test_replay_has_no_future_leakage(eng):
    add_events(eng, 1, ["10.00", "20.00", "30.00"])
    agent = DummyAgent()
    before = {i.event_id: i.fingerprint for i in replay(eng, 1, agent)}
    add_events(eng, 1, ["99.00", "98.00"], start=START + timedelta(days=60))  # known two months later
    after = replay(eng, 1, agent)
    for item in after:
        if item.event_id in before:
            assert item.fingerprint == before[item.event_id], "an earlier decision changed after later data arrived"
    seen = [json.loads(r.input_snapshot)["data"]["seen"] for r in records(eng)]
    assert seen == [1, 2, 3, 4, 5]  # each decision saw only the events known by its own time


def test_replay_until_stops_at_the_given_time(eng):
    add_events(eng, 1, ["10.00", "20.00", "30.00"])
    items = replay(eng, 1, DummyAgent(), until=START + timedelta(days=1))
    assert len(items) == 2


# ---------------------------------------------------------------------------------------------- tenancy


def test_another_tenant_sees_none_of_it(eng):
    (e1,) = add_events(eng, 1, ["100.00"])
    live(eng, 3)
    res = run(eng, 1, DummyAgent(), e1, adapters={})
    assert records(eng, 2) == [] and list_requests(eng, 2) == []
    with pytest.raises(ApprovalError, match="does not exist"):
        approve(eng, 2, res.approval_id, "Pat")
    with pytest.raises(LookupError):
        run(eng, 2, DummyAgent(), e1)  # tenant 2 cannot trigger on tenant 1's event
    (e2,) = add_events(eng, 2, ["100.00"])
    assert run(eng, 2, DummyAgent(), e2).outcome == "shadow"  # tenant 2 has no policy of its own: default shadow
    assert [r.tenant_id for r in records(eng, 1)] == [1] and [r.tenant_id for r in records(eng, 2)] == [2]


def test_fingerprint_ignores_timestamps_but_not_content(eng):
    ids = add_events(eng, 1, ["10.00", "20.00"])
    a, b = (run(eng, 1, DummyAgent(), i, force_shadow=True) for i in ids)
    with tenant_session(eng, 1) as s:
        ra, rb = s.get(m.DecisionRecord, a.record_id), s.get(m.DecisionRecord, b.record_id)
        assert fingerprint(ra) != fingerprint(rb)
        ra.approved_at = datetime(2030, 1, 1)
        fp = fingerprint(ra)
        ra.approved_at = None
        assert fingerprint(ra) == fp
