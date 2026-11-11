"""Replay -> R2 persistence mapping and the ui_data.js export.

Most tests use small hand-made result fixtures and need no database. The DB tests run against krisnnai_r2 inside one transaction that is rolled back
(rows carry source 'replay_test', never 'replay'), and are skipped when the database is unreachable. Run: pytest -v tests/test_replay_r2.py
"""
import copy
import datetime as dt
import json
import pathlib
import re
import sys
from decimal import Decimal

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "replay"))
sys.path.insert(0, str(ROOT / "tools" / "synthea"))
import r2_export_ui as ex  # noqa: E402
import r2_persist as pp  # noqa: E402

D = Decimal
SAMPLE = pathlib.Path(r"C:\Users\gopi.v\Downloads\krisnnai-site\ui_data.js")
DAY = dt.date(2026, 10, 1)
TS = dt.datetime(2026, 10, 1, 6, 0, 0)
TEST_SOURCE = "replay_test"


def fake_ids():
    return dict(claim=101, claim2=102, payer=6, denial=201, patient=301, provider=1, appointment=401, encounter=501, staff_biller=2, staff_denial=7, staff_lead=1)


def make_results(ids):
    """Engine-shaped rows (the engine's own table and column names, local ids from 1) for three decisions, a rework chain, an approval and a suppressed write-back."""
    i = ids
    run = lambda n, code: dict(agent_run_id=n, agent_code=code, agent_name=code, run_mode="shadow", trigger_type="schedule", started_at=TS + dt.timedelta(minutes=n), ended_at=TS + dt.timedelta(minutes=n, seconds=2),  # noqa: E731
                               run_status="ok", practice_id=1, items_in=1, decisions_made=1, error_count=0, code_version="v0.9-shadow", known_at=TS)
    dec = lambda n, run_id, code, dtype, ent, eid, out, amt, conf, summary, **kw: dict(agent_decision_id=n, agent_run_id=run_id, agent_code=code, decision_type=dtype, entity_type=ent, entity_id=eid,  # noqa: E731
                                                                                       outcome=out, decided_at=TS + dt.timedelta(minutes=1), run_mode="shadow", confidence=D(conf), reason_summary=summary,
                                                                                       rules_checked=2, rules_failed=1 if out != "clear" else 0, amount_at_stake=D(amt), data_fallback_level=0,
                                                                                       practice_id=1, finding_id=None, task_id=None, human_outcome=None, input_hash=b"\x01" * 32, **kw)
    chk = lambda n, dec_id, seq, rule, res, obs, exp: dict(agent_decision_details_id=n, agent_decision_id=dec_id, check_seq=seq, rule_code=rule, check_result=res, agent_code="A5",  # noqa: E731
                                                           rule_version="1", rule_source="built_in", severity="high", observed_value=obs, expected_value=exp, input_table="claim",
                                                           input_fallback_level=0, practice_id=1, payer_id=i["payer"], payer_rule_id=77)
    rows = {
        "agent_run": [run(1, "A1"), run(2, "A5"), run(3, "A8")],
        "agent_decision": [
            dec(1, 1, "A1", "eligibility_review", "appointment", i["appointment"], "clear", "0", "0.9700", "Coverage active", patient_id=i["patient"], payer_id=i["payer"], appointment_id=i["appointment"]),
            dec(2, 2, "A5", "prerelease_review", "claim", i["claim"], "hold", "210.00", "0.8500", "Predicted CARC 198: R-AUTH-VISITS", payer_id=i["payer"], claim_id=i["claim"], patient_id=i["patient"],
                provider_id=i["provider"], encounter_id=i["encounter"]),
            dec(3, 3, "A8", "denial_triage", "denial", i["denial"], "route", "130.00", "0.9000", "CARC 4: Billing error; owner coder", payer_id=i["payer"], claim_id=i["claim"], denial_id=i["denial"],
                patient_id=i["patient"]),
        ],
        "agent_decision_details": [chk(1, 1, 1, "R-COV-ACTIVE", "pass", "no end date", ">= 2026-10-01"), chk(2, 1, 2, "R-AAA-REJECT", "pass", "no reject", "no reject"),
                                   chk(3, 2, 1, "R-AUTH-VISITS", "fail", "visit 5", "<= 4"), chk(4, 2, 2, "R-COV-ACTIVE", "pass", "no end date", ">= 2026-10-01"),
                                   chk(5, 3, 1, "R-CARC-ROUTE", "pass", "CARC 4", "coder"), chk(6, 3, 2, "R-APPEAL-WINDOW", "fail", "deadline 2026-10-20", "open")],
        "agent_finding": [
            dict(agent_finding_id=1, agent_run_id=2, agent_code="A5", entity_type="claim", entity_id=i["claim"], found_date=DAY, agent_decision_id=2, finding_type="predicted_denial", finding_status="confirmed",
                 upstream_stage="authorization", is_preventable=True, severity="high", amount_at_risk=D("210.00"), predicted_probability=D("0.8500"), summary="Predicted CARC 198: R-AUTH-VISITS",
                 resolved_date=dt.date(2026, 10, 4), resolution="denied_confirmed", payer_id=i["payer"], claim_id=i["claim"], patient_id=i["patient"], practice_id=1, finding_hash=b"\x02" * 32),
            dict(agent_finding_id=2, agent_run_id=3, agent_code="A8", entity_type="denial", entity_id=i["denial"], found_date=DAY, agent_decision_id=3, finding_type="denial", finding_status="resolved",
                 upstream_stage="billing", is_preventable=True, severity="high", amount_at_risk=D("130.00"), deadline_date=dt.date(2026, 10, 20), resolved_date=dt.date(2026, 10, 4), resolution="recovered",
                 amount_recovered=D("130.00"), summary="CARC 4: Billing error; owner coder", payer_id=i["payer"], claim_id=i["claim"], denial_id=i["denial"], practice_id=1),
        ],
        "agent_task": [
            dict(agent_task_id=1, task_type="claim_hold_review", owner_role="biller", task_status="open", created_date=DAY, agent_code="A5", entity_type="claim", entity_id=i["claim"], agent_decision_id=2,
                 agent_finding_id=1, priority="hi", due_date=dt.date(2026, 10, 2), assigned_to=i["staff_biller"], amount_at_stake=D("210.00"), title="Review before release: CARC 198 risk",
                 practice_id=1, claim_id=i["claim"], payer_id=i["payer"], version=1, previous_agent_task_id=None, escalation_level=0, reminder_count=0),
            dict(agent_task_id=2, task_type="denial_work", owner_role="denial_specialist", task_status="returned", created_date=DAY, agent_code="A8", entity_type="denial", entity_id=i["denial"],
                 agent_decision_id=3, agent_finding_id=2, priority="md", due_date=dt.date(2026, 10, 3), assigned_to=i["staff_denial"], amount_at_stake=D("130.00"), title="Work the denial: Billing error",
                 practice_id=1, claim_id=i["claim"], payer_id=i["payer"], denial_id=i["denial"], completed_date=dt.date(2026, 10, 2), outcome="returned", minutes_spent=30, version=1, previous_agent_task_id=None),
            dict(agent_task_id=3, task_type="denial_work", owner_role="denial_specialist", task_status="done", created_date=DAY, agent_code="A8", entity_type="denial", entity_id=i["denial"],
                 agent_decision_id=3, agent_finding_id=2, priority="md", due_date=dt.date(2026, 10, 3), assigned_to=i["staff_denial"], amount_at_stake=D("130.00"), title="Work the denial: Billing error",
                 practice_id=1, claim_id=i["claim"], payer_id=i["payer"], denial_id=i["denial"], completed_date=dt.date(2026, 10, 4), outcome="resolved", minutes_spent=18, version=2, previous_agent_task_id=2),
        ],
        "agent_approval": [dict(agent_approval_id=1, agent_decision_id=3, approval_type="appeal_send", approval_status="approved", approved_by=i["staff_denial"], approver_role="denial_specialist",
                                approval_date=dt.date(2026, 10, 3), amount_approved=D("130.00"), limit_checked=True, entity_type="denial", entity_id=i["denial"], practice_id=1,
                                approval_ts=dt.datetime(2026, 10, 3, 10, 15), agent_task_id=3)],
        "agent_writeback": [dict(agent_writeback_id=1, agent_decision_id=3, target_system="portal", writeback_type="appeal_submit", send_status="suppressed", attempted_at=dt.datetime(2026, 10, 3, 10, 20),
                                 agent_approval_id=1, agent_code="A8", entity_type="denial", entity_id=i["denial"], attempt_no=1, payload_hash=b"\x03" * 32, practice_id=1, claim_id=i["claim"])],
        "agent_value": [
            dict(agent_value_id=1, agent_code="A8", value_stage="detected", amount=D("130.00"), value_date=DAY, entity_type="denial", entity_id=i["denial"], agent_finding_id=2, agent_decision_id=3,
                 practice_id=1, claim_id=i["claim"], denial_id=i["denial"], payer_id=i["payer"], transaction_id=None, is_holdout=False, incremental_amount=D("130.00"), value_kind="denial_recovery",
                 is_estimate=False, attribution_share=D("1.0")),
            dict(agent_value_id=2, agent_code="A8", value_stage="pending", amount=D("130.00"), value_date=dt.date(2026, 10, 4), entity_type="denial", entity_id=i["denial"], agent_finding_id=2,
                 agent_decision_id=3, practice_id=1, claim_id=i["claim"], denial_id=i["denial"], payer_id=i["payer"], transaction_id=None, is_holdout=False, incremental_amount=D("130.00"),
                 value_kind="denial_recovery", is_estimate=False, attribution_share=D("1.0")),
        ],
        "agent_forecast": [dict(agent_forecast_id=1, forecast_type="weekly_cash", as_of_date=DAY, target_start_date=DAY, target_end_date=dt.date(2026, 10, 7), expected_amount=D("1000.00"),
                                low_amount=D("700.00"), high_amount=D("1300.00"), probability=D("0.8"), claim_count=4, practice_id=1, payer_id=i["payer"], interval_level=D("0.80"), model_name="rules",
                                code_version="v0.9-shadow", actual_amount=D("900.00"), actual_known_date=dt.date(2026, 10, 7), within_range=True)],
    }
    rows["agent_decision"][1]["finding_id"], rows["agent_decision"][1]["task_id"] = 1, 1
    return {"rows": rows, "traces": {2: {"tables_read": ["claim", "encounter"]}}}


def tr(ids=None, **kw):
    return pp.translate(make_results(ids or fake_ids()), loaded_at=dt.datetime(2026, 11, 7, 9, 0, 0), source=TEST_SOURCE, **kw)


# ======================================================================== persistence mapping (no database)
def test_tables_are_agent_tables_only_and_checks_renamed():
    assert all(t.startswith("agent_") for t in pp.TABLES)
    assert len(pp.TABLES) == 9 and "agent_decision_check" in pp.TABLES
    rows = tr()
    assert len(rows["agent_decision_check"]) == 6                      # the engine's agent_decision_details
    assert set(rows) == set(pp.TABLES)


def test_every_column_is_an_r2_column_and_boilerplate_is_set():
    rows = tr()
    for t, lst in rows.items():
        cols = {c["name"] for c in pp.r2load.TBL[t]["cols"]}
        for r in lst:
            assert set(r) == cols, (t, set(r) ^ cols)
            assert r["tenant_id"] == 1 and r["source"] == TEST_SOURCE and r["loaded_at"] == dt.datetime(2026, 11, 7, 9, 0, 0)


def test_mandatory_columns_filled():
    rows = tr()
    for t, lst in rows.items():
        mand = [c["name"] for c in pp.r2load.TBL[t]["cols"] if c["priority"] == "Mandatory"]
        for r in lst:
            assert all(r.get(c) is not None for c in mand), (t, [c for c in mand if r.get(c) is None])


def test_value_maps_to_allowed_values():
    rows = tr()
    assert [d["outcome"] for d in rows["agent_decision"]] == ["proceed", "hold", "flag"]
    assert {f["agent_finding_id"]: f["finding_status"] for f in rows["agent_finding"]} == {1: "accepted", 2: "fixed"}
    st = {t["agent_task_id"]: (t["task_status"], t["outcome"], t["priority"]) for t in rows["agent_task"]}
    assert st[1] == ("open", None, "high") and st[2] == ("done", "returned", "normal") and st[3] == ("done", "done", "normal")
    ap = rows["agent_approval"][0]
    assert ap["approval_type"] == "send_to_payer" and ap["approved_by_staff_id"] == 7
    wb = rows["agent_writeback"][0]
    assert (wb["target_system"], wb["writeback_type"], wb["send_status"]) == ("payer_portal", "appeal_packet", "not_sent_shadow")
    assert rows["agent_run"][0]["run_status"] == "succeeded"
    assert rows["agent_forecast"][0]["forecast_type"] == "cash_week"
    for (t, col), ok in pp.ALLOWED_CHECK.items():
        for r in rows[t]:
            assert r[col] is None or r[col] in ok


def test_value_ledger_stage_and_estimate():
    v = {r["agent_value_id"]: r for r in tr()["agent_value"]}
    assert v[1]["value_stage"] == "detected" and v[1]["signed_amount"] == v[1]["amount"] == D("130.00")
    assert v[2]["value_stage"] == "recovered" and v[2]["is_estimate"] is True and v[2]["ledger_entry_id"] is None   # cash seen, remit not posted


def test_decision_record_keeps_rules_fired_and_lineage():
    rows = tr()
    for d in rows["agent_decision"]:
        checks = [c for c in rows["agent_decision_check"] if c["agent_decision_id"] == d["agent_decision_id"]]
        assert d["rules_checked"] == len(checks) >= 1
        assert d["rules_failed"] == sum(1 for c in checks if c["check_result"] == "fail")
        assert d["run_mode"] == "shadow" and len(d["input_hash"]) == 2 + 64      # salted hash literal, 32 bytes
    c2 = [c for c in rows["agent_decision_check"] if c["agent_decision_id"] == 2][0]
    assert c2["evidence_ref"] == "reads:claim,encounter" and c2["payer_rule_id"] is None
    d2 = rows["agent_decision"][1]
    assert (d2["recheck_condition"], d2["recheck_result"]) == ("payer_answer_received", "confirmed")   # verification condition and result


def test_load_batch_rides_in_run_code_version():
    rows = tr(load_batch_id=1)
    assert rows["agent_run"][0]["code_version"] == "v0.9-shadow|lb1"
    assert tr()["agent_run"][0]["code_version"] == "v0.9-shadow"


def test_money_is_decimal_and_float_is_refused():
    rows = tr()
    for t, lst in rows.items():
        for r in lst:
            for k, v in r.items():
                assert not isinstance(v, float), (t, k)
    bad = make_results(fake_ids())
    bad["rows"]["agent_task"][0]["amount_at_stake"] = 210.0
    with pytest.raises(pp.PersistError, match="Decimal"):
        pp.translate(bad)


def test_negative_value_amount_refused():
    bad = make_results(fake_ids())
    bad["rows"]["agent_value"][0]["amount"] = D("-1.00")
    with pytest.raises(pp.PersistError, match="negative"):
        pp.translate(bad)


def test_entity_type_maps_and_must_agree_with_typed_link():
    rows = tr()
    assert [d["entity_type"] for d in rows["agent_decision"]] == ["appointment", "claim", "denial"]
    bad = make_results(fake_ids())
    bad["rows"]["agent_decision"][1]["claim_id"] = 999
    with pytest.raises(pp.PersistError, match="disagrees"):
        pp.translate(bad)
    eng = make_results(fake_ids())
    eng["rows"]["agent_decision"][1].update(entity_type="claim_detail", entity_id=555)
    assert pp.translate(eng)["agent_decision"][1]["entity_type"] == "claim_line"
    eng["rows"]["agent_decision"][1].update(entity_type="payer_rule", entity_id=9, payer_id=6)          # A9: the rule row is not an agent table
    d = pp.translate(eng)["agent_decision"][1]
    assert (d["entity_type"], d["entity_id"]) == ("payer", 6)


def test_unknown_outcome_becomes_needs_human_and_bad_run_mode_is_refused():
    bad = make_results(fake_ids())
    bad["rows"]["agent_decision"][0]["outcome"] = "something_new"
    assert pp.translate(bad)["agent_decision"][0]["outcome"] == "needs_human"
    bad["rows"]["agent_run"][0]["run_mode"] = "autonomous"
    with pytest.raises(pp.PersistError, match="run_mode"):
        pp.translate(bad)


def test_identifier_like_text_is_refused():
    bad = make_results(fake_ids())
    bad["rows"]["agent_decision"][0]["reason_summary"] = "member 123456789012 not found"
    with pytest.raises(pp.PersistError, match="identifier"):
        pp.translate(bad)


def test_rework_chain_is_current_only_on_the_latest_version():
    t = {r["agent_task_id"]: r for r in tr()["agent_task"]}
    assert (t[2]["is_current"], t[3]["is_current"], t[3]["version"], t[3]["previous_agent_task_id"]) == (False, True, 2, 2)
    assert t[1]["is_current"] is True


def test_approved_without_approver_is_refused():
    bad = make_results(fake_ids())
    bad["rows"]["agent_approval"][0]["approved_by"] = None
    with pytest.raises(pp.PersistError, match="approved_by_staff_id"):
        pp.translate(bad)


def test_assign_ids_is_idempotent_and_remaps_parents():
    rows = tr()
    new, idmap, st = pp.assign_ids(copy.deepcopy(rows), {}, {t: 1000 for t in pp.TABLES})
    assert {t: len(v) for t, v in new.items()} == {t: len(v) for t, v in rows.items()}
    assert {r["agent_decision_id"] for r in new["agent_decision"]} == {1000, 1001, 1002}
    assert all(c["agent_decision_id"] in {1000, 1001, 1002} for c in new["agent_decision_check"])
    t3 = [r for r in new["agent_task"] if r["version"] == 2][0]
    assert t3["previous_agent_task_id"] in {r["agent_task_id"] for r in new["agent_task"]}
    # second pass: everything already there -> nothing new
    have = {}
    for t, lst in new.items():
        have[t] = {}
        seen = {}
        for r in lst:
            k = pp.natural_key(t, r)
            seen[k] = seen.get(k, 0) + 1
            have[t][(k, seen[k])] = r[pp.PK[t]]
    new2, _, st2 = pp.assign_ids(tr(), have, {t: 5000 for t in pp.TABLES})
    assert all(len(v) == 0 for v in new2.values()) and all(s["new"] == 0 for s in st2.values())


def test_two_decisions_with_one_key_stay_two():
    rows = tr()
    extra = copy.deepcopy(rows["agent_decision"][1])
    extra["agent_decision_id"] = 9
    rows["agent_decision"].append(extra)
    new, _, _ = pp.assign_ids(rows, {}, {})
    assert len(new["agent_decision"]) == 4


def test_orphan_child_is_refused():
    bad = make_results(fake_ids())
    bad["rows"]["agent_approval"][0]["agent_decision_id"] = 99
    with pytest.raises(pp.PersistError, match="not in the batch"):
        pp.assign_ids(pp.translate(bad), {}, {})


class _Cur:
    def __init__(self, db):
        self.db, self.sql, self.rowcount = db, [], 0

    def execute(self, sql, args=None):
        self.sql.append(sql)

    def fetchone(self):
        return (self.db,)


class _Conn:
    def __init__(self, db):
        self.cur = _Cur(db)

    def cursor(self):
        return self.cur


def test_refuses_any_database_other_than_r2():
    for db in ("krisnnai_canonical", "valleywellnessedi", "postgres"):
        conn = _Conn(db)
        with pytest.raises(pp.PersistError, match="only 'krisnnai_r2'"):
            pp.persist(conn, make_results(fake_ids()))
        with pytest.raises(pp.PersistError):
            pp.reset(conn)
        assert not [s for s in conn.cur.sql if "DELETE" in s or "INSERT" in s or "COPY" in s]


def test_reset_touches_only_agent_tables_filtered_by_tenant_and_source():
    conn = _Conn("krisnnai_r2")
    pp.reset(conn, tenant_id=1, source="replay")
    deletes = [s for s in conn.cur.sql if s.startswith("DELETE")]
    assert len(deletes) == 9
    for s in deletes:
        assert re.match(r'DELETE FROM "agent_\w+" WHERE tenant_id = %s AND source = %s$', s), s
    assert [re.search(r'"(agent_\w+)"', s).group(1) for s in deletes] == list(reversed(pp.TABLES))      # children before parents


def test_json_round_trip_keeps_decimal_and_dates(tmp_path):
    res = make_results(fake_ids())
    p = tmp_path / "run.json"
    pp.dump_results(res, p)
    back = pp.load_results(p)
    assert back["rows"]["agent_task"][0]["amount_at_stake"] == D("210.00") and isinstance(back["rows"]["agent_task"][0]["amount_at_stake"], Decimal)
    assert back["rows"]["agent_task"][0]["due_date"] == dt.date(2026, 10, 2)
    assert back["rows"]["agent_run"][0]["started_at"] == TS + dt.timedelta(minutes=1)
    assert back["rows"]["agent_decision"][0]["input_hash"] == b"\x01" * 32


# ======================================================================== export (no database)
def inputs_from(rows, ids):
    pay = {ids["payer"]: dict(payer_id=ids["payer"], payer_code="UHC", payer_name="UnitedHealthcare", filing_days=90, appeal_days=180)}
    return {
        "practice": {"practice_id": 1, "practice_name": "Synthea Texas Network (synthetic)"},
        "payers": pay,
        "staff": {2: dict(staff_number="STF-002", staff_role="biller", team="billing", weekly_hours=D("40")), 7: dict(staff_number="STF-007", staff_role="denial_analyst", team="denials", weekly_hours=D("40"))},
        "cpt": {},
        "decisions": rows["agent_decision"], "findings": rows["agent_finding"], "tasks": rows["agent_task"],
        "checks": {d: [c for c in rows["agent_decision_check"] if c["agent_decision_id"] == d] for d in (1, 2, 3)},
        "claims": {ids["claim"]: dict(claim_id=ids["claim"], claim_number="CLM-101", total_charge=D("210.00"), payer_id=ids["payer"])},
        "runs": {"status": "ok", "files_loaded": 1, "events_added": 12, "runs": 3, "first_run": "2026-10-01", "last_run": "2026-10-01", "code_version": "v0.9-shadow", "load_batch_id": 1, "source": "replay"},
        "claims_billed": 5, "data_start": dt.date(2023, 11, 8), "denials_by_carc": {"4": 40, "96": 100, "151": 7, "11": 3, "197": 9},
        "fvp": {"4": {"planted": 40, "found": 1}, "96": {"planted": 100, "found": 0}},
        "health": {"claims": 5, "clean_claim_rate": "0.900000", "days_in_ar": "40.000000", "ar_over_90_share": "0.100000"},
        "reconciliation": [{"name": "x", "description": "d", "items": 3, "mismatches": 0, "max_difference": "0.00", "passed": True, "tolerance": "0"}],
        "reference": {k: [] for k in ("carc_routes", "rejection_routes", "ncci_pairs", "mue_limits", "fee_schedule", "auth_requirements", "filing_windows", "appeal_windows", "policy")},
    }


def payload_at(as_of):
    ids = fake_ids()
    return ex.build_payload(inputs_from(tr(ids), ids), as_of)


def sample_json():
    if not SAMPLE.exists():
        return None
    s = SAMPLE.read_text(encoding="utf-8")
    return json.loads(s[s.index("=") + 1:].rstrip().rstrip(";"))


def test_top_level_keys_equal_the_sample():
    p = payload_at(dt.date(2026, 10, 5))
    assert sorted(p) == ex.TOP_KEYS
    s = sample_json()
    if s is None:
        pytest.skip("sample ui_data.js not on this machine")
    assert sorted(p) == sorted(s)


def test_nested_keys_match_the_sample():
    s = sample_json()
    if s is None:
        pytest.skip("sample ui_data.js not on this machine")
    p = payload_at(dt.date(2026, 10, 5))
    assert set(p["meta"]) == set(s["meta"]) and set(p["meta"]["planted"]) >= set(s["meta"]["planted"]) and set(p["meta"]["run"]) >= set(s["meta"]["run"])
    assert set(p["baseline"]) == set(s["baseline"]) and set(p["replay"]) == set(s["replay"])
    assert set(p["staff"]) == set(s["staff"])
    assert len(p["agents"]) == 15 and [a["id"] for a in p["agents"]] == [a["id"] for a in s["agents"]]
    for a, b in zip(p["agents"], s["agents"]):
        assert set(a) == set(b)
    assert p["queue"] and set(p["queue"][0]) == set(s["queue"][0])
    assert set(p["slices"][0] if p["slices"] else s["slices"][0]) == set(s["slices"][0]) if p["slices"] else True
    assert set(p["replay"]["reconciliation"][0]) == set(s["replay"]["reconciliation"][0])
    assert set(p["baseline"]["by_type"]) >= {"denial", "rejection", "timely_filing", "unbilled_visit", "underpayment"}
    k = next(iter(p["queue_stats"]))
    assert set(p["queue_stats"][k]) == set(next(iter(s["queue_stats"].values())))
    assert set(p["queue_totals"][next(iter(p["queue_totals"]))]) == {"open", "value"}


def test_money_is_two_decimal_strings_and_the_json_has_no_float_money():
    p = payload_at(dt.date(2026, 10, 5))
    money = re.compile(r"^\d+\.\d{2}$")
    for q in p["queue"]:
        assert money.match(q["value"]) and money.match(q["priority"]) and (q["billed"] is None or money.match(q["billed"]))
    for a in p["agents"]:
        assert all(money.match(x["dollars"]) for x in a["actions"])
    assert money.match(p["baseline"]["recoverable"]) and money.match(p["baseline"]["structural"])
    json.dumps(p)                                    # Decimal anywhere would raise: dumps() has no default handler
    assert "Decimal" not in ex.dumps(p)


def test_point_in_time_queue():
    # day 1: the A5 task and the first A8 task are open; the rework version does not exist yet
    q1 = {x["title"]: x for x in payload_at(dt.date(2026, 10, 1))["queue"]}
    assert len(q1) == 2
    # day 3: the A8 task came back on the 2nd and its rework version is open: still two open items, not three
    p3 = payload_at(dt.date(2026, 10, 3))
    assert len(p3["queue"]) == 2 and p3["queue_totals"]["billing|a8_denial"]["open"] == 1
    # day 5: the rework finished on the 4th; only the A5 task (overdue) is open
    p5 = payload_at(dt.date(2026, 10, 5))
    assert [q["agent"] for q in p5["queue"]] == ["a5_prevention"] and p5["queue"][0]["overdue"] is True
    # before anything happened
    assert payload_at(dt.date(2026, 9, 30))["queue"] == []


def test_queue_item_content_and_vocabulary():
    q = payload_at(dt.date(2026, 10, 5))["queue"][0]
    assert q["claim"] == "CLM-101" and q["payer"] == "UHC" and q["owner"] == "biller" and q["action_type"] == "a5_hold_review"
    assert q["value"] == "178.50" and q["billed"] == "210.00" and q["confidence"] == "0.85"      # expected dollars = at stake x confidence
    assert any(e["rule"] == "R-AUTH-VISITS" and e["result"] is False for e in q["evidence"])        # the rules that fired travel with the card
    assert q["next_steps"] and q["why"] and q["deadline"] == "2026-10-02" and q["raised_on"] == "2026-10-01"


def test_a8_owner_and_cause_and_planted_counts():
    p = payload_at(dt.date(2026, 10, 3))
    a8 = next(a for a in p["agents"] if a["id"] == "A8")
    assert {x["defect"]: x["count"] for x in a8["planted"]}["carc_4_em_injection_no_modifier_25"] == 40
    assert p["queue_stats"]["billing|a8_denial"]["by_cause"][0]["key"] == "CARC 4"


def test_planted_is_described_as_generator_rules_not_an_answer_key():
    m = payload_at(dt.date(2026, 10, 5))["meta"]
    rules = m["planted"]["generator_rules"]
    assert {r["carc"] for r in rules} == {"96", "4", "151", "11", "197"}
    assert "generator rules" in m["planted"]["note"] and "not a simulator's hidden answer key" in m["planted"]["note"]
    assert "answer key" not in json.dumps([r["rule"] for r in rules]).lower()
    assert m["as_of"] == "2026-10-05" and m["shadow"] is True and m["run"]["practice"].startswith("Synthea Texas Network")


def test_no_patient_identifiers_in_the_payload():
    text = ex.dumps(payload_at(dt.date(2026, 10, 5)))
    for banned in ("patient_id", "patient_number", "birth", "member_id", "first_name", "last_name", "ssn"):
        assert banned not in text.lower()
    # staff are pseudonymous ids, never names
    assert all(re.match(r"^STF-\d+$", e["name"]) for e in payload_at(dt.date(2026, 10, 5))["staff"]["employees"])


def test_found_vs_planted_is_honest_about_what_was_caught():
    f = {x["type"]: x for x in payload_at(dt.date(2026, 10, 5))["replay"]["found_vs_planted"]}
    assert f["carc_4"]["planted"] == 40 and f["carc_4"]["found"] == 1 and f["carc_4"]["recall"] == 0.025
    assert f["carc_96"]["recall"] == 0.0


# ======================================================================== owner mapping: the engine's owner_role -> the site's personas
SITE_HTML = pathlib.Path(r"C:\Users\gopi.v\Downloads\krisnnai-site\product.html")
# every (agent, engine owner_role) the engine can create, and the persona that must see it
ENGINE_TASKS = [("A1", "front_desk", "frontdesk"), ("A2", "front_desk", "frontdesk"), ("A3", "provider", "provider"), ("A3", "biller", "biller"), ("A4", "coder", "coder"), ("A5", "biller", "biller"),
                ("A6", "biller", "biller"), ("A7", "ar_specialist", "arlead"), ("A8", "denial_specialist", "denials"), ("A8", "biller", "denials"), ("A8", "front_desk", "denials"),
                ("A8", "coder", "denials"), ("A9", "manager", "manager"), ("A10", "billing_lead", "finance"), ("A11", "payment_poster", "poster"), ("A15", "billing_lead", "owner")]


def site_personas():
    """PERSONAS from the site's product.html, read only: {key: [{o: [...], a: [...]}, ...]}. None if the file is not on this machine."""
    if not SITE_HTML.exists():
        return None
    html = SITE_HTML.read_text(encoding="utf-8")
    block = html[html.index("const PERSONAS={"):html.index("const inSel=")]
    out = {}
    for m in re.finditer(r"\n (\w+):\{label:'[^']*',sel:(\[.*?\]),nav:", block):
        out[m.group(1)] = json.loads(re.sub(r"(\b[oa]):", r'"\1":', m.group(2)).replace("'", '"'))
    return out


def in_sel(sel, owner, agent):
    """product.html inSel(): some selector matches the owner (if it names owners) and the agent (if it names agents)."""
    return any((not s.get("o") or owner in s["o"]) and (not s.get("a") or agent in s["a"]) for s in sel)


def test_every_engine_task_reaches_its_persona_through_the_owner_mapping():
    pers = site_personas()
    if pers is None:
        pytest.skip("product.html not on this machine")
    for agent, role, persona in ENGINE_TASKS:
        owner = ex.owner_of(agent, role)
        assert in_sel(pers[persona], owner, ex.SITE_AGENT[agent]), (agent, role, owner, persona)


def test_a10_goes_to_finance_a12_to_patient_billing_and_a11_to_the_poster():
    assert ex.owner_of("A10", "billing_lead") == "finance"
    assert ex.owner_of("A12", "patient_billing") == "patient_billing" and ex.owner_of("A12", "biller") == "patient_billing"
    assert ex.owner_of("A11", "payment_poster") == "payment_poster" and ex.owner_of("A7", "ar_specialist") == "ar_lead"
    assert ex.owner_of("A9", "manager") == "practice_manager" and ex.owner_of("A15", "billing_lead") == "revenue_assurance_lead"


def test_an_item_lands_in_the_persona_it_is_meant_for_and_not_in_unrelated_ones():
    pers = site_personas()
    if pers is None:
        pytest.skip("product.html not on this machine")
    assert not in_sel(pers["finance"], ex.owner_of("A8", "denial_specialist"), "a8_denial")
    assert not in_sel(pers["poster"], ex.owner_of("A5", "biller"), "a5_prevention")
    assert not in_sel(pers["denials"], ex.owner_of("A5", "biller"), "a5_prevention")
    assert in_sel(pers["biller"], ex.owner_of("A5", "biller"), "a5_prevention")


def test_queue_totals_use_the_site_owner_words():
    p = payload_at(dt.date(2026, 10, 3))
    assert set(k.split("|")[0] for k in p["queue_totals"]) <= {"biller", "billing", "ar_lead", "payment_poster", "finance", "front_desk", "patient_billing", "coder", "practice_manager",
                                                               "provider", "credentialing", "revenue_assurance_lead"}


def test_found_vs_planted_counts_only_holds_that_name_the_carc():
    # a hold that predicted CARC 4 and 151 counts for both; one that predicted 198 counts for neither
    assert ex._carcs_of("Predicted CARC 4, 151: R-EM-INJ-MOD25, R-UNIT-LIMIT") == ["4", "151"]
    assert ex._carcs_of("Predicted CARC 198: R-AUTH-VISITS") == ["198"]
    assert ex._carcs_of("CARC 4: Billing error; owner coder") == []          # a denial summary is not a prediction
    rows = tr()
    ids = fake_ids()
    inp = inputs_from(rows, ids)
    inp["findings"] = [dict(f, summary="Predicted CARC 4, 151: R-EM-INJ-MOD25, R-UNIT-LIMIT", finding_status="accepted") if f["agent_code"] == "A5" else f for f in inp["findings"]]
    inp["fvp"] = {"4": {"planted": 10, "found": 4}, "151": {"planted": 20, "found": 5}, "96": {"planted": 10, "found": 0}}
    f = {x["type"]: x for x in ex.build_payload(inp, dt.date(2026, 10, 5))["replay"]["found_vs_planted"]}
    assert f["carc_4"]["precision"] == 1.0 and f["carc_151"]["precision"] == 1.0 and f["carc_96"]["precision"] is None
    assert f["carc_4"]["recall"] == 0.4 and f["carc_151"]["recall"] == 0.25


def test_the_found_query_counts_a_hold_before_the_denial_and_names_the_carc():
    import inspect
    src = inspect.getsource(ex.load_inputs)
    assert "f.found_date < d.denial_date" in src and "Predicted CARC" in src and "predicted_denial" in src


def test_default_output_is_out_ui_not_the_site_folder():
    import inspect
    src = inspect.getsource(ex.main)
    assert '"out" / "ui"' in src
    assert "krisnnai-site" not in inspect.getsource(ex)


def test_write_ui_data_writes_js_and_json(tmp_path):
    j, js = ex.write_ui_data(payload_at(dt.date(2026, 10, 5)), tmp_path)
    text = js.read_text(encoding="utf-8")
    assert text.startswith("window.KRISNNAI_LIVE = ") and text.rstrip().endswith(";")
    assert json.loads(text[len("window.KRISNNAI_LIVE = "):].rstrip().rstrip(";")) == json.loads(j.read_text(encoding="utf-8"))


# ======================================================================== database tests (skipped when R2 is unreachable)
@pytest.fixture(scope="module")
def conn():
    try:
        c = pp.r2load.connect()
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"krisnnai_r2 not reachable: {type(e).__name__}")
    yield c
    c.rollback()
    c.close()


@pytest.fixture()
def db(conn):
    conn.rollback()
    yield conn
    conn.rollback()                                   # nothing in these tests is ever committed


@pytest.fixture(scope="module")
def real_ids(conn):
    cur = conn.cursor()
    cur.execute("select d.denial_id, d.claim_id, d.payer_id, d.patient_id, c.rendering_provider_id, c.encounter_id from denial d join claim c on c.claim_id = d.claim_id and c.tenant_id = d.tenant_id "
                "where d.tenant_id = 1 and c.encounter_id is not null and c.rendering_provider_id is not null order by d.denial_id limit 1")
    den, cl, pay, pat, prov, enc = cur.fetchone()
    cur.execute("select appointment_id from appointment where tenant_id = 1 order by 1 limit 1")
    appt = cur.fetchone()[0]
    cur.execute("select claim_id from claim where tenant_id = 1 and claim_id <> %s order by 1 limit 1", (cl,))
    cl2 = cur.fetchone()[0]
    return dict(claim=cl, claim2=cl2, payer=pay, denial=den, patient=pat, provider=prov, appointment=appt, encounter=enc, staff_biller=2, staff_denial=7, staff_lead=1)


def counts(conn, tenant=1, source=TEST_SOURCE):
    cur = conn.cursor()
    out = {}
    for t in pp.TABLES:
        cur.execute(f'select count(*) from "{t}" where tenant_id = %s and source = %s', (tenant, source))
        out[t] = cur.fetchone()[0]
    return out


def test_db_persist_is_idempotent_and_reset_gives_identical_counts(db, real_ids):
    res = make_results(real_ids)
    r1 = pp.persist(db, res, source=TEST_SOURCE)
    c1 = counts(db)
    assert c1 == {"agent_run": 3, "agent_decision": 3, "agent_decision_check": 6, "agent_finding": 2, "agent_task": 3, "agent_approval": 1, "agent_writeback": 1, "agent_value": 2, "agent_forecast": 1}
    assert r1["written"] == c1
    r2 = pp.persist(db, make_results(real_ids), source=TEST_SOURCE)           # same run again: nothing new
    assert sum(r2["written"].values()) == 0 and counts(db) == c1
    r3 = pp.persist(db, make_results(real_ids), source=TEST_SOURCE, reset_first=True)
    assert r3["deleted"] == c1 and counts(db) == c1
    # ids are fresh keys, links are intact
    cur = db.cursor()
    cur.execute("select count(*) from agent_task t join agent_decision d on d.agent_decision_id = t.agent_decision_id where t.source = %s and d.source = %s", (TEST_SOURCE, TEST_SOURCE))
    assert cur.fetchone()[0] == 3


def test_db_reset_deletes_only_its_own_rows(db, real_ids):
    pp.persist(db, make_results(real_ids), source=TEST_SOURCE)
    other = make_results(real_ids)
    pp.persist(db, other, source=TEST_SOURCE + "_b")
    assert counts(db, source=TEST_SOURCE + "_b")["agent_decision"] == 3
    pp.reset(db, source=TEST_SOURCE)
    assert sum(counts(db).values()) == 0
    assert counts(db, source=TEST_SOURCE + "_b")["agent_decision"] == 3
    cur = db.cursor()
    cur.execute("select count(*) from agent_decision where source = 'replay'")      # real replay rows, whatever is there, are not ours to touch: count is unchanged by this test
    before = cur.fetchone()[0]
    pp.reset(db, source=TEST_SOURCE + "_b")
    cur.execute("select count(*) from agent_decision where source = 'replay'")
    assert cur.fetchone()[0] == before


def test_db_tenant_isolation(db, real_ids):
    pp.persist(db, make_results(real_ids), tenant_id=1, source=TEST_SOURCE)
    base = counts(db)
    assert sum(pp.reset(db, tenant_id=2, source=TEST_SOURCE).values()) == 0         # another tenant's reset cannot reach tenant 1
    assert counts(db) == base
    inp = ex.load_inputs(db, tenant_id=2, as_of=dt.date(2026, 10, 5), source=TEST_SOURCE)
    assert inp["decisions"] == [] and inp["tasks"] == [] and inp["findings"] == [] and inp["claims"] == {}
    p = ex.build_payload(inp, dt.date(2026, 10, 5))
    assert p["queue"] == [] and p["queue_totals"] == {} and sum(a["decisions"] for a in p["agents"]) == 0
    assert sorted(p) == ex.TOP_KEYS


def test_db_missing_link_is_refused_and_nothing_is_written(db, real_ids):
    bad = make_results(real_ids)
    bad["rows"]["agent_decision"][1].update(claim_id=987654321, entity_id=987654321)
    with pytest.raises(pp.PersistError, match="not in R2"):
        pp.persist(db, bad, source=TEST_SOURCE)
    assert sum(counts(db).values()) == 0


def test_db_export_resolves_every_claim_reference_and_keeps_the_schema(db, real_ids):
    pp.persist(db, make_results(real_ids), source=TEST_SOURCE)
    inp = ex.load_inputs(db, tenant_id=1, as_of=dt.date(2026, 10, 5), source=TEST_SOURCE)
    p = ex.build_payload(inp, dt.date(2026, 10, 5))
    assert sorted(p) == ex.TOP_KEYS
    s = sample_json()
    if s is not None:
        assert sorted(p) == sorted(s)
    assert p["queue"], "the A5 task is open on 2026-10-05"
    cur = db.cursor()
    for q in p["queue"]:
        if re.match(r"^CLM-\d+$", q["claim"]):
            cur.execute("select claim_id, total_charge from claim where tenant_id = 1 and claim_number = %s", (q["claim"],))
            row = cur.fetchone()
            assert row is not None, q["claim"]
            assert q["billed"] is None or q["billed"] == f"{row[1]:.2f}"
    assert p["meta"]["run"]["practice"] == "Synthea Texas Network (synthetic)" and p["meta"]["run"]["load_batch_id"] == 1
    assert {r["name"]: r["passed"] for r in p["replay"]["reconciliation"]}["decision_rule_count"] is True
    assert ex.dumps(p)                                                                   # serialisable
    # reference data comes from R2
    assert p["reference"]["carc_routes"] and p["reference"]["filing_windows"]
    assert {"claims", "clean_claim_rate", "days_in_ar", "ar_over_90_share"} == set(p["replay"]["health"])
