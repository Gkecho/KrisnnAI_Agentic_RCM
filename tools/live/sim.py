"""The live world: a simulated clock, the practice (visits, notes, charges, claims), a clearinghouse, and payers that decide claims by hidden rules.

Everything it does is written to Postgres as it happens. The agents never read this file's rules; they only see the rows it writes.
Human work (tasks the agents raise) is done by you from the inbox, or by a staff bot when a task has waited too long.
"""
import datetime as dt
import heapq
import random
import threading
import time
from collections import defaultdict
from decimal import Decimal

from common import DB, q2, D
from journey import is_biz, next_biz  # noqa: E402  (tools/synth)

START = dt.datetime(2026, 11, 2, 7, 0, 0)
DAY = 86400
BASE_MIN = {"unsigned_note": 6, "claim_hold_review": 16, "fix_rejection": 11, "claim_follow_up": 22, "denial_work": 26, "dispute_package": 40, "rule_review": 20}
ROLE_STAFF = {"biller": "B01", "ar_specialist": "AR01", "denial_specialist": "D01", "billing_lead": "B03", "manager": "M01", "front_desk": "FD01", "coder": "C01"}
ACTIONS = {"unsigned_note": ["chase_provider"], "claim_hold_review": ["fix_and_release", "release_as_is"], "fix_rejection": ["correct_and_resubmit"], "claim_follow_up": ["resubmit", "close"],
           "denial_work": ["send_appeal", "accept_denial"], "dispute_package": ["send_dispute", "dismiss"], "rule_review": ["approve_rule", "reject_rule"]}
EM_CODES = {"99203", "99204", "99213", "99214", "99395"}
PROC_AUTH = {"62323", "64483", "64493", "64635"}              # Humana wants a prior authorization for these
PROCS = PROC_AUTH | {"20610", "20552"}                         # a procedure on the same day makes an E/M need modifier 25
THERAPY_TIMED = ("97110", "97140", "97530", "97112")
BOT_AFTER_DAYS = 7          # a staff bot picks up routine tasks left this long; rule approvals always need a named person


class Clock:
    """Simulated time. `rate` is simulated seconds per real second."""

    def __init__(self, start=START, rate=3600.0):
        self.rate = rate
        self.sim0 = start
        self.real0 = time.time()
        self.paused = True
        self._lock = threading.Lock()

    def now(self):
        with self._lock:
            if self.paused:
                return self.sim0
            return self.sim0 + dt.timedelta(seconds=(time.time() - self.real0) * self.rate)

    def _freeze(self):
        self.sim0 = self.now()
        self.real0 = time.time()

    def set_rate(self, rate):
        with self._lock:
            if not self.paused:
                self.sim0 = self.sim0 + dt.timedelta(seconds=(time.time() - self.real0) * self.rate)
                self.real0 = time.time()
            self.rate = rate

    def pause(self):
        with self._lock:
            if not self.paused:
                self.sim0 = self.sim0 + dt.timedelta(seconds=(time.time() - self.real0) * self.rate)
                self.paused = True

    def resume(self):
        with self._lock:
            if self.paused:
                self.real0 = time.time()
                self.paused = False


class Sim(threading.Thread):
    def __init__(self, clock, publish, seed=7):
        super().__init__(daemon=True, name="simulator")
        self.clock = clock
        self.publish = publish
        self.db = DB(clock=clock, label="sim")
        self.r = random.Random(seed)
        self.heap, self.seq = [], 0
        self.stop_flag = threading.Event()
        self.lock = threading.RLock()          # the simulator and the web actions share one database connection
        self.counters = defaultdict(int)
        self.feed_log = []
        # hidden world state: the payers' rules and the practice's habits (agents never read these)
        self.rules = dict(uhc_poc_visit=13, aet_xu_since=dt.date(2026, 9, 1), bcbs_97140=D("0.88"), base_denial=.045, stall_prob=.02, reject_prob=.04, unposted_prob=.02,
                          stalled_payers=set(), slow_signers={"Lee", "Nakamura"}, mirror_enforce=False, uhc_m25_since=dt.date(2026, 7, 1))
        self._load_refs()

    # ------------------------------------------------------------------ reference data (read once)
    def _load_refs(self):
        d = self.db
        self.payer = {r["payer_id"]: r for r in d.q("select * from payer")}
        self.payer_code = {k: v["payer_code"] for k, v in self.payer.items()}
        self.cpt = {r["cpt_code_id"]: r["code"] for r in d.q("select cpt_code_id, code from cpt_code")}
        self.cpt_id = {v: k for k, v in self.cpt.items()}
        self.mod = {r["modifier_code"]: r["modifier_id"] for r in d.q("select modifier_id, modifier_code from modifier")}
        self.carc = {r["carc_code"]: r for r in d.q("select * from adjustment_reason")}
        self.carc_by_id = {r["adjustment_reason_id"]: r for r in self.carc.values()}
        self.rarc = {r["rarc_code"]: r["remark_code_id"] for r in d.q("select remark_code_id, rarc_code from remark_code")}
        self.pos11 = d.q("select place_of_service_id p from place_of_service where pos_code='11'")[0]["p"]
        self.staff = {r["staff_number"]: r["staff_id"] for r in d.q("select staff_id, staff_number from staff")}
        self.rate = {(r["payer_id"], r["cpt_code_id"]): r["allowed_per_unit"] for r in d.q("select payer_id, cpt_code_id, allowed_per_unit from contract_rate")}
        self.fee = {r["cpt_code_id"]: r["fee_per_unit"] for r in d.q("select cpt_code_id, fee_per_unit from fee_list")}
        self.provider = {r["provider_id"]: r for r in d.q("select provider_id, provider_name, provider_type, specialty_id from provider where practice_id is not null")}
        self.practice = d.q("select practice_id p from practice limit 1")[0]["p"]
        self.spec_code = {r["specialty_id"]: r["specialty_code"] for r in d.q("select specialty_id, specialty_code from specialty")}
        self.payer_type = {k: v["payer_type"] for k, v in self.payer.items()}
        # who bills for whom: a nurse or an assistant bills under the supervising clinician (taken from the history the practice already has)
        self.biller_of = {r["rendering_provider_id"]: r["supervising_provider_id"] for r in d.q(
            "select distinct on (rendering_provider_id) rendering_provider_id, supervising_provider_id from encounter where supervising_provider_id is not null order by rendering_provider_id, encounter_date desc")}
        self.n_claim = d.q("select coalesce(max(claim_id),0)+1 n from claim")[0]["n"]
        self.n_enc = d.q("select coalesce(max(encounter_id),0)+1 n from encounter")[0]["n"]
        self.n_bill = d.q("select coalesce(max(bill_id),0)+1 n from bill")[0]["n"]
        self.n_txn = d.q("select coalesce(max(transaction_id),0)+1 n from transactions")[0]["n"]
        self.n_pay = d.q("select coalesce(max(payment_id),0)+1 n from payment")[0]["n"]
        self.n_doc = d.q("select coalesce(max(document_id),0)+1 n from document")[0]["n"]
        self.n_apl = d.q("select coalesce(max(appeal_id),0)+1 n from appeal")[0]["n"]

    # ------------------------------------------------------------------ event queue
    def at(self, when, name, *args):
        self.seq += 1
        heapq.heappush(self.heap, (when, self.seq, name, args))

    def after(self, seconds, name, *args):
        self.at(self.clock.now() + dt.timedelta(seconds=seconds), name, *args)

    def today(self):
        return self.clock.now().date()

    def feed(self, kind, text, claim=None, amount=None, **extra):
        item = dict(type="world", t=self.clock.now().isoformat(timespec="minutes"), kind=kind, text=text, claim=claim, amount=float(amount) if amount is not None else None, **extra)
        self.feed_log.append(item)
        del self.feed_log[:-300]
        self.counters[kind] += 1
        self.publish(item)

    def run(self):
        self.bootstrap()
        last_sweep = None
        while not self.stop_flag.is_set():
            now = self.clock.now()
            if not self.clock.paused:
                while self.heap and self.heap[0][0] <= now:
                    when, _, name, args = heapq.heappop(self.heap)
                    try:
                        with self.lock:
                            getattr(self, "ev_" + name)(*args)
                    except Exception as ex:
                        self.feed("error", f"{name} failed: {ex}")
                if last_sweep is None or now - last_sweep >= dt.timedelta(hours=2):
                    last_sweep = now
                    try:
                        with self.lock:
                            self.bot_sweep()
                    except Exception as ex:
                        self.feed("error", f"staff bot failed: {ex}")
            time.sleep(0.1)

    # ------------------------------------------------------------------ the day
    def bootstrap(self):
        d, now = self.db, self.clock.now()
        self.at(now + dt.timedelta(seconds=1), "daily", now.date())
        inflight = d.q("""select c.claim_id, c.submitted_date, c.payer_id from claim c where c.claim_status = 'accepted'
                          and not exists (select 1 from claim_status_history h where h.claim_id = c.claim_id and h.event_type = 'remit_835')""")
        for c in inflight:
            turn = self.payer[c["payer_id"]]["standard_turnaround_days"]
            due = (c["submitted_date"] - now.date()).days + turn + self.r.randint(-3, 6)
            self.after(max(3600, due * DAY * self.r.uniform(.8, 1.1)) if due > 0 else self.r.uniform(3600, 4 * DAY), "adjudicate", c["claim_id"])
        for b in d.q("select b.bill_id, b.encounter_id from bill b where b.bill_status='open' and b.bill_type='insurance' and not exists (select 1 from claim c where c.bill_id=b.bill_id)"):
            self.after(self.r.uniform(1800, 2 * DAY), "make_claim", b["bill_id"])
        for e in d.q("select e.encounter_id, e.rendering_provider_id from encounter e where e.note_status='unsigned'"):
            slow = self.provider[e["rendering_provider_id"]]["provider_name"].split(",")[0] in self.rules["slow_signers"]
            self.after(self.r.uniform(1, 3 if slow else 1.5) * DAY + self.r.uniform(0, 3) * DAY * (1 if slow else 0), "sign_note", e["encounter_id"])
        self.feed("system", f"Live world started: {len(inflight)} claims already with payers, appointments booked through December")

    def ev_daily(self, day):
        if is_biz(day):
            for a in self.db.q("select appointment_id, start_time from appointment where appointment_status='scheduled' and appointment_date=%s order by start_time", [day]):
                st = a["start_time"] or dt.time(9, 0)
                when = max(dt.datetime.combine(day, st), self.clock.now() + dt.timedelta(seconds=self.r.uniform(1, 600)))
                self.at(when, "visit", a["appointment_id"])
            self.feed("system", f"{day:%a %d %b}: {len(self.db.q('select 1 from appointment where appointment_status=%s and appointment_date=%s', ['scheduled', day]))} visits on the schedule")
        self.at(dt.datetime.combine(day + dt.timedelta(days=1), dt.time(6, 0)), "daily", day + dt.timedelta(days=1))

    # ------------------------------------------------------------------ visits, notes, charges
    def ev_visit(self, appt_id):
        d, r = self.db, self.r
        a = d.q("select * from appointment where appointment_id=%s", [appt_id])[0]
        if a["appointment_status"] != "scheduled":
            return
        if r.random() < .03:
            d.update("appointment", appt_id, appointment_status="no_show")
            d.x("update resource_allocation set allocation_status='no_show' where appointment_id=%s", [appt_id])
            d.x("update appointment_slot set slot_status='no_show' where appointment_id=%s", [appt_id])
            self.feed("noshow", f"No-show: appointment {a['appointment_number']}")
            return
        lines = d.q("""select d.*, k.code from appointment_details d join cpt_code k on k.cpt_code_id = d.planned_cpt_code_id where d.appointment_id=%s order by d.line_number""", [appt_id])
        prov = self.provider[a["provider_id"]]
        today = self.today()
        pc = self.payer_code[a["payer_id"]]
        spec_ot = prov["provider_type"] == "OT"
        therapy = self.spec_code.get(a["specialty_id"]) in ("PT", "OT")
        bp = self.biller_of.get(a["provider_id"]) or a["provider_id"]          # the clinician the visit is billed under
        dx = d.q("select principal_diagnosis_code_id x from encounter where patient_id=%s and principal_diagnosis_code_id is not null order by encounter_date desc limit 1", [a["patient_id"]])
        dx = dx[0]["x"] if dx else None
        vno = d.q("""select count(*) n from encounter e where e.patient_id=%s and e.encounter_date >= coalesce((select max(encounter_date) from encounter where patient_id=%s and encounter_type='evaluation'), date '1900-01-01')""",
                  [a["patient_id"], a["patient_id"]])[0]["n"] + 1
        minutes = (sum(15 * int(l["planned_units"] or 1) for l in lines if l["code"] in THERAPY_TIMED) or 15) if therapy else max(10, sum(l["duration_minutes"] or 15 for l in lines))
        visit_codes = {l["code"] for l in lines}
        skip25 = (self.spec_code.get(a["specialty_id"]) == "ORTHO" and pc == "SYNUHC" and today >= self.rules["uhc_m25_since"] and r.random() < .5)    # the practice forgets modifier 25 on some UHC ortho visits
        enc_no = f"ENC-L{self.n_enc}"
        self.n_enc += 1
        auth = next((l["authorization_id"] for l in lines if l["authorization_id"]), None)
        enc = d.insert("encounter", encounter_number=enc_no, practice_id=self.practice, patient_id=a["patient_id"], encounter_date=today, rendering_provider_id=a["provider_id"],
                       encounter_status="completed", appointment_id=appt_id, payer_id=a["payer_id"], coverage_id=a["coverage_id"], facility_id=a["facility_id"], place_of_service_id=self.pos11,
                       specialty_id=a["specialty_id"], encounter_type=a["appointment_type"], visit_minutes=minutes, note_status="unsigned", charge_status="pending", coding_status="pending",
                       principal_diagnosis_code_id=dx, authorization_id=auth, referral_id=a["referral_id"], referring_provider_id=a["referring_provider_id"], supervising_provider_id=bp if bp != a["provider_id"] else None)
        has_pair = {"97140", "97530"} <= {l["code"] for l in lines}
        for l in lines:
            mods = []
            if therapy:
                mods = [self.mod["GO" if spec_ot else "GP"]]
                if pc in ("SYNMCR", "SYNHUM") and prov["provider_type"] == "PTA":
                    mods.append(self.mod["CQ"])
                elif pc == "SYNMCR" and vno >= 15:
                    mods.append(self.mod["KX"])
                if l["code"] == "97530" and has_pair and not (pc == "SYNAET" and r.random() < .5 and today >= self.rules["aet_xu_since"]):
                    mods.append(self.mod["XU"])
            else:
                if l["code"] in EM_CODES and visit_codes & PROCS and not skip25:
                    mods.append(self.mod["25"])
                if l["code"] == "20610":
                    mods.append(self.mod[r.choice(["RT", "LT"])])
            lvl = {"97161": 1, "97165": 1, "97162": 2, "97166": 2, "97163": 3}.get(l["code"])
            d.insert("encounter_details", encounter_id=enc, line_number=l["line_number"], practice_id=self.practice, patient_id=a["patient_id"], payer_id=a["payer_id"], provider_id=a["provider_id"],
                     cpt_code_id=l["planned_cpt_code_id"], units=l["planned_units"] or 1, service_date=today, rendering_provider_id=a["provider_id"], diagnosis_1_id=dx,
                     modifier_1_id=mods[0], modifier_2_id=mods[1] if len(mods) > 1 else None, procedure_documented=True, documented_level=lvl,
                     time_minutes=15 * int(l["planned_units"] or 1) if therapy and l["code"] in THERAPY_TIMED else None, authorization_id=l["authorization_id"], line_status="coded",
                     expected_charge=l["expected_charge"], place_of_service_id=self.pos11)
        is_eval = therapy and a["appointment_type"] == "evaluation"
        d.insert("document", document_number=f"DOC-L{self.n_doc}", practice_id=self.practice, patient_id=a["patient_id"], document_class="clinical",
                 document_type="evaluation" if is_eval else "daily_note" if therapy else "visit_note", document_status="draft", encounter_id=enc, author_provider_id=a["provider_id"],
                 signer_role="therapist" if therapy else "nurse" if prov["provider_type"] == "RN" else "provider", document_date=today, is_late_entry=False, is_addendum=False,
                 is_locked=False, cosign_required=bp != a["provider_id"] and prov["provider_type"] != "NP", minutes_documented=minutes)
        self.n_doc += 1
        if is_eval and not (pc == "SYNUHC" and r.random() < .06):     # some UHC plans of care are never written (the payer will notice at visit 13)
            d.insert("document", document_number=f"DOC-L{self.n_doc}", practice_id=self.practice, patient_id=a["patient_id"], document_class="clinical", document_type="plan_of_care",
                     document_status="signed", encounter_id=enc, author_provider_id=a["provider_id"], document_date=today, signed_at=self.clock.now().replace(microsecond=0), is_late_entry=False,
                     is_addendum=False, is_locked=True)
            self.n_doc += 1
        d.update("appointment", appt_id, appointment_status="completed")
        d.x("update resource_allocation set allocation_status='used' where appointment_id=%s", [appt_id])
        d.x("update appointment_slot set slot_status='completed' where appointment_id=%s", [appt_id])
        slow = prov["provider_name"].split(",")[0] in self.rules["slow_signers"]
        self.after(r.uniform(3, 6) * DAY if slow else r.uniform(0.1, 2) * DAY, "sign_note", enc)
        self.after(r.uniform(6, 9) * DAY if slow else r.uniform(0.2, 2) * DAY, "charge_entry", enc)
        self.feed("visit", f"Visit: {prov['provider_name'].split(',')[0]} saw a {self.payer[a['payer_id']]['payer_name']} patient ({a['appointment_type'].replace('_', ' ')}, visit {vno})", amount=sum(l["expected_charge"] or 0 for l in lines))

    def ev_sign_note(self, enc_id):
        d = self.db
        e = d.q("select * from encounter where encounter_id=%s", [enc_id])[0]
        if e["note_status"] == "signed":
            return
        today = self.today()
        d.update("encounter", enc_id, note_status="signed", note_signed_date=today, signature_lag_days=(today - e["encounter_date"]).days)
        d.x("update document set document_status='signed', signed_at=%s, is_locked=true where encounter_id=%s and document_status='draft'", [self.clock.now().replace(microsecond=0), enc_id])
        b = d.q("select bill_id, bill_status from bill where encounter_id=%s and bill_type='insurance'", [enc_id])
        self.feed("note", f"Note signed ({(today - e['encounter_date']).days} days after the visit)")
        if b and b[0]["bill_status"] == "on_hold":
            d.update("bill", b[0]["bill_id"], bill_status="open", hold_reason=None, hold_date=None)
            self.after(self.r.uniform(1800, 6 * 3600), "make_claim", b[0]["bill_id"])

    def ev_charge_entry(self, enc_id):
        d = self.db
        e = d.q("select * from encounter where encounter_id=%s", [enc_id])[0]
        if d.q("select 1 from bill where encounter_id=%s", [enc_id]):
            return
        pc = self.payer_code[e["payer_id"]]
        lines = d.q("select * from encounter_details where encounter_id=%s order by line_number", [enc_id])
        total = sum((q2(self.fee[l["cpt_code_id"]] * l["units"]) for l in lines), D(0))
        held = e["note_status"] != "signed"
        selfpay = pc == "SYNSELF"
        today = self.today()
        exp = None if selfpay else q2(sum(self.rate.get((e["payer_id"], l["cpt_code_id"]), D(0)) * l["units"] for l in lines))
        bill = d.insert("bill", bill_number=f"BILL-L{self.n_bill}", practice_id=self.practice, patient_id=e["patient_id"], encounter_id=enc_id, service_date=e["encounter_date"], charge_entered_date=today,
                        bill_status="on_hold" if held else "open", bill_type="self_pay" if selfpay else "insurance", total_billed=total, billing_provider_id=e["supervising_provider_id"] or e["rendering_provider_id"],
                        rendering_provider_id=e["supervising_provider_id"] or e["rendering_provider_id"], specialty_id=e["specialty_id"], payer_id=e["payer_id"], coverage_id=e["coverage_id"], facility_id=e["facility_id"],
                        place_of_service_id=self.pos11, hold_reason="note_unsigned" if held else None, hold_date=today if held else None, claims_created=0, expected_allowed=exp, entered_by_role="biller",
                        patient_statement_flag=False)
        self.n_bill += 1
        for l in lines:
            bd = d.insert("bill_details", bill_id=bill, line_number=l["line_number"], practice_id=self.practice, patient_id=e["patient_id"], payer_id=e["payer_id"], provider_id=e["supervising_provider_id"] or l["provider_id"],
                          cpt_code_id=l["cpt_code_id"], units=l["units"], fee_per_unit=self.fee[l["cpt_code_id"]], billed_amount=q2(self.fee[l["cpt_code_id"]] * l["units"]),
                          line_status="held" if held else "open", service_date=e["encounter_date"], modifier_1_id=l["modifier_1_id"], modifier_2_id=l["modifier_2_id"], diagnosis_1_id=l["diagnosis_1_id"],
                          rendering_provider_id=e["supervising_provider_id"] or l["rendering_provider_id"], encounter_detail_id=l["encounter_detail_id"], charge_entered_date=today,
                          expected_allowed=q2(self.rate.get((e["payer_id"], l["cpt_code_id"]), D(0)) * l["units"]) if not selfpay else None, authorization_id=l["authorization_id"],
                          place_of_service_id=self.pos11, entered_by_role="biller")
            self.txn(bd, e["patient_id"], "charge", q2(self.fee[l["cpt_code_id"]] * l["units"]), q2(self.fee[l["cpt_code_id"]] * l["units"]), "patient" if selfpay else "payer", payer_id=e["payer_id"])
        d.update("encounter", enc_id, charge_status="charged", coding_status="coded")
        self.feed("charge", f"Charge entered ${float(total):,.0f}" + (" (held: note unsigned)" if held else ""), amount=total)
        if not held and not selfpay:
            self.after(self.r.uniform(1800, 4 * 3600), "make_claim", bill)

    def txn(self, bill_detail, patient, kind, amount, effect, party, **kw):
        n = self.n_txn
        self.n_txn += 1
        return self.db.insert("transactions", transaction_number=f"TXN-L{n}", practice_id=self.practice, patient_id=patient, bill_detail_id=bill_detail, transaction_type=kind, amount=q2(amount),
                              balance_effect=q2(effect), transaction_date=self.today(), responsible_party=party, posted_date=self.today(), **kw)

    # ------------------------------------------------------------------ claims and the clearinghouse
    def ev_make_claim(self, bill_id):
        d = self.db
        b = d.q("select * from bill where bill_id=%s", [bill_id])[0]
        if b["claims_created"] or b["bill_status"] != "open" or b["bill_type"] != "insurance":
            return
        e = d.q("select * from encounter where encounter_id=%s", [b["encounter_id"]])[0]
        today = self.today()
        cl = d.insert("claim", claim_number=f"CLM-L{self.n_claim}", practice_id=self.practice, payer_id=b["payer_id"], patient_id=b["patient_id"], billing_provider_id=b["billing_provider_id"],
                      service_date_from=b["service_date"], submitted_date=today, total_charge=b["total_billed"], claim_status="ready", rendering_provider_id=b["rendering_provider_id"],
                      facility_id=b["facility_id"], place_of_service_id=self.pos11, specialty_id=b["specialty_id"], coverage_id=b["coverage_id"], claim_sequence="primary", frequency_code="1",
                      bill_id=bill_id, encounter_id=b["encounter_id"], principal_diagnosis_code_id=e["principal_diagnosis_code_id"], authorization_id=e["authorization_id"], claim_type="professional",
                      signature_on_file="Y", balance=b["total_billed"])
        self.n_claim += 1
        for l in d.q("select * from bill_details where bill_id=%s order by line_number", [bill_id]):
            d.insert("claim_details", claim_id=cl, line_number=l["line_number"], practice_id=self.practice, payer_id=b["payer_id"], patient_id=b["patient_id"], billing_provider_id=b["billing_provider_id"],
                     cpt_code_id=l["cpt_code_id"], units=l["units"], charge_amount=l["billed_amount"], line_status="pending", paid_amount=0, service_date=l["service_date"],
                     modifier_1_id=l["modifier_1_id"], modifier_2_id=l["modifier_2_id"], diagnosis_pointers="1", primary_diagnosis_code_id=l["diagnosis_1_id"], rendering_provider_id=l["rendering_provider_id"],
                     expected_allowed=l["expected_allowed"], bill_detail_id=l["bill_detail_id"])
        d.update("bill", bill_id, claims_created=1, latest_claim_status="ready", ready_to_bill_date=today)
        self.feed("claim", f"Claim ready for release (not sent yet)", claim=cl, amount=b["total_billed"])
        self.at(self.clock.now() + dt.timedelta(hours=3), "release_claim", cl, 0)

    def ev_release_claim(self, claim_id, waited):
        d = self.db
        c = d.q("select claim_status from claim where claim_id=%s", [claim_id])[0]
        if c["claim_status"] != "ready":
            return
        if self.rules["mirror_enforce"] and waited < 3 * DAY:
            hold = d.q("""select 1 from agent_task t join agent_decision x on x.agent_decision_id=t.agent_decision_id where t.agent_code='A5' and t.entity_type='claim' and t.entity_id=%s and t.task_status='open'""", [claim_id])
            if hold:
                self.at(self.clock.now() + dt.timedelta(hours=2), "release_claim", claim_id, waited + 7200)
                return
        self.history(claim_id, "submitted", "submitted", "837")
        d.update("claim", claim_id, claim_status="submitted", last_status_date=self.today())
        self.feed("submitted", "Claim sent to the clearinghouse", claim=claim_id)
        self.at(self.clock.now() + dt.timedelta(minutes=30), "ack", claim_id)

    def history(self, claim_id, event, status_after, cat, **kw):
        c = self.db.q("select payer_id, patient_id from claim where claim_id=%s", [claim_id])[0]
        return self.db.insert("claim_status_history", claim_id=claim_id, event_type=event, event_date=self.today(), status_after=status_after, practice_id=self.practice, payer_id=c["payer_id"],
                              patient_id=c["patient_id"], event_ts=self.clock.now().replace(microsecond=0), status_category=cat, channel="clearinghouse", **kw)

    def ev_ack(self, claim_id):
        self.history(claim_id, "acknowledged_999", "acknowledged", "A1")
        self.at(self.clock.now() + dt.timedelta(hours=2), "accept", claim_id, False)

    def ev_accept(self, claim_id, corrected):
        d, r = self.db, self.r
        c = d.q("select * from claim where claim_id=%s", [claim_id])[0]
        if not corrected and r.random() < self.rules["reject_prob"]:
            why = r.choice(["billing_npi_mismatch", "missing_info"])
            self.history(claim_id, "rejected_277ca", "rejected", "A3", is_rejection=True, rejection_reason=why, rejection_category="technical", is_technical=True, owner_role="biller")
            d.update("claim", claim_id, claim_status="rejected", last_status_date=self.today())
            self.feed("rejected", f"Rejected by the clearinghouse: {why.replace('_', ' ')}", claim=claim_id)
            return
        self.history(claim_id, "accepted_277ca", "accepted", "A1", payer_claim_number=f"PCN{claim_id:08d}")
        d.update("claim", claim_id, claim_status="accepted", payer_claim_number=f"PCN{claim_id:08d}", last_status_date=self.today())
        self.feed("accepted", "Accepted by the clearinghouse; waiting on the payer", claim=claim_id)
        if r.random() < self.rules["stall_prob"]:
            return                                          # this payer never answers
        turn = self.payer[c["payer_id"]]["standard_turnaround_days"] + r.randint(-3, 6)
        if c["payer_id"] in self.rules["stalled_payers"]:
            turn += 40
        self.after(max(2, turn) * DAY, "adjudicate", claim_id)

    # ------------------------------------------------------------------ the payer decides (hidden rules)
    def ev_adjudicate(self, claim_id):
        d, r = self.db, self.r
        c = d.q("select * from claim where claim_id=%s", [claim_id])[0]
        if c["claim_status"] not in ("accepted", "submitted", "no_response"):
            return
        if c["payer_id"] in self.rules["stalled_payers"]:
            self.after(5 * DAY, "adjudicate", claim_id)
            return
        pc = self.payer_code[c["payer_id"]]
        e = d.q("select * from encounter where encounter_id=%s", [c["encounter_id"]])[0]
        cv = d.q("select * from coverage where coverage_id=%s", [c["coverage_id"]])[0]
        lines = d.q("select * from claim_details where claim_id=%s order by line_number", [claim_id])
        codes = [self.cpt[l["cpt_code_id"]] for l in lines]
        vno = d.q("""select count(*) n from encounter x where x.patient_id=%s and x.encounter_date <= %s and x.encounter_date >= coalesce((select max(encounter_date) from encounter where patient_id=%s and encounter_type='evaluation' and encounter_date <= %s), date '1900-01-01')""",
                  [e["patient_id"], e["encounter_date"], e["patient_id"], e["encounter_date"]])[0]["n"]
        poc = d.q("""select count(*) n from document where patient_id=%s and document_type='plan_of_care' and document_date <= %s and document_date >= coalesce((select max(encounter_date) from encounter where patient_id=%s and encounter_type='evaluation' and encounter_date <= %s), date '1900-01-01')""",
                  [e["patient_id"], e["encounter_date"], e["patient_id"], e["encounter_date"]])[0]["n"]
        therapy = self.spec_code.get(c["specialty_id"]) in ("PT", "OT")
        ortho = self.spec_code.get(c["specialty_id"]) == "ORTHO"
        m25 = self.mod["25"]
        m25_line = next((l["line_number"] for l, k in zip(lines, codes) if k in EM_CODES and m25 not in (l["modifier_1_id"], l["modifier_2_id"])), None)
        auth_over = False
        if e["authorization_id"]:
            au = d.q('select units_approved from "authorization" where authorization_id=%s', [e["authorization_id"]])[0]
            used = d.q("select count(*) n from encounter where authorization_id=%s and encounter_date <= %s", [e["authorization_id"], e["encounter_date"]])[0]["n"]
            auth_over = used > au["units_approved"]
        claim_reason = None
        if cv["termination_date"] and cv["termination_date"] < e["encounter_date"]:
            claim_reason = ("27", None)
        elif c["patient_id"] % 67 == 0 and vno <= 2 and pc != "SYNMCR":
            claim_reason = ("22", "N479")
        elif auth_over:
            claim_reason = ("198", "N130")
        elif pc == "SYNUHC" and therapy and self.rules["uhc_poc_visit"] and vno >= self.rules["uhc_poc_visit"] and not poc:
            claim_reason = ("50", "N115")
        elif pc == "SYNHUM" and set(codes) & PROC_AUTH and not e["authorization_id"]:
            claim_reason = ("197", "N130")
        elif pc == "SYNUHC" and ortho and e["encounter_date"] >= self.rules["uhc_m25_since"] and set(codes) & PROCS and m25_line:
            claim_reason = ("4", "MA130")
        elif r.random() < self.rules["base_denial"]:
            claim_reason = (r.choices(["16", "11", "18", "252", "4", "97"], [30, 15, 10, 15, 10, 15])[0], "MA130")
        rows, first_pay = [], True
        for l, code in zip(lines, codes):
            contract = q2(self.rate.get((c["payer_id"], l["cpt_code_id"]), D(0)) * l["units"])
            allowed = contract
            if pc == "SYNBCBS" and code == "97140" and self.rules["bcbs_97140"] < 1:
                allowed = q2(contract * self.rules["bcbs_97140"])
            if self.mod["CQ"] in (l["modifier_1_id"], l["modifier_2_id"]):
                allowed = q2(allowed * D("0.85"))
            if self.provider[c["rendering_provider_id"]]["provider_type"] == "NP" and self.payer_type[c["payer_id"]] in ("medicare", "medicare_advantage"):
                allowed = q2(allowed * D("0.85"))                 # nurse practitioners are paid 85% of the physician rate
            reason = claim_reason[0] if claim_reason and (claim_reason[0] not in ("11", "4", "97") or l["line_number"] == (m25_line if claim_reason == ("4", "MA130") and m25_line else 1)) else None
            if pc == "SYNAET" and code == "97530" and "97140" in codes and not ({self.mod["XU"], self.mod["59"]} & {l["modifier_1_id"], l["modifier_2_id"]}) and d_ge(self.today(), self.rules["aet_xu_since"]):
                reason, claim_reason = "97", claim_reason or ("97", "M86")
            if reason:
                pr = D(0)
            elif pc == "SYNMCR":
                pr = q2(allowed * D("0.2"))
            else:
                pr = min(q2(cv["copay_amount"] or 0), allowed) if first_pay else D(0)
                first_pay = False
            rows.append(dict(l=l, code=code, contract=contract, allowed=allowed, reason=reason, pr=pr))
        paid_total = sum((x["allowed"] - x["pr"] for x in rows if not x["reason"]), D(0))
        payment = None
        unposted = r.random() < self.rules["unposted_prob"]
        if paid_total > 0:
            n = self.n_pay
            self.n_pay += 1
            payment = d.insert("payment", payment_number=f"PAY-L{n}", practice_id=self.practice, payment_source="payer", payment_date=self.today(), payment_amount=q2(paid_total), payment_method="eft",
                               payer_id=c["payer_id"], payment_type="era", received_date=self.today(), posted_date=None if unposted else self.today(), credit_debit="C", has_remittance=True, claim_count=1,
                               posted_amount=D(0) if unposted else q2(paid_total), unapplied_amount=q2(paid_total) if unposted else D(0), plb_amount=D(0), reconciles=not unposted, is_void=False)
        tot = dict(paid=D(0), adj=D(0), den=D(0), pr=D(0))
        for x in rows:
            l = x["l"]
            if x["reason"]:
                carc = self.carc[x["reason"]]
                dn = d.insert("denial", claim_id=claim_id, claim_detail_id=l["claim_detail_id"], practice_id=self.practice, patient_id=c["patient_id"], payer_id=c["payer_id"], denial_date=self.today(),
                              denied_amount=l["charge_amount"], adjustment_reason_id=carc["adjustment_reason_id"], denial_status="open", bill_detail_id=l["bill_detail_id"], group_code="CO",
                              reason_category=carc["reason_category"], clock_start_date=self.today(), appeal_deadline=self.today() + dt.timedelta(days=self.payer[c["payer_id"]]["appeal_days"]),
                              upstream_stage=carc["upstream_stage"], is_preventable=carc["is_preventable_default"], is_technical=carc["is_technical"], owner_role=carc["owner_role"], is_repeat=False,
                              denial_count_on_line=1, cpt_code_id=l["cpt_code_id"], provider_id=c["rendering_provider_id"], is_claim_level=False, units_denied=l["units"], authorization_id=c["authorization_id"],
                              outcome="pending", recovered_amount=D(0))
                rk = (claim_reason[1] if claim_reason and claim_reason[0] == x["reason"] else None) or "MA130"
                d.insert("denial_details", denial_id=dn, detail_seq=1, detail_type="CARC", adjustment_reason_id=carc["adjustment_reason_id"], remark_code_id=self.rarc[rk], group_code="CO",
                         reason_amount=l["charge_amount"], is_amount_allocated=True, is_primary=True, claim_detail_id=l["claim_detail_id"], denial_date=self.today())
                self.txn(l["bill_detail_id"], c["patient_id"], "denial", l["charge_amount"], 0, "payer", claim_id=claim_id, claim_detail_id=l["claim_detail_id"], payer_id=c["payer_id"], denial_id=dn,
                         adjustment_reason_id=carc["adjustment_reason_id"], group_code="CO", cpt_code_id=l["cpt_code_id"])
                d.update("claim_details", l["claim_detail_id"], line_status="denied", paid_amount=0, patient_responsibility=0, contractual_adjustment=0, denied_amount=l["charge_amount"],
                         primary_denial_reason_id=carc["adjustment_reason_id"])
                tot["den"] += l["charge_amount"]
            else:
                paid = x["allowed"] - x["pr"]
                contr = l["charge_amount"] - x["allowed"]
                d.update("claim_details", l["claim_detail_id"], line_status="paid", paid_amount=q2(paid), allowed_amount=x["allowed"], patient_responsibility=x["pr"], contractual_adjustment=q2(contr), denied_amount=0)
                if not unposted and paid > 0:
                    self.txn(l["bill_detail_id"], c["patient_id"], "payment", paid, -paid, "payer", claim_id=claim_id, claim_detail_id=l["claim_detail_id"], payer_id=c["payer_id"], payment_id=payment,
                             cpt_code_id=l["cpt_code_id"], payment_method="eft")
                if contr > 0:
                    self.txn(l["bill_detail_id"], c["patient_id"], "adjustment", contr, -contr, "payer", transaction_subtype="contractual", claim_id=claim_id, claim_detail_id=l["claim_detail_id"],
                             payer_id=c["payer_id"], adjustment_reason_id=self.carc["45"]["adjustment_reason_id"], group_code="CO", cpt_code_id=l["cpt_code_id"])
                if x["pr"] > 0:
                    self.txn(l["bill_detail_id"], c["patient_id"], "adjustment", x["pr"], 0, "patient", transaction_subtype="patient_responsibility", claim_id=claim_id, claim_detail_id=l["claim_detail_id"],
                             payer_id=c["payer_id"], adjustment_reason_id=self.carc["3" if pc != "SYNMCR" else "2"]["adjustment_reason_id"], group_code="PR", cpt_code_id=l["cpt_code_id"])
                tot["paid"] += paid
                tot["adj"] += contr
                tot["pr"] += x["pr"]
        status = "denied" if tot["den"] and not tot["paid"] else "partial" if tot["den"] else "paid"
        d.update("claim", claim_id, claim_status=status, paid_amount=q2(tot["paid"]), patient_responsibility=q2(tot["pr"]), adjusted_amount=q2(tot["adj"]), denied_amount=q2(tot["den"]),
                 balance=q2(tot["den"] + tot["pr"]), last_payment_date=self.today() if tot["paid"] else None, last_status_date=self.today())
        self.history(claim_id, "remit_835", status, "F1" if status == "paid" else "F2", reported_paid_amount=q2(tot["paid"]))
        d.update("bill", c["bill_id"], bill_status={"paid": "paid", "denied": "denied", "partial": "partial"}[status], latest_claim_status=status)
        if status == "paid":
            self.feed("paid", f"Paid ${float(tot['paid']):,.0f} by {self.payer[c['payer_id']]['payer_name']}" + (" (remit not posted)" if unposted else ""), claim=claim_id, amount=tot["paid"])
        else:
            self.feed("denied", f"{self.payer[c['payer_id']]['payer_name']} {status}: CARC {claim_reason[0] if claim_reason else '97'} ${float(tot['den']):,.0f}", claim=claim_id, amount=tot["den"])

    # ------------------------------------------------------------------ appeals
    def ev_decide_appeal(self, appeal_id):
        d, r = self.db, self.r
        a = d.q("select * from appeal where appeal_id=%s", [appeal_id])[0]
        dn = d.q("select * from denial where denial_id=%s", [a["denial_id"]])[0]
        carc = self.carc_by_id[dn["adjustment_reason_id"]]["carc_code"]
        p = {"50": .55, "97": .45, "197": .35, "4": .45, "11": .45, "16": .5, "252": .5, "18": .1, "198": .15, "27": .05, "22": .2}.get(carc, .25)
        won = r.random() < p
        today = self.today()
        if won:
            cd = d.q("select * from claim_details where claim_detail_id=%s", [dn["claim_detail_id"]])[0]
            c = d.q("select * from claim where claim_id=%s", [dn["claim_id"]])[0]
            contract = q2(self.rate.get((dn["payer_id"], cd["cpt_code_id"]), D(0)) * cd["units"])
            n = self.n_pay
            self.n_pay += 1
            pay = d.insert("payment", payment_number=f"PAY-L{n}", practice_id=self.practice, payment_source="payer", payment_date=today, payment_amount=contract, payment_method="eft", payer_id=dn["payer_id"],
                           payment_type="era", received_date=today, posted_date=today, credit_debit="C", has_remittance=True, claim_count=1, posted_amount=contract, unapplied_amount=D(0), plb_amount=D(0),
                           reconciles=True, is_void=False)
            self.txn(cd["bill_detail_id"], dn["patient_id"], "payment", contract, -contract, "payer", claim_id=dn["claim_id"], claim_detail_id=cd["claim_detail_id"], payer_id=dn["payer_id"],
                     payment_id=pay, denial_id=dn["denial_id"], cpt_code_id=cd["cpt_code_id"], payment_method="eft")
            d.update("claim_details", cd["claim_detail_id"], line_status="paid", paid_amount=contract, allowed_amount=contract, denied_amount=0)
            d.update("denial", dn["denial_id"], denial_status="resolved", outcome="overturned", resolved_date=today, recovered_amount=contract)
            d.update("appeal", appeal_id, appeal_status="won", decision_date=today, payer_decision="overturned", is_overturned=True, recovered_amount=contract)
            left = d.q("select count(*) n from denial where claim_id=%s and denial_status<>'resolved'", [dn["claim_id"]])[0]["n"]
            d.update("claim", dn["claim_id"], paid_amount=q2((c["paid_amount"] or 0) + contract), denied_amount=q2(max(D(0), (c["denied_amount"] or 0) - dn["denied_amount"])), claim_status="paid" if not left else "partial")
            self.feed("win", f"Appeal won: ${float(contract):,.0f} recovered", claim=dn["claim_id"], amount=contract)
        else:
            d.update("denial", dn["denial_id"], denial_status="upheld", outcome="upheld", resolved_date=today)
            d.update("appeal", appeal_id, appeal_status="lost", decision_date=today, payer_decision="upheld", is_overturned=False)
            self.feed("lost", "Appeal lost: the payer upheld the denial", claim=dn["claim_id"])

    # ------------------------------------------------------------------ what people do (tasks raised by the agents)
    def inbox(self, role):
        with self.lock:
            return self._inbox(role)

    def _inbox(self, role):
        return self.db.q("""select t.agent_task_id, t.agent_code, t.task_type, t.owner_role, t.title, t.created_date, t.due_date, t.priority, t.amount_at_stake, t.claim_id, t.agent_decision_id, t.agent_finding_id,
                                  f.summary, f.suggested_value, f.severity, f.deadline_date, c.claim_number
                           from agent_task t left join agent_finding f on f.agent_finding_id=t.agent_finding_id left join claim c on c.claim_id=t.claim_id
                           where t.task_status='open' and t.owner_role=%s order by case t.priority when 'hi' then 0 when 'md' then 1 else 2 end, t.created_date, t.agent_task_id limit 60""", [role])

    def act(self, task_id, action, who="you"):
        with self.lock:
            return self._act(task_id, action, who)

    def _act(self, task_id, action, who):
        d = self.db
        t = d.q("select * from agent_task where agent_task_id=%s", [task_id])
        if not t or t[0]["task_status"] != "open":
            return dict(ok=False, msg="that task is no longer open")
        t = t[0]
        if action not in ACTIONS.get(t["task_type"], []) + (["auto"] if who == "bot" else []):
            return dict(ok=False, msg=f"unknown action {action}")
        f = (d.q("select * from agent_finding where agent_finding_id=%s", [t["agent_finding_id"]]) or [None])[0]
        msg = getattr(self, "do_" + t["task_type"])(t, f, action if action != "auto" else ACTIONS[t["task_type"]][0], who)
        today = self.today()
        mins = max(1, int(BASE_MIN.get(t["task_type"], 15) * self.r.uniform(.7, 1.4)))
        staff_no = ROLE_STAFF.get(t["owner_role"], "B01")
        d.update("agent_task", task_id, task_status="done", completed_date=today, outcome="resolved" if action not in ("release_as_is", "accept_denial", "dismiss", "close", "reject_rule") else "closed",
                 minutes_spent=mins, assigned_to=self.staff[staff_no], contact_channel="inbox" if who == "you" else "staff bot")
        if t["agent_decision_id"]:
            d.update("agent_decision", t["agent_decision_id"], human_outcome="accepted" if action in ("fix_and_release", "send_appeal", "chase_provider", "correct_and_resubmit", "resubmit", "send_dispute", "approve_rule") else "overridden",
                     human_outcome_date=today)
        if f and f["finding_status"] in ("open", "in_progress"):
            d.update("agent_finding", f["agent_finding_id"], finding_status="resolved", resolved_date=today, resolution=action[:20])
        self.feed("human", f"{'You' if who == 'you' else 'Staff bot'} ({t['owner_role'].replace('_', ' ')}): {msg}", claim=t["claim_id"])
        return dict(ok=True, msg=msg)

    def approval(self, task, kind, amount, writeback=None):
        d = self.db
        if not task["agent_decision_id"]:
            return None
        aid = d.insert("agent_approval", agent_decision_id=task["agent_decision_id"], approval_type=kind, approval_status="approved", approved_by=self.staff[ROLE_STAFF.get(task["owner_role"], "B03")],
                       approver_role=task["owner_role"], approval_date=self.today(), amount_approved=q2(amount or 0), limit_checked=True, entity_type=task["entity_type"], entity_id=task["entity_id"],
                       practice_id=self.practice, approval_ts=self.clock.now().replace(microsecond=0), agent_task_id=task["agent_task_id"])
        if writeback:
            d.insert("agent_writeback", agent_decision_id=task["agent_decision_id"], target_system=writeback[0], writeback_type=writeback[1], send_status="suppressed", attempted_at=self.clock.now().replace(microsecond=0),
                     agent_approval_id=aid, agent_code=task["agent_code"], entity_type=task["entity_type"], entity_id=task["entity_id"], attempt_no=1, practice_id=self.practice, claim_id=task["claim_id"])
        return aid

    def do_unsigned_note(self, t, f, action, who):
        self.after(self.r.uniform(2, 8) * 3600, "sign_note", t["entity_id"])
        return "chased the provider; the note will be signed shortly"

    def do_claim_hold_review(self, t, f, action, who):
        d = self.db
        fix = (f or {}).get("suggested_value")
        c = d.q("select * from claim where claim_id=%s", [t["claim_id"]])[0]
        e = d.q("select * from encounter where encounter_id=%s", [c["encounter_id"]])[0]
        done = "released as it was"
        if action == "fix_and_release":
            if fix == "attach_poc":
                d.insert("document", document_number=f"DOC-L{self.n_doc}", practice_id=self.practice, patient_id=c["patient_id"], document_class="clinical", document_type="plan_of_care", document_status="signed",
                         encounter_id=c["encounter_id"], author_provider_id=c["rendering_provider_id"], document_date=e["encounter_date"], signed_at=self.clock.now().replace(microsecond=0), is_late_entry=True,
                         is_addendum=False, is_locked=True)
                self.n_doc += 1
                done = "attached the plan of care, then released"
            elif fix == "add_xu":
                l = d.q("select claim_detail_id, modifier_2_id from claim_details where claim_id=%s and cpt_code_id=%s", [t["claim_id"], self.cpt_id["97530"]])
                if l:
                    d.update("claim_details", l[0]["claim_detail_id"], modifier_2_id=self.mod["XU"])
                done = "added modifier XU to the 97530 line, then released"
            elif fix == "add_25":
                l = d.q("""select claim_detail_id, modifier_1_id, modifier_2_id from claim_details cd join cpt_code k using (cpt_code_id) where cd.claim_id=%s and k.code = any(%s)
                           and %s not in (coalesce(cd.modifier_1_id,0), coalesce(cd.modifier_2_id,0)) order by cd.line_number""", [t["claim_id"], sorted(EM_CODES), self.mod["25"]])
                for x in l:
                    d.update("claim_details", x["claim_detail_id"], **({"modifier_1_id": self.mod["25"]} if not x["modifier_1_id"] else {"modifier_2_id": self.mod["25"]}))
                done = "added modifier 25 to the E/M line, then released"
            elif fix == "get_auth":
                done = "asked the front desk for the prior authorization, then released"
            elif fix == "extend_auth" and e["authorization_id"]:
                d.x('update "authorization" set units_approved = units_approved + 8 where authorization_id=%s', [e["authorization_id"]])
                done = "got more visits approved on the authorization, then released"
            else:
                done = "nothing to fix here, released"
        if c["claim_status"] == "ready":
            self.at(self.clock.now() + dt.timedelta(minutes=5), "release_claim", t["claim_id"], 10 ** 9)
        return done

    def do_fix_rejection(self, t, f, action, who):
        c = self.db.q("select claim_status from claim where claim_id=%s", [t["claim_id"]])[0]
        if c["claim_status"] == "rejected":
            self.history(t["claim_id"], "resubmitted", "submitted", "837")
            self.db.update("claim", t["claim_id"], claim_status="submitted")
            self.at(self.clock.now() + dt.timedelta(hours=3), "accept", t["claim_id"], True)
        return "corrected the claim and resubmitted it"

    def do_claim_follow_up(self, t, f, action, who):
        if action == "resubmit":
            self.history(t["claim_id"], "resubmitted", "submitted", "837")
            self.db.update("claim", t["claim_id"], claim_status="submitted")
            self.at(self.clock.now() + dt.timedelta(hours=3), "accept", t["claim_id"], True)
            return "resubmitted the claim to the payer"
        return "closed the follow-up"

    def do_denial_work(self, t, f, action, who):
        d = self.db
        if action != "send_appeal":
            d.update("denial", t["entity_id"], denial_status="accepted", outcome="accepted")
            return "accepted the denial"
        dn = d.q("select * from denial where denial_id=%s", [t["entity_id"]])[0]
        n = self.n_apl
        self.n_apl += 1
        ap = d.insert("appeal", appeal_number=f"APL-L{n}", denial_id=dn["denial_id"], appeal_level="first", appeal_status="submitted", clock_start_date=dn["denial_date"], deadline_date=dn["appeal_deadline"],
                      claim_id=dn["claim_id"], submitted_date=self.today(), submission_channel="portal", amount_disputed=dn["denied_amount"], evidence_count=self.r.randint(1, 4), practice_id=self.practice,
                      patient_id=dn["patient_id"], payer_id=dn["payer_id"], agent_decision_id=t["agent_decision_id"])
        aid = self.approval(t, "appeal_send", dn["denied_amount"], ("portal", "appeal_submit"))
        if aid:
            d.update("appeal", ap, agent_approval_id=aid)
        d.update("denial", dn["denial_id"], denial_status="in_appeal")
        self.after(self.r.uniform(14, 30) * DAY, "decide_appeal", ap)
        return "sent the appeal (the payer will decide in two to four weeks)"

    def do_dispute_package(self, t, f, action, who):
        if action == "send_dispute":
            self.approval(t, "dispute_send", t["amount_at_stake"], ("portal", "dispute_submit"))
            return "sent the underpayment dispute (write-back suppressed in shadow mode)"
        return "dismissed the dispute"

    def do_rule_review(self, t, f, action, who):
        d = self.db
        if action == "approve_rule":
            d.update("payer_rule", t["entity_id"], is_enabled=True, approval_status="approved", approved_by_staff_id=self.staff["M01"], approved_date=self.today(), effective_from=self.today(), last_confirmed_date=self.today())
            self.approval(t, "rule_activation", 0)
            return "approved the new payer rule; Mirror starts using it"
        d.update("payer_rule", t["entity_id"], approval_status="rejected")
        return "rejected the proposed rule"

    def bot_sweep(self):
        """A staff bot picks up anything a person has left for more than BOT_AFTER_DAYS simulated days, so the system never stalls."""
        cutoff = self.today() - dt.timedelta(days=BOT_AFTER_DAYS)
        for t in self.db.q("select agent_task_id from agent_task where task_status='open' and task_type <> 'rule_review' and created_date <= %s limit 40", [cutoff]):
            self.act(t["agent_task_id"], "auto", who="bot")

    # ------------------------------------------------------------------ things you can break on purpose
    def chaos(self, kind, **kw):
        with self.lock:
            return self._chaos(kind)

    def _chaos(self, kind):
        d, today = self.db, self.today()
        if kind == "end_coverage":
            p = d.q("""select a.patient_id, a.coverage_id from appointment a join coverage v on v.coverage_id=a.coverage_id where a.appointment_status='scheduled' and a.appointment_date between %s and %s
                       and v.termination_date is null and a.payer_id <> (select payer_id from payer where payer_code='SYNSELF') order by random() limit 1""", [today, today + dt.timedelta(days=3)])
            if not p:
                return "no patient with a visit in the next three days"
            d.update("coverage", p[0]["coverage_id"], termination_date=today - dt.timedelta(days=1))
            return f"coverage for patient #{p[0]['patient_id']} ended yesterday; they have a visit this week"
        if kind == "bcbs_underpay":
            self.rules["bcbs_97140"] = D("0.80")
            return "BCBS now pays 80% of the contract on manual therapy (97140)"
        if kind == "uhc_poc":
            self.rules["uhc_poc_visit"] = 10
            return "UnitedHealthcare now wants a plan of care from visit 10 (was 13)"
        if kind == "aetna_xu":
            self.rules["aet_xu_since"] = today
            return "Aetna now enforces the distinct-service modifier on 97530 billed with 97140"
        if kind == "stall_payer":
            pid = next(k for k, v in self.payer_code.items() if v == "SYNCIG")
            self.rules["stalled_payers"].add(pid)
            return "Cigna has stopped answering claims"
        if kind == "provider_slow":
            self.rules["slow_signers"].add("Okafor")
            return "Dr. Okafor has stopped signing notes on time"
        if kind == "mirror_enforce":
            self.rules["mirror_enforce"] = not self.rules["mirror_enforce"]
            return "Mirror now holds claims until a person releases them" if self.rules["mirror_enforce"] else "Mirror is back in shadow mode (advises only)"
        return "unknown"


def d_ge(a, b):
    return a >= b
