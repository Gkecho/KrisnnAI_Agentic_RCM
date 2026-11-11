"""Stage 2c: the multispecialty growth of Valley Wellness Health: family medicine (physicians, nurse practitioners, registered nurses), orthopedics and
pain management at the Southlake facility, then the resource inventory (rooms, machines, nurses) and its allocation to every appointment (therapy included).

Works like journey.py: it leaves the same visit records in ctx["bills"], so money.py adjudicates them with everything else.

Planted stories (each has a known answer):
  S10 Humana Medicare Advantage: lumbar epidural / facet / ablation procedures billed without a prior authorization (CARC 197)
  S11 Texas Medicaid: coverage ends mid-year for many members (CARC 27); a 95-day filing window
  S12 UnitedHealthcare: orthopedic E/M billed with a same-day injection but without modifier 25 from 2026-07-01 (CARC 4)
  S13 Dr. Nakamura (family medicine): slow note signing, bills held
Nurse practitioners bill under their own number and are paid 85% by Medicare and Medicare Advantage; registered nurses never bill, their
services (injections, nurse visits, blood draws) bill under the supervising physician.
"""
import datetime as dt
from decimal import Decimal
from collections import defaultdict

from core import TODAY, h
from journey import q, next_biz, HIST_START, SCHED_END
from ref import PAYERS, RESOURCES

D = Decimal
SHARE = {   # payer mix by service line
    "FM": {"SYNUHC": .17, "SYNBCBS": .20, "SYNAET": .10, "SYNCIG": .09, "SYNMCR": .14, "SYNHUM": .12, "SYNMCD": .10, "SYNSELF": .08},
    "ORTHO": {"SYNUHC": .22, "SYNBCBS": .24, "SYNAET": .14, "SYNCIG": .10, "SYNMCR": .14, "SYNHUM": .08, "SYNMCD": .02, "SYNSELF": .06},
    "PAIN": {"SYNUHC": .15, "SYNBCBS": .18, "SYNAET": .10, "SYNCIG": .08, "SYNMCR": .22, "SYNHUM": .17, "SYNMCD": .05, "SYNSELF": .05},
}
DUR = {"99203": 40, "99204": 45, "99213": 20, "99214": 30, "99395": 40, "99211": 10, "36415": 5, "93000": 10, "96372": 10, "73030": 10, "73560": 10, "72100": 10,
       "76881": 20, "95907": 45, "20610": 20, "20552": 15, "62323": 45, "64483": 45, "64493": 45, "64635": 75}
EM = {"99203", "99204", "99213", "99214", "99395"}
PROC = ("62323", "64483", "64493", "64635")
REGION = {"shoulder": (["M25511", "M25512", "M75100", "M7541"], "73030"), "knee": (["M25561", "M25562", "M170", "M1711", "S83511A"], "73560"),
          "spine": (["M5126", "M4806", "M5459"], "72100")}
EQUIP = {"97032": "E-stim unit", "G0283": "E-stim unit", "97035": "Therapeutic ultrasound", "73030": "X-ray room", "73560": "X-ray room", "72100": "X-ray room",
         "76881": "Ultrasound suite", "95907": "EMG lab", "93000": "ECG cart", "20610": "Procedure room", "20552": "Procedure room", "62323": "C-arm suite",
         "64483": "C-arm suite", "64493": "C-arm suite", "64635": "C-arm suite", "36415": "Nurse treatment room", "96372": "Nurse treatment room", "99211": "Nurse treatment room"}
GYM = {"97110", "97112", "97116", "97530", "97535", "97542", "97750", "97150"}
OWN_ROOM = {"Nurse treatment room", "C-arm suite"}               # services in these rooms do not also need an exam room


def build_clinic(s, ctx, n_fm=2200, n_ortho=1100, n_pain=600):
    r = s.rnd
    P, pinfo, prov, cpt, icd, mod, fee, rate = ctx["payer"], ctx["pinfo"], ctx["provider"], ctx["cpt"], ctx["icd"], ctx["modifier"], ctx["fee"], ctx["rate"]
    num, fac, spec = ctx["num"], ctx["facility"], ctx["specialty"]
    roster, supervisor, bills = ctx["roster"], ctx["supervisor"], ctx["bills"]
    payer_names = {c: nm for c, nm, *_ in PAYERS}
    referrers = [x["provider_id"] for x in s.rows["provider"] if str(x["provider_number"]).startswith("REF")]
    busy = defaultdict(list)                  # (provider id, date) -> (start minute, end minute)
    pat_rows, seen = {}, defaultdict(list)

    # ------------------------------------------------------------------ patients and coverage
    def new_patients(line, count, base):
        out = []
        for i in range(count):
            n = base + i
            code = r.choices(list(SHARE[line]), list(SHARE[line].values()))[0]
            typ = pinfo[code]["typ"]
            age = r.randint(66, 88) if typ in ("medicare", "medicare_advantage") else r.randint(19, 64)
            pid = s.add("patient", patient_number_hash=h("patient", n), birth_year=2026 - age, is_age_90_plus=False, sex=r.choice("MF"), state="TX", primary_practice_id=ctx["practice"],
                        is_self_pay=(typ == "self_pay"), zip3=r.choice(["750", "751", "752", "760"]), language="Spanish" if r.random() < .1 else "English", is_deceased=False)
            pat_rows[pid] = s.rows["patient"][-1]
            cov, copay = None, D(0)
            if typ != "self_pay":
                copay = D(0) if typ in ("medicare", "medicaid") else D(r.choice([20, 25, 30, 35, 40]))
                plan = ("Medicare Part B" if typ == "medicare" else "Medicaid managed care" if typ == "medicaid" else
                        r.choice(["Medicare Advantage HMO", "Medicare Advantage PPO"]) if typ == "medicare_advantage" else r.choice(["PPO", "HMO", "EPO"]))
                cov = s.add("coverage", patient_id=pid, payer_id=P[code], member_number_hash=h("member", n), coverage_order=1, effective_date=dt.date(2024, 1, 1), plan_type=plan,
                            plan_name=f"{payer_names[code]} plan", relationship_to_holder="self", requires_referral=(typ == "commercial" and r.random() < .15),
                            copay_amount=copay, coinsurance_pct=D("0.2000") if typ == "medicare" else D("0.1000"), deductible_remaining=D(0))
                pat_rows[pid]["primary_coverage_id"] = cov
            out.append(dict(id=pid, n=n, code=code, typ=typ, cov=cov, copay=copay, term=None, cob=False, age=age))
        insured = [p for p in out if p["cov"]]
        for p in r.sample(insured, int(len(insured) * .02)):                                       # coverage ended
            p["term"] = r.choice([dt.date(2026, 8, 31), dt.date(2026, 9, 30), dt.date(2026, 10, 15), dt.date(2026, 10, 31)])
        for p in [x for x in insured if x["typ"] == "medicaid" and x["term"] is None]:             # S11 Medicaid members lose coverage at renewal
            if r.random() < .14:
                p["term"] = r.choice([dt.date(2026, 4, 30), dt.date(2026, 5, 31), dt.date(2026, 6, 30), dt.date(2026, 7, 31), dt.date(2026, 8, 31), dt.date(2026, 9, 30)])
        for p in insured:
            if p["term"]:
                next(x for x in s.rows["coverage"] if x["coverage_id"] == p["cov"])["termination_date"] = p["term"]
        for p in r.sample([x for x in insured if x["typ"] == "commercial" and x["term"] is None], int(len(insured) * .015)):
            p["cob"] = True
        return out

    # ------------------------------------------------------------------ one visit: appointment -> encounter -> note -> bill
    def emit(p, line, fac_id, vd, vi, kind, lines, clinical, biller, dxs, booked, first=False, auth=None, auth_units=None, referral=None, referred_by=None, **flags):
        code, typ = p["code"], p["typ"]
        tid, btid = prov[clinical], prov[biller]
        is_np = any(clinical in roster[x]["NP"] for x in roster)
        dur = max(15, sum(DUR[c] * u for c, u, _ in lines))
        want = r.choice([8, 9, 10, 11, 13, 14, 15]) * 60 + r.choice([0, 15, 30, 45])
        start = want
        for _ in range(40):                                                                         # first free time for the clinician
            if all(start + dur <= a or start >= b for a, b in busy[(tid, vd)]) and start + dur <= 17 * 60:
                break
            start += 15
            if start + dur > 17 * 60:
                start = 8 * 60 + (start % 60)
        busy[(tid, vd)].append((start, start + dur))
        status = "scheduled"
        if vd < TODAY:
            status = "no_show" if r.random() < .03 else "cancelled" if r.random() < .05 else "completed"
        mods_of = {}
        for c, u, _ in lines:
            ms = []
            if c in EM and flags.get("proc_same_day") and not (code == "SYNUHC" and vd >= dt.date(2026, 7, 1) and flags.get("skip25")):
                ms.append(mod["25"])
            if c == "20610":
                ms.append(mod[r.choice(["RT", "LT"])])
            mods_of[c] = ms
        auth_state = ("approved" if auth and vi < (auth_units or 0) else "exhausted") if auth else "not_required"
        appt = s.add("appointment", appointment_number=num("APT", "apt"), practice_id=ctx["practice"], patient_id=p["id"], appointment_date=vd, appointment_status=status,
                     provider_id=tid, specialty_id=spec[line], payer_id=P[code], coverage_id=p["cov"], facility_id=fac_id, start_time=dt.time(start // 60, start % 60), booked_date=booked,
                     appointment_type=kind, reschedule_count=0, copay_due=p["copay"] if p["cov"] else None, eligibility_state="verified" if vd < TODAY or first else "pending",
                     authorization_state=auth_state, booked_via="phone", referring_provider_id=referred_by, referral_id=referral,
                     **({"cancelled_date": vd - dt.timedelta(days=1), "cancel_reason": "patient request"} if status == "cancelled" else {}))
        for ln, (c, u, _) in enumerate(lines, 1):
            s.add("appointment_details", appointment_id=appt, line_number=ln, practice_id=ctx["practice"], patient_id=p["id"], payer_id=P[code], provider_id=tid, planned_cpt_code_id=cpt[c],
                  is_inferred=False, planned_units=D(u), expected_charge=q(fee[c] * u), expected_allowed=q(rate[(code, c)] * u) if (code, c) in rate else None,
                  auth_required="yes" if auth else "no", authorization_id=auth, duration_minutes=DUR[c] * u)
        if p["cov"] and first and booked <= TODAY:
            s.add("eligibility_check", trace_number=num("TRN", "trn"), appointment_id=appt, coverage_id=p["cov"], patient_id=p["id"], payer_id=P[code], practice_id=ctx["practice"],
                  is_secondary=False, check_date=booked, service_date=vd, service_type_code="AE", is_aaa_reject=False, plan_begin_date=dt.date(2024, 1, 1), plan_end_date=p["term"],
                  copay_amount=p["copay"], coinsurance_pct=D("20.00") if typ == "medicare" else D("10.00"), deductible_remaining=D(0), other_payer_id=None, auth_required_hint=bool(auth))
        if status != "completed":
            return
        lag_sig = r.randint(3, 6) if clinical == "Nakamura" else r.randint(0, 2)                    # S13 slow note signing
        signed = vd + dt.timedelta(days=lag_sig)
        note_ok = signed <= TODAY
        if clinical == "Nakamura" and vd >= TODAY - dt.timedelta(days=12) and r.random() < .25:
            note_ok = False
        minutes = max(10, dur)
        enc = s.add("encounter", encounter_number=num("ENC", "enc"), practice_id=ctx["practice"], patient_id=p["id"], encounter_date=vd, rendering_provider_id=tid, encounter_status="completed",
                    appointment_id=appt, payer_id=P[code], coverage_id=p["cov"], facility_id=fac_id, place_of_service_id=ctx["pos"]["11"], specialty_id=spec[line], encounter_type=kind,
                    visit_minutes=minutes, note_status="signed" if note_ok else "unsigned", note_signed_date=signed if note_ok else None, signature_lag_days=lag_sig if note_ok else None,
                    elements_documented=r.randint(4, 7), charge_status="charged" if note_ok else "pending", coding_status="coded" if note_ok else "pending",
                    principal_diagnosis_code_id=icd[dxs[0]], authorization_id=auth, supervising_provider_id=btid if btid != tid else None, referring_provider_id=referred_by, referral_id=referral)
        edl, full = {}, []
        for ln, (c, u, lvl) in enumerate(lines, 1):
            ms = mods_of[c]
            edl[ln] = s.add("encounter_details", encounter_id=enc, line_number=ln, practice_id=ctx["practice"], patient_id=p["id"], payer_id=P[code], provider_id=tid, cpt_code_id=cpt[c],
                            units=D(u), service_date=vd, rendering_provider_id=tid, diagnosis_1_id=icd[dxs[0]], diagnosis_2_id=icd[dxs[1]] if len(dxs) > 1 else None,
                            modifier_1_id=ms[0] if ms else None, modifier_2_id=ms[1] if len(ms) > 1 else None, procedure_documented=True, time_minutes=None,
                            authorization_id=auth, auth_required="yes" if auth else "no", line_status="coded", expected_charge=q(fee[c] * u), place_of_service_id=ctx["pos"]["11"])
            full.append((c, u, lvl, ms))
        s.add("document", document_number=num("DOC", "doc"), practice_id=ctx["practice"], patient_id=p["id"], document_class="clinical", document_type="visit_note",
              document_status="signed" if note_ok else "draft", encounter_id=enc, author_provider_id=tid, signer_role="nurse" if clinical in sum((roster[x]["RN"] for x in roster), []) else "provider",
              document_date=vd, signed_at=dt.datetime.combine(signed, dt.time(17, 0)) if note_ok else None, is_late_entry=False, is_addendum=False, is_locked=note_ok,
              cosign_required=btid != tid and not is_np, cosign_status=("done" if note_ok else "pending") if btid != tid and not is_np else None, minutes_documented=minutes)
        charge_date = next_biz(vd, r.randint(6, 9) if clinical == "Nakamura" else r.randint(0, 2))
        total = sum((q(fee[c] * u) for c, u, _, _ in full), D(0))
        held = not note_ok
        bill = s.add("bill", bill_number=num("BILL", "bill"), practice_id=ctx["practice"], patient_id=p["id"], encounter_id=enc, service_date=vd,
                     charge_entered_date=min(charge_date, TODAY) if not held else TODAY, bill_status="on_hold" if held else "open", bill_type="self_pay" if typ == "self_pay" else "insurance",
                     total_billed=total, billing_provider_id=btid, rendering_provider_id=btid, specialty_id=spec[line], payer_id=P[code], coverage_id=p["cov"], facility_id=fac_id,
                     place_of_service_id=ctx["pos"]["11"], hold_reason="note_unsigned" if held else None, hold_date=TODAY if held else None, claims_created=0,
                     expected_allowed=q(sum(rate[(code, c)] * u for c, u, _, _ in full)) if typ != "self_pay" else None, entered_by_role="biller", patient_statement_flag=False)
        bdl = []
        for ln, (c, u, lvl, ms) in enumerate(full, 1):
            bdl.append(s.add("bill_details", bill_id=bill, line_number=ln, practice_id=ctx["practice"], patient_id=p["id"], payer_id=P[code], provider_id=btid, cpt_code_id=cpt[c],
                             units=D(u), fee_per_unit=fee[c], billed_amount=q(fee[c] * u), line_status="held" if held else "open", service_date=vd,
                             modifier_1_id=ms[0] if ms else None, modifier_2_id=ms[1] if len(ms) > 1 else None, diagnosis_1_id=icd[dxs[0]], diagnosis_2_id=icd[dxs[1]] if len(dxs) > 1 else None,
                             rendering_provider_id=btid, encounter_detail_id=edl[ln], charge_entered_date=min(charge_date, TODAY),
                             expected_allowed=q(rate[(code, c)] * u) if (code, c) in rate else None, authorization_id=auth, place_of_service_id=ctx["pos"]["11"], entered_by_role="biller"))
        seen[p["id"]].append(vd)
        bills.append(dict(p=p, code=code, typ=typ, ot=False, thera=biller, tid=btid, vd=vd, vi=vi, enc=enc, bill=bill, bdl=bdl, lines=full, total=total, held=held,
                          charge_date=min(charge_date, TODAY), dxs=dxs, auth=auth, auth_units=auth_units, auth_used=vi + 1, poc_missing=False, fac=fac_id, has_pair=False,
                          referral=referral, edl=edl, np=is_np, proc_same_day=bool(flags.get("proc_same_day")), no_auth_proc=bool(flags.get("no_auth_proc"))))

    def when(offset_days=None):
        d = next_biz(HIST_START + dt.timedelta(days=r.randint(0, 390)))
        return d

    def booked_for(d, first):
        return min(d - dt.timedelta(days=r.randint(2, 9) if first else 7), TODAY - dt.timedelta(days=1))

    # ------------------------------------------------------------------ family medicine
    fm = roster["FM"]
    fm_staff = fm["MD"] + fm["NP"]
    fm_w = [4] * len(fm["MD"]) + [3] * len(fm["NP"])
    for p in new_patients("FM", n_fm, 200000):
        pcp = r.choices(fm_staff, fm_w)[0]
        fid = r.choices([fac[2], fac[1]], [65, 35])[0]
        dxs = r.sample(["E119", "I10", "E785", "J069", "Z0000", "E669", "F419", "N390", "M545"], r.choice([1, 2, 2, 3]))
        d = when()
        kinds = ["preventive" if r.random() < .25 else "new_patient"] + ["follow_up"] * r.choice([1, 2, 2, 3, 4])
        rns = [x for x in fm["RN"] if supervisor[x] == supervisor[pcp]] or fm["RN"]
        for vi, kind in enumerate(kinds):
            if vi:
                d = next_biz(d, r.randint(28, 90))
            if d > SCHED_END:
                break
            if kind == "preventive":
                lines = [("99395", 1, None), ("36415", 1, None)]
            elif kind == "new_patient":
                lines = [(r.choices(["99203", "99204"], [55, 45])[0], 1, None)] + ([("36415", 1, None)] if r.random() < .4 else []) + ([("93000", 1, None)] if r.random() < .1 else [])
            else:
                lines = [(r.choices(["99213", "99214"], [55, 45])[0], 1, None)] + ([("36415", 1, None)] if r.random() < .35 else []) + ([("93000", 1, None)] if r.random() < .08 else [])
            emit(p, "FM", fid, d, vi, kind, lines, pcp, pcp, dxs, booked_for(d, vi == 0), first=vi == 0)
            if kind == "follow_up" and r.random() < .18:                                            # nurse visit under the supervising physician
                nd = next_biz(d, r.randint(2, 10))
                if nd <= SCHED_END:
                    emit(p, "FM", fid, nd, vi, "nurse_visit", [("96372", 1, None)] if r.random() < .65 else [("99211", 1, None)], r.choice(rns), supervisor[pcp], dxs, booked_for(nd, False))

    # ------------------------------------------------------------------ orthopedics
    orr = roster["ORTHO"]
    or_staff = orr["MD"] + orr["NP"]
    or_w = [3] * len(orr["MD"]) + [2] * len(orr["NP"])
    for p in new_patients("ORTHO", n_ortho, 300000):
        doc = r.choices(or_staff, or_w)[0]
        region = r.choice(list(REGION))
        pool, xr = REGION[region]
        dxs = r.sample(pool, r.choice([1, 2]))
        d = when()
        referral = referred_by = None
        if p["cov"] and r.random() < .45:
            referred_by = r.choice(referrers)
            referral = s.add("referral", referral_number=num("REF", "ref"), practice_id=ctx["practice"], patient_id=p["id"], coverage_id=p["cov"], payer_id=P[p["code"]], referring_provider_id=referred_by,
                             referred_to_provider_id=prov[doc], specialty_id=spec["ORTHO"], referral_status="active", request_date=d - dt.timedelta(days=5), received_date=d - dt.timedelta(days=3),
                             valid_from=d - dt.timedelta(days=3), valid_to=d + dt.timedelta(days=120), visits_allowed=8, visits_used=0, diagnosis_code_id=icd[dxs[0]])
        n_follow = r.choice([1, 2, 2, 3])
        inj_at = r.randint(1, n_follow) if r.random() < .35 else None
        emg_at = r.randint(1, n_follow) if r.random() < .10 else None
        for vi in range(n_follow + 1):
            if vi:
                d = next_biz(d, r.randint(14, 35))
            if d > SCHED_END:
                break
            if vi == 0:
                lines = [(r.choices(["99203", "99204"], [50, 50])[0], 1, None), (xr, r.choice([1, 1, 2]), None)] + ([("76881", 1, None)] if r.random() < .12 else [])
                kind, proc = "new_patient", False
            else:
                lines = [(r.choices(["99213", "99214"], [60, 40])[0], 1, None)]
                kind, proc = "follow_up", False
                if vi == inj_at:
                    lines.append(("20610", 1, None))
                    kind, proc = "procedure", True
                if vi == emg_at:
                    lines.append(("95907", 1, None))
            emit(p, "ORTHO", fac[2], d, vi, kind, lines, doc, doc, dxs, booked_for(d, vi == 0), first=vi == 0, referral=referral, referred_by=referred_by,
                 proc_same_day=proc, skip25=proc and r.random() < .5)

    # ------------------------------------------------------------------ pain management
    pn = roster["PAIN"]
    pn_staff = pn["MD"] + pn["NP"]
    pn_w = [4] * len(pn["MD"]) + [2] * len(pn["NP"])
    for p in new_patients("PAIN", n_pain, 400000):
        doc = r.choices(pn_staff, pn_w)[0]
        dxs = r.sample(["M5459", "M5416", "M4806", "M5126", "G894", "M47816", "M792", "M545", "M4802"], r.choice([1, 2, 2]))
        d = when()
        series = r.choice([1, 1, 2, 3])
        procs = [r.choices(["62323", "64483", "64493"], [55, 25, 20])[0]]
        for _ in range(series - 1):
            procs.append("64635" if procs[-1] == "64493" and r.random() < .5 else procs[0])
        auth = None
        no_auth = False
        if p["typ"] not in ("medicare", "self_pay"):
            if p["code"] == "SYNHUM" and r.random() < .35:
                no_auth = True                                                                      # S10 Humana: the authorization was never requested
            else:
                auth = s.add("authorization", authorization_number=num("AUTH", "auth"), patient_id=p["id"], payer_id=P[p["code"]], practice_id=ctx["practice"], authorization_status="approved",
                             coverage_id=p["cov"], primary_cpt_code_id=cpt[procs[0]], units_approved=len(procs), units_used=0, valid_from=d - dt.timedelta(days=2), valid_to=d + dt.timedelta(days=150),
                             request_date=d - dt.timedelta(days=7), decision_date=d - dt.timedelta(days=3), authorization_type="visits", requesting_provider_id=prov[doc], rendering_provider_id=prov[doc],
                             urgency="routine", request_channel="portal", diagnosis_code_id=icd[dxs[0]], facility_id=fac[2], units_requested=len(procs), place_of_service_id=ctx["pos"]["11"])
        emit(p, "PAIN", fac[2], d, 0, "new_patient", [(r.choices(["99203", "99204"], [40, 60])[0], 1, None)], doc, doc, dxs, booked_for(d, True), first=True)
        done = 0
        for k, proc in enumerate(procs):
            d = next_biz(d, r.randint(14, 28))
            if d > SCHED_END:
                break
            lines = [(proc, 1, None)] + ([("20552", 1, None)] if r.random() < .15 else [])
            emit(p, "PAIN", fac[2], d, k, "procedure", lines, doc, doc, dxs, booked_for(d, False), auth=auth, auth_units=len(procs) if auth else None, no_auth_proc=no_auth)
            done += d < TODAY
            if k < len(procs) - 1 and r.random() < .5:
                fd = next_biz(d, r.randint(7, 14))
                if fd <= SCHED_END:
                    emit(p, "PAIN", fac[2], fd, k, "follow_up", [(r.choices(["99213", "99214"], [60, 40])[0], 1, None)], doc, doc, dxs, booked_for(fd, False))
        if auth:
            row = next(x for x in s.rows["authorization"] if x["authorization_id"] == auth)
            row["units_used"] = done
            if done >= len(procs):
                row["authorization_status"] = "exhausted"

    for pid, vds in seen.items():                                                                 # first and last seen
        pat_rows[pid]["first_seen_date"], pat_rows[pid]["last_seen_date"] = min(vds), max(vds)
    return ctx


RES_TYPE = {"Exam room": "room", "Nurse treatment room": "room", "Procedure room": "room", "C-arm suite": "room", "X-ray room": "room", "Ultrasound suite": "room",
            "EMG lab": "room", "Gym station": "room", "Treatment table": "equipment", "E-stim unit": "equipment", "Therapeutic ultrasound": "equipment",
            "Traction unit": "equipment", "ECG cart": "equipment"}
RES_CODE = {"Exam room": "EXAM", "Nurse treatment room": "NURSERM", "Procedure room": "PROC", "C-arm suite": "CARM", "X-ray room": "XRAY", "Ultrasound suite": "US", "EMG lab": "EMG",
            "Gym station": "GYM", "Treatment table": "TABLE", "E-stim unit": "ESTIM", "Therapeutic ultrasound": "TUS", "Traction unit": "TRAC", "ECG cart": "ECG"}
RES_COST = {"Exam room": "35.00", "Nurse treatment room": "40.00", "Procedure room": "110.00", "C-arm suite": "260.00", "X-ray room": "120.00", "Ultrasound suite": "80.00", "EMG lab": "90.00",
            "Gym station": "10.00", "Treatment table": "8.00", "E-stim unit": "12.00", "Therapeutic ultrasound": "14.00", "Traction unit": "10.00", "ECG cart": "15.00"}
BASE_CODES = {"Exam room": ["99203", "99204", "99213", "99214", "99395"], "Treatment table": ["97110", "97112", "97116", "97140", "97124", "97161", "97162", "97163", "97164", "97165", "97166"],
              "Gym station": sorted(GYM)}
NURSE_CPT = {"36415", "96372", "93000"}                                     # services a nurse performs when a physician or nurse practitioner runs the visit
NURSE_SERVES = ",".join(sorted(NURSE_CPT | {"99211"} | set(PROC) | {"20610", "20552"}))


def build_resource_master(s, ctx):
    """The inventory: every room and machine as its own row, and every registered nurse as a floating staff resource."""
    ctx["res_id"] = {}
    for fi, items in RESOURCES.items():
        fid = ctx["facility"][fi]
        for name, count in items:
            codes = ",".join(BASE_CODES.get(name) or sorted(c for c, r in EQUIP.items() if r == name))
            for inst in range(1, count + 1):
                nm = f"{name} {inst}" if count > 1 else name
                ctx["res_id"][(fid, nm)] = s.add("resource", resource_number=f"LOC{fi + 1}-{RES_CODE[name]}-{inst}", resource_name=nm, resource_type=RES_TYPE[name], resource_class=name,
                                                 practice_id=ctx["practice"], facility_id=fid, is_floating=False, capacity=1, serves_cpt_codes=codes or None,
                                                 in_service_date=dt.date(2019, 1, 1), resource_status="in_service", cost_per_hour=D(RES_COST[name]))
    ctx["nurses"] = []
    for spec_code, groups in ctx["roster"].items():
        for nm in groups["RN"]:
            pid = ctx["provider"][nm]
            ctx["res_id"][("RN", pid)] = s.add("resource", resource_number=f"RN-{nm.upper()}", resource_name=f"{nm}, RN", resource_type="staff", resource_class="Registered nurse",
                                               practice_id=ctx["practice"], facility_id=ctx["facility"][2], is_floating=True, capacity=1, provider_id=pid, serves_cpt_codes=NURSE_SERVES,
                                               in_service_date=dt.date(2019, 1, 1), resource_status="in_service", cost_per_hour=D("42.00"))
            ctx["nurses"].append(pid)
    return ctx


def build_resources(s, ctx):
    """Allocates a room, a machine and, where the service needs one, a nurse to every appointment (therapy included): writes appointment_slot and
    resource_allocation rows. When every instance is busy the allocation is flagged as an overbook."""
    fac_index = {fid: i for i, fid in enumerate(ctx["facility"])}
    cpt_by_id = ctx["cpt_by_id"]
    res_id, nurses = ctx["res_id"], ctx["nurses"]
    therapy = {ctx["specialty"]["PT"], ctx["specialty"]["OT"]}
    lines_of = defaultdict(list)
    for d in s.rows["appointment_details"]:
        lines_of[d["appointment_id"]].append(d)
    busy = defaultdict(list)                      # (facility, resource, date) -> (start, end, instance)
    nbusy = defaultdict(list)                     # (nurse provider id, date) -> (start, end)
    seq = defaultdict(int)
    stats = defaultdict(int)

    def span(ap):
        ls = lines_of[ap["appointment_id"]]
        a = ap["start_time"].hour * 60 + ap["start_time"].minute
        return a, a + max(30 if ap["specialty_id"] in therapy else 15, sum(x["duration_minutes"] or 15 for x in ls))

    for ap in s.rows["appointment"]:                                                                # nurses who are the appointment's own clinician are busy then
        if ap["provider_id"] in nurses and ap["appointment_status"] != "cancelled":
            nbusy[(ap["provider_id"], ap["appointment_date"])].append(span(ap))

    def take(fid, res, day, a, b):
        count = dict(RESOURCES[fac_index[fid]]).get(res)
        if not count:
            return None, False
        used = busy[(fid, res, day)]
        for inst in range(1, count + 1):
            if all(inst != i or b <= x or a >= y for x, y, i in used):
                used.append((a, b, inst))
                return (f"{res} {inst}" if count > 1 else res), False
        used.append((a, b, (len(used) % count) + 1))
        stats["overbooked"] += 1
        return (f"{res} {used[-1][2]}" if count > 1 else res), True

    def take_nurse(day, a, b):
        for pid in nurses:
            if all(b <= x or a >= y for x, y in nbusy[(pid, day)]):
                nbusy[(pid, day)].append((a, b))
                return pid, False
        pid = nurses[stats["nurse_overbooked"] % len(nurses)]
        nbusy[(pid, day)].append((a, b))
        stats["nurse_overbooked"] += 1
        return pid, True

    for ap in sorted(s.rows["appointment"], key=lambda x: (x["appointment_date"], x["start_time"])):
        ls = sorted(lines_of[ap["appointment_id"]], key=lambda x: x["line_number"])
        codes = [cpt_by_id[x["planned_cpt_code_id"]] for x in ls]
        a, b = span(ap)
        dur = b - a
        fid, day = ap["facility_id"], ap["appointment_date"]
        base = "Treatment table" if ap["specialty_id"] in therapy else "Exam room"
        need = {EQUIP.get(c) or ("Gym station" if c in GYM else None) for c in codes} - {None}
        if need & OWN_ROOM:
            base = None
        res_of = lambda c: EQUIP.get(c) or ("Gym station" if c in GYM else None)
        alloc, got, over = [], {}, False                                                            # alloc: (resource id, start, end, cpt, overbook, role)
        if ap["appointment_status"] != "cancelled":                                                 # a cancelled visit frees its resources
            for res in ([base] if base else []) + sorted(need):
                wa, wb = (a, b) if res == base else (a, a + max(10, sum(x["duration_minutes"] or 15 for x, c in zip(ls, codes) if res_of(c) == res)))
                nm, ov = take(fid, res, day, wa, wb)                     # equipment is held for its own service time, the room for the whole visit
                if nm:
                    got[res] = nm
                    over = over or ov
                    alloc.append((res_id[(fid, nm)], wa, wb, next((c for c in codes if res_of(c) == res), None), ov, RES_TYPE[res] == "equipment" and "equipment" or "room"))
            if ap["provider_id"] in nurses:                                                         # the nurse who runs the visit is held for all of it
                alloc.append((res_id[("RN", ap["provider_id"])], a, b, None, False, "clinical_staff"))
            else:                                                                                   # a nurse assists a procedure, a blood draw, an injection or an ECG
                nl = [(x, c) for x, c in zip(ls, codes) if c in NURSE_CPT or c in PROC or c in ("20610", "20552")]
                if nl:
                    na = a if any(c in PROC or c in ("20610", "20552") for _, c in nl) else a + 10
                    nb = na + max(10, sum(x["duration_minutes"] or 10 for x, _ in nl))
                    pid, ov = take_nurse(day, na, nb)
                    over = over or ov
                    alloc.append((res_id[("RN", pid)], na, nb, nl[0][1], ov, "clinical_staff"))
        for x, c in zip(ls, codes):
            res = res_of(c)
            x["room_or_equipment"] = got.get(res) or got.get(base) or (sorted(got.values())[0] if got else None)
        primary = next((got[x] for x in sorted(need) if x in got and x not in ("Gym station",)), None) or (got.get(base) if base else None) or next(iter(got.values()), None)
        seq[(ap["provider_id"], day)] += 1
        status = {"completed": "completed", "cancelled": "cancelled", "no_show": "no_show"}.get(ap["appointment_status"], "booked")
        slot = s.add("appointment_slot", practice_id=ctx["practice"], provider_id=ap["provider_id"], slot_date=day, start_time=ap["start_time"], duration_minutes=dur, slot_status=status,
                     slot_number=seq[(ap["provider_id"], day)], facility_id=fid, specialty_id=ap["specialty_id"], slot_type=ap["appointment_type"], appointment_id=ap["appointment_id"],
                     created_date=ap["booked_date"], room_or_resource=primary, is_overbook=over)
        stats["slots"] += 1
        for rid, wa, wb, c, ov, role in alloc:
            s.add("resource_allocation", practice_id=ctx["practice"], resource_id=rid, appointment_id=ap["appointment_id"], allocation_date=day, start_time=dt.time(wa // 60, wa % 60),
                  duration_minutes=wb - wa, appointment_slot_id=slot, facility_id=fid, allocation_status={"completed": "used", "no_show": "no_show"}.get(ap["appointment_status"], "booked"),
                  allocation_role=role, cpt_code_id=ctx["cpt"][c] if c else None, provider_id=ap["provider_id"], is_overbook=ov)
            stats["allocations"] += 1
    bill_spec = {x["bill_id"]: x["specialty_id"] for x in s.rows["bill"]}                     # claims carry the specialty of their bill
    for cl in s.rows["claim"]:
        cl["specialty_id"] = bill_spec.get(cl["bill_id"])
    ctx["resource_stats"] = dict(stats)
    return ctx
