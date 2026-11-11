"""Load stage 2 for the Synthea data into krisnnai_r2 (AWS RDS): appointments, encounters, diagnoses, charge lines, bills, claims and the ledger.

Usage: python tools/synthea/load_clinical_billing.py --reset      (empties only the stage 2 tables first; run load_ref_people.py before)

What comes from Synthea: every visit, its date, patient, provider, facility, payer, diagnoses and procedures, and whether its claim was closed or still billed.
What is derived here: the billing codes (crosswalk.py), the fee (one fee schedule), and the money. Synthea's own ledger does not separate payer and patient money
(a copay and an insurer's check look alike), so the allowed amount, payer payment, contractual adjustment and patient share are computed from payer ratios below.
Denials, appeals and remittance detail are not in Synthea and are added by the generator later.
"""
import collections
import datetime as dt
import pickle
import sys
import time
from decimal import Decimal, ROUND_HALF_UP

sys.path.insert(0, __import__("pathlib").Path(__file__).resolve().parent.as_posix())
from crosswalk import ENC, PROC, ICD, FEE, POS  # noqa: E402
from r2load import Loader, connect, reader, date, WORK, NOW  # noqa: E402

TODAY = NOW.date()
D = Decimal
q2 = lambda x: D(x).quantize(D("0.01"), rounding=ROUND_HALF_UP)
ALLOWED = {"MEDICARE": D("0.55"), "MEDICAID": D("0.42"), "DUAL": D("0.42"), "HUMANA": D("0.62"), "BCBS": D("0.72"), "UHC": D("0.70"), "AETNA": D("0.68"), "CIGNA": D("0.66"), "ANTHEM": D("0.70")}
TURN = {"MEDICARE": 14, "MEDICAID": 28}
COPAY_PAYERS = {"HUMANA", "BCBS", "UHC", "AETNA", "CIGNA", "ANTHEM"}
APPT_CLASS = {"ambulatory", "wellness", "outpatient", "urgentcare", "virtual"}
TABLES = ["appointment", "encounter", "encounter_diagnosis", "encounter_line", "bill", "bill_line", "claim", "claim_diagnosis", "claim_line", "ledger_entry"]
BATCH = 15000
FROM_DAY = dt.date(2023, 11, 6)         # three years of history; Synthea exports whole lifetimes, and billing from decades ago is not realistic
DERIVED_DX = {"Z0000": "Encounter for general adult medical examination without abnormal findings", "Z00129": "Encounter for routine child health examination without abnormal findings",
              "R69": "Illness, unspecified"}
PRENATAL = {"424619006", "424441002"}


def when(s):
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None)


def main(reset):
    conn = connect()
    cur = conn.cursor()
    if reset:
        cur.execute("TRUNCATE " + ",".join(f'"{t}"' for t in TABLES) + " CASCADE")
        conn.commit()
    else:
        cur.execute('select count(*) from "encounter"')
        assert cur.fetchone()[0] == 0, "encounters already loaded; run with --reset"
    st = pickle.load(open(WORK / "idmaps.pkl", "rb"))
    M = st["maps"]
    L = Loader(conn)
    L.maps, L.next = M, st["next"]
    for t in TABLES:
        L.next[t] = 0
    code_of = {v: k for k, v in M["payer"].items() if k in ALLOWED or k == "SELF"}
    self_id = M["payer"]["SELF"]
    # coverage index per patient
    cur.execute("select patient_id, payer_id, coverage_id, effective_date, termination_date from coverage where coverage_order = 1")
    cov = collections.defaultdict(list)
    for p, pay, cid, a, b in cur.fetchall():
        cov[p].append((pay, cid, a, b or dt.date(9999, 12, 31)))
    # diagnoses Synthea does not give: a preventive code for check-ups, pregnancy for prenatal visits, "illness, unspecified" for the rest. Rows using them are marked derived_default.
    new = [c for c in DERIVED_DX if c not in M["icd"]]
    for c in new:
        M["icd"][c] = L.key("diagnosis_code")
    L.rows("diagnosis_code", [dict(diagnosis_code_id=M["icd"][c], icd10_code=c, effective_from=dt.date(2019, 1, 1), effective_to=dt.date(9999, 12, 31), description=DERIVED_DX[c], is_billable=True,
                                   is_unrecognized=False) for c in new])
    conn.commit()
    # diagnoses and procedures per encounter, first claim status per encounter
    dx, procs, status = collections.defaultdict(list), collections.defaultdict(list), {}
    for r in reader("conditions.csv"):
        c = ICD.get(r["CODE"])
        if c and M["icd"][c[0]] not in dx[r["ENCOUNTER"]]:
            dx[r["ENCOUNTER"]].append(M["icd"][c[0]])
    for r in reader("procedures.csv"):
        if r["CODE"] in PROC:
            procs[r["ENCOUNTER"]].append(PROC[r["CODE"]][0])
    for r in reader("claims.csv"):
        status.setdefault(r["APPOINTMENTID"], r["STATUS1"])
    cur.execute("select patient_id, birth_year from patient")
    birth = dict(cur.fetchall())
    pat_age = lambda e: 2026 - birth[M["patient"][e["PATIENT"]]]
    print(f"diagnoses for {len(dx)} encounters, procedures for {len(procs)}, claim status for {len(status)}")

    buf = {t: [] for t in TABLES}
    stats = collections.Counter()
    t0 = time.time()

    def flush():
        for t in TABLES:
            if buf[t]:
                L.rows(t, buf[t])
                stats[t] += len(buf[t])
                buf[t] = []
        conn.commit()

    encs = sorted((r for r in reader("encounters.csv") if FROM_DAY <= date(r["START"]) <= TODAY), key=lambda r: (r["START"], r["Id"]))
    print(f"{len(encs)} encounters between {FROM_DAY} and {TODAY}")
    for i, e in enumerate(encs, 1):
        pat = M["patient"][e["PATIENT"]]
        start = when(e["START"])
        day = start.date()
        payer_uuid = e["PAYER"]
        pay_id = M["payer"].get(payer_uuid, self_id)
        code = code_of[pay_id]
        cls = e["ENCOUNTERCLASS"]
        pos = M["pos"][POS[cls][0]]
        fac, prov = M["facility"][e["ORGANIZATION"]], M["provider"][e["PROVIDER"]]
        cid = next((c for p, c, a, b in cov[pat] if p == pay_id and a <= day <= b), None)
        mins = max(5, min(480, int((when(e["STOP"]) - start).total_seconds() // 60))) if e["STOP"] else 20
        eid = L.key("encounter")
        appt = None
        if cls in APPT_CLASS:
            appt = L.key("appointment")
            buf["appointment"].append(dict(appointment_id=appt, appointment_number=f"APT-{appt}", practice_id=1, patient_id=pat, appointment_date=day, appointment_status="completed", provider_id=prov, payer_id=pay_id,
                                           coverage_id=cid, facility_id=fac, start_time=start.time().replace(microsecond=0), booked_date=day - dt.timedelta(days=7), appointment_type=cls))
        diags, derived = dx.get(e["Id"], [])[:12], False
        if not diags:
            derived = True
            kid = e["CODE"] == "410620009" or (pat_age(e) < 18)
            diags = [M["icd"]["Z3400"] if e["CODE"] in PRENATAL else M["icd"]["Z00129"] if kid and e["CODE"] in ("410620009", "162673000", "185349003") else M["icd"]["Z0000"] if e["CODE"] in ("162673000", "185349003") else M["icd"]["R69"]]
        buf["encounter"].append(dict(encounter_id=eid, encounter_number=f"ENC-{eid}", practice_id=1, patient_id=pat, encounter_date=day, rendering_provider_id=prov, encounter_status="completed", appointment_id=appt,
                                     payer_id=pay_id, coverage_id=cid, facility_id=fac, place_of_service_id=pos, specialty_id=1, encounter_type=cls, visit_minutes=mins, note_status="signed",
                                     note_signed_date=min(day + dt.timedelta(days=1), TODAY), signature_lag_days=1, charge_status="charged", coding_status="coded", principal_diagnosis_code_id=diags[0] if diags else None))
        for seq, d in enumerate(diags, 1):
            buf["encounter_diagnosis"].append(dict(encounter_diagnosis_id=L.key("encounter_diagnosis"), encounter_id=eid, diagnosis_sequence=seq, diagnosis_code_id=d, is_principal=seq == 1, diagnosis_role="derived_default" if derived else None, practice_id=1, patient_id=pat))
        codes = ([ENC[e["CODE"]][0]] if e["CODE"] in ENC else []) + procs.get(e["Id"], [])
        lines = collections.OrderedDict()
        for c in codes:
            lines[c] = lines.get(c, 0) + 1
        if not lines:
            stats["encounters without a billable code"] += 1
            if i % BATCH == 0:
                flush()
            continue
        eline = {}
        for n, (c, u) in enumerate(lines.items(), 1):
            eline[c] = L.key("encounter_line")
            buf["encounter_line"].append(dict(encounter_line_id=eline[c], encounter_id=eid, line_number=n, practice_id=1, patient_id=pat, payer_id=pay_id, provider_id=prov, specialty_id=1, cpt_code_id=M["cpt"][c], units=u,
                                              service_date=day, rendering_provider_id=prov, diagnosis_1_id=diags[0] if diags else None, procedure_documented=True, line_status="coded", expected_charge=q2(FEE[c] * u)))
        total = sum((q2(FEE[c] * u) for c, u in lines.items()), D(0))
        insured = code != "SELF"
        entered = min(day + dt.timedelta(days=1), TODAY)
        submitted = min(day + dt.timedelta(days=2), TODAY)
        paid_day = submitted + dt.timedelta(days=TURN.get(code, 21) + (i % 7))
        settled = insured and status.get(e["Id"], "CLOSED") == "CLOSED" and paid_day <= TODAY
        ratio = ALLOWED.get(code)
        sp_day = entered + dt.timedelta(days=10 + i % 25)
        selfpaid = (not insured) and i % 5 < 3 and sp_day <= TODAY                  # 60% of self-pay bills are paid in full by the patient
        done = settled or selfpaid
        bid = L.key("bill")
        cl = L.key("claim") if insured else None
        exp_allowed = q2(total * ratio) if insured else None
        buf["bill"].append(dict(bill_id=bid, bill_number=f"BILL-{bid}", practice_id=1, patient_id=pat, encounter_id=eid, service_date=day, charge_entered_date=entered, bill_status="paid" if done else "open",
                                bill_type="insurance" if insured else "self_pay", total_billed=total, billing_provider_id=prov, rendering_provider_id=prov, specialty_id=1, payer_id=pay_id, coverage_id=cid, facility_id=fac,
                                place_of_service_id=pos, claims_created=1 if insured else 0, latest_claim_status=("paid" if settled else "submitted") if insured else None, expected_allowed=exp_allowed))
        paid_t = adj_t = pr_t = D(0)
        first = True
        for n, (c, u) in enumerate(lines.items(), 1):
            billed = q2(FEE[c] * u)
            bl = L.key("bill_line")
            lstat = "paid" if done else "open"
            allowed = q2(billed * ratio) if insured else None
            pr = min(D(25), allowed) if (insured and settled and code in COPAY_PAYERS and first and c in {x[0] for x in ENC.values()}) else D(0)
            first = False
            paid = (allowed - pr) if settled else D(0)
            adj = (billed - allowed) if settled else D(0)
            buf["bill_line"].append(dict(bill_line_id=bl, bill_id=bid, line_number=n, practice_id=1, patient_id=pat, payer_id=pay_id, provider_id=prov, specialty_id=1, cpt_code_id=M["cpt"][c], units=u,
                                         fee_per_unit=q2(FEE[c]), billed_amount=billed, line_status=lstat, service_date=day, diagnosis_1_id=diags[0] if diags else None, rendering_provider_id=prov,
                                         encounter_line_id=eline[c], charge_entered_date=entered, expected_allowed=allowed))
            who = "payer" if insured else "patient"

            def led(kind, amount, effect, party, sub=None, group=None, tx_day=entered, **kw):
                tid = L.key("ledger_entry")
                buf["ledger_entry"].append(dict(ledger_entry_id=tid, transaction_number=f"TXN-{tid}", practice_id=1, patient_id=pat, bill_line_id=bl, transaction_type=kind, amount=amount, balance_effect=effect,
                                                transaction_date=tx_day, responsible_party=party, posted_date=tx_day, payer_id=pay_id, provider_id=prov, specialty_id=1, cpt_code_id=M["cpt"][c], transaction_subtype=sub,
                                                group_code=group, claim_id=cl, claim_line_id=clid, **kw))
            clid = None
            if insured:
                clid = L.key("claim_line")
                buf["claim_line"].append(dict(claim_line_id=clid, claim_id=cl, line_number=n, practice_id=1, payer_id=pay_id, patient_id=pat, billing_provider_id=prov, specialty_id=1, cpt_code_id=M["cpt"][c], units=u,
                                              charge_amount=billed, line_status=lstat, paid_amount=paid if settled else D(0), service_date=day, diagnosis_pointers="1", primary_diagnosis_code_id=diags[0] if diags else None,
                                              rendering_provider_id=prov, allowed_amount=allowed if settled else None, patient_responsibility=pr if settled else None, contractual_adjustment=adj if settled else None,
                                              denied_amount=D(0) if settled else None, expected_allowed=allowed, bill_line_id=bl, line_control_number=f"L{clid}"))
            led("charge", billed, billed, who)
            if selfpaid:
                led("payment", billed, -billed, "patient", tx_day=sp_day, payment_method="card")
            if settled:
                if paid > 0:
                    led("payment", paid, -paid, "payer", tx_day=paid_day, payment_method="eft")
                if adj > 0:
                    led("adjustment", adj, -adj, "payer", sub="contractual", group="CO", tx_day=paid_day)
                if pr > 0:
                    led("adjustment", pr, D(0), "patient", sub="patient_responsibility", group="PR", tx_day=paid_day)
            paid_t += paid
            adj_t += adj
            pr_t += pr
        if insured:
            buf["claim"].append(dict(claim_id=cl, claim_number=f"CLM-{cl}", practice_id=1, payer_id=pay_id, patient_id=pat, billing_provider_id=prov, service_date_from=day, service_date_to=day, submitted_date=submitted,
                                     total_charge=total, claim_status="paid" if settled else "submitted", rendering_provider_id=prov, facility_id=fac, place_of_service_id=pos, specialty_id=1, coverage_id=cid,
                                     claim_sequence="primary", frequency_code="1", bill_id=bid, encounter_id=eid, principal_diagnosis_code_id=diags[0] if diags else None, paid_amount=paid_t if settled else D(0),
                                     patient_responsibility=pr_t if settled else D(0), adjusted_amount=adj_t if settled else D(0), denied_amount=D(0), balance=pr_t if settled else total,
                                     last_payment_date=paid_day if settled and paid_t > 0 else None, last_status_date=paid_day if settled else submitted))
            for seq, d in enumerate(diags, 1):
                buf["claim_diagnosis"].append(dict(claim_diagnosis_id=L.key("claim_diagnosis"), claim_id=cl, diagnosis_sequence=seq, diagnosis_code_id=d, is_principal=seq == 1, practice_id=1, payer_id=pay_id, patient_id=pat))
        if i % BATCH == 0:
            flush()
            print(f"  {i}/{len(encs)} encounters, {int(time.time() - t0)}s, rows so far {sum(v for k, v in stats.items() if k in TABLES)}", flush=True)
    flush()
    cur.execute("""UPDATE patient p SET first_seen_date = s.lo, last_seen_date = s.hi FROM (SELECT patient_id, min(encounter_date) lo, max(encounter_date) hi FROM encounter GROUP BY 1) s WHERE s.patient_id = p.patient_id""")
    conn.commit()
    L.save_maps()
    print("loaded:", dict(stats))
    conn.close()


if __name__ == "__main__":
    main("--reset" in sys.argv)
