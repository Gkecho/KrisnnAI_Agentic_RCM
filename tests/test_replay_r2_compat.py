"""Replay on R2: the env switch keeps today's defaults, finite staff capacity and the A5 pattern rules (no database), and the canon_compat layer is views only, tenant-scoped, and row-for-row with the R2 tables.

The database tests are skipped when krisnnai_r2 cannot be reached. They only SELECT (read-only session); nothing is written.
"""
import datetime as dt
import importlib
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "replay"))
sys.path.insert(0, str(ROOT / "tools" / "synth"))


def _fresh(monkeypatch, **env):
    for k in ("KRISNNAI_REPLAY_DB", "KRISNNAI_REPLAY_START", "KRISNNAI_REPLAY_END"):
        monkeypatch.delenv(k, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    import world
    import engine
    return importlib.reload(world), importlib.reload(engine)


def test_default_is_unchanged(monkeypatch):
    world, engine = _fresh(monkeypatch)
    assert world.replay_db() is None and not world.is_r2()
    assert engine.START == dt.date(2025, 11, 3)
    assert engine.RULES_FROM == dt.date(2025, 11, 1)
    assert engine.A15_FROM == dt.date(2026, 1, 5)
    assert engine.A14_FROM == dt.date(2026, 2, 2)
    assert engine.A5_NEXT_BIZ is False and engine.AR_AS_OF is False          # canonical keeps today's behaviour


def test_r2_enables_next_business_day_and_as_of_ar(monkeypatch):
    _, engine = _fresh(monkeypatch, KRISNNAI_REPLAY_DB="krisnnai_r2")
    assert engine.A5_NEXT_BIZ is True and engine.AR_AS_OF is True


def test_a5_flag_works_for_canonical(monkeypatch):
    _, engine = _fresh(monkeypatch, KRISNNAI_REPLAY_A5_NEXT_BIZ="1")
    assert engine.A5_NEXT_BIZ is True and engine.AR_AS_OF is False


def test_plan_of_care_is_unknown_without_documents(monkeypatch):
    _, engine = _fresh(monkeypatch)
    from types import SimpleNamespace
    r = SimpleNamespace(W=SimpleNamespace(doc_types=set()))
    assert engine.Replay.has_poc(r, {"patient_id": 1, "encounter_date": dt.date(2025, 1, 1)}) is None      # unknown, not "missing"


def test_plan_of_care_known_when_documents_exist(monkeypatch):
    _, engine = _fresh(monkeypatch)
    from types import SimpleNamespace
    e = {"patient_id": 1, "encounter_date": dt.date(2025, 3, 1), "encounter_type": "evaluation"}
    W = SimpleNamespace(doc_types={"plan_of_care"}, pat_enc={1: [e]}, pat_doc={1: [{"document_type": "plan_of_care", "document_date": dt.date(2025, 3, 1)}]})
    r = SimpleNamespace(W=W)
    assert engine.Replay.has_poc(r, e) is True
    W.pat_doc = {1: []}
    assert engine.Replay.has_poc(r, e) is False


def test_only_exact_r2_name_is_accepted(monkeypatch):
    world, _ = _fresh(monkeypatch)
    for bad in ("krisnnai_r2_copy", "krisnnai_canonical", "krisnnai_r", "KRISNNAI_R2", "x"):
        monkeypatch.setenv("KRISNNAI_REPLAY_DB", bad)
        with pytest.raises(ValueError):
            world.replay_db()
    monkeypatch.setenv("KRISNNAI_REPLAY_DB", "krisnnai_r2")
    assert world.is_r2()


def test_window_env_overrides(monkeypatch):
    _, engine = _fresh(monkeypatch, KRISNNAI_REPLAY_START="2023-11-06", KRISNNAI_REPLAY_END="2026-11-06")
    assert engine.START == dt.date(2023, 11, 6) and engine.TODAY == dt.date(2026, 11, 6)
    assert engine.A14_FROM == engine.START + dt.timedelta(days=91)


def test_r2_write_mode_is_refused(monkeypatch):
    world, engine = _fresh(monkeypatch, KRISNNAI_REPLAY_DB="krisnnai_r2")
    r = engine.Replay.__new__(engine.Replay)
    r.write = True
    r._reset_state = lambda: None
    with pytest.raises(RuntimeError):
        engine.Replay.prepare(r)


# ======================================================================== finite staff capacity (no database)
def _pool(engine, cap, **kw):
    return engine.WorkPool("biller", cap, **{"overtime": 0, **kw})


def _add(pool, created, n, amount=100, due=None, prio="md"):
    for i in range(n):
        pool.add(created, due or created + dt.timedelta(days=3), amount, prio, (created, i))


def _biz_days(engine, start, n):
    out, d = [], start
    while len(out) < n:
        if engine.is_biz(d):
            out.append(d)
        d += dt.timedelta(days=1)
    return out


def test_backlog_carries_over_and_never_exceeds_capacity(monkeypatch):
    _, engine = _fresh(monkeypatch)
    pool = _pool(engine, 3)
    days = _biz_days(engine, dt.date(2026, 10, 5), 8)
    _add(pool, days[0], 10)                                  # 10 arrive on day 1: capacity 3 a day
    done_per_day = [len(pool.work(d)) for d in days[1:]]
    assert done_per_day[:4] == [3, 3, 3, 1]                  # 3, 3, 3, then the last one: carried over day after day
    assert all(n <= 3 for n in done_per_day) and not pool.items
    assert sum(done_per_day) == 10                           # nothing lost, nothing invented


def test_a_task_is_first_worked_after_the_day_it_was_created(monkeypatch):
    _, engine = _fresh(monkeypatch)
    pool = _pool(engine, 5)
    d1, d2 = _biz_days(engine, dt.date(2026, 10, 5), 2)
    _add(pool, d1, 2)
    assert pool.work(d1) == []                               # created today: not worked today
    assert len(pool.work(d2)) == 2                           # so a completion date is always after the creation date


def test_fractional_capacity_carries_the_remainder_and_idle_capacity_is_not_banked(monkeypatch):
    _, engine = _fresh(monkeypatch)
    pool = _pool(engine, 2.5)
    days = _biz_days(engine, dt.date(2026, 10, 5), 9)
    _add(pool, days[0], 30)
    got = [len(pool.work(d)) for d in days[1:]]
    assert got[:4] == [2, 3, 2, 3] and sum(got[:4]) == 10
    idle = _pool(engine, 2.5)
    for d in days:                                           # a quiet spell must not build a stock of free capacity
        idle.work(d)
    _add(idle, days[-1], 20)
    assert len(idle.work(days[-1] + dt.timedelta(days=1))) <= 3


def test_staff_work_the_highest_value_urgency_first_and_nothing_starves(monkeypatch):
    _, engine = _fresh(monkeypatch)
    pool = _pool(engine, 1)
    d1, d2 = _biz_days(engine, dt.date(2026, 10, 5), 2)
    pool.add(d1, d1 + dt.timedelta(days=5), 100, "md", "small")
    pool.add(d1, d1 + dt.timedelta(days=5), 900, "md", "big")
    pool.add(d1, d1 + dt.timedelta(days=5), 500, "hi", "mid_hi")
    assert pool.work(d2) == ["big"]                          # value first
    assert pool.work(d2 + dt.timedelta(days=1)) == ["mid_hi"]
    # a small task that has been overdue for 95 days outranks a fresh task worth 3 times as much
    old = _pool(engine, 1)
    d = dt.date(2026, 11, 2)
    old.add(d - dt.timedelta(days=100), d - dt.timedelta(days=95), 100, "md", "old_small")
    old.add(d - dt.timedelta(days=1), d + dt.timedelta(days=2), 300, "md", "new_big")
    assert old.work(d) == ["old_small"]


def test_overtime_only_when_the_backlog_is_deep_and_is_capped(monkeypatch):
    _, engine = _fresh(monkeypatch)
    pool = engine.WorkPool("biller", 4, overtime=.25, ot_days=4)
    d0 = dt.date(2026, 10, 5)
    _add(pool, d0, 16)
    assert pool.today_capacity() == 4                        # exactly 4 days of work: normal hours
    _add(pool, d0, 16)
    assert 4 * 1.25 < pool.today_capacity() <= 4 * (1 + engine.MAX_OVERTIME)       # deeper: extra hours, in proportion
    _add(pool, d0, 500)
    assert pool.today_capacity() == pytest.approx(4 * (1 + engine.MAX_OVERTIME))   # never more than the cap


def test_a_busy_quarter_builds_a_backlog_and_no_day_exceeds_capacity_plus_capped_overtime(monkeypatch):
    _, engine = _fresh(monkeypatch)
    pool = engine.WorkPool("denial_specialist", 16)
    days = _biz_days(engine, dt.date(2026, 1, 5), 60)
    for i, d in enumerate(days):
        pool.work(d)
        _add(pool, d, 20 + (i % 7))                          # 20-26 new items a day against 16 a day: more than the team can clear
    assert pool.history and all(done <= int(cap) + 1 for _d, _b, done, cap in pool.history)           # never more than that day's capacity (rounded up for the carried remainder)
    assert all(cap <= 16 * (1 + engine.MAX_OVERTIME) + 1e-9 for *_x, cap in pool.history)
    assert len(pool.items) > 3 * 16                          # a backlog stands at the end: nothing is magically cleared
    assert any(h[3] > 16 for h in pool.history)              # and overtime did kick in once it was deep
    hard = engine.WorkPool("denial_specialist", 16, overtime=0)
    for d in days:
        hard.work(d)
        _add(hard, d, 20)
    assert all(done <= 16 for _d, _b, done, _c in hard.history) and len(hard.items) > len(pool.items)   # without overtime: a hard cap of 16, and a deeper backlog


def test_weekends_and_holidays_are_off(monkeypatch):
    _, engine = _fresh(monkeypatch)
    from types import SimpleNamespace
    pool = _pool(engine, 5)
    fri = dt.date(2026, 10, 9)
    _add(pool, fri, 10)
    for it in pool.items:
        it["payload"] = lambda d: None                      # Replay.work_pools calls each finished task
    r = SimpleNamespace(pools={"biller": pool})
    for d in (dt.date(2026, 10, 10), dt.date(2026, 10, 11)):        # Saturday, Sunday
        assert not engine.is_biz(d)
        engine.Replay.work_pools(r, d)
    assert len(pool.items) == 10 and not pool.history       # nobody worked
    holiday = dt.date(2026, 10, 12)                          # Columbus Day: journey.is_biz treats it as a holiday
    assert not engine.is_biz(holiday)
    engine.Replay.work_pools(r, holiday)
    assert len(pool.items) == 10 and not pool.history
    engine.Replay.work_pools(r, dt.date(2026, 10, 13))
    assert pool.history[-1][0] == dt.date(2026, 10, 13) and len(pool.items) == 5


def test_capacity_comes_from_the_mapped_staff_in_canon_compat(monkeypatch):
    _, engine = _fresh(monkeypatch)
    staff = [dict(staff_id=2, staff_role="biller"), dict(staff_id=3, staff_role="biller"), dict(staff_id=4, staff_role="biller"),
             dict(staff_id=2, staff_role="biller"), dict(staff_id=3, staff_role="biller"),                 # the B01/B02 alias rows repeat a staff_id: counted once
             dict(staff_id=7, staff_role="denial_analyst"), dict(staff_id=8, staff_role="denial_analyst"),
             dict(staff_id=11, staff_role="payment_poster")]
    cap, per = engine.role_capacities(staff), engine.CAP_POOLS
    assert cap["denial_specialist"] == pytest.approx(2 * per["denial_specialist"][1] * per["denial_specialist"][2])
    assert cap["biller"] == pytest.approx(3 * per["biller"][1] * per["biller"][2])
    assert cap["patient_billing"] == pytest.approx(3 * per["patient_billing"][1] * per["patient_billing"][2])
    assert cap["payment_poster"] == per["payment_poster"][2]
    assert "front_desk" not in cap and "ar_specialist" not in cap          # nobody with that staff_role: no pool
    assert sum(sh for (sr, sh, _p) in per.values() if sr == "biller") <= 1.0     # the same biller is not promised twice
    assert sum(sh for (sr, sh, _p) in per.values() if sr == "biller_manager") <= 1.0


def test_capacity_is_on_for_r2_and_off_for_canonical(monkeypatch):
    _, engine = _fresh(monkeypatch)
    assert engine.CAPACITY is False
    _, engine = _fresh(monkeypatch, KRISNNAI_REPLAY_DB="krisnnai_r2")
    assert engine.CAPACITY is True


# ======================================================================== A5 pattern rules (no database)
from decimal import Decimal  # noqa: E402
from types import SimpleNamespace  # noqa: E402

CPT = {c: i for i, c in enumerate(["99213", "96372", "95115", "96127", "97110", "99408", "G0444", "G0136", "99395", "90935", "96413", "D0120", "99214"], 1)}
PAYERS = {1: "MEDICARE", 2: "UHC", 3: "HUMANA"}
M25 = 99


def mkW():
    return SimpleNamespace(has_ext=True, payer_code=PAYERS, cpt={v: k for k, v in CPT.items()}, mod={"25": M25}, cd={}, enc_lines={}, line_units={}, claim_dx={}, claim={},
                           auth_by_key={}, line_hist={})


def add_claim(W, cid, payer, svc, sub, lines, dx="Z0000", patient=1, extra_enc=()):
    """lines: [(code, units, modifier_1)]. extra_enc: codes on the visit that are not on this claim (an injection billed separately)."""
    cl = dict(claim_id=cid, payer_id=payer, patient_id=patient, encounter_id=cid, service_date_from=svc, submitted_date=sub, claim_number=f"CLM-{cid}")
    W.claim[cid] = cl
    W.cd[cid] = []
    W.enc_lines[cid] = [dict(cpt_code_id=CPT[c]) for c, _u, _m in lines] + [dict(cpt_code_id=CPT[c]) for c in extra_enc]
    for n, (code, units, m1) in enumerate(lines, 1):
        det = cid * 10 + n
        W.cd[cid].append(dict(claim_detail_id=det, cpt_code_id=CPT[code], modifier_1_id=m1, modifier_2_id=None))
        W.line_units[det] = units
        W.line_hist.setdefault((patient, CPT[code]), []).append((svc, det, units, cid, payer))
    W.claim_dx[cid] = dx
    return cl


def fired(engine, W, cl, d):
    res, fails = engine.pattern_checks(W, cl, d)
    return {rule for _c, _p, rule in fails}, res


D1, SUB = dt.date(2026, 3, 2), dt.date(2026, 3, 4)


def test_a5_dental_to_medicare_holds_and_other_cases_do_not(monkeypatch):
    _, engine = _fresh(monkeypatch)
    W = mkW()
    assert fired(engine, W, add_claim(W, 1, 1, D1, SUB, [("D0120", 1, None)]), SUB)[0] == {"R-DENTAL-MEDICARE"}
    assert fired(engine, W, add_claim(W, 2, 2, D1, SUB, [("D0120", 1, None)]), SUB)[0] == set()        # dental to a payer that covers it
    assert fired(engine, W, add_claim(W, 3, 1, D1, SUB, [("99213", 1, None)]), SUB) == (set(), [])     # clean Medicare claim: the rule does not even apply


def test_a5_em_with_injection_needs_modifier_25(monkeypatch):
    _, engine = _fresh(monkeypatch)
    W = mkW()
    assert fired(engine, W, add_claim(W, 1, 2, D1, SUB, [("99213", 1, None)], extra_enc=["96372"]), SUB)[0] == {"R-EM-INJ-MOD25"}
    assert fired(engine, W, add_claim(W, 2, 2, D1, SUB, [("99213", 1, M25)], extra_enc=["96372"]), SUB)[0] == set()
    assert fired(engine, W, add_claim(W, 3, 2, D1, SUB, [("99213", 1, None)]), SUB)[0] == set()        # no injection on the visit
    assert fired(engine, W, add_claim(W, 4, 2, D1, SUB, [("99213", 1, None), ("96372", 1, None)]), SUB)[0] == {"R-EM-INJ-MOD25"}


def test_a5_unit_and_frequency_limits(monkeypatch):
    _, engine = _fresh(monkeypatch)
    W = mkW()
    assert fired(engine, W, add_claim(W, 1, 2, D1, SUB, [("96127", 5, None)]), SUB)[0] == {"R-UNIT-LIMIT"}
    assert fired(engine, W, add_claim(W, 2, 2, D1, SUB, [("96127", 4, None)]), SUB)[0] == set()
    assert fired(engine, W, add_claim(W, 3, 2, D1, SUB, [("99408", 2, None)]), SUB)[0] == {"R-UNIT-LIMIT"}
    assert fired(engine, W, add_claim(W, 4, 2, D1, SUB, [("97110", 6, None)]), SUB)[0] == {"R-UNIT-LIMIT"}
    # once a year: the second G0444 in a calendar year, Medicare only
    first = add_claim(W, 10, 1, dt.date(2026, 1, 5), dt.date(2026, 1, 7), [("G0444", 1, None)], patient=9)
    second = add_claim(W, 11, 1, dt.date(2026, 6, 5), dt.date(2026, 6, 7), [("G0444", 1, None)], patient=9)
    assert fired(engine, W, first, first["submitted_date"])[0] == set()
    assert fired(engine, W, second, second["submitted_date"])[0] == {"R-UNIT-LIMIT"}
    uhc = add_claim(W, 12, 2, dt.date(2026, 7, 5), dt.date(2026, 7, 7), [("G0444", 1, None)], patient=9)
    assert fired(engine, W, uhc, uhc["submitted_date"])[0] == set()                                     # G0444 is only limited for Medicare
    add_claim(W, 13, 2, dt.date(2026, 7, 8), dt.date(2026, 7, 9), [("G0136", 1, None)], patient=8)
    g0136b = add_claim(W, 14, 3, dt.date(2026, 7, 20), dt.date(2026, 7, 21), [("G0136", 1, None)], patient=8)
    assert fired(engine, W, g0136b, g0136b["submitted_date"])[0] == {"R-UNIT-LIMIT"}                    # G0136 is limited for every payer
    nextyear = add_claim(W, 15, 1, dt.date(2027, 1, 5), dt.date(2027, 1, 7), [("G0444", 1, None)], patient=9)
    assert fired(engine, W, nextyear, nextyear["submitted_date"])[0] == set()                           # a new calendar year


def test_a5_frequency_does_not_look_ahead(monkeypatch):
    _, engine = _fresh(monkeypatch)
    W = mkW()
    early = add_claim(W, 20, 1, dt.date(2026, 2, 1), dt.date(2026, 2, 3), [("G0444", 1, None)], patient=5)
    late = add_claim(W, 21, 1, dt.date(2026, 5, 1), dt.date(2026, 5, 3), [("G0444", 1, None)], patient=5)
    early["submitted_date"] = dt.date(2026, 5, 20)       # the earlier visit was only submitted after the later claim was reviewed
    assert fired(engine, W, late, dt.date(2026, 5, 4))[0] == set()
    assert fired(engine, W, late, dt.date(2026, 5, 20))[0] == {"R-UNIT-LIMIT"}      # once the earlier claim is on file, it counts


def test_a5_preventive_visit_needs_a_routine_diagnosis(monkeypatch):
    _, engine = _fresh(monkeypatch)
    W = mkW()
    assert fired(engine, W, add_claim(W, 1, 2, D1, SUB, [("99395", 1, None)], dx="Z7189"), SUB)[0] == {"R-PREVENTIVE-DX"}
    assert fired(engine, W, add_claim(W, 2, 2, D1, SUB, [("99395", 1, None)], dx="Z00129"), SUB)[0] == set()
    assert fired(engine, W, add_claim(W, 3, 2, D1, SUB, [("99395", 1, None)], dx=None), SUB) == (set(), [])   # unknown diagnosis: abstain, not "missing"
    assert fired(engine, W, add_claim(W, 4, 2, D1, SUB, [("99213", 1, None)], dx="Z7189"), SUB)[0] == set()   # not a preventive code


def auth(status="approved", vf=dt.date(2026, 2, 27), vt=dt.date(2026, 6, 6), units=3, decided=dt.date(2026, 2, 25)):
    return dict(status=status, valid_from=vf, valid_to=vt, units_approved=units, decision_date=decided)


def test_a5_authorization_required_and_none_on_file(monkeypatch):
    _, engine = _fresh(monkeypatch)
    W = mkW()
    need = add_claim(W, 1, 2, D1, SUB, [("96413", 1, None)])
    assert fired(engine, W, need, SUB)[0] == {"R-AUTH-REQUIRED"}
    W.auth_by_key[(1, 2, CPT["96413"])] = [auth()]
    assert fired(engine, W, need, SUB)[0] == set()                                                      # an approved authorization covers it
    W.auth_by_key[(1, 2, CPT["96413"])] = [auth(status="denied")]
    assert fired(engine, W, need, SUB)[0] == {"R-AUTH-REQUIRED"}
    W.auth_by_key[(1, 2, CPT["96413"])] = [auth(vt=dt.date(2026, 2, 28))]                              # expired before the visit
    assert fired(engine, W, need, SUB)[0] == {"R-AUTH-REQUIRED"}
    W.auth_by_key[(1, 2, CPT["96413"])] = [auth(units=1)]                                               # one unit approved: the second visit is not covered
    second = add_claim(W, 2, 2, D1 + dt.timedelta(days=2), SUB, [("96413", 1, None)])
    assert fired(engine, W, second, SUB)[0] == {"R-AUTH-REQUIRED"}
    assert fired(engine, W, need, SUB)[0] == set()                                                      # while the first still is
    assert fired(engine, W, add_claim(W, 3, 2, D1, SUB, [("99213", 1, None)]), SUB) == (set(), [])     # not on the payer's authorization list: never checked
    assert fired(engine, W, add_claim(W, 4, 1, D1, SUB, [("96413", 1, None)], patient=4), SUB)[0] == set()   # MEDICARE has no authorization list in the map


def test_a5_authorization_decided_after_the_review_date_is_not_known(monkeypatch):
    _, engine = _fresh(monkeypatch)
    W = mkW()
    cl = add_claim(W, 1, 2, D1, SUB, [("96413", 1, None)])
    W.auth_by_key[(1, 2, CPT["96413"])] = [auth(decided=dt.date(2026, 3, 10))]                         # approved after the claim was reviewed
    assert fired(engine, W, cl, SUB)[0] == {"R-AUTH-REQUIRED"}
    assert fired(engine, W, cl, dt.date(2026, 3, 10))[0] == set()


def test_a5_each_rule_names_its_evidence_and_a_clean_claim_has_none(monkeypatch):
    _, engine = _fresh(monkeypatch)
    W = mkW()
    names, res = fired(engine, W, add_claim(W, 1, 2, D1, SUB, [("99395", 1, None)], dx="Z7189"), SUB)
    r = next(x for x in res if x[0] == "R-PREVENTIVE-DX")
    assert r[1] == "fail" and "Z7189" in r[2] and "Z0000" in r[3]
    assert engine.pattern_checks(W, add_claim(W, 2, 2, D1, SUB, [("99213", 1, None)]), SUB) == ([], [])
    res, fails = engine.pattern_checks(W, add_claim(W, 3, 2, D1, SUB, [("99395", 1, None)], dx="Z0000"), SUB)
    assert fails == [] and res and all(x[1] == "pass" for x in res)


def test_a5_abstains_outside_r2(monkeypatch):
    _, engine = _fresh(monkeypatch)
    W = mkW()
    W.has_ext = False
    assert engine.pattern_checks(W, add_claim(W, 1, 1, D1, SUB, [("D0120", 1, None)]), SUB) == ([], [])


def test_a5_auth_list_matches_the_data_generator():
    try:
        sys.path.insert(0, str(ROOT / "tools" / "synthea"))
        import load_auth_eligibility as gen
    except Exception as ex:
        pytest.skip(f"synthea loader not importable: {type(ex).__name__}")
    import engine
    assert engine.AUTH_REQUIRED == gen.REQUIRED


def test_a5_hold_carries_a_decision_rules_evidence_and_a_biller_task(monkeypatch):
    _, engine = _fresh(monkeypatch)
    W = mkW()
    W.carc, W.carc_id, W.cov, W.den_by_claim = {}, {}, {}, {}
    cl = add_claim(W, 1, 2, D1, SUB, [("99395", 1, None), ("96413", 1, None)], dx="Z7189")
    cl.update(coverage_id=None, total_charge=Decimal("300.00"), rendering_provider_id=1, bill_id=1, authorization_id=None)
    W.enc = {1: dict(encounter_date=D1, authorization_id=None, patient_id=1)}
    for ln in W.cd[1]:
        ln["expected_allowed"] = None
    emitted = []
    r = SimpleNamespace(W=W, remit={}, learned={}, generic={"R-AUTH-VISITS": 1, "R-COV-ACTIVE": 2, "R-PREVENTIVE-DX": 3, "R-AUTH-REQUIRED": 4}, mirror_find={}, cur_src=None,
                        r=SimpleNamespace(random=lambda: 1.0), rule=engine.Replay.rule, S=SimpleNamespace(rows={"agent_finding": ["F"]}), refs_of=lambda c: {"claim_id": c["claim_id"]})
    r.emit = lambda *a, **k: emitted.append((a, k)) or (1, 1, 1)
    engine.Replay.a5(r, SUB, [cl])
    (a, k), = emitted
    assert a[0] == "A5" and a[1] == "prerelease_review" and a[5] == "hold"                              # a decision record is written, with the hold outcome
    names = {x[0]: x[1] for x in a[7]}
    assert names["R-PREVENTIVE-DX"] == "fail" and names["R-AUTH-REQUIRED"] == "fail"                    # the rules that fired are in the record
    assert any(x[0] == "R-AUTH-REQUIRED" and x[5] == 4 for x in a[7])                                   # and point at their rule row
    assert k["task"]["role"] == "biller" and k["task"]["ttype"] == "claim_hold_review"                  # the fix task goes to the biller
    assert k["finding"]["summary"].startswith("Predicted CARC 197, 11:")
    assert r.mirror_find[1][1] == {"11", "197"}


# ======================================================================== A1 / A2 / A3 / A7 detectors added for R2 (no database)
def _emits(engine, fn, W, d, item):
    got = []
    r = SimpleNamespace(W=W, rule=engine.Replay.rule, cur_src=None, emit=lambda *a, **k: got.append((a, k)) or (1, 1, 1))
    getattr(engine.Replay, fn)(r, d, item)
    return got


def _pre_W():
    W = mkW()
    W.payer_code = PAYERS
    W.appt_expected = {7: Decimal("150")}
    W.checks_by_appt, W.elig_other = {}, {}
    return W


APPT = dict(appointment_id=7, patient_id=1, payer_id=2, provider_id=1, appointment_date=dt.date(2026, 11, 10), booked_date=dt.date(2026, 11, 2))
REVIEW = dt.date(2026, 11, 5)


def _chk(cid, day, **kw):
    return dict(eligibility_check_id=cid, appointment_id=7, check_date=day, **kw)


def test_a1_no_eligibility_check_for_a_visit_in_three_business_days(monkeypatch):
    _, engine = _fresh(monkeypatch)
    W = _pre_W()
    (a, k), = _emits(engine, "a1_pre_visit", W, REVIEW, APPT)
    assert k["finding"]["finding_type"] == "no_eligibility_check" and k["task"]["role"] == "front_desk" and a[5] == "flag"
    assert any(r_[0] == "R-ELIG-CHECKED" and r_[1] == "fail" for r_ in a[7])                  # rule evidence travels with the decision
    W.checks_by_appt = {7: [_chk(1, dt.date(2026, 11, 4))]}                                    # a check two business days ago: clean
    assert _emits(engine, "a1_pre_visit", W, REVIEW, APPT) == []
    W.checks_by_appt = {7: [_chk(1, dt.date(2026, 11, 9))]}                                    # done only after the review date: not known then (no look-ahead)
    assert _emits(engine, "a1_pre_visit", W, REVIEW, APPT)[0][1]["finding"]["finding_type"] == "no_eligibility_check"


def test_a1_stale_check_and_coverage_order_conflict(monkeypatch):
    _, engine = _fresh(monkeypatch)
    W = _pre_W()
    W.checks_by_appt = {7: [_chk(1, dt.date(2026, 9, 20))]}                                    # 51 days before the visit
    assert _emits(engine, "a1_pre_visit", W, REVIEW, APPT)[0][1]["finding"]["finding_type"] == "stale_eligibility_check"
    W.checks_by_appt = {7: [_chk(1, dt.date(2026, 10, 15))]}                                   # 26 days: fine
    assert _emits(engine, "a1_pre_visit", W, REVIEW, APPT) == []
    W.checks_by_appt = {7: [_chk(5, dt.date(2026, 11, 4))]}
    W.elig_other = {5: 3}                                                                      # the check names HUMANA as primary, the booking says UHC
    assert _emits(engine, "a1_pre_visit", W, REVIEW, APPT)[0][1]["finding"]["finding_type"] == "coverage_order_conflict"
    W.elig_other = {5: 2}                                                                      # naming the booked payer is no conflict
    assert _emits(engine, "a1_pre_visit", W, REVIEW, APPT) == []
    W.checks_by_appt = {7: [_chk(5, dt.date(2026, 11, 9))]}
    W.elig_other = {5: 3}
    assert _emits(engine, "a1_pre_visit", W, REVIEW, APPT)[0][1]["finding"]["finding_type"] == "no_eligibility_check"     # the conflict was not known yet


def test_back_biz_and_review_day_skip_weekends_and_holidays(monkeypatch):
    _, engine = _fresh(monkeypatch)
    assert engine.back_biz(dt.date(2026, 11, 9), 3) == dt.date(2026, 11, 4)            # Mon - 3 business days = Wed
    assert engine.is_biz(engine.back_biz(dt.date(2026, 11, 16), 3))


def _auth_W(auths, lines, history=()):
    W = _pre_W()
    W.appt_lines = {7: lines}
    W.auth_by_key = {(1, 2, CPT["96413"]): auths}
    W.line_hist = {(1, CPT["96413"]): list(history)}
    return W


def test_a2_scheduled_authorization_problems_over_every_line(monkeypatch):
    _, engine = _fresh(monkeypatch)
    ok = auth(vf=dt.date(2026, 10, 1), vt=dt.date(2027, 1, 31), units=10, decided=dt.date(2026, 9, 28))
    lines = [(1, CPT["99213"], 1), (2, CPT["96413"], 1)]                                         # the service that needs authorization is line 2
    W = _auth_W([ok], lines)
    assert _emits(engine, "a2_scheduled", W, REVIEW, APPT) == []                                # covered, plenty of time, plenty of units: clean
    W = _auth_W([], lines)
    (a, k), = _emits(engine, "a2_scheduled", W, REVIEW, APPT)
    assert k["finding"]["finding_type"] == "authorization_missing" and k["task"]["role"] == "front_desk" and any(r_[0] == "R-AUTH-ON-FILE" and r_[1] == "fail" for r_ in a[7])
    W = _auth_W([dict(ok, valid_to=dt.date(2026, 11, 20))], lines)                                    # ends 10 days after the visit
    assert _emits(engine, "a2_scheduled", W, REVIEW, APPT)[0][1]["finding"]["finding_type"] == "authorization_expiring"
    W = _auth_W([dict(ok, units_approved=3)], lines, history=[(dt.date(2026, 10, 5), 1, 1, 1, 2), (dt.date(2026, 10, 20), 2, 1, 2, 2)])
    assert _emits(engine, "a2_scheduled", W, REVIEW, APPT)[0][1]["finding"]["finding_type"] == "authorization_units_low"      # 3 approved, 2 used, 1 planned: none left
    W = _auth_W([dict(ok, decision_date=dt.date(2026, 11, 8))], lines)                                # approved after the review date: not known yet
    assert _emits(engine, "a2_scheduled", W, REVIEW, APPT)[0][1]["finding"]["finding_type"] == "authorization_missing"
    W = _auth_W([], [(1, CPT["99213"], 1)])                                                      # a service not on the payer's list: never flagged
    assert _emits(engine, "a2_scheduled", W, REVIEW, APPT) == []


def test_a3_unbilled_visit_goes_to_the_biller_and_an_unsigned_note_also_to_the_provider(monkeypatch):
    _, engine = _fresh(monkeypatch)
    W = SimpleNamespace(appt_expected={9: Decimal("90")}, prov_name={1: "Dr X"})
    base = dict(encounter_id=5, patient_id=1, payer_id=2, rendering_provider_id=1, appointment_id=9, encounter_date=dt.date(2026, 10, 28))
    d = dt.date(2026, 11, 3)
    signed = _emits(engine, "a3_unbilled", W, d, dict(base, note_signed_date=dt.date(2026, 10, 29)))
    assert len(signed) == 1 and signed[0][1]["task"]["role"] == "biller" and signed[0][1]["task"]["ttype"] == "unbilled_visit"
    assert any(r_[0] == "R-CHARGE-ENTERED" and r_[1] == "fail" for r_ in signed[0][0][7])
    for note in (None, dt.date(2026, 11, 20)):                                                   # unsigned, or signed only after the review date
        both = _emits(engine, "a3_unbilled", W, d, dict(base, note_signed_date=note))
        assert [x[1]["task"]["role"] for x in both] == ["biller", "provider"]


def test_a7_grace_is_zero_on_r2_and_14_on_canonical(monkeypatch):
    _, engine = _fresh(monkeypatch)
    assert engine.A7_GRACE == 14 and engine.PREVISIT is False
    _, engine = _fresh(monkeypatch, KRISNNAI_REPLAY_DB="krisnnai_r2")
    assert engine.A7_GRACE == 0 and engine.PREVISIT is True
    monkeypatch.setenv("KRISNNAI_REPLAY_A7_GRACE", "7")
    _, engine = _fresh(monkeypatch, KRISNNAI_REPLAY_DB="krisnnai_r2", KRISNNAI_REPLAY_A7_GRACE="7")
    assert engine.A7_GRACE == 7


def test_a7_follow_up_closes_itself_when_the_payer_answers_and_leaves_the_backlog(monkeypatch):
    _, engine = _fresh(monkeypatch)
    d0, d1 = dt.date(2026, 11, 2), dt.date(2026, 11, 4)
    pool = engine.WorkPool("ar_specialist", 2)
    pool.add(d0, d0, 100, "hi", lambda d: None, key=11)
    pool.add(d0, d0, 100, "hi", lambda d: None, key=12)
    trow = dict(agent_task_id=11, task_status="open", owner_role="ar_specialist")
    frow = dict(finding_status="open")
    done = []
    r = SimpleNamespace(a7_open={5: (trow, frow)}, pools={"ar_specialist": pool}, upd=lambda t, row, **c: (row.update(c), done.append((t, c))))
    engine.Replay.a7_answered(r, d1, 99)                          # a claim A7 never flagged: nothing happens
    assert not done and len(pool.items) == 2
    engine.Replay.a7_answered(r, d1, 5)
    assert trow["task_status"] == "done" and trow["outcome"] == "no_action_needed" and trow["completed_date"] == d1 > d0
    assert frow["finding_status"] == "resolved" and frow["resolution"] == "payer_answered"
    assert [it["key"] for it in pool.items] == [12]               # the answered claim is no longer in the backlog
    r.a7_open[5] = (dict(trow, task_status="done"), frow)         # already worked by staff: left alone
    n = len(done)
    engine.Replay.a7_answered(r, d1, 5)
    assert len(done) == n


def test_a7_only_runs_from_its_go_live_day_on_r2(monkeypatch):
    _, engine = _fresh(monkeypatch)
    assert engine.A7_FROM == dt.date(1900, 1, 1)
    _, engine = _fresh(monkeypatch, KRISNNAI_REPLAY_DB="krisnnai_r2", KRISNNAI_REPLAY_END="2026-11-06")
    assert engine.A7_FROM == dt.date(2026, 10, 7)


@pytest.fixture(scope="module")
def cur():
    os.environ["KRISNNAI_PG_DB"] = "krisnnai_r2"
    try:
        from core import connect
        conn, db = connect()
    except Exception as ex:          # no network / credentials: skip rather than fail
        pytest.skip(f"krisnnai_r2 not reachable: {type(ex).__name__}")
    assert db == "krisnnai_r2"
    conn.set_session(readonly=True)
    c = conn.cursor()
    yield c
    conn.close()


def test_schema_has_views_only(cur):
    cur.execute("SELECT c.relkind, count(*) FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'canon_compat' AND c.relkind NOT IN ('i','S','c','t') GROUP BY 1")
    assert dict(cur.fetchall()) == {"v": 29}


def test_every_view_filters_tenant_1(cur):
    cur.execute("SELECT viewname, definition FROM pg_views WHERE schemaname = 'canon_compat'")
    for name, definition in cur.fetchall():
        assert "tenant_id = 1" in definition, name


def test_no_cross_tenant_rows_visible(cur):
    cur.execute("SELECT table_name FROM information_schema.columns WHERE table_schema = 'canon_compat' AND column_name = 'tenant_id'")
    for (t,) in cur.fetchall():
        cur.execute(f'SELECT count(*) FROM canon_compat."{t}" WHERE tenant_id <> 1')
        assert cur.fetchone()[0] == 0, t


@pytest.mark.parametrize("view,source", [("claim", "claim"), ("claim_details", "claim_line"), ("appointment_details", "appointment_line"), ("encounter_details", "encounter_line"),
                                         ("denial", "denial"), ("payment", "payment"), ("claim_status_history", "claim_status_history"), ("appointment", "appointment")])
def test_row_counts_match_source(cur, view, source):
    cur.execute(f'SELECT (SELECT count(*) FROM canon_compat."{view}"), (SELECT count(*) FROM public."{source}" WHERE tenant_id = 1)')
    a, b = cur.fetchone()
    assert a == b > 0


def test_event_vocabulary_is_mapped(cur):
    cur.execute("SELECT DISTINCT event_type FROM canon_compat.claim_status_history")
    got = {r[0] for r in cur.fetchall()}
    assert {"accepted_277ca", "remit_835"} <= got and "acknowledged" not in got and "adjudicated" not in got


def test_one_recovery_payment_per_overturned_denial(cur):
    cur.execute("SELECT count(*), count(DISTINCT denial_id) FROM canon_compat.transactions")
    a, b = cur.fetchone()
    cur.execute("SELECT count(*) FROM public.denial WHERE tenant_id = 1 AND outcome = 'overturned'")
    assert a == b == cur.fetchone()[0]


def test_payer_turnaround_filled_except_self_pay(cur):
    cur.execute("SELECT payer_code, standard_turnaround_days FROM canon_compat.payer")
    got = dict(cur.fetchall())
    assert got.pop("SELF") is None
    assert all(v is not None and v > 0 for v in got.values()), got


def test_ar_exposes_every_snapshot_with_its_date(cur):
    cur.execute("SELECT count(DISTINCT as_of_date), min(as_of_date), max(snapshot_type) FROM canon_compat.ar")
    n, first, _ = cur.fetchone()
    assert n == 13 and first == dt.date(2025, 11, 30)
