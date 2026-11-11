"""Stage 7: the "in-flight layer" for krisnnai_r2: the work a practice has open on a normal day, relative to the R2 data date 2026-11-06.

R2 on 2026-11-06 is a clean, fully adjudicated history, so most agents find nothing. This stage adds what is in flight, without changing any money the finance pages read
(claim, claim_line paid/allowed/charge, ledger_entry, payment.posted_amount, remittance_claim, denial, ar_snapshot are never touched):

1. Upcoming appointments, next 14 days, business days only, status 'scheduled', with lines, slot and status log (patients, providers, payers, coverages and planned services are copied
   from each patient's latest real visit; volume follows the practice's own daily average, thinning out with distance). One eligibility check each, except ~12% with none and ~10% stale
   (>30 days); ~3% whose check shows the coverage ended before the visit and ~1.5% with another payer primary. Auth-required services (REQUIRED map of load_auth_eligibility.py)
   get a new authorization, except ~10% of them: no authorization, expiring within 14 days, fewer visits approved than scheduled (A2), or units nearly used up.
2. Notes: ~12% of the encounters of the last 21 days get an unsigned note (draft) or a late signature (encounter.note_status / note_signed_date / signature_lag_days).
   Visits without a bill (documented, not charged) are NOT created here: R2 already has them (about 5% of the last 14 days).
3. 277CA rejections on ~8% of the recent unanswered 'submitted' claims (claim_status_history, is_rejection = true). Claims that already carry an accepted-acknowledgement row have that
   row turned into the rejection (original values saved), so a claim never has both. Claim dates and amounts are not touched. A7 eligibility is only counted and reported.
4. Underpayments: ~2% of paid claim lines adjudicated in the last 60 days, plus two payer/CPT cells with a payer-wide shortfall (for A15), get a higher expected_allowed so that
   allowed_amount is 8-30% below it. Only claim_line.expected_allowed changes (original values saved).
5. A11: a few payer EFTs received in the last days but not posted (payment with posted_amount 0, unapplied_amount = payment_amount). payment.posted_amount sums are unchanged.
Not done: A4 (R2 has no 9716x evaluation codes, which is all A4 reads), A13 (enrollment stays empty by decision), bank_deposit untouched.

Every inserted row has source 'inflight_sim' (tenant_id 1). Every changed value is saved in schema backup_inflight; --reset restores them exactly and deletes the inserted rows.
A plain run first does the same clean-up, so a rerun gives the identical result. Randomness is md5 of ids, no clock.
Run this stage last: load_denials.py / load_auth_eligibility.py --reset would overwrite the saved columns' source tables.

    python tools/synthea/load_inflight.py            # clean + build + commit
    python tools/synthea/load_inflight.py --dry      # same, prints counts, rolls back
    python tools/synthea/load_inflight.py --reset    # restore changed values, delete inserted rows
"""
import datetime as dt
import hashlib
import math
import sys
from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal

from psycopg2.extras import execute_values

from load_auth_eligibility import REQUIRED
from r2load import Loader, connect

SRC = "inflight_sim"
TODAY = dt.date(2026, 11, 6)
BK = "backup_inflight"
D = Decimal
INSERTED = ["appointment_status_log", "appointment_slot", "appointment_line", "eligibility_check", "authorization_line", "authorization", "appointment", "claim_status_history", "payment"]
REJECTIONS = [  # (277CA category code, id in claim_status_code, reason text, category, technical, owner)
    ("A7", 8, "Member ID invalid", "member_id", True, "front_desk"),
    ("A6", 7, "Rendering NPI bad", "provider_id", True, "biller"),
    ("A7", 8, "Dx invalid for DOS", "diagnosis", True, "coder"),
    ("A3", 4, "Duplicate claim", "duplicate", False, "biller"),
    ("A8", 9, "Payer ID mismatch", "payer_id", True, "front_desk"),
    ("A6", 7, "Prior auth missing", "missing_information", False, "front_desk"),
    ("A6", 7, "Taxonomy mismatch", "provider_id", True, "biller"),
]


def U(*parts):
    """Repeatable pseudo-random number in [0, 1) from md5 of the parts."""
    return int(hashlib.md5("|".join(str(p) for p in parts).encode()).hexdigest()[:7], 16) / 268435456.0


def money(x):
    return D(x).quantize(D("0.01"), ROUND_HALF_UP)


def fill(k):
    """Share of a normal day's volume already booked k calendar days ahead."""
    return max(0.12, 0.85 * math.exp(-(k - 1) / 5))


def one(cur, sql, args=None):
    cur.execute(sql, args)
    return cur.fetchone()[0]


def rows(cur, sql, args=None):
    cur.execute(sql, args)
    names = [c[0] for c in cur.description]
    return [dict(zip(names, r)) for r in cur.fetchall()]


# ---------------------------------------------------------------- reset
def has_backup(cur):
    return one(cur, "select to_regclass(%s)", (f"{BK}.encounter_note",)) is not None


def clean(cur):
    """Restores every saved value, then deletes the rows this stage inserted. Returns what it did."""
    out = {}
    if has_backup(cur):
        cur.execute(f"""UPDATE encounter e SET note_status = b.note_status, note_signed_date = b.note_signed_date, signature_lag_days = b.signature_lag_days
                        FROM {BK}.encounter_note b WHERE e.encounter_id = b.encounter_id AND e.tenant_id = 1""")
        out["restored encounter"] = cur.rowcount
        cur.execute(f"UPDATE claim_line c SET expected_allowed = b.expected_allowed FROM {BK}.claim_line_expected b WHERE c.claim_line_id = b.claim_line_id AND c.tenant_id = 1")
        out["restored claim_line"] = cur.rowcount
        cur.execute(f"""UPDATE claim_status_history h SET status_after = b.status_after, is_rejection = b.is_rejection, rejection_reason = b.rejection_reason, rejection_category = b.rejection_category,
                        is_technical = b.is_technical, owner_role = b.owner_role, status_code = b.status_code, status_code_id = b.status_code_id,
                        status_category_code_id = b.status_category_code_id
                        FROM {BK}.csh_ack b WHERE h.claim_status_history_id = b.claim_status_history_id AND h.tenant_id = 1""")
        out["restored claim_status_history"] = cur.rowcount
        for t in ("encounter_note", "claim_line_expected", "csh_ack"):
            cur.execute(f"DELETE FROM {BK}.{t}")
    for t in INSERTED:
        cur.execute(f'DELETE FROM "{t}" WHERE tenant_id = 1 AND source = %s', (SRC,))
        out[f"deleted {t}"] = cur.rowcount
    return out


def make_backup_tables(cur):
    cur.execute(f"CREATE SCHEMA IF NOT EXISTS {BK}")
    cur.execute(f"CREATE TABLE IF NOT EXISTS {BK}.encounter_note (encounter_id bigint PRIMARY KEY, note_status varchar(20), note_signed_date date, signature_lag_days int)")
    cur.execute(f"CREATE TABLE IF NOT EXISTS {BK}.claim_line_expected (claim_line_id bigint PRIMARY KEY, expected_allowed numeric(12,2))")
    cur.execute(f"""CREATE TABLE IF NOT EXISTS {BK}.csh_ack (claim_status_history_id bigint PRIMARY KEY, status_after varchar(30), is_rejection boolean, rejection_reason text,
                    rejection_category varchar(30), is_technical boolean, owner_role varchar(30), status_code varchar(10), status_code_id bigint, status_category_code_id bigint)""")


# ---------------------------------------------------------------- 1. appointments, eligibility, authorizations
def business_days():
    return [TODAY + dt.timedelta(days=k) for k in range(1, 15) if (TODAY + dt.timedelta(days=k)).weekday() < 5]


def build_appointments(cur, ld, stats):
    cpt_code = dict(rows_t(cur, "select cpt_code_id, code from cpt_code where tenant_id = 1"))
    payers = rows(cur, "select payer_id, payer_code, payer_type from payer where tenant_id = 1 and payer_code <> 'SELF' order by payer_id")
    base = one(cur, """select round(count(*)::numeric / count(distinct appointment_date)) from appointment
                       where tenant_id = 1 and appointment_date between '2026-10-23' and '2026-11-05' and source <> %s""", (SRC,))
    days = business_days()
    base = int(base)
    stats["practice daily average appointments (10-23..11-05)"] = base

    tmpl_cols = """a.appointment_id, a.patient_id, a.provider_id, a.payer_id, a.coverage_id, a.facility_id, a.start_time, a.appointment_type, p.payer_code, p.payer_type,
                   cv.copay_amount, cv.coinsurance_pct, cv.deductible_remaining, cv.effective_date"""
    from_ = """FROM appointment a JOIN payer p ON p.payer_id = a.payer_id JOIN coverage cv ON cv.coverage_id = a.coverage_id
               WHERE a.tenant_id = 1 AND a.source <> %s AND a.appointment_status = 'completed' AND a.appointment_date BETWEEN '2026-08-08' AND '2026-11-06'
                 AND EXISTS (select 1 from appointment_line x where x.appointment_id = a.appointment_id) AND (cv.termination_date IS NULL OR cv.termination_date >= '2026-11-20') AND p.payer_code <> 'SELF'"""
    auth_pat = "select patient_id from appointment_line where tenant_id = 1 and auth_required = 'yes' and patient_id is not null"
    pool = rows(cur, f"""select distinct on (a.patient_id) {tmpl_cols} {from_} AND a.patient_id NOT IN ({auth_pat})
                         order by a.patient_id, a.appointment_date desc, a.appointment_id desc""", (SRC,))
    series = rows(cur, f"""select distinct on (a.patient_id) {tmpl_cols} {from_}
                           AND EXISTS (select 1 from appointment_line al where al.appointment_id = a.appointment_id and al.auth_required = 'yes')
                           order by a.patient_id, a.appointment_date desc, a.appointment_id desc""", (SRC,))
    visits = dict(rows_t(cur, """select a.patient_id, count(distinct a.appointment_id) from appointment a join appointment_line al on al.appointment_id = a.appointment_id
                                 where a.tenant_id = 1 and al.auth_required = 'yes' and a.appointment_date >= '2026-09-22' and a.source <> %s group by 1""", (SRC,)))

    plan = []   # one dict per appointment to create
    pool.sort(key=lambda t: U(t["patient_id"], "inflight-pick"))
    i = 0
    for d in days:
        n = round(base * fill((d - TODAY).days))
        for t in pool[i:i + n]:
            plan.append(dict(t=t, date=d, series=False))
        i += n
    for t in series:
        n = min(6, max(1, round(visits.get(t["patient_id"], 1) * 14 / 45)))
        ranked = sorted(days, key=lambda d: U(t["patient_id"], d, "series") / fill((d - TODAY).days))[:n]
        for d in sorted(ranked):
            plan.append(dict(t=t, date=d, series=True))
    plan.sort(key=lambda p: (p["date"], p["t"]["patient_id"]))

    tids = sorted({p["t"]["appointment_id"] for p in plan})
    lines = defaultdict(list)
    for r in rows(cur, """select appointment_id, line_number, planned_cpt_code_id, is_inferred, planned_units, expected_charge, expected_allowed, planned_diagnosis_code_id, planned_provider_id,
                                 specialty_id, duration_minutes, provider_id, payer_id from appointment_line where tenant_id = 1 and appointment_id = ANY(%s) order by appointment_id, line_number""", (tids,)):
        lines[r["appointment_id"]].append(r)
    slot = {r["appointment_id"]: r for r in rows(cur, "select appointment_id, duration_minutes, slot_type from appointment_slot where tenant_id = 1 and appointment_id = ANY(%s)", (tids,))}

    ids = {t: one(cur, f'select coalesce(max({t}_id), 0) from "{t}"') for t in ("appointment", "appointment_line", "appointment_slot", "appointment_status_log", "eligibility_check", "authorization", "authorization_line")}
    # authorizations are per series (patient) over the auth-required lines; ~10% of the auth-required services get a problem
    by_pat = defaultdict(list)
    for p in plan:
        if p["series"]:
            by_pat[p["t"]["patient_id"]].append(p)
    pats = sorted(by_pat, key=lambda x: U(x, "auth-problem"))
    k_problem = max(1, math.ceil(0.10 * len(pats)))
    flavors = ["short", "none", "expiring", "near"]
    flav = {}
    for j, pid in enumerate(pats[:k_problem]):
        f = flavors[j % 4]
        if f == "short" and len(by_pat[pid]) < 2:
            f = "near"
        flav[pid] = f
    if k_problem >= 1 and "short" not in flav.values():      # make sure the A2 case exists when some patient has 2+ visits
        for pid in pats:
            if len(by_pat[pid]) >= 2 and pid not in flav:
                flav[pid] = "short"
                break

    out = defaultdict(list)
    auth_of = {}
    n_auth_lines = n_problem_lines = 0
    for pid in sorted(by_pat):
        ps = by_pat[pid]
        t = ps[0]["t"]
        req_lines = [l for l in lines[t["appointment_id"]] if (t["payer_code"] in REQUIRED and cpt_code.get(l["planned_cpt_code_id"]) in REQUIRED[t["payer_code"]])]
        if not req_lines:
            continue
        m = len(ps)
        n_auth_lines += m * len(req_lines)
        f = flav.get(pid)
        if f:
            n_problem_lines += m * len(req_lines)
        if f == "none":
            continue
        ids["authorization"] += 1
        aid = ids["authorization"]
        auth_of[pid] = aid
        first = min(p["date"] for p in ps)
        vf = TODAY - dt.timedelta(days=7 + int(U(pid, "vf") * 14))
        vt = vf + dt.timedelta(days=90)
        approved, used = m + 10, int(U(pid, "used") * 4)
        if f == "expiring":
            vt = TODAY + dt.timedelta(days=1 + int(U(pid, "vt") * 13))
            vf = vt - dt.timedelta(days=60)
        elif f == "short":
            approved, used = max(1, m // 2), 0
        elif f == "near":
            used = 12
            approved = used + m
        prov = t["provider_id"]
        out["authorization"].append(dict(
            authorization_id=aid, authorization_number=f"AUTH-{t['payer_code']}-{aid:07d}", patient_id=pid, payer_id=t["payer_id"], practice_id=1, authorization_status="approved",
            coverage_id=t["coverage_id"], primary_cpt_code_id=req_lines[0]["planned_cpt_code_id"], units_requested=approved, units_approved=approved, units_used=used, valid_from=vf, valid_to=vt,
            request_date=vf - dt.timedelta(days=3), decision_date=vf - dt.timedelta(days=2), authorization_type="prior_auth", requesting_provider_id=prov, rendering_provider_id=prov,
            urgency="routine", request_channel="portal" if U(pid, "ch") < .6 else "fax", diagnosis_code_id=req_lines[0]["planned_diagnosis_code_id"], facility_id=t["facility_id"], source=SRC))
        out["authorization_line"].append(dict(
            authorization_line_id=aid, authorization_id=aid, line_number=1, cpt_code_id=req_lines[0]["planned_cpt_code_id"], unit_type="units", units_requested=approved, units_approved=approved,
            units_used=used, line_status="approved", valid_from=vf, valid_to=vt, practice_id=1, patient_id=pid, payer_id=t["payer_id"], source=SRC))
    stats["auth-required appointment services"] = n_auth_lines
    stats["auth-required services with a problem"] = n_problem_lines
    stats["auth problem flavors by patient"] = {f: list(flav.values()).count(f) for f in sorted(set(flav.values()))}

    for p in plan:
        t, d = p["t"], p["date"]
        ids["appointment"] += 1
        aid = ids["appointment"]
        p["id"] = aid
        booked = TODAY - dt.timedelta(days=int(U(aid, "book") * min(10, 3 + (d - TODAY).days)))
        bts = dt.datetime.combine(booked, dt.time(8 + int(U(aid, "bh") * 9), int(U(aid, "bm") * 60)))
        out["appointment"].append(dict(
            appointment_id=aid, appointment_number=f"APT-{aid}", practice_id=1, patient_id=t["patient_id"], appointment_date=d, appointment_status="scheduled", provider_id=t["provider_id"],
            payer_id=t["payer_id"], coverage_id=t["coverage_id"], facility_id=t["facility_id"], start_time=t["start_time"], booked_date=booked, appointment_type=t["appointment_type"],
            created_at=bts, source=SRC))
        sl = slot.get(t["appointment_id"], {})
        out["appointment_slot"].append(dict(
            appointment_slot_id=aid, practice_id=1, provider_id=t["provider_id"], slot_date=d, start_time=t["start_time"], duration_minutes=sl.get("duration_minutes") or 20, slot_status="booked",
            slot_number=f"SL-{aid}", facility_id=t["facility_id"], slot_type=t["appointment_type"], appointment_id=aid, created_date=booked, is_overbook=False, created_at=bts, source=SRC))
        ids["appointment_status_log"] += 1
        out["appointment_status_log"].append(dict(appointment_status_log_id=ids["appointment_status_log"], appointment_id=aid, from_status=None, to_status="scheduled", status_changed_at=bts,
                                                  change_channel="scheduler", source=SRC))
        is_req = lambda l: t["payer_code"] in REQUIRED and cpt_code.get(l["planned_cpt_code_id"]) in REQUIRED[t["payer_code"]]
        # the authorized service is the first line: the engine (and R2's own links) only look at line 1 of an appointment
        for no, l in enumerate(sorted(lines[t["appointment_id"]], key=lambda l: (0 if is_req(l) else 1, l["line_number"])), 1):
            ids["appointment_line"] += 1
            req = is_req(l)
            out["appointment_line"].append(dict(
                appointment_line_id=ids["appointment_line"], appointment_id=aid, line_number=no, practice_id=1, patient_id=t["patient_id"], payer_id=t["payer_id"], provider_id=l["provider_id"],
                specialty_id=l["specialty_id"], planned_cpt_code_id=l["planned_cpt_code_id"], is_inferred=l["is_inferred"], planned_units=l["planned_units"], expected_charge=l["expected_charge"],
                expected_allowed=l["expected_allowed"], auth_required="yes" if req else "no", authorization_id=auth_of.get(t["patient_id"]) if req else None,
                planned_diagnosis_code_id=l["planned_diagnosis_code_id"], planned_provider_id=l["planned_provider_id"], duration_minutes=l["duration_minutes"], created_at=bts, source=SRC))
    stats["appointments"] = len(plan)
    stats["appointments by date"] = {str(d): sum(1 for p in plan if p["date"] == d) for d in days}

    # eligibility: ~12% none, ~10% stale, ~3% coverage ended, ~1.5% other payer primary
    other_ids = [x["payer_id"] for x in payers]
    n = dict(none=0, stale=0, fresh=0, ended=0, other_primary=0)
    for p in plan:
        t, d, aid = p["t"], p["date"], p["id"]
        r = U(aid, "elig")
        ended = U(aid, "end") < 0.025
        other = (not ended) and U(aid, "oth") < 0.015
        if r < 0.12 and not (ended or other):
            n["none"] += 1
            continue
        stale = (not (ended or other)) and r < 0.22
        check = TODAY - dt.timedelta(days=(31 + int(U(aid, "sd") * 60)) if stale else int(U(aid, "cd") * 14))
        ptype = t["payer_type"]
        ded_total = D(1500) if ptype == "commercial" else D(240) if ptype == "medicare" else D(0)
        ids["eligibility_check"] += 1
        eid = ids["eligibility_check"]
        n["stale" if stale else "fresh"] += 1
        op = None
        if other:
            n["other_primary"] += 1
            op = other_ids[int(U(aid, "opi") * len(other_ids))]
            if op == t["payer_id"]:
                op = other_ids[(other_ids.index(op) + 1) % len(other_ids)]
        if ended:
            n["ended"] += 1
        out["eligibility_check"].append(dict(
            eligibility_check_id=eid, trace_number=f"ELG{eid:09d}", check_sequence=1, appointment_id=aid, coverage_id=t["coverage_id"], patient_id=t["patient_id"], payer_id=t["payer_id"], practice_id=1,
            is_secondary=False, check_date=check, check_ts=dt.datetime.combine(check, dt.time(8, 30)), service_date=d, service_type_code="30", is_aaa_reject=False,
            plan_begin_date=t["effective_date"], plan_end_date=(TODAY - dt.timedelta(days=1 + int(U(aid, "pe") * 25))) if ended else None,
            copay_amount=t["copay_amount"] if t["copay_amount"] is not None else (D(25) if ptype == "commercial" else D(0)),
            coinsurance_pct=t["coinsurance_pct"] if t["coinsurance_pct"] is not None else (D(0) if ptype == "medicaid" else D("0.20")), coverage_level="individual", network_indicator="Y",
            deductible_remaining=t["deductible_remaining"] if t["deductible_remaining"] is not None else money(ded_total * D(str(round(U(aid, "dr"), 4)))), deductible_total=ded_total,
            oop_max=D(6000) if ptype == "commercial" else None, other_payer_id=op,
            auth_required_hint=any(t["payer_code"] in REQUIRED and cpt_code.get(l["planned_cpt_code_id"]) in REQUIRED[t["payer_code"]] for l in lines[t["appointment_id"]]), source=SRC))
    stats["eligibility"] = n
    for tb in ("appointment", "appointment_slot", "appointment_status_log", "appointment_line", "authorization", "authorization_line", "eligibility_check"):
        ld.rows(tb, out[tb])
    return {tb: len(out[tb]) for tb in out}


def rows_t(cur, sql, args=None):
    cur.execute(sql, args)
    return cur.fetchall()


# ---------------------------------------------------------------- 2. notes
def build_notes(cur, stats):
    enc = rows(cur, """select e.encounter_id, e.encounter_date, e.note_status, e.note_signed_date, e.signature_lag_days, (b.bill_id is not null) has_bill
                       from encounter e left join bill b on b.encounter_id = e.encounter_id and b.tenant_id = 1
                       where e.tenant_id = 1 and e.encounter_date between '2026-10-16' and '2026-11-06' order by e.encounter_id""")
    upd, bak = [], []
    n = dict(unsigned=0, late_signed=0, with_bill=0)
    for e in enc:
        if U(e["encounter_id"], "note") >= 0.12:
            continue
        d = e["encounter_date"]
        review = d + dt.timedelta(days=3)
        while review.weekday() >= 5:
            review += dt.timedelta(days=1)
        signed = review + dt.timedelta(days=1 + int(U(e["encounter_id"], "late") * 5))      # after the A3 review day
        if U(e["encounter_id"], "kind") < 0.45 and signed <= TODAY:
            upd.append((e["encounter_id"], "signed", signed, (signed - d).days))
            n["late_signed"] += 1
        else:
            upd.append((e["encounter_id"], "draft", None, None))
            n["unsigned"] += 1
        n["with_bill"] += 1 if e["has_bill"] else 0
        bak.append((e["encounter_id"], e["note_status"], e["note_signed_date"], e["signature_lag_days"]))
    execute_values(cur, f"INSERT INTO {BK}.encounter_note VALUES %s", bak)
    execute_values(cur, """UPDATE encounter e SET note_status = v.ns, note_signed_date = v.sd::date, signature_lag_days = v.lag::int
                           FROM (VALUES %s) v(id, ns, sd, lag) WHERE e.encounter_id = v.id AND e.tenant_id = 1""", upd)
    stats["encounters last 21 days"] = len(enc)
    stats["notes"] = n
    stats["encounters of the last 14 days without a bill (already in R2)"] = one(cur, """select count(*) from encounter e where e.tenant_id = 1 and e.encounter_date between '2026-10-23' and '2026-11-06'
                                                                              and not exists (select 1 from bill b where b.encounter_id = e.encounter_id)""")
    stats["encounters of the last 14 days"] = one(cur, "select count(*) from encounter where tenant_id = 1 and encounter_date between '2026-10-23' and '2026-11-06'")
    return len(upd)


# ---------------------------------------------------------------- 3. claim rejections, A7 check
def build_rejections(cur, ld, stats):
    pool = rows(cur, """select c.claim_id, c.submitted_date, c.payer_id, c.patient_id, s.billing_provider_id, s.specialty_id, s.payer_claim_number,
                               a.claim_status_history_id ack_id
                        from claim c
                        join claim_status_history s on s.claim_id = c.claim_id and s.event_type = 'submitted' and s.tenant_id = 1
                        left join claim_status_history a on a.claim_id = c.claim_id and a.event_type = 'acknowledged' and a.tenant_id = 1
                        where c.tenant_id = 1 and c.claim_status = 'submitted' and c.submitted_date >= '2026-11-02'
                          and not exists (select 1 from claim_status_history h where h.claim_id = c.claim_id and h.event_type in ('pending', 'adjudicated', 'reprocessed'))
                        order by c.claim_id""")
    base_id = one(cur, "select coalesce(max(claim_status_history_id), 0) from claim_status_history")
    new, upd, bak = [], [], []
    for c in pool:
        if U(c["claim_id"], "rej") >= 0.08:
            continue
        code, code_id, reason, cat, tech, owner = REJECTIONS[int(U(c["claim_id"], "why") * len(REJECTIONS))]
        ev = min(TODAY, c["submitted_date"] + dt.timedelta(days=1 + int(U(c["claim_id"], "lag") * 2)))
        if c["ack_id"]:
            upd.append((c["ack_id"], reason, cat, tech, owner, code, code_id))
        else:
            ev = TODAY if c["submitted_date"] >= TODAY else ev
            base_id += 1
            new.append(dict(
                claim_status_history_id=base_id, claim_id=c["claim_id"], event_type="acknowledged", event_date=ev, status_after="rejected", practice_id=1, payer_id=c["payer_id"],
                patient_id=c["patient_id"], event_ts=dt.datetime.combine(ev, dt.time(15, 0)), response_sequence=2, status_category="A", status_category_code_id=code_id, status_code=code,
                status_code_id=code_id, is_rejection=True, rejection_reason=reason, rejection_category=cat, is_technical=tech, owner_role=owner, channel="clearinghouse",
                payer_claim_number=c["payer_claim_number"], billing_provider_id=c["billing_provider_id"], specialty_id=c["specialty_id"], source=SRC))
    if upd:
        ids = [u[0] for u in upd]
        cur.execute(f"""INSERT INTO {BK}.csh_ack SELECT claim_status_history_id, status_after, is_rejection, rejection_reason, rejection_category, is_technical, owner_role, status_code,
                        status_code_id, status_category_code_id FROM claim_status_history WHERE tenant_id = 1 AND claim_status_history_id = ANY(%s)""", (ids,))
        execute_values(cur, """UPDATE claim_status_history h SET status_after = 'rejected', is_rejection = true, rejection_reason = v.reason, rejection_category = v.cat, is_technical = v.tech::boolean,
                               owner_role = v.owner, status_code = v.code, status_code_id = v.cid::bigint, status_category_code_id = v.cid::bigint
                               FROM (VALUES %s) v(id, reason, cat, tech, owner, code, cid) WHERE h.claim_status_history_id = v.id::bigint AND h.tenant_id = 1""", upd)
        # event_date of an updated ack stays as it was (submitted + 1 day or so), which is on or before the data date
    ld.rows("claim_status_history", new)
    total_sub = one(cur, "select count(*) from claim where tenant_id = 1 and claim_status = 'submitted'")
    stats["submitted claims"] = total_sub
    stats["rejection pool (submitted 11-02..11-06, no pending/adjudicated event)"] = len(pool)
    stats["rejections"] = dict(total=len(new) + len(upd), converted_from_accepted_ack=len(upd), new_rows=len(new), pct_of_all_submitted=round(100.0 * (len(new) + len(upd)) / total_sub, 2),
                               pct_of_pool=round(100.0 * (len(new) + len(upd)) / max(1, len(pool)), 1))
    # A7: submitted claims with no remit, by payer, that have reached submitted + turnaround + grace
    q = rows(cur, """select p.payer_code, p.standard_turnaround_days t, c.submitted_date from claim c join payer p on p.payer_id = c.payer_id
                     where c.tenant_id = 1 and c.claim_status = 'submitted' and p.standard_turnaround_days is not null""")
    a7 = {}
    for grace in (14, 7, 0):
        a7[f"grace {grace}"] = sum(1 for r in q if r["submitted_date"] + dt.timedelta(days=r["t"] + grace) <= TODAY)
    stats["A7 qualifying submitted claims (turnaround + grace <= 2026-11-06)"] = a7
    stats["A7 oldest submitted claim date"] = str(min(r["submitted_date"] for r in q))
    return len(new) + len(upd)


# ---------------------------------------------------------------- 4. underpayments
def build_underpayments(cur, stats):
    pool = rows(cur, """select cl.claim_line_id, cl.allowed_amount, cl.expected_allowed, c.payer_id, cl.cpt_code_id
                        from claim_line cl join claim c on c.claim_id = cl.claim_id and c.tenant_id = 1
                        join claim_status_history h on h.claim_id = c.claim_id and h.event_type = 'adjudicated' and h.tenant_id = 1
                        where cl.tenant_id = 1 and cl.line_status = 'paid' and h.event_date between '2026-09-07' and '2026-11-06' and cl.allowed_amount > 0 and cl.expected_allowed > 0
                          and cl.modifier_1_id is distinct from (select modifier_id from modifier where modifier_code = 'CQ' and tenant_id = 1)
                          and cl.modifier_2_id is distinct from (select modifier_id from modifier where modifier_code = 'CQ' and tenant_id = 1)
                        order by cl.claim_line_id""")
    cells = defaultdict(list)
    for r in pool:
        cells[(r["payer_id"], r["cpt_code_id"])].append(r)
    big = sorted((k for k, v in cells.items() if 40 <= len(v) <= 150), key=lambda k: (-len(cells[k]), k))
    cell_pick = []
    seen_payers = set()
    for k in big:                           # two big cells on two different payers
        if k[0] not in seen_payers:
            cell_pick.append(k)
            seen_payers.add(k[0])
        if len(cell_pick) == 2:
            break
    targeted = {r["claim_line_id"] for k in cell_pick for r in cells[k] if U(r["claim_line_id"], "cell") < 0.35}
    upd, bak = [], []
    for r in pool:
        lid = r["claim_line_id"]
        if lid not in targeted and U(lid, "under") >= 0.02:
            continue
        pct = D(str(round(0.08 + 0.22 * U(lid, "pct"), 4)))
        new = money(r["allowed_amount"] / (D(1) - pct))
        upd.append((lid, new))
        bak.append((lid, r["expected_allowed"]))
    execute_values(cur, f"INSERT INTO {BK}.claim_line_expected VALUES %s", bak)
    execute_values(cur, "UPDATE claim_line c SET expected_allowed = v.e::numeric FROM (VALUES %s) v(id, e) WHERE c.claim_line_id = v.id AND c.tenant_id = 1", upd)
    stats["paid lines adjudicated in last 60 days"] = len(pool)
    stats["underpaid lines"] = dict(total=len(upd), pct=round(100.0 * len(upd) / len(pool), 2), in_targeted_cells=len(targeted & {u[0] for u in upd}))
    stats["targeted payer/CPT cells (payer_id, cpt_code_id, lines)"] = [(k[0], k[1], len(cells[k])) for k in cell_pick]
    return len(upd)


# ---------------------------------------------------------------- 5. A11
def build_unposted(cur, ld, stats):
    payers = rows(cur, "select payer_id, payer_code from payer where tenant_id = 1 and payer_type <> 'self_pay' and payer_code <> 'SELF' order by payer_id")
    recent = one(cur, "select count(*) from payment where tenant_id = 1 and payment_source = 'payer' and payment_date between '2026-10-23' and '2026-11-06' and source <> %s", (SRC,))
    n = max(2, round(recent * 0.02))
    base = one(cur, "select coalesce(max(payment_id), 0) from payment")
    out = []
    for i in range(n):
        p = payers[int(U(i, "up") * len(payers))]
        d = TODAY - dt.timedelta(days=1 + int(U(i, "ud") * 5))
        amt = money(400 + 2600 * U(i, "ua"))
        out.append(dict(payment_id=base + i + 1, payment_number=f"EFT-{p['payer_code']}-{d:%Y%m%d}-HOLD{i + 1}", practice_id=1, payment_source="payer", payment_date=d, payment_amount=amt,
                        payment_method="eft", payer_id=p["payer_id"], payment_type="eft", received_date=d, credit_debit="C", has_remittance=False, claim_count=0, posted_amount=D(0),
                        unapplied_amount=amt, plb_amount=D(0), reconciles=False, is_void=False, source=SRC))
    ld.rows("payment", out)
    stats["unposted payer EFTs"] = dict(total=n, recent_payer_payments_14d=recent, unapplied_total=str(sum(o["unapplied_amount"] for o in out)))
    return n


# ---------------------------------------------------------------- main
def main():
    reset, dry = "--reset" in sys.argv, "--dry" in sys.argv
    conn = connect()
    cur = conn.cursor()
    try:
        cleaned = clean(cur)
        print("clean:", {k: v for k, v in cleaned.items() if v})
        if reset:
            conn.commit()
            return
        make_backup_tables(cur)
        ld = Loader(conn)
        stats, n = {}, {}
        n.update(build_appointments(cur, ld, stats))
        n["encounter notes changed"] = build_notes(cur, stats)
        n["claim_status_history rejections"] = build_rejections(cur, ld, stats)
        n["claim_line expected_allowed raised"] = build_underpayments(cur, stats)
        n["payment (unposted EFT)"] = build_unposted(cur, ld, stats)
        for k, v in n.items():
            print(f"{k:38s}{v:>8,}")
        for k, v in stats.items():
            print(f"  {k}: {v}")
        if dry:
            conn.rollback()
            print("dry run: rolled back")
        else:
            conn.commit()
            print("committed")
    except Exception:
        conn.rollback()
        raise


if __name__ == "__main__":
    main()
