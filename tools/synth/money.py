"""Stage 2b: claims, clearinghouse events, payer adjudication, the money ledger, denials, appeals and AR.

Works from the visit records that journey.build_journey leaves in ctx["bills"]. See journey.py for the planted stories.
"""
import datetime as dt
from decimal import Decimal
from collections import defaultdict

from core import TODAY
from journey import q, next_biz, bucket

D = Decimal
PROC_AUTH = {"62323", "64483", "64493", "64635"}
EM_CODES = {"99203", "99204", "99213", "99214", "99395"}
BASE_REASONS = [("16", 30), ("11", 15), ("18", 10), ("252", 15), ("4", 10), ("29", 5), ("97", 15)]


def build_money(s, ctx):
    r = s.rnd
    P, pinfo, pid_to_code = ctx["payer"], ctx["pinfo"], ctx["pid_to_code"]
    cpt, carc, rarc, mod, rate, fee = ctx["cpt"], ctx["carc"], ctx["rarc"], ctx["modifier"], ctx["rate"], ctx["fee"]
    num, staff, prov = ctx["num"], ctx["staff"], ctx["provider"]
    cpt_by_id = ctx["cpt_by_id"]
    pend = []                       # payer / patient payment transactions, grouped into payment rows afterwards
    ar_rows = []
    results = []

    def txn(bd, p, kind, amount, effect, when, party, **kw):
        return s.add("transactions", transaction_number=num("TXN", "txn"), practice_id=ctx["practice"], patient_id=p["id"], bill_detail_id=bd, transaction_type=kind,
                     amount=q(amount), balance_effect=q(effect), transaction_date=when, responsible_party=party, posted_date=when, **kw)

    for b in ctx["bills"]:
        p, code, typ, vd = b["p"], b["code"], b["typ"], b["vd"]
        lines, bdl = b["lines"], b["bdl"]
        payer_id = P[code]
        # the charge posts when charges are entered
        if not b["held"]:
            for bd, (c, u, lvl, mods) in zip(bdl, lines):
                txn(bd, p, "charge", fee[c] * u, fee[c] * u, b["charge_date"], "patient" if typ == "self_pay" else "payer", cpt_code_id=cpt[c], payer_id=payer_id,
                    provider_id=b["tid"])
        # copay collected at the visit
        collected = D(0)
        if typ != "self_pay" and p["copay"] > 0 and r.random() < .85 and not b["held"]:
            collected = p["copay"]
            pend.append(dict(src="patient", payer=None, date=vd, amount=collected, kw=dict(bd=bdl[0], p=p, kind="payment", effect=-collected, party="patient",
                                                                                           when=vd, extra=dict(payment_method="card"))))
        if typ == "self_pay":
            collected = q(b["total"] * D("0.7"))
            if not b["held"]:
                pend.append(dict(src="patient", payer=None, date=vd, amount=collected, kw=dict(bd=bdl[0], p=p, kind="payment", effect=-collected, party="patient",
                                                                                               when=vd, extra=dict(payment_method="card"))))
        rec = dict(b=b, collected=collected, claim=None)
        results.append(rec)
        if typ == "self_pay" or b["held"]:
            continue
        # ---- claim
        sub = next_biz(b["charge_date"], r.randint(1, 2))
        if sub > TODAY:
            continue
        turn = pinfo[code]["turn"]
        stall = sub < TODAY - dt.timedelta(days=35) and r.random() < .02                # S8 no payer response
        reject_tech = r.random() < .04
        paid_date = next_biz(sub, max(7, turn + r.randint(-3, 6)) + (2 if reject_tech else 0))
        adjudicated = (paid_date <= TODAY) and not stall
        # ---- decide each line's outcome
        outcomes = []
        for ln, (c, u, lvl, mods) in enumerate(lines, 1):
            reason = remark = None
            if p["term"] and vd > p["term"]:
                reason = "27"
            elif p["cob"] and b["vi"] <= 2:                                     # the first claims go to the wrong payer; after that it is corrected
                reason = "22"
            elif b["auth"] and b["vi"] + 1 > b["auth_units"]:
                reason = "198"
            elif code == "SYNUHC" and b["poc_missing"] and b["vi"] >= 12:
                reason, remark = "50", "N115"
            elif code == "SYNAET" and c == "97530" and b["has_pair"] and mod["XU"] not in mods and mod["59"] not in mods and vd >= dt.date(2026, 9, 1):
                reason = "97"
            elif code == "SYNHUM" and b.get("no_auth_proc") and c in PROC_AUTH:           # S10 Humana: procedure billed without the prior authorization
                reason = "197"
            elif code == "SYNUHC" and b.get("proc_same_day") and c in EM_CODES and mod["25"] not in mods and vd >= dt.date(2026, 7, 1):     # S12 UHC: no modifier 25
                reason = "4"
            outcomes.append(reason)
        if not any(outcomes) and r.random() < .045:                                    # ordinary denial, one reason for the claim
            reason = r.choices([c for c, _ in BASE_REASONS], [w for _, w in BASE_REASONS])[0]
            outcomes = [reason if i == 0 or reason in ("18", "252", "16") else None for i in range(len(lines))]
        claim = s.add("claim", claim_number=num("CLM", "clm"), practice_id=ctx["practice"], payer_id=payer_id, patient_id=p["id"], billing_provider_id=prov[b["thera"]],
                      service_date_from=vd, submitted_date=sub, total_charge=b["total"], claim_status="accepted", rendering_provider_id=b["tid"], facility_id=b["fac"],
                      place_of_service_id=ctx["pos"]["11"], coverage_id=p["cov"], claim_sequence="primary", frequency_code="1", bill_id=b["bill"], encounter_id=b["enc"],
                      principal_diagnosis_code_id=ctx["icd"][b["dxs"][0]], authorization_id=b["auth"], claim_type="professional", signature_on_file="Y",
                      batch_control_number=f"B{sub:%y%m%d}", referral_provider_id=None)
        rec["claim"] = claim
        crow = s.rows["claim"][-1]
        cdl, tot = [], dict(paid=D(0), adj=D(0), denied=D(0), pr=D(0))
        line_info = []
        for i, (bd, (c, u, lvl, mods), reason) in enumerate(zip(bdl, lines, outcomes), 1):
            charge = q(fee[c] * u)
            contract = q(rate[(code, c)] * u)
            allowed = contract
            if code == "SYNBCBS" and c == "97140" and vd >= dt.date(2026, 8, 1):
                allowed = q(contract * D("0.88"))                                          # S2 underpayment against the contract
            if mod["CQ"] in mods:
                allowed = q(allowed * D("0.85"))
            if b.get("np") and typ in ("medicare", "medicare_advantage"):                      # nurse practitioners are paid 85% of the physician rate
                allowed = q(allowed * D("0.85"))
            line_info.append(dict(bd=bd, c=c, u=u, mods=mods, charge=charge, contract=contract, allowed=allowed, reason=reason))
        first_pay = True
        for li in line_info:
            if li["reason"]:
                li["pr"] = D(0)
            elif typ == "medicare":
                li["pr"] = q(li["allowed"] * D("0.2"))
            else:
                li["pr"] = min(p["copay"], li["allowed"]) if first_pay else D(0)
                first_pay = False
        for li in line_info:
            ln_status = "pending"
            li.update(paid=D(0), contractual=D(0), denied=D(0), allowed_rec=None, fate=None)
            if adjudicated:
                if li["reason"]:
                    li["denied"] = li["charge"]
                    ln_status = "denied"
                else:
                    li["paid"] = li["allowed"] - li["pr"]
                    li["contractual"] = li["charge"] - li["allowed"]
                    li["allowed_rec"] = li["allowed"]
                    ln_status = "paid"
            li["status"] = ln_status
        # ---- denial fates (what happened after the payer said no)
        denial_ids = {}
        for li in line_info:
            if not li["reason"] or not adjudicated:
                continue
            reason = li["reason"]
            age = (TODAY - paid_date).days
            fixable = {"27": .10, "22": .55, "198": .30}.get(reason, .55)
            if age > 30:
                fate = r.choices(["recovered", "written_off", "open"], [fixable, .15 if reason not in ("27",) else .5, max(.0, 1 - fixable - .15)])[0]
            else:
                fate = "appealed" if r.random() < .3 else "open"
            li["fate"] = fate
            if fate in ("recovered", "written_off"):
                li["resolved"] = next_biz(paid_date, r.randint(14, 45))
                if li["resolved"] > TODAY:
                    li["fate"], li["resolved"] = "appealed", None
            if li["fate"] == "recovered":
                li["paid"] = li["allowed"] - li["pr"]
                li["contractual"] = li["charge"] - li["allowed"]
                li["allowed_rec"] = li["allowed"]
                li["denied"] = D(0)
                li["status"] = "paid"
            elif li["fate"] == "written_off":
                li["contractual"] = li["charge"]
                li["denied"] = D(0)
                li["status"] = "written_off"
        for i, li in enumerate(line_info, 1):
            cd = s.add("claim_details", claim_id=claim, line_number=i, practice_id=ctx["practice"], payer_id=payer_id, patient_id=p["id"], billing_provider_id=prov[b["thera"]],
                       cpt_code_id=cpt[li["c"]], units=D(li["u"]), charge_amount=li["charge"], line_status=li["status"], paid_amount=q(li["paid"]), service_date=vd,
                       modifier_1_id=li["mods"][0] if li["mods"] else None, modifier_2_id=li["mods"][1] if len(li["mods"]) > 1 else None, diagnosis_pointers="1,2" if len(b["dxs"]) > 1 else "1",
                       primary_diagnosis_code_id=ctx["icd"][b["dxs"][0]], rendering_provider_id=b["tid"], allowed_amount=li["allowed_rec"],
                       patient_responsibility=q(li["pr"]) if adjudicated else None, contractual_adjustment=q(li["contractual"]) if adjudicated else None,
                       denied_amount=q(li["denied"]) if adjudicated else None, expected_allowed=li["contract"], bill_detail_id=li["bd"],
                       primary_denial_reason_id=carc[li["reason"]] if li["reason"] and adjudicated else None, line_control_number=f"{claim}-{i}")
            li["cd"] = cd
            tot["paid"] += li["paid"]; tot["adj"] += li["contractual"]; tot["denied"] += li["denied"]; tot["pr"] += li["pr"] if adjudicated else 0
        # ---- ledger and denial rows
        if adjudicated:
            for li in line_info:
                if li["reason"]:
                    reason = li["reason"]
                    dn = s.add("denial", claim_id=claim, claim_detail_id=li["cd"], practice_id=ctx["practice"], patient_id=p["id"], payer_id=payer_id, denial_date=paid_date,
                               denied_amount=li["charge"], adjustment_reason_id=carc[reason], denial_status={"recovered": "resolved", "written_off": "written_off", "appealed": "in_appeal", "open": "open"}[li["fate"]],
                               bill_detail_id=li["bd"], group_code="PR" if reason in ("1", "2", "3") else "CO", clock_start_date=paid_date,
                               appeal_deadline=paid_date + dt.timedelta(days=pinfo[code]["appeal"]), upstream_stage=s.rows["adjustment_reason"][carc[reason] - 1]["upstream_stage"],
                               is_preventable=s.rows["adjustment_reason"][carc[reason] - 1]["is_preventable_default"], owner_role=s.rows["adjustment_reason"][carc[reason] - 1]["owner_role"],
                               reason_category=s.rows["adjustment_reason"][carc[reason] - 1]["reason_category"], is_technical=s.rows["adjustment_reason"][carc[reason] - 1]["is_technical"],
                               is_repeat=False, denial_count_on_line=1, cpt_code_id=cpt[li["c"]], provider_id=b["tid"], is_claim_level=False, units_denied=D(li["u"]),
                               authorization_id=b["auth"], resolved_date=li.get("resolved"), outcome={"recovered": "overturned", "written_off": "written_off", "appealed": "pending", "open": "pending"}[li["fate"]],
                               recovered_amount=q(li["allowed"] - li["pr"]) if li["fate"] == "recovered" else D(0))
                    li["denial"] = dn
                    rk = {"50": "N115", "198": "N130", "197": "N130", "16": "MA130", "252": "MA130", "4": "MA130", "11": "MA130", "18": "N522", "22": "N479", "27": "N130", "29": "N130", "97": "M86"}[reason]
                    s.add("denial_details", denial_id=dn, detail_seq=1, detail_type="CARC", adjustment_reason_id=carc[reason], remark_code_id=rarc[rk],
                          group_code="CO", reason_amount=li["charge"], is_amount_allocated=True, is_primary=True, claim_detail_id=li["cd"], denial_date=paid_date)
                    txn(li["bd"], p, "denial", li["charge"], 0, paid_date, "payer", claim_id=claim, claim_detail_id=li["cd"], payer_id=payer_id, denial_id=dn,
                        adjustment_reason_id=carc[reason], group_code="CO", cpt_code_id=cpt[li["c"]], provider_id=b["tid"])
                    if li["fate"] == "appealed" or (li["fate"] == "recovered" and r.random() < .8):
                        appeal_date = next_biz(paid_date, r.randint(5, 20))
                        if appeal_date <= TODAY:
                            ok = li["fate"] == "recovered"
                            s.add("appeal", appeal_number=num("APL", "apl"), denial_id=dn, appeal_level="first", appeal_status="won" if ok else "submitted", clock_start_date=paid_date,
                                  deadline_date=paid_date + dt.timedelta(days=pinfo[code]["appeal"]), claim_id=claim, submitted_date=appeal_date, submission_channel="portal",
                                  amount_disputed=li["charge"], evidence_count=r.randint(1, 4), practice_id=ctx["practice"], patient_id=p["id"], payer_id=payer_id,
                                  decision_date=li.get("resolved") if ok else None, payer_decision="overturned" if ok else None, is_overturned=True if ok else None,
                                  recovered_amount=q(li["allowed"] - li["pr"]) if ok else None)
                if not li["reason"] or li["fate"] == "recovered":
                    when = paid_date if not li["reason"] else li["resolved"]
                    if li["paid"] > 0:
                        pend.append(dict(src="payer", payer=payer_id, date=when, amount=li["paid"], kw=dict(
                            bd=li["bd"], p=p, kind="payment", effect=-li["paid"], party="payer", when=when, extra=dict(
                                claim_id=claim, claim_detail_id=li["cd"], payer_id=payer_id, cpt_code_id=cpt[li["c"]], provider_id=b["tid"], payment_method="eft",
                                denial_id=li.get("denial")))))
                    if li["contractual"] > 0:
                        txn(li["bd"], p, "adjustment", li["contractual"], -li["contractual"], when, "payer", transaction_subtype="contractual", claim_id=claim,
                            claim_detail_id=li["cd"], payer_id=payer_id, adjustment_reason_id=carc["45"], group_code="CO", cpt_code_id=cpt[li["c"]])
                    if li["pr"] > 0:
                        txn(li["bd"], p, "adjustment", li["pr"], 0, when, "patient", transaction_subtype="patient_responsibility", claim_id=claim, claim_detail_id=li["cd"],
                            payer_id=payer_id, adjustment_reason_id=carc["3" if typ != "medicare" else "2"], group_code="PR", cpt_code_id=cpt[li["c"]])
                elif li["fate"] == "written_off":
                    txn(li["bd"], p, "adjustment", li["charge"], -li["charge"], li["resolved"], "payer", transaction_subtype="write_off", claim_id=claim, claim_detail_id=li["cd"],
                        payer_id=payer_id, approved_by=staff["B03"], approved_date=li["resolved"], cpt_code_id=cpt[li["c"]])
        # ---- claim row totals and clearinghouse history
        pr_total = tot["pr"]
        outstanding_patient = max(D(0), (pr_total if adjudicated else sum((li["pr"] for li in line_info), D(0))) - rec["collected"])
        denied_open = sum((li["charge"] for li in line_info if li.get("fate") in ("open", "appealed")), D(0))
        pay_part = D(0) if adjudicated else b["total"]
        crow.update(paid_amount=q(tot["paid"]), patient_responsibility=q(pr_total), adjusted_amount=q(tot["adj"]), denied_amount=q(denied_open),
                    balance=q(denied_open + outstanding_patient + pay_part), last_payment_date=paid_date if tot["paid"] > 0 else None, last_status_date=paid_date if adjudicated else sub,
                    payer_claim_number=f"PCN{claim:08d}" if not stall else None)
        statuses = [li["status"] for li in line_info]
        if adjudicated:
            paid_any = any(li["paid"] > 0 for li in line_info)
            open_den = any(li.get("fate") in ("open", "appealed") for li in line_info)
            crow["claim_status"] = ("partial" if paid_any else "denied") if open_den else ("paid" if paid_any else "written_off")
        elif stall:
            crow["claim_status"] = "no_response"
        ev = []
        ack = next_biz(sub, 1)
        ev.append(("submitted", sub, "submitted", "837", "clearinghouse"))
        ev.append(("acknowledged_999", ack, "acknowledged", "A1", "clearinghouse"))
        if reject_tech:
            ev.append(("rejected_277ca", next_biz(sub, 2), "rejected", "A3", "clearinghouse"))
            ev.append(("resubmitted", next_biz(sub, 3), "submitted", "837", "clearinghouse"))
            ev.append(("accepted_277ca", next_biz(sub, 4), "accepted", "A1", "clearinghouse"))
        else:
            ev.append(("accepted_277ca", next_biz(sub, 2), "accepted", "A1", "clearinghouse"))
        if stall:
            ev.append(("status_check_277", next_biz(sub, 35), "pending", "P1", "payer_api"))
        if adjudicated:
            ev.append(("remit_835", paid_date, crow["claim_status"], "F1" if crow["claim_status"] == "paid" else "F2", "clearinghouse"))
        for seq_i, (et, ed, st, cat, ch) in enumerate(ev, 1):
            if ed > TODAY:
                continue
            is_rej = et == "rejected_277ca"
            s.add("claim_status_history", claim_id=claim, event_type=et, event_date=ed, status_after=st, practice_id=ctx["practice"], payer_id=payer_id, patient_id=p["id"],
                  event_ts=dt.datetime.combine(ed, dt.time(9, 30)), response_sequence=seq_i, status_category=cat, is_rejection=is_rej,
                  rejection_reason=r.choice(["billing_npi_mismatch", "missing_info"]) if is_rej else None, rejection_category="technical" if is_rej else None,
                  is_technical=is_rej, owner_role="biller" if is_rej else None, channel=ch, payer_claim_number=crow["payer_claim_number"],
                  billing_provider_id=prov[b["thera"]], reported_paid_amount=q(tot["paid"]) if et == "remit_835" else None)
        # the bill reflects its claim
        brow = next(x for x in s.rows["bill"] if x["bill_id"] == b["bill"])
        brow.update(bill_status={"paid": "paid", "denied": "denied", "partial": "partial", "written_off": "closed"}.get(crow["claim_status"], "claimed"), claims_created=1,
                    latest_claim_status=crow["claim_status"], first_claim_submitted_date=sub, ready_to_bill_date=b["charge_date"])
        rec.update(claim=claim, line_info=line_info, adjudicated=adjudicated, sub=sub, stall=stall, outstanding_patient=outstanding_patient, crow=crow)

    # ---- group the cash into payment rows; a few payer remits are never posted (S5)
    groups = defaultdict(list)
    for sp in pend:
        groups[(sp["src"], sp["payer"], sp["date"])].append(sp)
    payer_keys = [k for k, v in groups.items() if k[0] == "payer" and TODAY - dt.timedelta(days=30) <= k[2] <= TODAY - dt.timedelta(days=5) and sum(x["amount"] for x in v) > 300]
    unposted = set(r.sample(payer_keys, min(8, len(payer_keys))))
    ctx["unposted_payments"] = []
    for key in sorted(groups, key=lambda k: (k[2], str(k[1]))):
        items = groups[key]
        amount = sum((x["amount"] for x in items), D(0))
        posted = key not in unposted
        pay = s.add("payment", payment_number=num("PAY", "pay"), practice_id=ctx["practice"], payment_source=key[0], payment_date=key[2], payment_amount=q(amount),
                    payment_method="eft" if key[0] == "payer" else "card", payer_id=key[1], payment_type="era" if key[0] == "payer" else "copay", received_date=key[2],
                    posted_date=key[2] if posted else None, credit_debit="C", has_remittance=key[0] == "payer", claim_count=len(items),
                    posted_amount=q(amount) if posted else D(0), unapplied_amount=D(0) if posted else q(amount), plb_amount=D(0), reconciles=posted, is_void=False)
        if not posted:
            ctx["unposted_payments"].append(pay)
            continue
        for x in items:
            k = x["kw"]
            extra = dict(k["extra"])
            extra["payment_id"] = pay
            s.add("transactions", transaction_number=num("TXN", "txn"), practice_id=ctx["practice"], patient_id=k["p"]["id"], bill_detail_id=k["bd"], transaction_type=k["kind"],
                  amount=q(abs(k["effect"])), balance_effect=q(k["effect"]), transaction_date=k["when"], responsible_party=k["party"], posted_date=k["when"], **extra)

    # ---- AR snapshot as of today (payer-owned and patient-owned balances)
    run = 1
    for rec in results:
        b = rec["b"]
        if not rec.get("claim") and not b["typ"] == "self_pay":
            continue
        p, code = b["p"], b["code"]
        if b["held"]:
            continue
        if b["typ"] == "self_pay":
            bal = q(b["total"] - rec["collected"])
            if bal > 0:
                days = (TODAY - b["vd"]).days
                s.add("ar", as_of_date=TODAY, snapshot_type="daily", snapshot_run_id=run, bill_id=b["bill"], balance_owner="patient", balance=bal, practice_id=ctx["practice"],
                      patient_id=p["id"], aging_date=b["vd"], days_outstanding=days, aging_bucket=bucket(days), aging_basis="service_date", payer_id=None, service_date=b["vd"],
                      provider_id=b["tid"], expected_collectible=bal, is_in_denial=False, is_credit=False)
            continue
        crow = rec["crow"]
        payer_out = q(crow["balance"] - rec["outstanding_patient"]) if rec["adjudicated"] else q(sum((li["contract"] for li in rec["line_info"]), D(0)))
        if payer_out > 0:
            days = (TODAY - rec["sub"]).days
            fil = dt.timedelta(days=ctx["pinfo"][code]["filing"])
            s.add("ar", as_of_date=TODAY, snapshot_type="daily", snapshot_run_id=run, bill_id=b["bill"], balance_owner="payer", balance=payer_out, practice_id=ctx["practice"],
                  patient_id=p["id"], aging_date=rec["sub"], days_outstanding=days, aging_bucket=bucket(days), aging_basis="submitted_date", claim_id=rec["claim"],
                  payer_id=P[code], claim_status=crow["claim_status"], claim_sequence="primary", submitted_date=rec["sub"], expected_collectible=payer_out,
                  last_payment_date=crow.get("last_payment_date"), last_activity_date=crow.get("last_status_date"),
                  days_since_activity=(TODAY - crow["last_status_date"]).days if crow.get("last_status_date") else None, open_denied_amount=crow["denied_amount"],
                  is_in_denial=crow["denied_amount"] > 0, is_credit=False, filing_deadline=b["vd"] + fil, provider_id=b["tid"], service_date=b["vd"],
                  next_action_date=next_biz(TODAY, 2))
        if rec["outstanding_patient"] > 0:
            days = (TODAY - b["vd"]).days
            s.add("ar", as_of_date=TODAY, snapshot_type="daily", snapshot_run_id=run, bill_id=b["bill"], balance_owner="patient", balance=q(rec["outstanding_patient"]),
                  practice_id=ctx["practice"], patient_id=p["id"], aging_date=b["vd"], days_outstanding=days, aging_bucket=bucket(days), aging_basis="service_date",
                  claim_id=rec["claim"], payer_id=P[code], service_date=b["vd"], provider_id=b["tid"], expected_collectible=q(rec["outstanding_patient"]),
                  is_in_denial=False, is_credit=False)
    ctx["results"] = results
    return ctx
