"""Claim-level agent log as an Excel workbook, plus agent performance by payer, provider, facility and specialty.
Works for the live system and the replay (any database with the canonical agent tables).

    build_workbook(fetch, traces, basis, start, end, touched_only=True, plan=None, label="", filters=None) -> (bytes, info)
    performance_view(fetch, basis, start, end, touched_only, filters, dim) -> dict      (the same numbers as the workbook's performance sheets, for the screen)
      fetch(sql, params) -> list of dict rows        traces: {decision_id: trace dict}      plan(sql, params) -> {"tables": [...], "columns": [...]} (optional)
      filters: {"payer": id, "provider": id, "practice": id, "facility": id, "specialty": id}  (any may be missing)
Period basis:  "service"      the claim's date of service
               "transaction"  any ledger transaction or payer/clearinghouse event on the claim dated inside the period
               "activity"     any agent decision on the claim made inside the period
"""
import datetime as dt
import io
from collections import defaultdict

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

MAXCLAIMS = 30000
CELL = 32000
NAMES = {"A1": "Gatekeeper", "A2": "Permit Clerk", "A3": "Note Chaser", "A4": "Code Whisperer", "A5": "Mirror", "A6": "Courier", "A7": "Hunter", "A8": "Advocate", "A9": "Coach", "A10": "Auditor",
         "A11": "Bookkeeper", "A12": "Concierge", "A13": "Credentialing", "A14": "Captain", "A15": "Detective"}
RAISED = {"flag", "hold", "route", "suggest", "proposed"}
DIMS = [("Payer", "payer_name"), ("Provider", "provider_name"), ("Facility", "facility_name"), ("Specialty", "specialty_name"), ("Practice", "practice_name"), ("All claims", "all")]
FILTER_COL = {"payer": "c.payer_id", "provider": "c.rendering_provider_id", "practice": "c.practice_id", "facility": "c.facility_id", "specialty": "c.specialty_id"}


def _s(v):
    if v is None:
        return None
    if isinstance(v, (dt.datetime, dt.date)):
        return v
    if hasattr(v, "as_tuple"):
        return float(v)
    if isinstance(v, (list, dict)):
        return str(v)
    if isinstance(v, memoryview):
        return None
    if isinstance(v, str):
        return v[:CELL]
    return v


def _ts(v):
    if isinstance(v, dt.datetime):
        return v.replace(tzinfo=None)
    if isinstance(v, dt.date):
        return dt.datetime.combine(v, dt.time(0, 0))
    return None


def _f(x):
    return float(x) if x is not None else 0.0


def norm_trace(tr, plan):
    """One shape for the live traces and the replay traces."""
    if not tr:
        return None
    reads = []
    for r in tr.get("reads", []):
        sql = r.get("sql")
        params = r.get("params", [])
        tables, cols = r.get("plan_tables"), r.get("plan_columns")
        if tables is None and plan and sql:
            try:
                p = plan(sql, params)
                tables, cols = p["tables"], p["columns"]
            except Exception:
                tables = cols = None
        if tables is None and r.get("table"):
            tables, cols = [r["table"]], [f"{r['table']}.{c}" for c in r.get("cols", [])]
        reads.append(dict(sql=sql, params=params, rows=r.get("rows"), ms=r.get("ms"), why=r.get("why"), tables=tables or [], columns=cols or [], answer=r.get("sample") or r.get("result")))
    return dict(trigger=tr.get("trigger"), handoff=tr.get("handoff"), ms=tr.get("ms"), reads=reads, data_source=tr.get("data_source"))


# ---------------------------------------------------------------------------------------------------- which claims are in scope
def scope_sql(basis, start, end, touched_only, filters):
    if basis == "service":
        scope, sp = "c.service_date_from between %s and %s", [start, end]
    elif basis == "transaction":
        scope = ("(exists (select 1 from transactions t where t.claim_id = c.claim_id and t.transaction_date between %s and %s) "
                 "or exists (select 1 from claim_status_history h where h.claim_id = c.claim_id and h.event_date between %s and %s))")
        sp = [start, end, start, end]
    elif basis == "activity":
        scope, sp = "exists (select 1 from agent_decision d where (d.claim_id = c.claim_id or d.encounter_id = c.encounter_id) and d.decided_at::date between %s and %s)", [start, end]
    else:
        raise ValueError("basis must be service, transaction or activity")
    for k, col in FILTER_COL.items():
        v = (filters or {}).get(k)
        if v not in (None, "", 0, "0"):
            scope += f" and {col} = %s"
            sp.append(int(v))
    if touched_only:
        scope += " and (exists (select 1 from agent_decision d where d.claim_id = c.claim_id) or exists (select 1 from agent_decision d where d.encounter_id = c.encounter_id))"
    return scope, sp


CLAIM_SELECT = """select c.claim_id, c.claim_number, p.payer_name, c.patient_id, c.encounter_id, c.bill_id, c.service_date_from, c.submitted_date, c.total_charge, c.claim_status, c.paid_amount,
                         c.denied_amount, c.balance, pr.provider_name, f.facility_name, sp.specialty_name, pc.practice_name,
                         (select string_agg(distinct a.carc_code, ', ') from denial d join adjustment_reason a using (adjustment_reason_id) where d.claim_id = c.claim_id) as denial_codes,
                         (select min(event_date) from claim_status_history h where h.claim_id = c.claim_id and h.event_type = 'remit_835') as remit_date
                  from claim c join payer p on p.payer_id = c.payer_id left join provider pr on pr.provider_id = c.rendering_provider_id left join facility f on f.facility_id = c.facility_id
                  left join specialty sp on sp.specialty_id = c.specialty_id left join practice pc on pc.practice_id = c.practice_id"""


def load_claims(fetch, basis, start, end, touched_only, filters):
    scope, sp = scope_sql(basis, start, end, touched_only, filters)
    claims = fetch(f"{CLAIM_SELECT} where {scope} order by c.claim_id limit {MAXCLAIMS}", sp)
    ids = [c["claim_id"] for c in claims] or [0]
    encs = [c["encounter_id"] for c in claims if c["encounter_id"]] or [0]
    decs = fetch("select d.* from agent_decision d where d.claim_id = any(%s) or d.encounter_id = any(%s) order by d.decided_at, d.agent_decision_id", [ids, encs])
    return claims, ids, encs, decs


# ---------------------------------------------------------------------------------------------------- performance by group
def performance(claims, decs, tasks, values):
    """Returns (agent rows, claim outcome rows). tasks: {decision_id: [task rows]}, values: [rows with agent_decision_id, value_stage, amount]."""
    by_id = {c["claim_id"]: c for c in claims}
    enc_claim = {c["encounter_id"]: c["claim_id"] for c in claims if c["encounter_id"]}
    val = defaultdict(lambda: defaultdict(float))
    for v in values:
        val[v["agent_decision_id"]][v["value_stage"]] += _f(v["amount"])
    G = defaultdict(lambda: dict(dec=0, raised=0, claims=set(), tasks=0, done=0, bot=0, mins=[], days=[], acc=0, ovr=0, atstake=0.0, det=0.0, conf=0.0, holds=0, hd=0))
    for d in decs:
        cid = d["claim_id"] or enc_claim.get(d["encounter_id"])
        cl = by_id.get(cid)
        if not cl:
            continue
        denied = bool(cl["denial_codes"])
        for dim, key in DIMS:
            g = G[(dim, "all" if key == "all" else (cl.get(key) or "(none)"), d["agent_code"])]
            g["dec"] += 1
            g["claims"].add(cid)
            if d["outcome"] in RAISED:
                g["raised"] += 1
                g["atstake"] += _f(d["amount_at_stake"])
            if d["human_outcome"] == "accepted":
                g["acc"] += 1
            elif d["human_outcome"] == "overridden":
                g["ovr"] += 1
            for t in tasks.get(d["agent_decision_id"], []):
                g["tasks"] += 1
                if t["task_status"] == "done":
                    g["done"] += 1
                    g["bot"] += t["contact_channel"] == "staff bot"
                    if t["minutes_spent"]:
                        g["mins"].append(t["minutes_spent"])
                    if t["completed_date"] and t["created_date"]:
                        g["days"].append((t["completed_date"] - t["created_date"]).days)
            g["det"] += val[d["agent_decision_id"]].get("detected", 0)
            g["conf"] += val[d["agent_decision_id"]].get("confirmed", 0)
            if d["agent_code"] == "A5" and d["outcome"] == "hold":
                g["holds"] += 1
                g["hd"] += denied
    avg = lambda xs: round(sum(xs) / len(xs), 1) if xs else None
    rows = []
    for (dim, value, agent), g in sorted(G.items(), key=lambda kv: (kv[0][0], str(kv[0][1]), int(kv[0][2][1:]))):
        rows.append([dim, value if value != "all" else "(every claim)", agent, NAMES.get(agent, agent), g["dec"], g["raised"], len(g["claims"]), g["tasks"], g["done"], g["done"] - g["bot"], g["bot"],
                     avg(g["mins"]), avg(g["days"]), g["acc"], g["ovr"], round(g["acc"] / (g["acc"] + g["ovr"]), 3) if g["acc"] + g["ovr"] else None, round(g["atstake"], 2), round(g["det"], 2), round(g["conf"], 2),
                     g["holds"] if agent == "A5" else None, g["hd"] if agent == "A5" else None, round(g["hd"] / g["holds"], 3) if agent == "A5" and g["holds"] else None])
    O = defaultdict(lambda: dict(n=0, denied=0, charge=0.0, paid=0.0, days=[], touched=0))
    touched = {(d["claim_id"] or enc_claim.get(d["encounter_id"])) for d in decs}
    for c in claims:
        for dim, key in DIMS:
            o = O[(dim, "all" if key == "all" else (c.get(key) or "(none)"))]
            o["n"] += 1
            o["denied"] += bool(c["denial_codes"])
            o["charge"] += _f(c["total_charge"])
            o["paid"] += _f(c["paid_amount"])
            if c["remit_date"] and c["submitted_date"]:
                o["days"].append((c["remit_date"] - c["submitted_date"]).days)
            o["touched"] += c["claim_id"] in touched
    out = [[dim, v if v != "all" else "(every claim)", o["n"], o["touched"], round(o["touched"] / o["n"], 3) if o["n"] else None, o["denied"], round(o["denied"] / o["n"], 3) if o["n"] else None,
            round(o["charge"], 2), round(o["paid"], 2), avg(o["days"])] for (dim, v), o in sorted(O.items(), key=lambda kv: (kv[0][0], str(kv[0][1])))]
    return rows, out


PERF_HEAD = ["Group by", "Group", "Agent", "Agent name", "Decisions", "Raised something", "Claims touched", "Tasks", "Tasks done", "Done by a person", "Done by staff bot", "Avg minutes per task", "Avg days to finish a task",
             "Accepted by a person", "Overridden by a person", "Acceptance rate", "$ at stake raised", "$ detected", "$ confirmed with payer money", "Mirror holds", "Held claims denied anyway", "Mirror hold hit rate"]
OUT_HEAD = ["Group by", "Group", "Claims", "Claims an agent touched", "Share touched", "Claims denied", "Denial rate", "Charges", "Paid", "Avg days submit to answer"]


def _task_map(fetch, dids):
    tasks = defaultdict(list)
    for r in fetch("select t.*, s.staff_number from agent_task t left join staff s on s.staff_id = t.assigned_to where t.agent_decision_id = any(%s) order by t.agent_task_id", [dids]):
        tasks[r["agent_decision_id"]].append(r)
    return tasks


def performance_view(fetch, basis, start, end, touched_only, filters, dim):
    claims, ids, encs, decs = load_claims(fetch, basis, start, end, touched_only, filters)
    dids = [d["agent_decision_id"] for d in decs] or [0]
    values = fetch("select agent_decision_id, value_stage, amount from agent_value where agent_decision_id = any(%s)", [dids])
    rows, out = performance(claims, decs, _task_map(fetch, dids), values)
    keep = {"payer": "Payer", "provider": "Provider", "facility": "Facility", "specialty": "Specialty", "practice": "Practice", "all": "All claims"}[dim]
    return dict(claims=len(claims), decisions=len(decs), head=PERF_HEAD, rows=[r for r in rows if r[0] == keep], out_head=OUT_HEAD, out=[r for r in out if r[0] == keep])


# ---------------------------------------------------------------------------------------------------- the workbook
def build_workbook(fetch, traces, basis, start, end, touched_only=True, plan=None, label="", filters=None):
    claims, ids, encs, decs = load_claims(fetch, basis, start, end, touched_only, filters)
    enc_claim = {c["encounter_id"]: c["claim_id"] for c in claims if c["encounter_id"]}
    by_id = {c["claim_id"]: c for c in claims}
    dids = [d["agent_decision_id"] for d in decs] or [0]
    details = defaultdict(list)
    for r in fetch("select * from agent_decision_details where agent_decision_id = any(%s) order by agent_decision_id, check_seq", [dids]):
        details[r["agent_decision_id"]].append(r)
    finds = {r["agent_decision_id"]: r for r in fetch("select * from agent_finding where agent_decision_id = any(%s)", [dids])}
    tasks = _task_map(fetch, dids)
    apprs = defaultdict(list)
    for r in fetch("select a.*, s.staff_number from agent_approval a left join staff s on s.staff_id = a.approved_by where a.agent_decision_id = any(%s)", [dids]):
        apprs[r["agent_decision_id"]].append(r)
    wbs = defaultdict(list)
    for r in fetch("select * from agent_writeback where agent_decision_id = any(%s)", [dids]):
        wbs[r["agent_decision_id"]].append(r)
    values = fetch("select agent_decision_id, value_stage, amount from agent_value where agent_decision_id = any(%s)", [dids])
    hist = defaultdict(list)
    for r in fetch("select * from claim_status_history where claim_id = any(%s) order by claim_status_history_id", [ids]):
        hist[r["claim_id"]].append(r)
    enc_rows = {r["encounter_id"]: r for r in fetch("select encounter_id, encounter_date, note_status, note_signed_date, signature_lag_days from encounter where encounter_id = any(%s)", [encs])}
    bill_rows = {r["encounter_id"]: r for r in fetch("select encounter_id, charge_entered_date, total_billed, bill_status from bill where encounter_id = any(%s)", [encs])}
    narrow = any((filters or {}).get(k) not in (None, "", 0, "0") for k in ("provider", "practice", "facility", "specialty"))
    others = [] if narrow else fetch("select d.* from agent_decision d where d.claim_id is null and d.encounter_id is null and d.decided_at::date between %s and %s"
                                     + (" and d.payer_id = %s" if (filters or {}).get("payer") not in (None, "", 0, "0") else "") + " order by d.decided_at",
                                     [start, end] + ([int(filters["payer"])] if (filters or {}).get("payer") not in (None, "", 0, "0") else []))
    perf_rows, out_rows = performance(claims, decs, tasks, values)

    wb = Workbook()
    head = PatternFill("solid", fgColor="DDE3F5")

    def sheet(title, headers, rows, widths=None, wrap=()):
        ws = wb.create_sheet(title)
        ws.append(headers)
        for r in rows:
            ws.append([_s(v) for v in r])
        for c in ws[1]:
            c.font = Font(bold=True)
            c.fill = head
            c.alignment = Alignment(wrap_text=True, vertical="top")
        ws.freeze_panes = "B2" if len(headers) > 2 else "A2"
        ws.auto_filter.ref = ws.dimensions
        for i, h in enumerate(headers, 1):
            ws.column_dimensions[get_column_letter(i)].width = (widths or {}).get(h, min(max(len(h) + 2, 12), 30))
        for row in ws.iter_rows(min_row=2):
            for c in row:
                if isinstance(c.value, dt.datetime):
                    c.number_format = "yyyy-mm-dd hh:mm"
                elif isinstance(c.value, dt.date):
                    c.number_format = "yyyy-mm-dd"
                elif isinstance(c.value, float) and headers[c.column - 1] in ("Acceptance rate", "Mirror hold hit rate", "Share touched", "Denial rate"):
                    c.number_format = "0.0%"
                if headers[c.column - 1] in wrap:
                    c.alignment = Alignment(wrap_text=True, vertical="top")
        return ws

    log_rows, q_rows, r_rows, t_rows, tl = [], [], [], [], []
    per_claim = defaultdict(lambda: dict(n=0, agents=set(), first=None, last=None, tasks=0, bot=0))
    for d in decs:
        cid = d["claim_id"] or enc_claim.get(d["encounter_id"])
        cl = by_id.get(cid, {})
        tr = norm_trace(traces.get(d["agent_decision_id"]), plan)
        dts = d["decided_at"]
        rules = details.get(d["agent_decision_id"], [])
        rule_txt = "; ".join(f"{r['rule_code']}: {r['check_result']} (saw {r['observed_value']}, expected {r['expected_value']})" for r in rules)
        f = finds.get(d["agent_decision_id"])
        tk = tasks.get(d["agent_decision_id"], [])
        ap = apprs.get(d["agent_decision_id"], [])
        wbk = wbs.get(d["agent_decision_id"], [])
        reads = tr["reads"] if tr else []
        num = lambda x, u="": "?" if x is None else f"{x}{u}"
        sql_txt = "\n".join(f"{i}. [{num(r['rows'])} rows, {num(r['ms'])} ms] {r['sql'] or '(read of ' + ', '.join(r['tables']) + ')'}  params={r['params']}" for i, r in enumerate(reads, 1)) if reads else "(SQL log not available: this decision was made in an earlier session)"
        tbls = sorted({t for r in reads for t in r["tables"]})
        cols = sorted({c for r in reads for c in r["columns"]})
        who_task = "; ".join(f"{t['title']} -> {t['owner_role']} ({t['task_status']}" + (f", done {t['completed_date']} by {t['staff_number'] or '?'} via {t['contact_channel'] or '?'}, {t['minutes_spent']} min" if t["task_status"] == "done" else "") + ")" for t in tk)
        log_rows.append([cl.get("claim_number"), cid, dts, cl.get("payer_name"), cl.get("provider_name"), cl.get("facility_name"), cl.get("specialty_name"), d["agent_code"], d["decision_type"], d["entity_type"], d["entity_id"],
                         tr and tr["trigger"], d["outcome"], d["confidence"], d["amount_at_stake"], d["reason_summary"], f"{d['rules_failed']} of {d['rules_checked']} failed", rule_txt, ", ".join(tbls), ", ".join(cols), len(reads),
                         round(sum(r["ms"] or 0 for r in reads), 1), tr and tr["ms"], sql_txt, f and f"{f['finding_type']} · {f['finding_status']}" + (f" · resolved {f['resolved_date']} ({f['resolution']})" if f["resolved_date"] else ""),
                         f and f["suggested_value"], who_task, "; ".join(f"{a['approval_type']} {a['approval_status']} by {a['staff_number']} on {a['approval_date']}" for a in ap),
                         "; ".join(f"{w['writeback_type']} -> {w['target_system']}: {w['send_status']}" for w in wbk), d["human_outcome"], d["human_outcome_date"], tr and tr["handoff"], d["run_mode"],
                         ((tr and tr["data_source"] or {}).get("answered_from") or "not recorded"),
                         "; ".join(f"{c['question']} -> {'database can answer' if c['answerable'] else 'DATABASE CANNOT ANSWER'}: {c['why']}" + (f" | outbound: {c['outbound']['kind']} via {c['outbound']['via']} ({c['outbound']['status']})" if c.get("outbound") else "")
                                   for c in ((tr and tr["data_source"] or {}).get("checks") or [])), d["agent_decision_id"]])
        for i, r in enumerate(reads, 1):
            q_rows.append([cl.get("claim_number"), d["agent_decision_id"], dts, d["agent_code"], i, r["sql"], str(r["params"]), r["rows"], r["ms"], ", ".join(r["tables"]), ", ".join(r["columns"]), r["why"], str(r["answer"])[:2000] if r["answer"] else None])
        for r in rules:
            r_rows.append([cl.get("claim_number"), d["agent_decision_id"], dts, d["agent_code"], r["check_seq"], r["rule_code"], r["check_result"], r["observed_value"], r["expected_value"], r["severity"], r["rule_source"], r["payer_rule_id"]])
        for t in tk:
            t_rows.append([cl.get("claim_number"), cl.get("payer_name"), cl.get("provider_name"), d["agent_decision_id"], t["agent_code"], t["task_type"], t["title"], t["owner_role"], t["priority"], t["created_date"], t["due_date"],
                           t["completed_date"], t["task_status"], t["staff_number"], t["contact_channel"], t["minutes_spent"], t["outcome"], t["amount_at_stake"], t["version"]])
        pc = per_claim[cid]
        pc["n"] += 1
        pc["agents"].add(d["agent_code"])
        pc["first"] = min(filter(None, [pc["first"], dts]), default=dts)
        pc["last"] = max(filter(None, [pc["last"], dts]), default=dts)
        pc["tasks"] += len(tk)
        pc["bot"] += sum(1 for t in tk if t["contact_channel"] == "staff bot")
        tl.append((_ts(dts), 5, cid, f"Agent {d['agent_code']}", f"{d['decision_type']}: {d['outcome']}. {d['reason_summary'] or ''}", d["agent_decision_id"], (tr and tr["trigger"]) or ""))
        for t in tk:
            tl.append((_ts(t["created_date"]) + dt.timedelta(hours=6), 6, cid, f"Task to {t['owner_role']}", f"raised by {t['agent_code']}: {t['title']}", d["agent_decision_id"], ""))
            if t["task_status"] == "done" and t["completed_date"]:
                tl.append((_ts(t["completed_date"]) + dt.timedelta(hours=12), 7, cid, "Person" if t["contact_channel"] != "staff bot" else "Staff bot", f"finished: {t['title']} ({t['minutes_spent']} min, outcome {t['outcome']})", d["agent_decision_id"], ""))
        for a in ap:
            tl.append((_ts(a["approval_date"]) + dt.timedelta(hours=13), 8, cid, f"Approval ({a['approver_role']})", f"{a['approval_type']} {a['approval_status']} by {a['staff_number']}", d["agent_decision_id"], ""))
        for w in wbk:
            tl.append((_ts(w["attempted_at"]), 9, cid, "Write-back", f"{w['writeback_type']} to {w['target_system']}: {w['send_status']} (shadow mode, nothing sent)", d["agent_decision_id"], ""))
    for cid, c in by_id.items():
        e = enc_rows.get(c["encounter_id"])
        b = bill_rows.get(c["encounter_id"])
        if e:
            tl.append((_ts(e["encounter_date"]), 0, cid, "Practice", f"Visit on {e['encounter_date']}", None, ""))
            if e["note_signed_date"]:
                tl.append((_ts(e["note_signed_date"]) + dt.timedelta(hours=1), 1, cid, "Provider", f"Note signed ({e['signature_lag_days']} days after the visit)", None, ""))
        if b:
            tl.append((_ts(b["charge_entered_date"]) + dt.timedelta(hours=2), 2, cid, "Practice", f"Charge entered ${float(b['total_billed']):,.2f}", None, ""))
        tl.append((_ts(c["submitted_date"]) + dt.timedelta(hours=3), 3, cid, "Practice", f"Claim {c['claim_number']} created, ready for release", None, ""))
        for h in hist.get(cid, []):
            who = "Clearinghouse" if h["event_type"] in ("acknowledged_999", "accepted_277ca", "rejected_277ca") else "Payer" if h["event_type"] in ("remit_835", "status_check_277") else "Practice"
            tl.append((_ts(h["event_ts"] or h["event_date"]), 4, cid, who, f"{h['event_type'].replace('_', ' ')} → {h['status_after']}" + (f" ({h['rejection_reason']})" if h["rejection_reason"] else ""), None, ""))
    tl.sort(key=lambda x: (by_id.get(x[2], {}).get("claim_number") or "", x[0], x[1]))

    claim_rows = []
    for c in claims:
        pc = per_claim.get(c["claim_id"])
        claim_rows.append([c["claim_number"], c["claim_id"], c["payer_name"], c["patient_id"], c["provider_name"], c["facility_name"], c["specialty_name"], c["service_date_from"], c["submitted_date"], c["remit_date"],
                           c["total_charge"], c["claim_status"], c["paid_amount"], c["denied_amount"], c["balance"], c["denial_codes"], pc["n"] if pc else 0, ", ".join(sorted(pc["agents"], key=lambda a: int(a[1:]))) if pc else "",
                           pc["tasks"] if pc else 0, pc["bot"] if pc else 0, pc["first"] if pc else None, pc["last"] if pc else None, (c["remit_date"] - c["submitted_date"]).days if c["remit_date"] and c["submitted_date"] else None])
    fdesc = ", ".join(f"{k}={v}" for k, v in (filters or {}).items() if v not in (None, "", 0, "0")) or "none"
    ws0 = wb.active
    ws0.title = "Read me"
    lines = ["KrisnnAI claim-level agent log (synthetic data, shadow mode)", f"Source: {label or 'database'}", f"Period basis: {dict(service='date of service', transaction='transaction date (any ledger posting or payer/clearinghouse event on the claim)', activity='agent decision date')[basis]}",
             f"Period: {start} to {end}", f"Filters: {fdesc}", f"Only claims an agent touched: {'yes' if touched_only else 'no'}",
             f"Claims: {len(claims)}   ·   agent decisions on those claims: {len(decs)}   ·   decisions with no claim, decided in the period: {len(others)}", "",
             "Sheets", "  Claims               one row per claim: money, status, payer, provider, facility, specialty, and how much agent activity it had",
             "  Claim log            one row per agent decision: trigger, the SQL it ran, tables and columns, rules, reason, answer, task, approval, write-back, why it moved on",
             "  Timeline             the claim's whole journey in time order: visit, note, charge, claim, clearinghouse, payer, agent decisions, people",
             "  Queries              one row per SQL statement an agent ran (text, parameters, rows returned, milliseconds, tables and columns touched)",
             "  Rules checked        one row per rule an agent checked: what it saw, what it expected, pass or fail (DATA-FIRST: could the database answer, or was an outside call justified?)", "  Tasks & people      every task an agent raised and who finished it (a person, or the staff bot) and how long it took",
             "  Agent performance    each agent measured by payer, by provider, by facility, by specialty, by practice and overall (filter the 'Group by' column)",
             "  Claim outcomes       the same groups on the claim side: denial rate, money, days to a payer answer, share of claims an agent touched",
             "  No-claim decisions   decisions that belong to no claim, such as Coach's proposed payer rules", "", "How to read the performance sheets",
             "  Acceptance rate = tasks a person carried out as the agent suggested / (those + those a person overrode). Staff-bot work is counted separately and is not a person's judgement.",
             "  Mirror hold hit rate = held claims that the payer then denied anyway / all held claims. Where people fixed the cause first, a low rate can mean the hold worked.",
             "  $ confirmed counts only money with a ledger transaction as proof."]
    for i, t in enumerate(lines, 1):
        ws0.cell(row=i, column=1, value=t).font = Font(bold=(i in (1, 9, 20)))
    ws0.column_dimensions["A"].width = 160
    sheet("Claims", ["Claim", "Claim id", "Payer", "Patient id", "Rendering provider", "Facility", "Specialty", "Date of service", "Submitted", "Payer answered", "Charge", "Status", "Paid", "Denied", "Balance", "Denial codes",
                     "Agent decisions", "Agents involved", "Tasks", "Tasks done by staff bot", "First agent touch", "Last agent touch", "Days submit to answer"], claim_rows,
          {"Claim": 14, "Payer": 22, "Rendering provider": 18, "Facility": 26, "Specialty": 18, "Agents involved": 20, "First agent touch": 17, "Last agent touch": 17})
    sheet("Claim log", ["Claim", "Claim id", "Decided at", "Payer", "Provider", "Facility", "Specialty", "Agent", "Decision type", "Entity", "Entity id", "What triggered it", "Outcome", "Confidence", "$ at stake", "Reason", "Rules failed",
                        "Rules checked", "Tables read", "Columns read", "Queries run", "Query time ms", "End-to-end ms", "SQL it ran", "Finding", "Suggested fix", "Task and who did it", "Approval", "Write-back", "Human outcome",
                        "Human outcome date", "Why it moved on", "Mode", "Answered from", "Data-first check (could the database answer?)", "Decision id"], log_rows,
          {"Claim": 14, "Decided at": 17, "Payer": 20, "Provider": 16, "Facility": 24, "Specialty": 16, "What triggered it": 44, "Reason": 50, "Rules checked": 60, "Tables read": 30, "Columns read": 50, "SQL it ran": 90, "Finding": 36,
           "Task and who did it": 50, "Why it moved on": 60, "Approval": 30, "Write-back": 28, "Data-first check (could the database answer?)": 70, "Answered from": 18},
          wrap=("What triggered it", "Reason", "Rules checked", "SQL it ran", "Task and who did it", "Why it moved on", "Tables read", "Columns read", "Finding", "Data-first check (could the database answer?)"))
    sheet("Timeline", ["Claim", "When", "Who", "What happened", "Decision id", "Trigger"], [[by_id.get(x[2], {}).get("claim_number"), x[0], x[3], x[4], x[5], x[6]] for x in tl],
          {"Claim": 14, "When": 17, "Who": 22, "What happened": 90, "Trigger": 50}, wrap=("What happened", "Trigger"))
    sheet("Queries", ["Claim", "Decision id", "Decided at", "Agent", "Step", "SQL", "Parameters", "Rows returned", "Milliseconds", "Tables touched", "Columns touched", "Why it ran this", "What it got back"], q_rows,
          {"Claim": 14, "SQL": 100, "Parameters": 30, "Tables touched": 28, "Columns touched": 50, "Why it ran this": 44, "What it got back": 50}, wrap=("SQL", "Tables touched", "Columns touched", "Why it ran this", "What it got back"))
    sheet("Rules checked", ["Claim", "Decision id", "Decided at", "Agent", "Check no", "Rule", "Result", "What it saw", "What it expected", "Severity", "Rule source", "Payer rule id"], r_rows, {"Rule": 22, "What it saw": 40, "What it expected": 36})
    sheet("Tasks & people", ["Claim", "Payer", "Provider", "Decision id", "Raised by", "Task type", "Title", "Owner role", "Priority", "Created", "Due", "Completed", "Status", "Staff", "Done via", "Minutes", "Outcome", "$ at stake", "Version"], t_rows,
          {"Title": 60, "Payer": 20, "Provider": 16})
    sheet("Agent performance", PERF_HEAD, perf_rows, {"Group": 26, "Agent name": 16})
    sheet("Claim outcomes", OUT_HEAD, out_rows, {"Group": 26})
    sheet("No-claim decisions", ["Decided at", "Agent", "Decision type", "Outcome", "Reason", "Decision id"], [[d["decided_at"], d["agent_code"], d["decision_type"], d["outcome"], d["reason_summary"], d["agent_decision_id"]] for d in others],
          {"Reason": 90, "Decided at": 17}, wrap=("Reason",))
    for ws, color in zip(wb.worksheets, ["999999", "3B5BDB", "1F9D57", "C77700", "7048E8", "0C8599", "D6336C", "868E96", "2F9E44", "E8590C", "495057"]):
        ws.sheet_properties.tabColor = color
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue(), dict(claims=len(claims), decisions=len(decs), queries=len(q_rows), timeline=len(tl), no_claim=len(others))
