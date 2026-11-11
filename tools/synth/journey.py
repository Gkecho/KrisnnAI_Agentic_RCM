"""Stage 2: patients, coverage, then the journey appointment -> encounter -> bill -> claim -> money -> denial -> AR.

Planted stories (each has a known answer so the agents can be scored against it):
  S1 UHC: episodes past visit 12 without a plan of care on file are denied CARC 50 (+N115)
  S2 BCBS: from 2026-08-01 the payer allows less than the contract on 97140
  S3 Dr. Lee: slow charge entry and notes still unsigned (bills held)
  S4 Aetna: authorization of 12 units runs out mid-episode (CARC 198)
  S5 Remits paid by the payer but never posted to the ledger (unapplied cash)
  S6 Coverage ended: patients still booked or seen after the policy terminated (CARC 27)
  S7 Aetna: 97530 billed with 97140 and no distinct-service modifier from 2026-09-01 (CARC 97)
  S8 Claims with no payer response (stalled; timely-filing risk)
  S9 Coding level: evaluations billed lower (Dr. Okafor) or higher (Dr. Chen) than documented
  Also: other-payer-primary (CARC 22), rejected-at-clearinghouse billing NPI mismatch, duplicates, missing attachments.
"""
import datetime as dt
from decimal import Decimal
from collections import defaultdict

from core import TODAY, h
from ref import PAYERS, holidays

D = Decimal
HIST_START = dt.date(2025, 11, 1)
SCHED_END = dt.date(2026, 12, 18)          # appointments are already booked about five weeks ahead of today
HOL = {**holidays(2025), **holidays(2026)}


def q(x):
    return D(x).quantize(D("0.01"))


def is_biz(d):
    return d.weekday() < 5 and d not in HOL


def next_biz(d, n=0):
    d += dt.timedelta(days=n)
    while not is_biz(d):
        d += dt.timedelta(days=1)
    return d


def bucket(days):
    return "0-30" if days <= 30 else "31-60" if days <= 60 else "61-90" if days <= 90 else "91-120" if days <= 120 else "120+"


def build_journey(s, ctx, n_patients=1500):
    r = s.rnd
    P = ctx["payer"]
    payer_names = {code: name for code, name, *_ in PAYERS}
    share = [(code, sh) for code, _, _, _, _, _, _, sh, _ in PAYERS]
    pinfo = {code: dict(typ=typ, filing=fil, appeal=app, turn=turn) for code, _, typ, fil, cor, app, turn, sh, m in PAYERS}
    pid_to_code = {v: k for k, v in P.items()}
    prov = ctx["provider"]
    pts = ["Rao", "Lee", "Okafor", "Chen", "Patel", "Dsouza", "Walker", "Ito"]
    pt_w = [18, 16, 14, 13, 11, 10, 9, 9]
    ptas = {"Brooks": "Rao", "Haines": "Lee", "Moreno": "Okafor"}
    covers = {"Rao": "Brooks", "Lee": "Haines", "Okafor": "Moreno"}                   # the assistant who covers a therapist's follow-ups
    medicare_like = ("medicare", "medicare_advantage")
    cpt, icd, carc, rarc, mod, fee, rate = ctx["cpt"], ctx["icd"], ctx["carc"], ctx["rarc"], ctx["modifier"], ctx["fee"], ctx["rate"]
    staff = ctx["staff"]
    cpt_by_id = {v: k for k, v in cpt.items()}
    dx_codes = ctx.get("icd_pt", list(icd))

    # ---- outside referring physicians
    referrers = [s.add("provider", npi=f"19000003{i:02d}", provider_number=f"REF{i + 1:02d}", provider_type="MD", provider_name=f"Referrer {i + 1:02d}, MD",
                       credential="MD") for i in range(14)]

    # ---- patients and coverage
    patients = []
    for n in range(n_patients):
        code = r.choices([c for c, _ in share], [w for _, w in share])[0]
        typ = pinfo[code]["typ"]
        age = r.randint(66, 88) if typ in medicare_like else r.randint(19, 64)
        pid = s.add("patient", patient_number_hash=h("patient", n), birth_year=2026 - age, is_age_90_plus=False, sex=r.choice("MF"), state="TX",
                    primary_practice_id=ctx["practice"], is_self_pay=(typ == "self_pay"), zip3=r.choice(["750", "751", "752", "753"]),
                    language="Spanish" if r.random() < .1 else "English", is_deceased=False, first_seen_date=None)
        cov = cov_row = None
        copay = D(0)
        if typ != "self_pay":
            copay = D(0) if typ in ("medicare", "medicaid") else D(r.choice([20, 25, 30, 35, 40]))
            term = None
            cov = s.add("coverage", patient_id=pid, payer_id=P[code], member_number_hash=h("member", n), coverage_order=1, effective_date=dt.date(2024, 1, 1),
                        plan_type=("Medicare Part B" if typ == "medicare" else "Medicaid managed care" if typ == "medicaid" else
                                   r.choice(["Medicare Advantage HMO", "Medicare Advantage PPO"]) if typ == "medicare_advantage" else r.choice(["PPO", "HMO", "EPO"])),
                        plan_name=f"{payer_names[code]} plan", relationship_to_holder="self", requires_referral=(typ == "commercial" and r.random() < .15),
                        copay_amount=copay, coinsurance_pct=D("0.2000") if typ == "medicare" else D("0.1000"), deductible_remaining=D(0))
        patients.append(dict(id=pid, n=n, code=code, typ=typ, cov=cov, copay=copay, term=None, cob=False, age=age))
    # S6 coverage ended for 2% of insured patients; S* other payer primary for 1.5%
    insured = [p for p in patients if p["cov"]]
    for p in r.sample(insured, int(len(insured) * .02)):
        p["term"] = r.choice([dt.date(2026, 8, 31), dt.date(2026, 9, 30), dt.date(2026, 10, 15), dt.date(2026, 10, 31)])
        row = next(x for x in s.rows["coverage"] if x["coverage_id"] == p["cov"])
        row["termination_date"] = p["term"]
    for p in r.sample([x for x in insured if x["typ"] == "commercial" and x["term"] is None], int(len(insured) * .015)):
        p["cob"] = True

    # ---- episodes and visits
    claims, bills = [], []                       # per-claim working records, adjudicated below
    pay_specs = []                               # money to post: grouped into payment rows afterwards
    seq = defaultdict(int)

    def num(prefix, key):
        seq[key] += 1
        return f"{prefix}-{seq[key]:06d}"

    visits_made = 0
    for p in patients:
        for ep_no in range(1 if r.random() < .7 else 2):
            code, typ = p["code"], p["typ"]
            ot = r.random() < .15
            thera = r.choice(["Nguyen", "Nguyen", "Khan"]) if ot else r.choices(pts, pt_w)[0]
            long_uhc = code == "SYNUHC" and r.random() < .10
            long_aet = code == "SYNAET" and r.random() < .22
            n_vis = r.randint(14, 18) if long_uhc else r.randint(14, 16) if long_aet else r.randint(4, 11)
            start = HIST_START + dt.timedelta(days=r.randint(0, 390 if ep_no == 0 else 350) + (45 if ep_no else 0))
            start = next_biz(start)
            if start > SCHED_END:
                continue
            fac = r.choices(ctx["facility"][:2], [60, 40])[0]               # therapy runs at the first two facilities
            dxs = r.sample(dx_codes, r.choice([1, 2, 2, 3]))
            referral = None
            auth_id = auth_units = None
            referred_by = r.choice(referrers) if (typ == "commercial" and r.random() < .35) or typ == "medicare" else None
            if referred_by and (p["cov"] and r.random() < .6):
                referral = s.add("referral", referral_number=num("REF", "ref"), practice_id=ctx["practice"], patient_id=p["id"], coverage_id=p["cov"],
                                 payer_id=P[code], referring_provider_id=referred_by, referred_to_provider_id=prov[thera], specialty_id=ctx["specialty"]["OT" if ot else "PT"],
                                 referral_status="active", request_date=start - dt.timedelta(days=5), received_date=start - dt.timedelta(days=3),
                                 valid_from=start - dt.timedelta(days=3), valid_to=start + dt.timedelta(days=120), visits_allowed=24, visits_used=0,
                                 diagnosis_code_id=icd[dxs[0]])
            needs_auth = code in ("SYNAET", "SYNCIG") and r.random() < (.85 if code == "SYNAET" else .5)
            if needs_auth:
                auth_units = 12 if code == "SYNAET" else 20
                auth_id = s.add("authorization", authorization_number=num("AUTH", "auth"), patient_id=p["id"], payer_id=P[code], practice_id=ctx["practice"],
                                authorization_status="approved", coverage_id=p["cov"], primary_cpt_code_id=cpt["97110"], units_approved=auth_units, units_used=0,
                                valid_from=start - dt.timedelta(days=2), valid_to=start + dt.timedelta(days=100), request_date=start - dt.timedelta(days=7),
                                decision_date=start - dt.timedelta(days=3), authorization_type="visits", requesting_provider_id=prov[thera],
                                rendering_provider_id=prov[thera], urgency="routine", request_channel="portal", diagnosis_code_id=icd[dxs[0]],
                                facility_id=fac, units_requested=auth_units, place_of_service_id=ctx["pos"]["11"])
            poc_missing = code == "SYNUHC" and (long_uhc and r.random() < .55)          # S1 plan of care never filed
            # visit dates: 2 or 3 a week
            days, d, wk = [], start, 0
            pattern = r.choice([(0, 2), (1, 3), (0, 2, 4), (1, 3, 4)])
            while len(days) < n_vis and d <= SCHED_END:
                for wd in pattern:
                    cand = d - dt.timedelta(days=d.weekday()) + dt.timedelta(days=wd)
                    if cand >= start and is_biz(cand) and cand <= SCHED_END and len(days) < n_vis:
                        days.append(cand)
                d += dt.timedelta(days=7)
            booked = min(start - dt.timedelta(days=r.randint(2, 9)), TODAY - dt.timedelta(days=1))     # nothing is booked in the future
            plan_doc = None
            auth_used = 0
            for vi, vd in enumerate(days):
                is_eval = vi == 0
                therapist = thera
                if not ot and not is_eval and r.random() < .35:
                    therapist = covers.get(thera, thera)                                                # assistants cover three PTs' follow-ups
                tid = prov[therapist]
                status = "scheduled"
                if vd < TODAY:
                    status = "no_show" if r.random() < .03 else "cancelled" if r.random() < .05 else "completed"
                # --- lines for the visit
                lines = []
                if is_eval:
                    ev_level = r.choices([1, 2, 3], [45, 40, 15])[0]
                    billed_level = ev_level
                    if thera == "Okafor" and ev_level == 2 and r.random() < .55:
                        billed_level = 1                              # S9 under-coded
                    if thera == "Chen" and ev_level == 1 and r.random() < .30:
                        billed_level = 2                              # S9 over-coded
                    ecode = ("97165", "97166", "97166")[billed_level - 1] if ot else ("97161", "97162", "97163")[billed_level - 1]
                    lines.append((ecode, 1, ev_level))
                    lines.append(("97110", 1, None))
                    if r.random() < .5:
                        lines.append(("97010", 1, None))
                else:
                    lines.append(("97110", r.choices([1, 2, 3], [25, 50, 25])[0], None))
                    if r.random() < .65:
                        lines.append(("97140", r.choice([1, 1, 2]), None))
                    if r.random() < .40:
                        lines.append(("97530", r.choice([1, 2]), None))
                    if r.random() < .20:
                        lines.append(("97112", 1, None))
                    if r.random() < .15:
                        lines.append(("97010", 1, None))
                has_pair = any(c == "97140" for c, _, _ in lines) and any(c == "97530" for c, _, _ in lines)
                appt = s.add("appointment", appointment_number=num("APT", "apt"), practice_id=ctx["practice"], patient_id=p["id"], appointment_date=vd,
                             appointment_status=status, provider_id=tid, specialty_id=ctx["specialty"]["OT" if ot else "PT"], payer_id=P[code], coverage_id=p["cov"],
                             facility_id=fac, start_time=dt.time(r.choice([8, 9, 10, 11, 13, 14, 15, 16]), r.choice([0, 30])), booked_date=booked if vi == 0 else min(vd - dt.timedelta(days=7), TODAY - dt.timedelta(days=1)),
                             appointment_type="evaluation" if is_eval else "follow_up", reschedule_count=0, copay_due=p["copay"] if p["cov"] else None,
                             eligibility_state="verified" if vd < TODAY or vi == 0 else "pending",
                             authorization_state=("approved" if auth_id and auth_used < (auth_units or 0) else "exhausted") if auth_id else "not_required",
                             booked_via="phone", referring_provider_id=referred_by, referral_id=referral,
                             **({"cancelled_date": vd - dt.timedelta(days=1), "cancel_reason": "patient request"} if status == "cancelled" else {}))
                for ln, (c, u, lvl) in enumerate(lines, 1):
                    s.add("appointment_details", appointment_id=appt, line_number=ln, practice_id=ctx["practice"], patient_id=p["id"], payer_id=P[code], provider_id=tid,
                          planned_cpt_code_id=cpt[c], is_inferred=False, planned_units=D(u), expected_charge=q(fee[c] * u),
                          expected_allowed=q(rate[(code, c)] * u) if (code, c) in rate else None, auth_required="yes" if auth_id else "no", authorization_id=auth_id,
                          duration_minutes=15 * u if cpt_by_id[cpt[c]] in ("97110", "97140", "97530", "97112") else 15)
                visits_made += 1
                # eligibility check at the first booking, and 3 and 1 days before each visit that is still ahead
                if p["cov"] and (vi == 0 or (vd >= TODAY and (vd - dt.timedelta(days=3) <= TODAY))):
                    for back in ([0] if vi == 0 else [3, 1]):
                        cd = (booked if vi == 0 else vd - dt.timedelta(days=back))
                        if cd > TODAY:
                            continue
                        s.add("eligibility_check", trace_number=num("TRN", "trn"), appointment_id=appt, coverage_id=p["cov"], patient_id=p["id"], payer_id=P[code],
                              practice_id=ctx["practice"], is_secondary=False, check_date=cd, service_date=vd, service_type_code="AE", is_aaa_reject=False,
                              plan_begin_date=dt.date(2024, 1, 1), plan_end_date=p["term"], copay_amount=p["copay"], coinsurance_pct=D("20.00") if typ == "medicare" else D("10.00"),
                              deductible_remaining=D(0), other_payer_id=None, auth_required_hint=bool(auth_id))
                if status != "completed":
                    continue
                # --- encounter and note
                lag_sig = r.randint(3, 6) if therapist == "Lee" else r.randint(0, 2)
                signed = vd + dt.timedelta(days=lag_sig)
                note_ok = signed <= TODAY
                if therapist == "Lee" and vd >= TODAY - dt.timedelta(days=12) and r.random() < .25:
                    note_ok = False                                  # S3 unsigned notes
                minutes = sum(15 * u for c, u, _ in lines if cpt_by_id[cpt[c]] in ("97110", "97140", "97530", "97112"))
                auth_used += 1                                           # an authorization covers a number of visits
                enc = s.add("encounter", encounter_number=num("ENC", "enc"), practice_id=ctx["practice"], patient_id=p["id"], encounter_date=vd, rendering_provider_id=tid,
                            encounter_status="completed", appointment_id=appt, payer_id=P[code], coverage_id=p["cov"], facility_id=fac, place_of_service_id=ctx["pos"]["11"],
                            specialty_id=ctx["specialty"]["OT" if ot else "PT"], encounter_type="evaluation" if is_eval else "follow_up", visit_minutes=minutes or 15,
                            note_status="signed" if note_ok else "unsigned", note_signed_date=signed if note_ok else None, signature_lag_days=lag_sig if note_ok else None,
                            elements_documented=r.randint(4, 7), charge_status="charged" if note_ok else "pending", coding_status="coded" if note_ok else "pending",
                            principal_diagnosis_code_id=icd[dxs[0]], authorization_id=auth_id, supervising_provider_id=prov[thera] if therapist != thera else None,
                            referring_provider_id=referred_by, referral_id=referral)
                edl = {}
                for ln, (c, u, lvl) in enumerate(lines, 1):
                    mods = []
                    mods.append(mod["GO"] if ot else mod["GP"])
                    if typ in medicare_like and therapist in ptas:
                        mods.append(mod["CQ"])
                    if typ == "medicare" and vi >= 14 and len(mods) < 2:
                        mods.append(mod["KX"])
                    if c == "97530" and has_pair and len(mods) < 2:
                        flag_s7 = code == "SYNAET" and vd >= dt.date(2026, 9, 1) and r.random() < .5
                        if not flag_s7:
                            mods.append(mod["XU"])
                    edl[ln] = s.add("encounter_details", encounter_id=enc, line_number=ln, practice_id=ctx["practice"], patient_id=p["id"], payer_id=P[code], provider_id=tid,
                                    cpt_code_id=cpt[c], units=D(u), service_date=vd, rendering_provider_id=tid, diagnosis_1_id=icd[dxs[0]],
                                    diagnosis_2_id=icd[dxs[1]] if len(dxs) > 1 else None, modifier_1_id=mods[0], modifier_2_id=mods[1] if len(mods) > 1 else None,
                                    procedure_documented=True, documented_level=lvl, time_minutes=15 * u if c in ("97110", "97140", "97530", "97112") else None,
                                    authorization_id=auth_id, auth_required="yes" if auth_id else "no", line_status="coded", expected_charge=q(fee[c] * u),
                                    place_of_service_id=ctx["pos"]["11"])
                    lines[ln - 1] = (c, u, lvl, mods)
                dtype = "evaluation" if is_eval else "daily_note"
                s.add("document", document_number=num("DOC", "doc"), practice_id=ctx["practice"], patient_id=p["id"], document_class="clinical", document_type=dtype,
                      document_status="signed" if note_ok else "draft", encounter_id=enc, author_provider_id=tid, signer_role="therapist", document_date=vd,
                      signed_at=dt.datetime.combine(signed, dt.time(17, 0)) if note_ok else None, is_late_entry=False, is_addendum=False, is_locked=note_ok,
                      cosign_required=therapist in ptas, cosign_status="done" if therapist in ptas and note_ok else ("pending" if therapist in ptas else None),
                      minutes_documented=minutes or None)
                if is_eval and not poc_missing:
                    plan_doc = s.add("document", document_number=num("DOC", "doc"), practice_id=ctx["practice"], patient_id=p["id"], document_class="clinical",
                                     document_type="plan_of_care", document_status="signed", encounter_id=enc, author_provider_id=prov[thera], document_date=vd,
                                     signed_at=dt.datetime.combine(vd, dt.time(18, 0)), is_late_entry=False, is_addendum=False, is_locked=True)
                # --- bill
                lag = r.randint(6, 9) if therapist == "Lee" else r.randint(0, 2)       # S3 slow charge entry
                charge_date = next_biz(vd, lag)
                total = sum((q(fee[c] * u) for c, u, _, _ in lines), D(0))
                held = not note_ok
                bill = s.add("bill", bill_number=num("BILL", "bill"), practice_id=ctx["practice"], patient_id=p["id"], encounter_id=enc, service_date=vd,
                             charge_entered_date=min(charge_date, TODAY) if not held else TODAY, bill_status="on_hold" if held else "open",
                             bill_type="self_pay" if typ == "self_pay" else "insurance", total_billed=total, billing_provider_id=prov[thera], rendering_provider_id=tid,
                             specialty_id=ctx["specialty"]["OT" if ot else "PT"], payer_id=P[code], coverage_id=p["cov"], facility_id=fac, place_of_service_id=ctx["pos"]["11"],
                             hold_reason="note_unsigned" if held else None, hold_date=TODAY if held else None, claims_created=0,
                             expected_allowed=q(sum(rate[(code, c)] * u for c, u, _, _ in lines)) if typ != "self_pay" else None, entered_by_role="biller",
                             patient_statement_flag=False)
                bdl = []
                for ln, (c, u, lvl, mods) in enumerate(lines, 1):
                    bd = s.add("bill_details", bill_id=bill, line_number=ln, practice_id=ctx["practice"], patient_id=p["id"], payer_id=P[code], provider_id=tid,
                               cpt_code_id=cpt[c], units=D(u), fee_per_unit=fee[c], billed_amount=q(fee[c] * u), line_status="held" if held else "open", service_date=vd,
                               modifier_1_id=mods[0], modifier_2_id=mods[1] if len(mods) > 1 else None, diagnosis_1_id=icd[dxs[0]],
                               diagnosis_2_id=icd[dxs[1]] if len(dxs) > 1 else None, rendering_provider_id=tid, encounter_detail_id=edl[ln],
                               charge_entered_date=min(charge_date, TODAY), expected_allowed=q(rate[(code, c)] * u) if (code, c) in rate else None,
                               authorization_id=auth_id, place_of_service_id=ctx["pos"]["11"], entered_by_role="biller")
                    bdl.append(bd)
                rec = dict(p=p, code=code, typ=typ, ot=ot, thera=thera, tid=tid, vd=vd, vi=vi, enc=enc, bill=bill, bdl=bdl, lines=lines, total=total, held=held,
                           charge_date=min(charge_date, TODAY), dxs=dxs, auth=auth_id, auth_units=auth_units, auth_used=auth_used, poc_missing=poc_missing, fac=fac,
                           has_pair=has_pair, referral=referral, edl=edl)
                bills.append(rec)
            if referral:
                row = next(x for x in s.rows["referral"] if x["referral_id"] == referral)
                row["visits_used"] = sum(1 for x in days if x < TODAY)
            if auth_id:
                row = next(x for x in s.rows["authorization"] if x["authorization_id"] == auth_id)
                row["units_used"] = min(auth_used, auth_units + 6)
                if auth_used >= auth_units:
                    row["authorization_status"] = "exhausted"
    # the first and last service dates a patient was seen
    seen = defaultdict(list)
    for b in bills:
        seen[b["p"]["id"]].append(b["vd"])
    for row in s.rows["patient"]:
        if seen.get(row["patient_id"]):
            row["first_seen_date"], row["last_seen_date"] = min(seen[row["patient_id"]]), max(seen[row["patient_id"]])
        if row["is_self_pay"] is False:
            row["primary_coverage_id"] = next((c["coverage_id"] for c in s.rows["coverage"] if c["patient_id"] == row["patient_id"]), None)
    ctx["bills"], ctx["pay_specs"], ctx["num"], ctx["pinfo"], ctx["pid_to_code"] = bills, pay_specs, num, pinfo, pid_to_code
    ctx["cpt_by_id"] = cpt_by_id
    return ctx


def add_enrollments(s, ctx):
    """Provider enrolment with each payer, and monthly exclusion screening (source data the credentialing agent reads)."""
    r = s.rnd
    P = ctx["payer"]
    for i, pr in enumerate([p for p in s.rows["provider"] if p["specialty_id"] and p["provider_type"] != "RN"]):      # billing providers; nurses do not enrol
        for code in [c for c in P if c != "SYNSELF"]:
            exp_days = 70 + (i * 37 + len(code) * 11) % 500
            if pr["provider_name"].startswith("Haines") and code == "SYNCIG":
                exp_days = 21
            if pr["provider_name"].startswith("Okafor") and code == "SYNMCR":
                exp_days = 38
            exp = TODAY + dt.timedelta(days=exp_days)
            s.add("enrollment", enrollment_number=ctx["num"]("ENR", "enr"), provider_id=pr["provider_id"], payer_id=P[code], practice_id=ctx["practice"], event_type="enrollment",
                  event_date=dt.date(2024, 1, 15), enrollment_status="active", enrollment_type="individual", effective_date=dt.date(2024, 1, 15), expires_date=exp,
                  revalidation_due_date=exp - dt.timedelta(days=60), last_revalidated_date=dt.date(2025, 2, 1))
        for mth in range(0, 12):
            sd = dt.date(2025, 11, 15) + dt.timedelta(days=30 * mth)
            if sd <= TODAY:
                s.add("enrollment", provider_id=pr["provider_id"], practice_id=ctx["practice"], event_type="screening", event_date=sd, screening_source="OIG", screening_result="clear",
                      screening_list_date=sd, match_method="npi")
