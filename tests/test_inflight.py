"""Tests for tools/synthea/load_inflight.py (the in-flight layer of krisnnai_r2). DB-backed (synthetic data); skipped if krisnnai_r2 is unreachable.

The module fixture runs the loader as a script (--reset, then a build, then a second build, then --reset again), takes hash snapshots of everything the loader may touch and
leaves the database in the built state at the end.
"""

from __future__ import annotations

import datetime as dt
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "synthea" / "load_inflight.py"
sys.path.insert(0, str(ROOT / "tools" / "synthea"))
TODAY = dt.date(2026, 11, 6)
SRC = "inflight_sim"

# what the loader may change, hashed in full; and what it must never change
CHANGED = {
    "encounter_note": "select md5(string_agg(concat_ws('|', encounter_id, note_status, note_signed_date, signature_lag_days), ',' order by encounter_id)) from encounter",
    "claim_line_expected": "select md5(string_agg(concat_ws('|', claim_line_id, expected_allowed), ',' order by claim_line_id)) from claim_line",
    "claim_status_history_old_rows": "select md5(string_agg(concat_ws('|', claim_status_history_id, event_type, event_date, status_after, is_rejection, rejection_reason, rejection_category, is_technical, owner_role, status_code, status_code_id, status_category_code_id), ',' order by claim_status_history_id)) from claim_status_history where source <> 'inflight_sim'",
}
MONEY = {
    "claim_line money": "select md5(string_agg(concat_ws('|', claim_line_id, charge_amount, allowed_amount, paid_amount, denied_amount, patient_responsibility, line_status), ',' order by claim_line_id)) from claim_line",
    "claim": "select md5(string_agg(concat_ws('|', claim_id, claim_status, submitted_date, total_charge), ',' order by claim_id)) from claim",
    "ledger_entry": "select md5(string_agg(concat_ws('|', ledger_entry_id, amount, transaction_date), ',' order by ledger_entry_id)) from ledger_entry",
    "payment posted": "select coalesce(sum(posted_amount), 0)::text || '/' || count(*) filter (where source <> 'inflight_sim') from payment",
    "remittance_claim": "select md5(string_agg(concat_ws('|', remittance_claim_id, paid_amount), ',' order by remittance_claim_id)) from remittance_claim",
    "denial": "select md5(string_agg(concat_ws('|', denial_id, denied_amount, denial_date), ',' order by denial_id)) from denial",
    "ar_snapshot": "select md5(string_agg(concat_ws('|', ar_snapshot_id, balance), ',' order by ar_snapshot_id)) from ar_snapshot",
    "bank_deposit": "select count(*)::text from bank_deposit",
    "enrollment": "select count(*)::text from enrollment",
    "agent tables": "select (select count(*) from agent_run) || '/' || (select count(*) from agent_decision) || '/' || (select count(*) from agent_finding) || '/' || (select count(*) from agent_task)",
    "appointments not ours": "select count(*)::text from appointment where source <> 'inflight_sim'",
}
INSERTED = ["appointment", "appointment_line", "appointment_slot", "appointment_status_log", "eligibility_check", "authorization", "authorization_line", "claim_status_history", "payment"]


def run(*args):
    r = subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, cwd=str(ROOT / "tools" / "synthea"))
    assert r.returncode == 0, r.stderr[-800:]
    return r.stdout


def snap(cur):
    out = {}
    for k, q in {**CHANGED, **MONEY}.items():
        cur.execute(q)
        out[k] = cur.fetchone()[0]
    for t in INSERTED:
        cur.execute(f'select count(*) from "{t}" where source = %s', (SRC,))
        out[f"rows {t}"] = cur.fetchone()[0]
    return out


@pytest.fixture(scope="module")
def db():
    try:
        from r2load import connect
        c = connect()
    except Exception as exc:  # no network / no config on this machine
        pytest.skip(f"krisnnai_r2 not reachable: {type(exc).__name__}")
    c.rollback()
    c.autocommit = True
    cur = c.cursor()
    s = {}
    run("--reset")
    s["clean"] = snap(cur)
    out1 = run()
    s["built1"] = snap(cur)
    out2 = run()
    s["built2"] = snap(cur)
    s["stdout"] = out2
    s["same_report"] = [l for l in out1.splitlines() if not l.startswith("clean")] == [l for l in out2.splitlines() if not l.startswith("clean")]
    run("--reset")
    s["reset"] = snap(cur)
    run()                                   # leave the database built
    s["final"] = snap(cur)
    yield cur, s
    c.close()


def q1(cur, sql, args=None):
    cur.execute(sql, args)
    return cur.fetchone()[0]


def test_rerun_is_identical(db):
    cur, s = db
    assert s["built1"] == s["built2"] == s["final"]
    assert s["same_report"]
    assert s["built1"]["rows appointment"] > 100


def test_reset_restores_exact_values(db):
    cur, s = db
    assert s["reset"] == s["clean"]
    assert all(s["reset"][f"rows {t}"] == 0 for t in INSERTED)
    # and the build really changed what it says it changes
    for k in CHANGED:
        assert s["built1"][k] != s["clean"][k], k


def test_money_and_forbidden_tables_untouched(db):
    cur, s = db
    for k in MONEY:
        assert s["built1"][k] == s["clean"][k], k


def test_agent_tables_enrollment_bank_deposit_untouched(db):
    cur, s = db
    assert s["built1"]["agent tables"] == s["clean"]["agent tables"]
    assert q1(cur, "select count(*) from enrollment") == 0
    assert s["built1"]["bank_deposit"] == s["clean"]["bank_deposit"]


def test_every_inserted_row_is_tenant_1_and_tagged(db):
    cur, s = db
    for t in INSERTED:
        assert q1(cur, f'select count(*) from "{t}" where source = %s and tenant_id <> 1', (SRC,)) == 0, t
    text = SCRIPT.read_text(encoding="utf-8")
    assert "tenant_id = 1 AND source = %s" in text            # --reset deletes only tenant 1 rows with our tag


def test_upcoming_appointments(db):
    cur, s = db
    n, lo, hi, we, notsched = None, None, None, None, None
    cur.execute("""select count(*), min(appointment_date), max(appointment_date), count(*) filter (where extract(dow from appointment_date) in (0, 6)),
                          count(*) filter (where appointment_status <> 'scheduled'), count(*) filter (where booked_date > %s) from appointment where source = %s""", (TODAY, SRC))
    n, lo, hi, we, notsched, future_booked = cur.fetchone()
    assert n > 100 and lo > TODAY and hi <= TODAY + dt.timedelta(days=14)
    assert we == 0 and notsched == 0 and future_booked == 0
    # lines, slots and status log as R2 does it
    assert q1(cur, "select count(*) from appointment a where source = %s and not exists (select 1 from appointment_slot s where s.appointment_id = a.appointment_id)", (SRC,)) == 0
    assert q1(cur, "select count(*) from appointment a where source = %s and not exists (select 1 from appointment_status_log s where s.appointment_id = a.appointment_id and s.to_status = 'scheduled')", (SRC,)) == 0
    assert q1(cur, "select count(*) from appointment a where source = %s and not exists (select 1 from appointment_line l where l.appointment_id = a.appointment_id)", (SRC,)) == 0
    # existing patients, providers and coverages
    assert q1(cur, "select count(*) from appointment a where source = %s and not exists (select 1 from appointment o where o.patient_id = a.patient_id and o.provider_id = a.provider_id and o.coverage_id = a.coverage_id and o.source <> %s)", (SRC, SRC)) == 0


def test_eligibility_mix(db):
    cur, s = db
    n = q1(cur, "select count(*) from appointment where source = %s", (SRC,))
    none = q1(cur, "select count(*) from appointment a where source = %s and not exists (select 1 from eligibility_check e where e.appointment_id = a.appointment_id)", (SRC,))
    stale = q1(cur, "select count(*) from eligibility_check where source = %s and check_date < %s - 30", (SRC, TODAY))
    ended = q1(cur, "select count(*) from eligibility_check where source = %s and plan_end_date < service_date", (SRC,))
    other = q1(cur, "select count(*) from eligibility_check where source = %s and other_payer_id is not null", (SRC,))
    assert 0.08 <= none / n <= 0.17
    assert 0.06 <= stale / n <= 0.16
    assert 0.02 <= (ended + other) / n <= 0.08
    assert q1(cur, "select count(*) from eligibility_check where source = %s and check_date > %s", (SRC, TODAY)) == 0
    assert q1(cur, "select count(*) from eligibility_check where source = %s and plan_end_date >= service_date", (SRC,)) == 0


def test_authorizations_and_a2_condition(db):
    cur, s = db
    from load_auth_eligibility import REQUIRED
    pairs = [(p, c) for p, cs in REQUIRED.items() for c in cs]
    cur.execute("""select count(*) from appointment_line l join appointment a on a.appointment_id = l.appointment_id join payer p on p.payer_id = a.payer_id join cpt_code k on k.cpt_code_id = l.planned_cpt_code_id
                   where l.source = %s and (p.payer_code, k.code) in %s""", (SRC, tuple(pairs)))
    required = cur.fetchone()[0]
    assert required > 20
    assert q1(cur, "select count(*) from appointment_line where source = %s and auth_required = 'yes'", (SRC,)) == required
    unlinked = q1(cur, "select count(*) from appointment_line where source = %s and auth_required = 'yes' and authorization_id is null", (SRC,))
    assert unlinked >= 1
    # ~10% of the auth-required services have a problem: none, expiring within 14 days, too few visits, or nearly no units left
    prob = q1(cur, """select count(*) from appointment_line l join appointment a on a.appointment_id = l.appointment_id left join "authorization" au on au.authorization_id = l.authorization_id
                      where l.source = %s and l.auth_required = 'yes' and (l.authorization_id is null or au.valid_to <= %s + 14 or au.units_approved - au.units_used <= (select count(*) from appointment_line l2 where l2.authorization_id = au.authorization_id)
                            or au.units_approved < (select count(*) from appointment_line l3 where l3.authorization_id = au.authorization_id and l3.line_number = 1))""", (SRC, TODAY))
    assert 0.05 <= prob / required <= 0.20, (prob, required)
    # A2 reads line 1 of each appointment and flags the n-th scheduled/completed visit when n > units_approved
    a2 = q1(cur, """select count(*) from (select row_number() over (partition by l.authorization_id order by a.appointment_date, a.appointment_id) n, au.units_approved
                    from appointment_line l join appointment a on a.appointment_id = l.appointment_id join "authorization" au on au.authorization_id = l.authorization_id
                    where l.line_number = 1 and a.appointment_status in ('completed', 'scheduled') and au.source = %s) x where n > units_approved""", (SRC,))
    assert a2 >= 1
    assert q1(cur, "select count(*) from \"authorization\" where source = %s and (valid_to > %s + 365 or request_date > %s)", (SRC, TODAY, TODAY)) == 0


def test_notes(db):
    cur, s = db
    total = q1(cur, "select count(*) from encounter where encounter_date between %s and %s", (TODAY - dt.timedelta(days=20), TODAY))
    draft = q1(cur, "select count(*) from encounter where encounter_date between %s and %s and note_status = 'draft' and note_signed_date is null", (TODAY - dt.timedelta(days=20), TODAY))
    late = q1(cur, "select count(*) from encounter where encounter_date between %s and %s and note_status = 'signed' and signature_lag_days > 3", (TODAY - dt.timedelta(days=20), TODAY))
    assert 0.08 <= (draft + late) / total <= 0.16 and draft > 20 and late > 20
    assert q1(cur, "select count(*) from encounter where note_signed_date > %s", (TODAY,)) == 0
    # R2 already has documented-but-unbilled recent visits; the loader does not add any
    unbilled = q1(cur, "select count(*) from encounter e where encounter_date between %s and %s and not exists (select 1 from bill b where b.encounter_id = e.encounter_id)", (TODAY - dt.timedelta(days=14), TODAY))
    assert unbilled > 0


def test_rejections(db):
    cur, s = db
    n = q1(cur, "select count(*) from claim_status_history where is_rejection")
    assert n >= 20
    assert q1(cur, "select count(*) from claim_status_history where is_rejection and (rejection_reason is null or event_date > %s)", (TODAY,)) == 0
    assert q1(cur, """select count(*) from claim_status_history h where is_rejection and exists (select 1 from claim_status_history x where x.claim_id = h.claim_id and x.event_type = 'acknowledged' and not x.is_rejection)""") == 0
    assert q1(cur, "select count(*) from claim_status_history h join claim c on c.claim_id = h.claim_id where h.is_rejection and c.claim_status <> 'submitted'") == 0
    assert q1(cur, "select count(distinct rejection_reason) from claim_status_history where is_rejection") >= 4


def test_underpayments(db):
    cur, s = db
    cur.execute("""select count(*), min(1 - allowed_amount / expected_allowed), max(1 - allowed_amount / expected_allowed) from claim_line cl
                   where exists (select 1 from backup_inflight.claim_line_expected b where b.claim_line_id = cl.claim_line_id)""")
    n, lo, hi = cur.fetchone()
    assert n > 50 and float(lo) >= 0.0799 and float(hi) <= 0.3001
    assert q1(cur, "select count(*) from backup_inflight.claim_line_expected b join claim_line cl on cl.claim_line_id = b.claim_line_id where cl.expected_allowed <= b.expected_allowed") == 0


def test_unposted_payments(db):
    cur, s = db
    cur.execute("select count(*), min(unapplied_amount), max(posted_amount), max(payment_date) from payment where source = %s", (SRC,))
    n, mn, mp, md = cur.fetchone()
    assert n >= 2 and mn > 0 and mp == 0 and md <= TODAY


def test_nothing_dated_after_data_date(db):
    cur, s = db
    checks = {
        "appointment_status_log": "status_changed_at::date", "claim_status_history": "event_date", "payment": "payment_date", "authorization": "greatest(request_date, decision_date)",
        "appointment_slot": "created_date", "eligibility_check": "check_date",
    }
    for t, col in checks.items():
        assert q1(cur, f'select count(*) from "{t}" where source = %s and {col} > %s', (SRC, TODAY)) == 0, t
    assert q1(cur, "select count(*) from appointment where source = %s and (booked_date > %s or created_at::date > %s)", (SRC, TODAY, TODAY)) == 0


def test_a4_and_a13_skipped(db):
    cur, s = db
    assert q1(cur, "select count(*) from encounter_line where documented_level is not null") == 0
    assert q1(cur, "select count(*) from enrollment") == 0
