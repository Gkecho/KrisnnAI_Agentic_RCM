"""The live agents: each is its own worker thread with its own database connection. They poll Postgres, run real SQL for every decision, and write
their own agent_* rows. They share nothing with the simulator except the database, and they never read the payers' hidden rules.

Every decision keeps a trace made of the SQL that actually ran (text, parameters, rows returned, milliseconds); nothing is reconstructed afterwards.
Shadow mode: nothing here changes a claim or sends anything. People (or the staff bot) work the tasks the agents raise.
"""
import datetime as dt
import json
import threading
import time
import traceback
from pathlib import Path

from common import DB, q2, D

EM_CODES = {"99203", "99204", "99213", "99214", "99395"}
PROC_AUTH = {"62323", "64483", "64493", "64635"}
PROCS = PROC_AUTH | {"20610", "20552"}
from journey import next_biz  # noqa: E402

NAMES = {"A3": "Note Chaser", "A5": "Mirror", "A6": "Courier", "A7": "Hunter", "A8": "Advocate", "A9": "Coach", "A10": "Auditor"}
SLA = {"hi": 1, "md": 3, "lo": 5}
LOGS = Path(__file__).resolve().parent / "logs"


class Ctx:
    def __init__(self, clock, publish):
        self.clock, self.publish = clock, publish
        self.traces, self.agents = {}, {}
        LOGS.mkdir(exist_ok=True)
        self.logf = open(LOGS / f"live-{dt.datetime.now():%Y%m%d-%H%M%S}.jsonl", "w", encoding="utf-8")
        self.lock = threading.Lock()

    def log(self, tr):
        with self.lock:
            self.logf.write(json.dumps(tr, default=str) + "\n")
            self.logf.flush()


class Agent(threading.Thread):
    code, interval = "A0", 1.5

    def __init__(self, ctx):
        super().__init__(daemon=True, name=self.code)
        self.ctx = ctx
        self.db = DB(clock=ctx.clock, label=self.code)
        self.stop_flag = threading.Event()
        self.stats = dict(polls=0, decisions=0, last_poll_ms=0.0, queries=0, last="", state="idle", errors=0)
        self.run_id = None
        self.run_items = 0
        self.practice = self.db.q("select practice_id p from practice limit 1")[0]["p"]
        self.staff = {r["staff_number"]: r["staff_id"] for r in self.db.q("select staff_id, staff_number from staff")}
        self.setup()
        ctx.agents[self.code] = self

    def setup(self):
        pass

    def today(self):
        return self.ctx.clock.now().date()

    def run(self):
        while not self.stop_flag.is_set():
            if self.ctx.clock.paused:
                time.sleep(0.3)
                continue
            t0 = time.perf_counter()
            self.stats["state"] = "polling"
            q0 = self.db.queries
            try:
                self.poll()
            except Exception:
                self.stats["errors"] += 1
                self.ctx.publish(dict(type="error", msg=f"{self.code} {NAMES[self.code]}: {traceback.format_exc(limit=3)}"))
            self.end_run()
            self.stats["polls"] += 1
            self.stats["last_poll_ms"] = round((time.perf_counter() - t0) * 1000, 1)
            self.stats["queries"] += self.db.queries - q0
            self.stats["state"] = "idle"
            time.sleep(self.interval)

    # ------------------------------------------------------------------ runs and decisions
    def ensure_run(self):
        if self.run_id is None:
            now = self.ctx.clock.now().replace(microsecond=0)
            self.run_id = self.db.insert("agent_run", agent_code=self.code, agent_name=NAMES[self.code], run_mode="shadow", trigger_type="event", started_at=now, run_status="running",
                                         practice_id=self.practice, items_in=0, decisions_made=0, error_count=0, code_version="live-0.1")
            self.run_items = 0
        return self.run_id

    def end_run(self):
        if self.run_id is not None:
            self.db.update("agent_run", self.run_id, ended_at=self.ctx.clock.now().replace(microsecond=0), run_status="ok", items_in=self.run_items, decisions_made=self.run_items)
            self.run_id = None

    def begin(self):
        self.db.trace = []
        self.dchecks = []
        self.t_item = time.perf_counter()

    def data_first(self, question, tables, answerable, why, outbound=None):
        """The database-first rule. Before anything outside is read, the agent asks whether the database (the PM data already loaded) can answer. The verdict is recorded with the decision.
        An outbound call is recorded only when the database cannot answer; in shadow mode it is never sent."""
        self.dchecks.append(dict(question=question, tables=tables, answerable=bool(answerable), why=why, outbound=None if answerable else outbound))
        return bool(answerable)

    def decide(self, dtype, entity, eid, outcome, amount, rules, refs, say, trigger, handoff, poll_read=None, finding=None, task=None, values=(), conf=.9, kind="flag"):
        db, now = self.db, self.ctx.clock.now().replace(microsecond=0)
        today = now.date()
        reads = self.db.trace or []
        self.db.trace = None
        run = self.ensure_run()
        self.run_items += 1
        dec = db.insert("agent_decision", agent_run_id=run, agent_code=self.code, decision_type=dtype, entity_type=entity, entity_id=eid, outcome=outcome, decided_at=now, run_mode="shadow",
                        confidence=D(str(conf)).quantize(D("0.0001")), reason_summary=(finding or {}).get("summary", say)[:300], rules_checked=len(rules), rules_failed=sum(1 for x in rules if x[1] == "fail"),
                        amount_at_stake=q2(amount or 0), data_fallback_level=0, practice_id=self.practice, **refs)
        for i, (rule, res, obs, exp, sev, prid) in enumerate(rules, 1):
            db.insert("agent_decision_details", agent_decision_id=dec, check_seq=i, rule_code=rule, check_result=res, agent_code=self.code, rule_version="1", rule_source="learned" if prid else "built_in",
                      severity=sev, observed_value=str(obs)[:100], expected_value=str(exp)[:100], input_table=entity, input_fallback_level=0, practice_id=self.practice, payer_id=refs.get("payer_id"), payer_rule_id=prid)
        checks = getattr(self, "dchecks", None) or [dict(question="Everything this decision needed", tables=[], answerable=True, why="every fact came from SQL on the canonical tables (the queries above); no outside system was needed", outbound=None)]
        self.dchecks = []
        outbound = [c["outbound"] for c in checks if c["outbound"]]
        data_source = dict(answered_from="outbound call justified" if outbound else "database", checks=checks, outbound=outbound)
        db.insert("agent_decision_details", agent_decision_id=dec, check_seq=len(rules) + 1, rule_code="DATA-FIRST", check_result="fail" if outbound else "pass", agent_code=self.code, rule_version="1", rule_source="built_in",
                  severity="low", observed_value=("database could not answer: " + "; ".join(c["why"] for c in checks if c["outbound"]))[:100] if outbound else "answered from the database", expected_value="answered from the database",
                  input_table="canonical tables", input_fallback_level=1 if outbound else 0, practice_id=self.practice, payer_id=refs.get("payer_id"))
        fid = tid = None
        if finding:
            fid = db.insert("agent_finding", agent_run_id=run, agent_code=self.code, entity_type=entity, entity_id=eid, found_date=today, agent_decision_id=dec, practice_id=self.practice, **finding, **refs)
        if task:
            tid = db.insert("agent_task", task_type=task["ttype"], owner_role=task["role"], task_status="open", created_date=today, agent_code=self.code, entity_type=entity, entity_id=eid, agent_decision_id=dec,
                            agent_finding_id=fid, priority=task.get("priority", "md"), due_date=next_biz(today, SLA[task.get("priority", "md")]), amount_at_stake=q2(amount or 0), title=task["title"][:100],
                            practice_id=self.practice, escalation_level=0, reminder_count=0, **refs)
        if fid or tid:
            db.update("agent_decision", dec, finding_id=fid, task_id=tid)
        for stage, vkind, amt, txn in values:
            db.insert("agent_value", agent_code=self.code, value_stage=stage, amount=q2(amt), value_date=today, entity_type=entity, entity_id=eid, agent_finding_id=fid, agent_decision_id=dec,
                      practice_id=self.practice, claim_id=refs.get("claim_id"), denial_id=refs.get("denial_id"), payer_id=refs.get("payer_id"), provider_id=refs.get("provider_id"), transaction_id=txn,
                      is_holdout=False, incremental_amount=q2(amt), value_kind=vkind, is_estimate=stage == "detected" and vkind in ("denial_prevented", "claim_recovery"), attribution_share=D("1.0"))
        ms = round((time.perf_counter() - self.t_item) * 1000, 1)
        tr = dict(id=dec, agent=self.code, agent_name=NAMES[self.code], date=now.isoformat(timespec="minutes"), decision_type=dtype, entity=entity, entity_id=eid, outcome=outcome, confidence=conf,
                  amount=float(amount or 0), trigger=trigger, reads=([poll_read] if poll_read else []) + reads, rules=[dict(rule=x[0], result=x[1], observed=str(x[2]), expected=str(x[3]), severity=x[4], payer_rule_id=x[5]) for x in rules],
                  answer=say, creates=dict(finding=fid, task=tid, values=len(values)), handoff=handoff, ms=ms, mode="shadow", live=True, data_source=data_source)
        self.ctx.traces[dec] = tr
        self.ctx.log(tr)
        self.stats["decisions"] += 1
        self.stats["last"] = say
        self.ctx.publish(dict(type="agent", a=self.code, name=NAMES[self.code], txt=say, amt=float(amount or 0), kind=kind, dec=dec, claim=refs.get("claim_id"), ms=ms, out=bool(outbound), t=now.isoformat(timespec="minutes")))
        return dec, fid, tid

    def poll_read(self, sql, params, rows, ms_before, why):
        """The query that surfaced the items, as the first read of each decision's trace."""
        return dict(sql=" ".join(sql.split()), params=[str(p) for p in params], rows=len(rows), ms=round(ms_before, 2), why=why, sample=[])

    @staticmethod
    def rule(code, ok, observed, expected, sev="medium", prid=None):
        return (code, "pass" if ok else "fail", observed, expected, sev, prid)

    def refs_claim(self, c):
        return dict(claim_id=c["claim_id"], patient_id=c["patient_id"], payer_id=c["payer_id"], provider_id=c["rendering_provider_id"], encounter_id=c["encounter_id"], bill_id=c["bill_id"],
                    authorization_id=c["authorization_id"])


# ====================================================================== A3 Note Chaser
class A3(Agent):
    code, interval = "A3", 2.0

    def poll(self):
        today = self.today()
        sql = """select e.encounter_id, e.encounter_date, e.rendering_provider_id, e.payer_id, e.patient_id, (select coalesce(sum(d.expected_charge),0) from encounter_details d where d.encounter_id = e.encounter_id) as amount
                 from encounter e where e.note_status = 'unsigned' and e.encounter_date <= %s::date - 3 and e.encounter_date >= %s::date - 90
                 and not exists (select 1 from agent_finding f where f.agent_code = 'A3' and f.entity_type = 'encounter' and f.entity_id = e.encounter_id) order by e.encounter_date limit 10"""
        t0 = time.perf_counter()
        rows = self.db.q(sql, [today, today])
        pr = self.poll_read(sql, [today, today], rows, (time.perf_counter() - t0) * 1000, "encounters whose note is still unsigned three days after the visit and that I have not flagged yet")
        for e in rows:
            self.begin()
            now = self.db.q("select note_status, note_signed_date from encounter where encounter_id = %s", [e["encounter_id"]], "is the note still unsigned right now")[0]
            prov = self.db.q("select provider_name from provider where provider_id = %s", [e["rendering_provider_id"]], "who has to sign")[0]["provider_name"]
            self.data_first("Is the visit note still unsigned?", ["encounter"], True, "note status comes with the PM data loaded from the EMR; no EMR call is needed")
            self.decide("documentation_review", "encounter", e["encounter_id"], "flag", e["amount"], [self.rule("R-NOTE-SIGNED", False, now["note_status"], "signed within 2 days")],
                        dict(patient_id=e["patient_id"], payer_id=e["payer_id"], provider_id=e["rendering_provider_id"], encounter_id=e["encounter_id"]),
                        f"{prov.split(',')[0]}'s note from {e['encounter_date']:%d %b} is still unsigned; the charge is held",
                        f"The visit on {e['encounter_date']} still had no signed note three days later",
                        "A biller gets a task to chase the provider. The charge stays on hold, so no claim exists yet: A5 Mirror sees nothing until the note is signed.",
                        poll_read=pr, finding=dict(finding_type="unsigned_note", finding_status="open", upstream_stage="documentation", is_preventable=True, severity="medium", amount_at_risk=q2(e["amount"]),
                                                   summary=f"Note by {prov.split(',')[0]} unsigned since {e['encounter_date']}; the charge is held", suggested_value="chase_provider"),
                        task=dict(ttype="unsigned_note", role="biller", priority="md", title=f"Chase {prov.split(',')[0]} to sign the {e['encounter_date']:%d %b} note"), conf=.97)
        for f in self.db.q("select f.agent_finding_id from agent_finding f join encounter e on e.encounter_id = f.entity_id where f.agent_code = 'A3' and f.finding_status in ('open','in_progress') and e.note_status = 'signed'"):
            self.db.update("agent_finding", f["agent_finding_id"], finding_status="resolved", resolved_date=today, resolution="signed")


# ====================================================================== A5 Mirror
class A5(Agent):
    code, interval = "A5", 1.5

    def setup(self):
        self.generic = {}
        for code, fam in (("R-AUTH-VISITS", "authorization"), ("R-COV-ACTIVE", "eligibility")):
            r = self.db.q("select payer_rule_id from payer_rule where rule_code = %s and rule_source_code = 'built_in'", [code])
            self.generic[code] = r[0]["payer_rule_id"] if r else self.db.insert("payer_rule", rule_code=code, rule_family=fam, rule_action="hold_for_review", rule_source_code="built_in", is_enabled=True, is_synthetic=True,
                                                                               approval_status="approved", effective_from=dt.date(2025, 11, 1), owner_role="front_desk", severity="high")

    def poll(self):
        sql = """select c.claim_id, c.claim_number, c.payer_id, c.encounter_id, c.coverage_id, c.total_charge, c.patient_id, c.rendering_provider_id, c.bill_id, c.authorization_id, c.submitted_date from claim c
                 where c.claim_status = 'ready' and not exists (select 1 from agent_decision d where d.agent_code = 'A5' and d.entity_type = 'claim' and d.entity_id = c.claim_id) order by c.claim_id limit 8"""
        t0 = time.perf_counter()
        rows = self.db.q(sql)
        pr = self.poll_read(sql, [], rows, (time.perf_counter() - t0) * 1000, "claims that are ready for release and that I have not reviewed yet")
        for c in rows:
            self.review(c, pr)
        sql2 = """select f.agent_finding_id, f.entity_id, exists (select 1 from denial d where d.claim_id = f.entity_id) as denied from agent_finding f where f.agent_code = 'A5' and f.finding_type = 'predicted_denial'
                  and f.finding_status = 'open' and exists (select 1 from claim_status_history h where h.claim_id = f.entity_id and h.event_type = 'remit_835')"""
        for f in self.db.q(sql2):
            self.db.update("agent_finding", f["agent_finding_id"], finding_status="confirmed" if f["denied"] else "unconfirmed", resolved_date=self.today(), resolution="denied_confirmed" if f["denied"] else "no_denial")

    def review(self, c, pr):
        db = self.db
        self.begin()
        today = self.today()
        e = db.q("select encounter_date, authorization_id, patient_id from encounter where encounter_id = %s", [c["encounter_id"]], "the visit behind the claim")[0]
        cv = db.q("select termination_date from coverage where coverage_id = %s", [c["coverage_id"]], "was the policy active on the visit date")[0]
        ver = db.q("select max(check_date) as last_check from eligibility_check where coverage_id = %s and check_date <= %s", [c["coverage_id"], e["encounter_date"]], "when coverage was last verified with the payer")[0]
        age = (e["encounter_date"] - ver["last_check"]).days if ver["last_check"] else None
        stale = age is None or age > 120
        self.data_first("Is the coverage information recent enough to trust?", ["eligibility_check", "coverage"], not stale,
                        "no eligibility check on file before the visit" if age is None else f"the last eligibility check was {age} days before the visit (more than 120), so the plan may have changed" if stale else f"the last eligibility check was {age} days before the visit and the coverage end date is in the database",
                        outbound=dict(kind="270/271 eligibility re-check", via="clearinghouse", reason="coverage cannot be confirmed from the data on file", status="suppressed in shadow mode: it would be sent only after a person approves"))
        results, fails = [], []
        if e["authorization_id"]:
            au = db.q('select units_approved from "authorization" where authorization_id = %s', [e["authorization_id"]], "visits the payer approved")[0]
            n = db.q("select count(*) as n from encounter where authorization_id = %s and encounter_date <= %s", [e["authorization_id"], e["encounter_date"]], "visits already used against it")[0]["n"]
            bad = n > au["units_approved"]
            results.append(self.rule("R-AUTH-VISITS", not bad, f"visit {n}", f"<= {au['units_approved']}", "high", self.generic["R-AUTH-VISITS"]))
            if bad:
                fails.append(("198", .92, "extend_auth", "R-AUTH-VISITS"))
        bad = bool(cv["termination_date"] and cv["termination_date"] < e["encounter_date"])
        results.append(self.rule("R-COV-ACTIVE", not bad, f"ended {cv['termination_date']}" if cv["termination_date"] else "no end date", f">= {e['encounter_date']}", "high", self.generic["R-COV-ACTIVE"]))
        if bad:
            fails.append(("27", .95, "none", "R-COV-ACTIVE"))
        learned = db.q("""select payer_rule_id, rule_code, requirement_code, unit_limit, effective_from from payer_rule where is_enabled and approval_status = 'approved' and rule_source_code = 'learned'
                          and payer_id = %s and effective_from <= %s""", [c["payer_id"], today], "payer rules a person has approved (learned by Coach) for this payer")
        for pr_ in learned:
            if pr_["requirement_code"] == "plan_of_care":
                vn = db.q("""select count(*) as visit_number from encounter x where x.patient_id = %s and x.encounter_date <= %s and x.encounter_date >= coalesce((select max(encounter_date) from encounter
                             where patient_id = %s and encounter_type = 'evaluation' and encounter_date <= %s), date '1900-01-01')""", [e["patient_id"], e["encounter_date"], e["patient_id"], e["encounter_date"]], "which visit of the episode this is")[0]["visit_number"]
                poc = db.q("""select count(*) as plan_of_care_on_file from document where patient_id = %s and document_type = 'plan_of_care' and document_date <= %s and document_date >= coalesce((select max(encounter_date)
                              from encounter where patient_id = %s and encounter_type = 'evaluation' and encounter_date <= %s), date '1900-01-01')""", [e["patient_id"], e["encounter_date"], e["patient_id"], e["encounter_date"]],
                           "is a plan of care on file for this episode")[0]["plan_of_care_on_file"]
                bad = vn >= pr_["unit_limit"] and poc == 0
                results.append(self.rule(pr_["rule_code"], not bad, f"visit {vn}, plan of care {'on file' if poc else 'missing'}", f"visit < {pr_['unit_limit']} or plan on file", "high", pr_["payer_rule_id"]))
                if bad:
                    fails.append(("50", .85, "attach_poc", pr_["rule_code"]))
            elif pr_["requirement_code"] == "procedure_auth":
                codes = {x["code"] for x in db.q("select k.code from claim_details cd join cpt_code k using (cpt_code_id) where cd.claim_id = %s", [c["claim_id"]], "the billed procedures")}
                bad = bool(codes & PROC_AUTH) and not c["authorization_id"]
                results.append(self.rule(pr_["rule_code"], not bad, "procedure billed without an authorization" if bad else "authorization on file or no procedure", "prior authorization for spine and nerve procedures", "high", pr_["payer_rule_id"]))
                if bad:
                    fails.append(("197", .85, "get_auth", pr_["rule_code"]))
            elif pr_["requirement_code"] == "mod25":
                lines = db.q("""select k.code, m1.modifier_code as m1, m2.modifier_code as m2 from claim_details c join cpt_code k using (cpt_code_id) left join modifier m1 on m1.modifier_id = c.modifier_1_id
                                left join modifier m2 on m2.modifier_id = c.modifier_2_id where c.claim_id = %s""", [c["claim_id"]], "the billed lines and their modifiers")
                bad = any(x["code"] in PROCS for x in lines) and any(x["code"] in EM_CODES and "25" not in (x["m1"], x["m2"]) for x in lines)
                results.append(self.rule(pr_["rule_code"], not bad, "E/M with a procedure and no modifier 25" if bad else "modifier present or no procedure", "modifier 25 on the E/M", "high", pr_["payer_rule_id"]))
                if bad:
                    fails.append(("4", .85, "add_25", pr_["rule_code"]))
            elif pr_["requirement_code"] == "xu_modifier":
                lines = db.q("""select k.code, c.modifier_1_id, c.modifier_2_id, m1.modifier_code as m1, m2.modifier_code as m2 from claim_details c join cpt_code k using (cpt_code_id)
                                left join modifier m1 on m1.modifier_id = c.modifier_1_id left join modifier m2 on m2.modifier_id = c.modifier_2_id where c.claim_id = %s""", [c["claim_id"]], "the billed lines and their modifiers")
                codes = {x["code"] for x in lines}
                l97 = [x for x in lines if x["code"] == "97530"]
                bad = {"97140", "97530"} <= codes and not any({x["m1"], x["m2"]} & {"XU", "59"} for x in l97)
                results.append(self.rule(pr_["rule_code"], not bad, "97140 + 97530 without XU/59" if bad else "modifier present or no pair", "distinct-service modifier", "high", pr_["payer_rule_id"]))
                if bad:
                    fails.append(("97", .85, "add_xu", pr_["rule_code"]))
        refs = self.refs_claim(c)
        trig = f"Claim {c['claim_number']} reached its release window and is about to go to the clearinghouse"
        if fails:
            carc, p, fix, rname = max(fails, key=lambda x: x[1])
            ct = db.q("select reason_category from adjustment_reason where carc_code = %s", [carc], "category of the predicted denial reason")[0]["reason_category"]
            self.decide("prerelease_review", "claim", c["claim_id"], "hold", c["total_charge"], results, refs, f"Would hold {c['claim_number']}: CARC {carc} risk ({rname})", trig,
                        "A biller gets a review task. In shadow mode the claim is released anyway unless you switch on 'Mirror holds claims'; this prediction is scored when the payer answers.",
                        poll_read=pr, finding=dict(finding_type="predicted_denial", finding_status="open", upstream_stage="billing", is_preventable=True, severity="high", amount_at_risk=q2(c["total_charge"]),
                                                   predicted_probability=D(str(p)).quantize(D("0.0001")), predicted_reason_category=ct, suggested_value=fix, summary=f"Predicted CARC {carc}: {rname}"),
                        task=dict(ttype="claim_hold_review", role="biller", priority="hi", title=f"Review before release: CARC {carc} risk ({rname})"), conf=p, kind="hold",
                        values=[("detected", "denial_prevented", c["total_charge"], None)])
        else:
            self.decide("prerelease_review", "claim", c["claim_id"], "release", c["total_charge"], results, refs, f"Released {c['claim_number']}: all checks pass", trig,
                        "No rule failed, so the claim goes on to the clearinghouse (A6 Courier watches for rejections).", poll_read=pr, conf=.9, kind="clear")


# ====================================================================== A6 Courier
class A6(Agent):
    code, interval = "A6", 1.5

    def setup(self):
        self.wm = self.db.q("select coalesce(max(claim_status_history_id),0) m from claim_status_history")[0]["m"]

    def poll(self):
        sql = "select h.claim_status_history_id, h.claim_id, h.event_date, h.rejection_reason from claim_status_history h where h.is_rejection and h.claim_status_history_id > %s order by 1 limit 10"
        t0 = time.perf_counter()
        rows = self.db.q(sql, [self.wm])
        pr = self.poll_read(sql, [self.wm], rows, (time.perf_counter() - t0) * 1000, "new clearinghouse rejections since I last looked")
        for h in rows:
            self.wm = h["claim_status_history_id"]
            self.begin()
            c = self.db.q("select * from claim where claim_id = %s", [h["claim_id"]], "the rejected claim")[0]
            self.data_first("Why did the clearinghouse reject the claim?", ["claim_status_history"], True, "the 277CA rejection reason is already in the database; no clearinghouse call is needed")
            self.decide("rejection_review", "claim", c["claim_id"], "flag", c["total_charge"], [self.rule("R-277CA-ACCEPT", False, h["rejection_reason"], "accepted", "high")], self.refs_claim(c),
                        f"{c['claim_number']} rejected at the clearinghouse: {h['rejection_reason'].replace('_', ' ')}", f"The clearinghouse rejected {c['claim_number']} on {h['event_date']} (277CA)",
                        "A biller gets a same-day task to correct and resubmit. If the payer then goes quiet, A7 Hunter takes over; if it denies, A8 Advocate does.", poll_read=pr,
                        finding=dict(finding_type="clearinghouse_rejection", finding_status="open", upstream_stage="billing", is_preventable=True, severity="high", amount_at_risk=q2(c["total_charge"]),
                                     deadline_date=next_biz(self.today(), 1), summary=f"Rejected at the clearinghouse: {h['rejection_reason']}", suggested_value="correct_and_resubmit"),
                        task=dict(ttype="fix_rejection", role="biller", priority="hi", title="Correct and resubmit the rejected claim"), conf=.95,
                        values=[("detected", "cash_acceleration", c["total_charge"], None)])


# ====================================================================== A7 Hunter
class A7(Agent):
    code, interval = "A7", 3.0

    def poll(self):
        today = self.today()
        sql = """select c.claim_id, c.claim_number, c.payer_id, c.patient_id, c.rendering_provider_id, c.encounter_id, c.bill_id, c.authorization_id, c.total_charge, c.submitted_date, c.service_date_from,
                        p.standard_turnaround_days, p.filing_days from claim c join payer p on p.payer_id = c.payer_id
                 where c.claim_status in ('accepted','no_response','submitted') and c.submitted_date + (p.standard_turnaround_days + 14) <= %s::date and c.submitted_date >= %s::date - 120
                 and not exists (select 1 from claim_status_history h where h.claim_id = c.claim_id and h.event_type = 'remit_835')
                 and not exists (select 1 from agent_finding f where f.agent_code = 'A7' and f.entity_type = 'claim' and f.entity_id = c.claim_id) order by c.total_charge desc limit 4"""
        t0 = time.perf_counter()
        rows = self.db.q(sql, [today, today])
        pr = self.poll_read(sql, [today, today], rows, (time.perf_counter() - t0) * 1000, "claims past the payer's normal answer time plus 14 days with no remittance, not yet flagged")
        for c in rows:
            self.begin()
            n = self.db.q("select count(*) as remit_835_events from claim_status_history where claim_id = %s and event_type = 'remit_835' and event_date <= %s", [c["claim_id"], today], "has the payer answered")[0]["remit_835_events"]
            last = self.db.q("select max(event_date) as last_event from claim_status_history where claim_id = %s", [c["claim_id"]], "how recent the database's last event for this claim is")[0]["last_event"]
            age = (today - last).days if last else None
            self.data_first("Has the payer answered this claim?", ["claim_status_history"], n > 0,
                            "a remittance is already in the database" if n > 0 else f"the database has no remittance and its last event for this claim is {age} days old, so it cannot say whether the payer received or lost the claim",
                            outbound=dict(kind="276/277 claim status check", via="clearinghouse", reason="the database is silent; only the payer can say what happened", status="suppressed in shadow mode: it would be sent only after the AR specialist approves"))
            days = (today - c["submitted_date"]).days
            deadline = c["service_date_from"] + dt.timedelta(days=c["filing_days"])
            risk = (deadline - today).days
            self.decide("claim_follow_up", "claim", c["claim_id"], "flag", c["total_charge"],
                        [self.rule("R-PAYER-RESPONSE", n > 0, f"{days} days, no response", f"<= {c['standard_turnaround_days'] + 14} days", "high"), self.rule("R-FILING-WINDOW", risk > 30, f"{risk} days left", "> 30", "high")],
                        self.refs_claim(c), f"{c['claim_number']}: no payer response after {days} days; filing window ends {deadline}",
                        f"{c['claim_number']} passed the payer's normal answer time plus 14 days with no remittance",
                        "An AR specialist gets a task to call the payer or resubmit before the filing window closes. If the payer later denies it, A8 Advocate takes over.", poll_read=pr,
                        finding=dict(finding_type="no_payer_response", finding_status="open", upstream_stage="billing", is_preventable=False, severity="high" if risk <= 30 else "medium",
                                     amount_at_risk=q2(c["total_charge"]), deadline_date=deadline, summary=f"No payer response after {days} days; filing window ends {deadline}", suggested_value="resubmit"),
                        task=dict(ttype="claim_follow_up", role="ar_specialist", priority="hi" if risk <= 30 else "md", title="Call the payer or resubmit: no response"), conf=.88,
                        values=[("detected", "claim_recovery", c["total_charge"], None)])


# ====================================================================== A8 Advocate
class A8(Agent):
    code, interval = "A8", 1.5

    def setup(self):
        self.wm = self.db.q("select coalesce(max(denial_id),0) m from denial")[0]["m"]
        self.start_day = self.ctx.clock.now().date()

    def poll(self):
        sql = """select d.denial_id, d.claim_id, d.denial_date, d.denied_amount, d.adjustment_reason_id, d.appeal_deadline, d.payer_id, d.patient_id, d.upstream_stage, d.is_preventable, c.claim_number,
                        c.rendering_provider_id, c.encounter_id, c.bill_id, c.authorization_id from denial d join claim c on c.claim_id = d.claim_id where d.denial_id > %s order by d.denial_id limit 10"""
        t0 = time.perf_counter()
        rows = self.db.q(sql, [self.wm])
        pr = self.poll_read(sql, [self.wm], rows, (time.perf_counter() - t0) * 1000, "new denials on payer remittances since I last looked")
        for d in rows:
            self.wm = d["denial_id"]
            self.begin()
            cr = self.db.q("select carc_code, short_label, reason_class, owner_role, is_appealable from adjustment_reason where adjustment_reason_id = %s", [d["adjustment_reason_id"]], "what the reason code means and who owns it")[0]
            today = self.today()
            self.data_first("What does the denial mean, who owns it, and how long is the appeal window?", ["denial", "adjustment_reason"], True,
                            "the reason code, owner and deadline are in the database" + ("; an appeal would be sent through the payer portal later, only after a person approves it" if cr["is_appealable"] else ""))
            sev = "high" if (d["appeal_deadline"] - today).days <= 30 else "medium"
            role = "denial_specialist" if cr["is_appealable"] else cr["owner_role"] if cr["owner_role"] in ("front_desk", "coder", "biller", "billing_lead") else "biller"
            self.decide("denial_triage", "denial", d["denial_id"], "route", d["denied_amount"],
                        [self.rule("R-CARC-ROUTE", True, f"CARC {cr['carc_code']}", cr["owner_role"], "medium"), self.rule("R-APPEAL-WINDOW", d["appeal_deadline"] > today, f"deadline {d['appeal_deadline']}", "open", "high")],
                        dict(claim_id=d["claim_id"], patient_id=d["patient_id"], payer_id=d["payer_id"], provider_id=d["rendering_provider_id"], encounter_id=d["encounter_id"], bill_id=d["bill_id"],
                             authorization_id=d["authorization_id"], denial_id=d["denial_id"]),
                        f"{d['claim_number']} denied CARC {cr['carc_code']}: {cr['short_label']}; owner {cr['owner_role']}", f"The 835 for {d['claim_number']} arrived with a denial on {d['denial_date']}",
                        f"The task goes to the {role.replace('_', ' ')}. A9 Coach counts this denial toward pattern detection (10 alike in 60 days proposes a prevention rule), and a corrected claim passes A5 Mirror again.", poll_read=pr,
                        finding=dict(finding_type="denial", finding_status="open", upstream_stage=d["upstream_stage"], is_preventable=d["is_preventable"], severity=sev, amount_at_risk=q2(d["denied_amount"]),
                                     deadline_date=d["appeal_deadline"], summary=f"CARC {cr['carc_code']}: {cr['short_label']}; owner {cr['owner_role']}", suggested_value="send_appeal" if cr["is_appealable"] else "accept_denial"),
                        task=dict(ttype="denial_work", role=role, priority="hi" if sev == "high" else "md", title=f"Work the denial: {cr['short_label']}"), conf=.9, kind="denial",
                        values=[("detected", "denial_recovery", d["denied_amount"], None)])
        won = self.db.q("""select a.appeal_id, a.denial_id, a.recovered_amount, a.claim_id, t.transaction_id, f.agent_finding_id from appeal a join transactions t on t.denial_id = a.denial_id and t.transaction_type = 'payment'
                           left join agent_finding f on f.agent_code = 'A8' and f.entity_type = 'denial' and f.entity_id = a.denial_id
                           where a.is_overturned and a.decision_date > %s and not exists (select 1 from agent_value v where v.agent_code = 'A8' and v.denial_id = a.denial_id and v.value_stage = 'confirmed')""", [self.start_day])
        for w in won:
            self.db.insert("agent_value", agent_code="A8", value_stage="confirmed", amount=q2(w["recovered_amount"]), value_date=self.today(), entity_type="denial", entity_id=w["denial_id"], agent_finding_id=w["agent_finding_id"],
                           practice_id=self.practice, claim_id=w["claim_id"], denial_id=w["denial_id"], transaction_id=w["transaction_id"], is_holdout=False, incremental_amount=q2(w["recovered_amount"]),
                           value_kind="denial_recovery", is_estimate=False, attribution_share=D("1.0"))
            if w["agent_finding_id"]:
                self.db.update("agent_finding", w["agent_finding_id"], amount_recovered=q2(w["recovered_amount"]), resolution="recovered")
            self.ctx.publish(dict(type="agent", a="A8", name=NAMES["A8"], txt=f"Confirmed with the payer's money: ${float(w['recovered_amount']):,.0f} recovered (ledger transaction #{w['transaction_id']})", amt=float(w["recovered_amount"]),
                                  kind="win", dec=None, claim=w["claim_id"], ms=0, t=self.ctx.clock.now().isoformat(timespec="minutes")))


# ====================================================================== A9 Coach
class A9(Agent):
    code, interval = "A9", 2.0
    TEMPLATES = {"50": ("R-UHC-POC-V", "documentation", "plan_of_care"), "97": ("R-AET-XU", "coding", "xu_modifier"), "197": ("R-HUM-AUTH", "authorization", "procedure_auth"),
                 "4": ("R-UHC-M25", "coding", "mod25")}

    def setup(self):
        self.last_day = None

    def poll(self):
        today = self.today()
        if self.last_day == today:
            return
        self.last_day = today
        sql = """select d.payer_id, d.adjustment_reason_id, a.carc_code, count(*) as denials, sum(d.denied_amount) as denied_amount, min(d.denial_date) as first_date from denial d
                 join adjustment_reason a using (adjustment_reason_id) where d.denial_date >= %s::date - 60 and a.carc_code in ('50','97','197','4') group by 1, 2, 3 having count(*) >= 10
                 and not exists (select 1 from payer_rule r where r.rule_source_code = 'learned' and r.payer_id = d.payer_id and r.adjustment_reason_id = d.adjustment_reason_id)"""
        t0 = time.perf_counter()
        rows = self.db.q(sql, [today])
        pr = self.poll_read(sql, [today], rows, (time.perf_counter() - t0) * 1000, "payer and reason-code combinations with at least 10 denials in 60 days and no learned rule yet")
        for cl in rows:
            self.begin()
            rcode, fam, req = self.TEMPLATES[cl["carc_code"]]
            self.data_first("Are denials from this payer clustering around one reason?", ["denial", "adjustment_reason"], True, "the pattern is counted from the denial table; no payer lookup is needed")
            thr = None
            if cl["carc_code"] == "50":
                thr = self.db.q("""select min(vn) as min_visit from (select (select count(*) from encounter e2 where e2.patient_id = e.patient_id and e2.encounter_date <= e.encounter_date and e2.encounter_date >=
                                  (select max(e3.encounter_date) from encounter e3 where e3.patient_id = e.patient_id and e3.encounter_type = 'evaluation' and e3.encounter_date <= e.encounter_date)) as vn
                                  from denial d join claim c on c.claim_id = d.claim_id join encounter e on e.encounter_id = c.encounter_id where d.payer_id = %s and d.adjustment_reason_id = %s and d.denial_date >= %s::date - 60) x""",
                                [cl["payer_id"], cl["adjustment_reason_id"], today], "the earliest visit number among those denials: the threshold for the rule")[0]["min_visit"]
            pid = self.db.insert("payer_rule", rule_code=rcode + (str(thr) if thr else ""), rule_family=fam, rule_action="hold_for_review", rule_source_code="learned", payer_id=cl["payer_id"],
                                 adjustment_reason_id=cl["adjustment_reason_id"], requirement_code=req, unit_limit=thr, evidence_claim_count=cl["denials"], evidence_denied_count=cl["denials"],
                                 evidence_denied_amount=q2(cl["denied_amount"]), evidence_from_date=cl["first_date"], evidence_to_date=today, owner_role="biller", severity="high", is_enabled=False, is_synthetic=True,
                                 approval_status="proposed", effective_from=today)
            self.decide("rule_proposal", "payer_rule", pid, "proposed", cl["denied_amount"], [self.rule("PATTERN-CLUSTER", False, f"{cl['denials']} denials in 60 days", ">= 10", "high")], dict(payer_id=cl["payer_id"]),
                        f"{cl['denials']} CARC {cl['carc_code']} denials from one payer in 60 days: proposes rule {rcode}{thr or ''}", f"Daily pattern scan on {today}: {cl['denials']} denials of the same kind in 60 days reached the threshold of 10",
                        "The manager gets a task to approve the rule. Once approved, A5 Mirror starts holding matching claims before release.", poll_read=pr,
                        finding=dict(finding_type="rule_proposal", finding_status="open", upstream_stage="billing", is_preventable=True, severity="high", amount_at_risk=q2(cl["denied_amount"]),
                                     summary=f"{cl['denials']} CARC {cl['carc_code']} denials in 60 days; proposed rule {rcode}", suggested_value="approve_rule"),
                        task=dict(ttype="rule_review", role="manager", priority="md", title=f"Approve rule {rcode}{thr or ''}: {cl['denials']} denials in 60 days"), conf=.9, kind="learn")


# ====================================================================== A10 Auditor
class A10(Agent):
    code, interval = "A10", 2.0

    def setup(self):
        self.wm = self.db.q("select coalesce(max(claim_status_history_id),0) m from claim_status_history")[0]["m"]

    def poll(self):
        sql = "select h.claim_status_history_id, h.claim_id from claim_status_history h where h.event_type = 'remit_835' and h.claim_status_history_id > %s order by 1 limit 15"
        t0 = time.perf_counter()
        rows = self.db.q(sql, [self.wm])
        pr = self.poll_read(sql, [self.wm], rows, (time.perf_counter() - t0) * 1000, "new payer remittances since I last looked")
        for h in rows:
            self.wm = h["claim_status_history_id"]
            self.begin()
            lines = self.db.q("""select cd.claim_detail_id, cd.allowed_amount, cd.expected_allowed, k.code, c.claim_number, c.payer_id, c.patient_id, c.rendering_provider_id, c.encounter_id, c.bill_id, c.authorization_id, c.claim_id,
                                        (cd.modifier_1_id = m.modifier_id or cd.modifier_2_id = m.modifier_id or (pv.provider_type = 'NP' and py.payer_type in ('medicare', 'medicare_advantage'))) as has_cq
                                 from claim_details cd join claim c on c.claim_id = cd.claim_id join cpt_code k on k.cpt_code_id = cd.cpt_code_id join provider pv on pv.provider_id = c.rendering_provider_id
                                 join payer py on py.payer_id = c.payer_id cross join (select modifier_id from modifier where modifier_code = 'CQ') m where cd.claim_id = %s and cd.allowed_amount is not null and cd.expected_allowed > 0""", [h["claim_id"]],
                               "paid lines with the allowed amount and the contract amount, and whether a reduced rate applies (CQ assistant modifier, or a nurse practitioner under Medicare)")
            self.data_first("What should the payer have paid?", ["claim_details", "contract_rate"], True, "the contract amount is stored on the claim line (expected_allowed); no payer-portal lookup is needed")
            short = []
            for l in lines:
                exp = l["expected_allowed"] * (D("0.85") if l["has_cq"] else D(1))
                gap = q2(exp - l["allowed_amount"])
                if gap > q2(exp * D("0.03")):
                    short.append((l, exp, gap))
            if not short:
                self.db.trace = None
                continue
            reads = list(self.db.trace)
            for l, exp, gap in short:
                self.db.trace = list(reads)
                self.decide("payment_audit", "claim_detail", l["claim_detail_id"], "flag", gap, [self.rule("R-CONTRACT-RATE", False, f"allowed {l['allowed_amount']}", f"{q2(exp)}", "high")],
                            dict(claim_id=l["claim_id"], patient_id=l["patient_id"], payer_id=l["payer_id"], provider_id=l["rendering_provider_id"], encounter_id=l["encounter_id"], bill_id=l["bill_id"],
                                 authorization_id=l["authorization_id"]), f"{l['claim_number']} {l['code']} paid ${float(gap):,.2f} below the contract", f"The payer's remittance for {l['claim_number']} arrived; paid lines are compared with the contract rate",
                            "A billing lead gets a dispute task. Repeated shortfalls from one payer would show up as a payer-wide pattern.", poll_read=pr,
                            finding=dict(finding_type="underpayment", finding_status="open", upstream_stage="payment", is_preventable=False, severity="medium", amount_at_risk=gap,
                                         summary=f"{l['code']} paid {gap} below the contract rate", suggested_value="send_dispute"),
                            task=dict(ttype="dispute_package", role="billing_lead", priority="md", title="Dispute the underpayment with the payer"), conf=.93, values=[("detected", "underpayment", gap, None)])


AGENTS = [A3, A5, A6, A7, A8, A9, A10]
