"""The replay engine: walks the calendar over the loaded history and lets the fifteen agents react day by day.

Each simulated day: (1) scheduled human actions that fall due are applied, (2) that day's real events are released from the
history, (3) every agent evaluates the events that reached it, using only rows known by that day (rules first, no model),
(4) the new agent rows are queued for the database writer. Shadow mode: nothing is sent anywhere.
"""
import datetime as dt
import bisect
import heapq
import queue
import json
import os
import re
import threading
import time
from collections import defaultdict
from decimal import Decimal

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "synth"))
from core import Synth, h, connect, TODAY  # noqa: E402
from journey import q, is_biz, next_biz  # noqa: E402
import tracelog  # noqa: E402
from world import connect_replay, is_r2  # noqa: E402

D = Decimal


def _env_date(name, default):
    v = os.environ.get(name, "").strip()
    return dt.date.fromisoformat(v) if v else default


# The simulated calendar. Defaults are today's canonical window; KRISNNAI_REPLAY_START / KRISNNAI_REPLAY_END (ISO dates) override it, e.g. for a one-month run on R2.
START = _env_date("KRISNNAI_REPLAY_START", dt.date(2025, 11, 3))
TODAY = _env_date("KRISNNAI_REPLAY_END", TODAY)
# Dates the agents used to hard-code, now expressed relative to START (identical to the old constants when START is the default).
RULES_FROM = START - dt.timedelta(days=2)             # was 2025-11-01
A15_FROM = START + dt.timedelta(days=63)              # was 2026-01-05
A14_FROM = START + dt.timedelta(days=91)              # was 2026-02-02
# A5 reviews a claim on the day it is submitted. R2 claims are dated on any weekday/weekend, and the engine only runs on business days, so for R2 (or KRISNNAI_REPLAY_A5_NEXT_BIZ=1)
# a claim submitted on a non-business day is reviewed on the NEXT business day, using only what is known by that day. Canonical default: unchanged.
A5_NEXT_BIZ = is_r2() or os.environ.get("KRISNNAI_REPLAY_A5_NEXT_BIZ", "") == "1"
# A12 on R2 reads the latest ar_snapshot known on the replay date (rule 9) instead of one current snapshot.
AR_AS_OF = is_r2()
VERSION = "v0.9-shadow"
NAMES = {"A1": "Gatekeeper", "A2": "Permit Clerk", "A3": "Note Chaser", "A4": "Code Whisperer", "A5": "Mirror", "A6": "Courier", "A7": "Hunter",
         "A8": "Advocate", "A9": "Coach", "A10": "Auditor", "A11": "Bookkeeper", "A12": "Concierge", "A13": "Credentialing", "A14": "Captain", "A15": "Detective"}
ROLE_STAFF = {"front_desk": ["FD01", "FD02"], "biller": ["B01", "B02"], "denial_specialist": ["D01"], "coder": ["C01", "C02", "C03"], "ar_specialist": ["AR01"],
              "payment_poster": ["PP01"], "billing_lead": ["B03"], "manager": ["M01"], "provider": [], "patient_billing": ["B01", "B02"]}
SPEED = {"C02": 1.5, "B02": 1.1, "FD02": 1.3, "C03": .8}
REWORK = {"C02": .10, "B02": .14, "C03": .18, "FD02": .12, "D01": .05}
BASE_MIN = {"authorization_check": 14, "coverage_follow_up": 12, "unsigned_note": 6, "code_review": 18, "claim_hold_review": 16, "fix_rejection": 11, "claim_follow_up": 22,
            "denial_work": 26, "dispute_package": 40, "post_remit": 14, "patient_follow_up": 9, "revalidation": 35, "rule_review": 20, "unbilled_visit": 10}
SLA = {"hi": 1, "md": 3, "lo": 5}
AGENT_TABLES = ["payer_rule", "agent_run", "agent_decision", "agent_finding", "agent_task", "agent_decision_details", "agent_approval", "agent_writeback", "agent_value",
                "agent_forecast", "patient_statement"]
TEMPLATES = {"50": ("R-UHC-POC-V", "documentation", "plan_of_care"), "97": ("R-AET-XU", "coding", "xu_modifier")}


# ====================================================================== finite staff capacity (R2; canonical keeps the old "everything done in 1-11 days" model)
# On R2 a task is no longer scheduled to finish by a random lag. It joins its role's backlog and the role's staff work it, a fixed number of items per working day,
# highest score first (amount x urgency, the ranking the site uses), with carry-over to the next working day. Weekends and holidays are off (journey.is_biz).
CAPACITY = is_r2() or os.environ.get("KRISNNAI_REPLAY_CAPACITY", "") == "1"
# engine role -> (R2 staff_role whose people do the work, share of their working time spent on this queue, items one full-time person clears per working day)
# Items per day follow the minutes in BASE_MIN: 480 min x ~75% productive time (calls on hold, meetings, breaks, training) / minutes per item, then scaled for how quick the
# typical item is (a hold review on a known payer rule is a few minutes; an appeal prep is long). The people come from canon_compat.staff: the count of distinct staff_id with that
# staff_role (R2: 3 billers, 2 denial analysts, 2 AR specialists, 1 poster, 3 front desk, 2 coders, 1 biller_manager).
CAP_POOLS = {
    "denial_specialist": ("denial_analyst", 1.0, 8),      # ~45 min an item (read the denial, pull records, draft or fix, track the deadline)
    "biller": ("biller", 0.80, 34),                        # holds fall into five known causes and are fixed in batches: ~14 min an item; the rest of their day is charge entry, posting and patient accounts
    "patient_billing": ("biller", 0.10, 10),               # patient accounts: ~45 min an item (several call attempts, a payment plan, a statement)
    "ar_specialist": ("ar_specialist", 1.0, 6),            # a no-response follow-up is several payer calls and portal checks over a day: ~75 min of work an item
    "payment_poster": ("payment_poster", 1.0, 24),         # ~15 min an item (match the remit, post, clear unapplied)
    "front_desk": ("front_desk", 0.15, 14),                # front desk is mostly the desk: ~15% of their time goes to follow-ups
    "coder": ("coder", 0.50, 20),                          # code reviews, half the day
    "billing_lead": ("biller_manager", 0.60, 12),          # disputes and approvals, ~30 min
    "manager": ("biller_manager", 0.40, 10),               # rule approvals and revalidation
}
A12_TASK_RATE = 1.0 if CAPACITY else .25     # share of sent statements that also become a staff follow-up item (R2: every one; a worklist of patient balances)
# ---- R2 detectors on top of the old rules (off for canonical unless KRISNNAI_REPLAY_PREVISIT=1)
PREVISIT = is_r2() or os.environ.get("KRISNNAI_REPLAY_PREVISIT", "") == "1"
# A7 flags a claim that is past its payer's standard turnaround plus this many days with no answer. Canonical: 14. R2: 0, because R2 payers always answer within turnaround + 3 days,
# so a grace of 7 or 14 never fires; 0 means "past the standard turnaround with no answer yet" (the task is the follow-up call).
A7_GRACE = int(os.environ.get("KRISNNAI_REPLAY_A7_GRACE", "0" if is_r2() else "14"))
# A7 only runs from this day. On R2 the rule "past the standard turnaround with no answer" also fires on every claim a payer answers 1-3 days late (50,000 of them over the history,
# each closed by the answer itself), so the follow-up worklist goes live for the last 30 days only, like A14 and A15 start after their own warm-up. Set the variable to an ISO date to change it.
A7_FROM = _env_date("KRISNNAI_REPLAY_A7_FROM", TODAY - dt.timedelta(days=30) if is_r2() else dt.date(1900, 1, 1))
A1_WINDOW_BD = 3           # A1: an appointment within the next 3 business days is checked for a recent eligibility check
A1_STALE_DAYS = 30         # a check older than this on the visit date is stale
A2_EXPIRY_DAYS = 14        # A2: an authorization that ends within this many days of the visit
A2_LOW_UNITS = 1           # A2: units left after this visit at or under this count = nearly used up
A3_UNBILLED_DAYS = 3       # A3: an encounter with no bill more than this many days after the visit
OVERTIME = float(os.environ.get("KRISNNAI_REPLAY_OVERTIME", "0.25"))   # overtime (set the variable to 0 for a hard cap): once the backlog is more than OT_DAYS days of normal capacity the team works extra, +25% at that depth, growing in proportion to the backlog,
MAX_OVERTIME = 0.60        # up to +60% (borrowed hours, a temp, weekend catch-up). This keeps a busy queue from growing for ever without ever emptying it.
OT_DAYS = 3
STALE_BOOST_DAYS = 90      # a task overdue this long (or more) has its score x4: nothing starves for ever


class WorkPool:
    """One role's backlog. add() when a task is created; work(d) on each working day returns the tasks the staff finish that day.

    capacity = items per working day (may be fractional: the remainder carries to the next day, so 2.5 means 2, 3, 2, 3 ...). A task created on day d is first worked on
    the next working day. Idle capacity is not banked. Deterministic: ties break on the order the tasks arrived.
    """

    def __init__(self, role, capacity, overtime=OVERTIME, ot_days=OT_DAYS):
        self.role, self.capacity, self.overtime, self.ot_days = role, float(capacity), overtime, ot_days
        self.items = []
        self.credit = 0.0
        self.seq = 0
        self.history = []              # (date, backlog_before, items_done, capacity_today)

    @staticmethod
    def score(d, it):
        late = max(0, (d - it["due"]).days)
        urgency = (1.5 if late > 0 else 1.0) * (1.2 if it["priority"] == "hi" else 1.0) * (1 + 3 * min(late, STALE_BOOST_DAYS) / STALE_BOOST_DAYS)
        return float(it["amount"] or 0) * urgency

    def add(self, created, due, amount, priority, payload, key=None):
        self.seq += 1
        self.items.append(dict(created=created, due=due, amount=amount, priority=priority, payload=payload, seq=self.seq, key=key))

    def discard(self, key):
        """Takes a task out of the backlog without working it (the need went away). True if it was there."""
        n = len(self.items)
        self.items = [it for it in self.items if key is None or it["key"] != key]
        return len(self.items) < n

    def today_capacity(self):
        deep = self.ot_days * self.capacity
        if len(self.items) <= deep:
            return self.capacity
        return self.capacity * (1 + min(MAX_OVERTIME, self.overtime * len(self.items) / deep))

    def work(self, d):
        cap = self.today_capacity()
        self.credit += cap
        n = int(self.credit + 1e-9)
        ready = [it for it in self.items if it["created"] < d]
        ready.sort(key=lambda it: (-self.score(d, it), it["seq"]))
        take = ready[:n]
        self.credit -= n                 # only the fractional remainder carries; capacity not used today (nothing ready) is lost, not banked
        before = len(self.items)
        if take:
            ids = {id(it) for it in take}
            self.items = [it for it in self.items if id(it) not in ids]
        self.history.append((d, before, len(take), cap))
        return [it["payload"] for it in take]


def role_capacities(staff_rows, pools=None):
    """Items per working day for each role: people with the mapped R2 staff_role (distinct staff_id) x share x items per person per day. A role whose staff_role has nobody gets no pool."""
    people = defaultdict(set)
    for r_ in staff_rows:
        people[r_["staff_role"]].add(r_["staff_id"])
    out = {}
    for role, (srole, share, per_day) in (pools or CAP_POOLS).items():
        n = len(people.get(srole, ()))
        if n:
            out[role] = n * share * per_day
    return out


# ====================================================================== A5 pre-submission pattern rules (the five patterns the R2 data generators built in)
# Each rule uses only what is known on the review date: the claim, its lines and encounter, the patient's earlier claims submitted by then, and authorizations decided by then.
CDT_RE = re.compile(r"^D\d{4}$")
EM_CODES = {"99211", "99213", "99214", "99203", "99204"}
INJECTION_CODES = {"96372", "95115"}
UNIT_CAPS = {"96127": 4, "97110": 4, "99408": 1}                        # max units per line per day
ONCE_A_YEAR = {"G0444": {"MEDICARE"}, "G0136": None}                    # code -> payers that allow it once per calendar year (None = every payer)
PREVENTIVE_CODES = {"99393", "99395", "99396"}
ROUTINE_DX = {"Z0000", "Z00129"}                                         # the practice's routine-exam diagnoses
# payer code -> codes that need prior authorization (the list the authorization stage built into payer_rule; mirrored from tools/synthea/load_auth_eligibility.py, tested equal)
AUTH_REQUIRED = {"HUMANA": ["90935", "96413", "97110"], "UHC": ["90935", "96413", "95115"], "AETNA": ["90935", "96413"], "CIGNA": ["90935", "96413"], "ANTHEM": ["90935", "96413"],
                 "BCBS": ["90935", "96413"], "MEDICAID": ["90935", "96413", "97110"], "DUAL": ["90935", "96413", "97110"]}
# hand-set confidence of each pattern rule (not read from the data): how often a claim that breaks it is denied
PATTERN_CONF = {"96": .50, "4": .65, "151": .30, "11": .25, "197": .80}
PATTERN_RULES = [("R-DENTAL-MEDICARE", "coverage", "96"), ("R-EM-INJ-MOD25", "coding", "4"), ("R-UNIT-LIMIT", "unit_limit", "151"), ("R-PREVENTIVE-DX", "dx_required", "11"),
                 ("R-AUTH-REQUIRED", "authorization", "197")]


def _res(code, ok, observed, expected, sev="high"):
    return (code, "pass" if ok else "fail", observed, expected, sev, None)


def auth_on_file(W, claim, ln, d):
    """True if an approved authorization decided by day d covers this line: date inside its window and cumulative units (this line included) within the approved units."""
    cid = ln["claim_detail_id"]
    pt, py, cp, svc = claim["patient_id"], claim["payer_id"], ln["cpt_code_id"], claim["service_date_from"]
    for a in W.auth_by_key.get((pt, py, cp), ()):
        if a["status"] != "approved" or a["decision_date"] is None or a["decision_date"] > d or not a["valid_from"] <= svc <= a["valid_to"]:
            continue
        used = sum((u or 0) for sd, c2, u, _cl, p2 in W.line_hist.get((pt, cp), ()) if p2 == py and a["valid_from"] <= sd and (sd, c2) <= (svc, cid))
        if used <= a["units_approved"]:
            return True
    return False


def pattern_checks(W, cl, d):
    """The five A5 pattern rules for one claim on review day d. Returns (rule results, fails) with fails = [(carc, confidence, rule_code)].
    A rule that does not apply to the claim adds nothing; a rule whose inputs are unknown (no diagnosis, no units) abstains. Outside R2 (W.has_ext false) nothing runs."""
    if not getattr(W, "has_ext", False):
        return [], []
    pc = W.payer_code[cl["payer_id"]]
    lines = W.cd[cl["claim_id"]]
    code = lambda ln: W.cpt[ln["cpt_code_id"]]            # noqa: E731
    svc = cl["service_date_from"]
    res, fails = [], []

    cdt = [code(x) for x in lines if CDT_RE.match(code(x))]
    if cdt:
        bad = pc == "MEDICARE"
        res.append(_res("R-DENTAL-MEDICARE", not bad, f"{cdt[0]} billed to {pc}", "dental (CDT) is not covered by MEDICARE" if bad else "dental covered", "high"))
        if bad:
            fails.append(("96", PATTERN_CONF["96"], "R-DENTAL-MEDICARE"))

    em = [x for x in lines if code(x) in EM_CODES]
    if em and any(W.cpt[x["cpt_code_id"]] in INJECTION_CODES for x in W.enc_lines.get(cl["encounter_id"], ())):
        m25 = W.mod.get("25")
        missing = [x for x in em if m25 is None or m25 not in (x["modifier_1_id"], x["modifier_2_id"])]
        res.append(_res("R-EM-INJ-MOD25", not missing, f"{code(em[0])} with an injection on the visit, modifier 25 {'missing' if missing else 'present'}", "modifier 25 on the E/M line", "high"))
        if missing:
            fails.append(("4", PATTERN_CONF["4"], "R-EM-INJ-MOD25"))

    over, checked = [], False
    for x in lines:
        cap, u = UNIT_CAPS.get(code(x)), W.line_units.get(x["claim_detail_id"])
        if cap is not None and u is not None:
            checked = True
            if u > cap:
                over.append(f"{code(x)} {u} units")
        elif code(x) in ONCE_A_YEAR and (ONCE_A_YEAR[code(x)] is None or pc in ONCE_A_YEAR[code(x)]):
            checked = True
            prior = [1 for sd, c2, _u, cid_, _p in W.line_hist.get((cl["patient_id"], x["cpt_code_id"]), ())
                     if sd.year == svc.year and (sd, c2) < (svc, x["claim_detail_id"]) and W.claim[cid_]["submitted_date"] <= d]
            if prior:
                over.append(f"{code(x)} again in {svc.year}")
    if checked:
        res.append(_res("R-UNIT-LIMIT", not over, "; ".join(over) or "within unit and frequency limits", "within the payer's unit and once-a-year limits", "high"))
        if over:
            fails.append(("151", PATTERN_CONF["151"], "R-UNIT-LIMIT"))

    prev = [x for x in lines if code(x) in PREVENTIVE_CODES]
    dx = W.claim_dx.get(cl["claim_id"])
    if prev and dx is not None:
        bad = dx not in ROUTINE_DX
        res.append(_res("R-PREVENTIVE-DX", not bad, f"{code(prev[0])} with diagnosis {dx}", "a routine-exam diagnosis (" + ", ".join(sorted(ROUTINE_DX)) + ")", "high"))
        if bad:
            fails.append(("11", PATTERN_CONF["11"], "R-PREVENTIVE-DX"))

    need = [x for x in lines if code(x) in AUTH_REQUIRED.get(pc, ())]
    if need:
        miss = [code(x) for x in need if not auth_on_file(W, cl, x, d)]
        res.append(_res("R-AUTH-REQUIRED", not miss, f"{', '.join(miss)} without an approved authorization on file" if miss else "authorization on file", "approved authorization covering the date and units", "high"))
        if miss:
            fails.append(("197", PATTERN_CONF["197"], "R-AUTH-REQUIRED"))
    return res, fails


def nb(d):
    while not is_biz(d):
        d += dt.timedelta(days=1)
    return d


def back_biz(d, n):
    """The business day n business days before d."""
    while n > 0:
        d -= dt.timedelta(days=1)
        if is_biz(d):
            n -= 1
    return d


class Replay:
    def __init__(self, world, publish=lambda p: None, write=True, seed=20261102):
        self.W = world
        self.publish = publish
        self.write = write
        self.S = Synth(seed)
        self.S.ids.update(world.ids)
        self.r = self.S.rnd
        self.stop_flag = threading.Event()
        self.pause_flag = threading.Event()
        self.speed = 1.0
        self.status = "idle"
        self.written = defaultdict(int)
        self.wq = queue.Queue()
        self._reset_state()
        self._index()

    # ------------------------------------------------------------------ state
    def _reset_state(self):
        self.S.rows.clear(); self.S.ids.clear(); self.S._next.clear()
        self.S.ids.update(self.W.ids)
        self.sched = []                     # (date, seq, fn)
        self.seq = 0
        self.mark = defaultdict(int)
        self.new_today = set()
        self.updates = []
        self.counts = defaultdict(int)
        self.board = defaultdict(int)
        self.agent_stat = {a: dict(dec=0, find=0, tasks=0, ms=0.0, items=0, last="") for a in NAMES}
        self.value = dict(detected=D(0), confirmed=D(0), pending=D(0))
        self.mirror = dict(tp=0, fp=0, fn=0, tn=0)
        self.cycle = dict(charge_lag=[], remit_days=[], task_days=defaultdict(list))
        self.learned = {}
        self.generic = {}
        self.denials_seen = []
        self.mirror_find = {}
        self.task_rows = {}
        self.feed_total = 0
        self.day_no = 0
        self.runs = {}
        self.flagged_cells = {}
        self.traces = {}
        self.cur_src = None
        self._t_last = time.perf_counter()
        self.hn = 0
        self.a7_open = {}
        self.pools = {role: WorkPool(role, cap) for role, cap in role_capacities(self.W.t.get("staff", [])).items()} if CAPACITY else {}
        self._open_log()

    def _open_log(self):
        logs = Path(__file__).resolve().parent / "logs"
        logs.mkdir(exist_ok=True)
        if getattr(self, "logf", None):
            self.logf.close()
        self.logf = open(logs / f"replay-{dt.datetime.now():%Y%m%d-%H%M%S}.jsonl", "w", encoding="utf-8") if self.write else None

    def log_trace(self, tr):
        if self.logf:
            self.logf.write(json.dumps(tr, default=str) + "\n")
            self.logf.flush()

    def _index(self):
        W = self.W
        self.T = defaultdict(lambda: defaultdict(list))     # T[agent][date] -> items
        self.E = defaultdict(lambda: defaultdict(list))     # E[kind][date]  -> world events
        T, E = self.T, self.E
        for ck in W.t["eligibility_check"]:
            T["A1"][nb(ck["check_date"])].append(ck)
        if PREVISIT and W.has_ext:
            for ap in W.t["appointment"]:         # appointments still scheduled at the end of the data: reviewed when they come within 3 business days, and a week ahead for authorizations
                if ap["appointment_status"] != "scheduled" or W.payer[ap["payer_id"]]["payer_type"] == "self_pay":
                    continue
                first = nb(ap["booked_date"] or START)
                T["A1"][max(first, back_biz(ap["appointment_date"], A1_WINDOW_BD))].append(dict(_pre=ap))
                T["A2"][max(first, nb(ap["appointment_date"] - dt.timedelta(days=7)))].append(dict(_sched=ap))
        by_auth = defaultdict(list)
        for ap in W.t["appointment"]:
            a = W.appt_auth.get(ap["appointment_id"])
            if a and ap["appointment_status"] in ("completed", "scheduled"):
                by_auth[a].append(ap)
        for a, lst in by_auth.items():
            lst.sort(key=lambda x: x["appointment_date"])
            for n, ap in enumerate(lst, 1):
                if n > W.auth[a]["units_approved"]:
                    T["A2"][nb(max(ap["appointment_date"] - dt.timedelta(days=7), ap["booked_date"] or START))].append((ap, n, a))
        for e in W.t["encounter"]:
            eb = W.bill_by_enc.get(e["encounter_id"])      # R2 has encounters that never produced a bill (no charge to hold, nothing to bill)
            if eb is not None and eb["bill_type"] == "insurance":      # self-pay visits never become claims
                E["visit"][e["encounter_date"]].append(e)
            if eb is not None:
                T["A3"][nb(e["encounter_date"] + dt.timedelta(days=3))].append(e)
            elif PREVISIT and W.has_ext and W.payer[e["payer_id"]]["payer_type"] != "self_pay":      # a visit with no charge at all: the biller is asked why (3 days after, so day 4)
                T["A3"][nb(e["encounter_date"] + dt.timedelta(days=A3_UNBILLED_DAYS + 1))].append(dict(_unbilled=e))
            if e["note_signed_date"]:
                E["note"][e["note_signed_date"]].append(e)
                if any(l["documented_level"] for l in W.enc_lines[e["encounter_id"]]):
                    T["A4"][nb(e["note_signed_date"] + dt.timedelta(days=1))].append(e)
        for b in W.t["bill"]:
            if b["bill_type"] == "insurance" and b["bill_status"] != "on_hold":
                E["charged"][b["charge_entered_date"]].append(b)
        for c in W.t["claim"]:
            E["submitted"][c["submitted_date"]].append(c)
            T["A5"][nb(c["submitted_date"]) if A5_NEXT_BIZ else c["submitted_date"]].append(c)
            turn = W.payer[c["payer_id"]]["standard_turnaround_days"]
            if turn is not None:                 # no standard turnaround for this payer (NULL in R2): A7 has no rule to apply, so it abstains
                d7 = nb(c["submitted_date"] + dt.timedelta(days=turn + A7_GRACE))
                if d7 >= A7_FROM:
                    T["A7"][d7].append(c)
        for cl, evs in W.hist.items():
            for x in evs:
                E["hist"][x["event_date"]].append((cl, x))
                if x["is_rejection"]:
                    T["A6"][nb(x["event_date"])].append((cl, x))
                if x["event_type"] == "remit_835":
                    T["A10"][nb(x["event_date"])].append(cl)
        self.remit = {cl: x["event_date"] for cl, evs in W.hist.items() for x in evs if x["event_type"] == "remit_835"}
        for dn in W.t["denial"]:
            T["A8"][nb(dn["denial_date"])].append(dn)
        for p in W.t["payment"]:
            E["cash"][p["payment_date"]].append(p)
            T["A11"][nb(p["payment_date"] + dt.timedelta(days=1))].append(p)
        if AR_AS_OF:
            by_bill = defaultdict(list)
            for a in W.t["ar"]:
                if a["balance_owner"] == "patient":
                    by_bill[a["bill_id"]].append(a)
            for lst in by_bill.values():
                lst.sort(key=lambda x: x["as_of_date"])
                dd = nb(lst[-1]["service_date"] + dt.timedelta(days=30))
                k = bisect.bisect_right([x["as_of_date"] for x in lst], dd)
                if k and lst[k - 1]["days_outstanding"] >= 20:          # latest snapshot on or before the review date; none yet = abstain
                    T["A12"][dd].append(lst[k - 1])
        else:
            for a in W.t["ar"]:
                if a["balance_owner"] == "patient" and a["days_outstanding"] >= 20:
                    T["A12"][nb(a["service_date"] + dt.timedelta(days=30))].append(a)
        for en in W.t["enrollment"]:
            if en["event_type"] == "enrollment":
                T["A13"][nb(max(START, en["expires_date"] - dt.timedelta(days=60)))].append(en)
        for ap in W.t["appeal"]:
            if ap["submitted_date"]:
                E["appeal"][ap["submitted_date"]].append((ap, "sent"))
            if ap["decision_date"]:
                E["appeal"][ap["decision_date"]].append((ap, "won" if ap["is_overturned"] else "lost"))
        self.pays = defaultdict(list)
        for p in W.t["payment"]:
            if p["payment_source"] == "payer":
                self.pays[p["payer_id"]].append(p)
        self.claims_by_payer = defaultdict(list)
        for c in W.t["claim"]:
            self.claims_by_payer[c["payer_id"]].append(c)
        self.total_days = (TODAY - START).days + 1

    # ------------------------------------------------------------------ row helpers
    def add(self, table, d, **vals):
        now = dt.datetime.now().replace(microsecond=0)
        rid = self.S.add(table, known_at=dt.datetime.combine(d, dt.time(6, 0, 0)), loaded_at=now, **vals)
        self.new_today.add((table, rid))
        self.counts[table] += 1
        return rid, self.S.rows[table][-1]

    def upd(self, table, row, **cols):
        row.update(cols)
        pk = row[self.S.pk[table]]
        if (table, pk) not in self.new_today:
            self.updates.append((table, pk, dict(cols)))

    def sched_at(self, d, fn):
        self.seq += 1
        heapq.heappush(self.sched, (d, self.seq, fn))

    def pick(self, role):
        names = ROLE_STAFF.get(role, [])
        return self.r.choice(names) if names else None

    # ------------------------------------------------------------------ the common emitter
    def emit(self, agent, dtype, entity, eid, d, outcome, amount, rules, refs, say, finding=None, task=None, values=(), conf=.9, human=None, approval=None, writeback=None,
             kind="flag"):
        S, W = self.S, self.W
        run_id, run_row = self.runs[agent]
        run_row["items_in"] += 1
        run_row["decisions_made"] += 1
        dec, dec_row = self.add("agent_decision", d, agent_run_id=run_id, agent_code=agent, decision_type=dtype, entity_type=entity, entity_id=eid, outcome=outcome,
                                decided_at=dt.datetime.combine(d, dt.time(6, 1)), run_mode="shadow", confidence=D(str(conf)).quantize(D("0.0001")),
                                reason_summary=(finding or {}).get("summary", dtype)[:300], rules_checked=len(rules), rules_failed=sum(1 for x in rules if x[1] == "fail"),
                                amount_at_stake=q(amount), data_fallback_level=0, input_hash=h("input", f"{agent}{entity}{eid}{d}"), practice_id=W.practice, **refs)
        for i, (rule, res, obs, exp, sev, prid) in enumerate(rules, 1):
            self.add("agent_decision_details", d, agent_decision_id=dec, check_seq=i, rule_code=rule, check_result=res, agent_code=agent, rule_version="1",
                     rule_source="learned" if prid and prid not in self.generic.values() else "built_in", severity=sev, observed_value=str(obs)[:100], expected_value=str(exp)[:100],
                     input_table=entity, input_fallback_level=0, practice_id=W.practice, payer_id=refs.get("payer_id"), payer_rule_id=prid)
        fid = tid = None
        frow = None
        if finding:
            fkw = {k: v for k, v in finding.items() if k not in ("resolve_with_task",)}
            fid, frow = self.add("agent_finding", d, agent_run_id=run_id, agent_code=agent, entity_type=entity, entity_id=eid, found_date=d, agent_decision_id=dec,
                                 practice_id=W.practice, finding_hash=h("finding", f"{agent}{entity}{eid}{finding['finding_type']}"), **fkw, **refs)
            dec_row["finding_id"] = fid
            self.agent_stat[agent]["find"] += 1
        if task:
            tid = self.make_task(agent, entity, eid, d, dec, dec_row, fid, frow, amount, refs, finding, **task)
            dec_row["task_id"] = tid
        for stage, vkind, amt, vdate, est, txn in values:
            self.add_value(agent, stage, vkind, amt, vdate, est, txn, entity, eid, fid, dec, refs, d)
        if approval:
            self.sched_at(next_biz(d, self.r.randint(1, 3)), lambda day, ap=approval, dec=dec, tid=tid, entity=entity, eid=eid, amount=amount, refs=refs, agent=agent, wb=writeback:
                          self.do_approval(day, agent, ap, dec, tid, entity, eid, amount, refs, wb))
        self.agent_stat[agent]["dec"] += 1
        self.agent_stat[agent]["last"] = say
        now = time.perf_counter()
        item_ms = round((now - self._t_last) * 1000, 3)
        self._t_last = now
        trigger, reads, handoff = tracelog.build(self, dtype, d, self.cur_src, rules, refs, outcome)
        tr = dict(id=dec, agent=agent, agent_name=NAMES[agent], date=d.isoformat(), decision_type=dtype, entity=entity, entity_id=eid, outcome=outcome, confidence=conf, amount=float(amount or 0),
                  trigger=trigger, reads=reads, rules=[dict(rule=x[0], result=x[1], observed=str(x[2]), expected=str(x[3]), severity=x[4], payer_rule_id=x[5]) for x in rules],
                  answer=say, creates=dict(finding=fid, task=tid, values=len(values), approval=bool(approval), writeback=bool(writeback)), handoff=handoff, ms=item_ms, mode="shadow",
                  tables_read=sorted({r_["table"] for r_ in reads}), columns_read=sorted({f"{r_['table']}.{c}" for r_ in reads for c in r_["cols"]}))
        self.traces[dec] = tr
        self.log_trace(tr)
        self.day_items.append(dict(a=agent, txt=say, amt=float(amount or 0), kind=kind, ent=entity, id=eid, claim=refs.get("claim_id"), trace=dec, ms=item_ms))
        return dec, fid, tid

    def add_value(self, agent, stage, vkind, amt, vdate, est, txn, entity, eid, fid, dec, refs, d):
        self.add("agent_value", d, agent_code=agent, value_stage=stage, amount=q(amt), value_date=min(vdate, TODAY), entity_type=entity, entity_id=eid, agent_finding_id=fid,
                 agent_decision_id=dec, practice_id=self.W.practice, claim_id=refs.get("claim_id"), denial_id=refs.get("denial_id"), payer_id=refs.get("payer_id"),
                 provider_id=refs.get("provider_id"), transaction_id=txn, is_holdout=False, incremental_amount=q(amt), value_kind=vkind, is_estimate=est, attribution_share=D("1.0"))
        key = {"detected": "detected", "confirmed": "confirmed"}.get(stage, "pending")
        self.value[key] += D(q(amt))

    def make_task(self, agent, entity, eid, d, dec, dec_row, fid, frow, amount, refs, finding, ttype, role, priority="md", title=""):
        r = self.r
        sname = self.pick(role)
        sid = self.W.staff[sname] if sname else None
        speed = SPEED.get(sname, 1.0)
        due = next_biz(d, SLA[priority])
        lag = max(0, round(SLA[priority] * speed * r.uniform(.4, 2.2)))
        done = next_biz(d, lag)
        mins = int(BASE_MIN.get(ttype, 15) * speed * r.uniform(.7, 1.4))
        rework = bool(sname) and r.random() < REWORK.get(sname, .04) and ttype != "unsigned_note"
        tid, trow = self.add("agent_task", d, task_type=ttype, owner_role=role, task_status="open", created_date=d, agent_code=agent, entity_type=entity, entity_id=eid,
                             agent_decision_id=dec, agent_finding_id=fid, priority=priority, due_date=due, assigned_to=sid, amount_at_stake=q(amount), title=title[:100],
                             practice_id=self.W.practice, escalation_level=0, reminder_count=0, **refs)
        self.agent_stat[agent]["tasks"] += 1
        self.task_rows[tid] = trow
        if role != "provider" or ttype == "unsigned_note":
            fin = lambda day: self.complete_task(day, tid, trow, dec_row, frow, mins, due, rework, finding)      # noqa: E731
            if role in self.pools:                 # finite capacity: the role's staff reach it in priority order, on a later working day
                self.pools[role].add(d, due, amount, priority, fin, key=tid)
            else:
                self.sched_at(done, fin)
        return tid

    def complete_task(self, day, tid, trow, dec_row, frow, mins, due, rework, finding):
        r = self.r
        late = (day - due).days
        esc = 0 if late <= 2 else 1 if late <= 5 else 2 if late <= 10 else 3
        self.cycle["task_days"][trow["agent_code"]].append((day - trow["created_date"]).days)
        if rework:
            self.upd("agent_task", trow, task_status="returned", completed_date=day, outcome="returned", minutes_spent=mins, contact_channel="system", escalation_level=esc, reminder_count=esc)
            done2 = min(TODAY, next_biz(day, 1))
            t2, row2 = self.add("agent_task", day, **{k: v for k, v in trow.items() if k not in ("agent_task_id", "known_at", "loaded_at")}, )
            row2.update(task_status="open", completed_date=None, outcome=None, minutes_spent=None, version=trow["version"] + 1, previous_agent_task_id=trow["agent_task_id"])
            fin2 = lambda d2: self.upd("agent_task", row2, task_status="done", completed_date=d2, outcome="resolved", minutes_spent=int(mins * .6))      # noqa: E731
            if trow["owner_role"] in self.pools:    # the reworked task waits its turn like any other
                self.pools[trow["owner_role"]].add(day, due, trow["amount_at_stake"], trow["priority"], fin2)
            else:
                self.sched_at(done2, fin2)
            self.task_rows[t2] = row2
        else:
            self.upd("agent_task", trow, task_status="done", completed_date=day, outcome="resolved", minutes_spent=mins, contact_channel="system", escalation_level=esc,
                     reminder_count=esc + (1 if r.random() < .25 else 0))
        if dec_row is not None and dec_row["human_outcome"] is None:
            self.upd("agent_decision", dec_row, human_outcome="accepted" if r.random() < .85 else "edited", human_outcome_date=day)
        if frow is not None and finding and finding.get("resolve_with_task") and frow["finding_status"] != "resolved":
            self.upd("agent_finding", frow, finding_status="resolved", resolved_date=day, resolution=finding["resolve_with_task"])
        self.day_items.append(dict(a=trow["agent_code"], txt=f"Task done: {trow['title']} ({mins} min, {(day - trow['created_date']).days} d)", amt=0, kind="human", ent="task", id=trow["agent_task_id"], claim=trow["claim_id"]))

    def do_approval(self, day, agent, ap, dec, tid, entity, eid, amount, refs, wb):
        if day > TODAY:
            return
        r = self.r
        by = ap.get("by") or self.pick(ap["role"])
        ok = r.random() < ap.get("rate", .92)
        aid, arow = self.add("agent_approval", day, agent_decision_id=dec, approval_type=ap["type"], approval_status="approved" if ok else "rejected", approved_by=self.W.staff[by],
                             approver_role=ap["role"], approval_date=day, amount_approved=q(amount) if ok else None, limit_checked=True, entity_type=entity, entity_id=eid,
                             practice_id=self.W.practice, approval_ts=dt.datetime.combine(day, dt.time(10, 15)), agent_task_id=tid)
        if ok and wb:
            self.add("agent_writeback", day, agent_decision_id=dec, target_system=wb[0], writeback_type=wb[1], send_status="suppressed", attempted_at=dt.datetime.combine(day, dt.time(10, 20)),
                     agent_approval_id=aid, agent_code=agent, entity_type=entity, entity_id=eid, attempt_no=1, payload_hash=h("payload", str(dec)), practice_id=self.W.practice,
                     claim_id=refs.get("claim_id"), appointment_id=refs.get("appointment_id"))
        if entity == "denial" and eid in self.W.appeal:
            self.updates.append(("appeal", self.W.appeal[eid]["appeal_id"], dict(agent_decision_id=dec, agent_approval_id=aid)))
        self.day_items.append(dict(a=agent, txt=f"{ap['type'].replace('_', ' ')} {'approved' if ok else 'rejected'} by {by}" + (" · write-back suppressed (shadow)" if ok and wb else ""), amt=float(amount or 0),
                                   kind="human", ent=entity, id=eid, claim=refs.get("claim_id")))

    def refs_of(self, cl=None, **kw):
        out = dict(kw)
        if cl:
            out.update(claim_id=cl["claim_id"], patient_id=cl["patient_id"], payer_id=cl["payer_id"], provider_id=cl["rendering_provider_id"], encounter_id=cl["encounter_id"],
                       bill_id=cl["bill_id"], authorization_id=cl["authorization_id"])
        return out

    @staticmethod
    def rule(code, ok, observed, expected, sev="medium", prid=None):
        return (code, "pass" if ok else "fail", observed, expected, sev, prid)

    def visit_no(self, e):
        n = 0
        for x in self.W.pat_enc[e["patient_id"]]:
            if x["encounter_date"] > e["encounter_date"]:
                break
            n = 1 if x["encounter_type"] == "evaluation" else n + 1
        return max(n, 1)

    def has_poc(self, e):
        """True / False, or None (unknown) when the document table holds no plan_of_care rows at all (R2: the table is empty)."""
        if "plan_of_care" not in self.W.doc_types:
            return None
        lst = self.W.pat_enc[e["patient_id"]]
        ev = max((x["encounter_date"] for x in lst if x["encounter_type"] == "evaluation" and x["encounter_date"] <= e["encounter_date"]), default=None)
        return any(dd["document_type"] == "plan_of_care" and ev and ev <= dd["document_date"] <= e["encounter_date"] for dd in self.W.pat_doc[e["patient_id"]])

    # ================================================================== the agents (each reacts to what reached it today)
    def a1_pre_visit(self, d, ap):
        """Appointment within 3 business days: is there an eligibility check, is it recent, does it name another payer as primary? Only checks done by day d count."""
        W = self.W
        self.cur_src = ap
        known = sorted((c for c in W.checks_by_appt.get(ap["appointment_id"], ()) if c["check_date"] <= d), key=lambda c: c["check_date"])
        last = known[-1] if known else None
        age = (ap["appointment_date"] - last["check_date"]).days if last else None
        other = next((W.elig_other[c["eligibility_check_id"]] for c in known if c["eligibility_check_id"] in W.elig_other and W.elig_other[c["eligibility_check_id"]] != ap["payer_id"]), None)
        rules = [self.rule("R-ELIG-CHECKED", last is not None, "no check on file" if last is None else "checked " + str(last["check_date"]), "a check before the visit on " + str(ap["appointment_date"]), "high"),
                 self.rule("R-ELIG-FRESH", last is None or age <= A1_STALE_DAYS, "n/a" if last is None else f"{age} days before the visit", f"<= {A1_STALE_DAYS} days", "medium"),
                 self.rule("R-COB-ORDER", other is None, "primary as booked" if other is None else "check names " + str(W.payer_code.get(other, other)) + " as primary", str(W.payer_code[ap["payer_id"]]) + " primary", "high")]
        if all(r_[1] == "pass" for r_ in rules):
            return
        cause = "R-COB-ORDER" if other is not None else "R-ELIG-CHECKED" if last is None else "R-ELIG-FRESH"
        txt = {"R-ELIG-CHECKED": "No eligibility check on file for the visit on " + str(ap["appointment_date"]),
               "R-ELIG-FRESH": f"Last eligibility check is {age} days old for the visit on " + str(ap["appointment_date"]),
               "R-COB-ORDER": "Another payer is primary for the visit on " + str(ap["appointment_date"])}[cause]
        ftype = {"R-ELIG-CHECKED": "no_eligibility_check", "R-ELIG-FRESH": "stale_eligibility_check", "R-COB-ORDER": "coverage_order_conflict"}[cause]
        amt = q(W.appt_expected[ap["appointment_id"]])
        self.emit("A1", "pre_visit_review", "appointment", ap["appointment_id"], d, "flag", amt, rules, dict(patient_id=ap["patient_id"], payer_id=ap["payer_id"], appointment_id=ap["appointment_id"], provider_id=ap["provider_id"]),
                  txt, finding=dict(finding_type=ftype, finding_status="open", upstream_stage="eligibility", is_preventable=True, severity="high", amount_at_risk=amt, deadline_date=ap["appointment_date"], summary=txt,
                                    resolve_with_task="verified"),
                  task=dict(ttype="coverage_follow_up", role="front_desk", priority="hi", title="Verify coverage before the visit: " + ftype.replace("_", " ")), conf=.9)

    def a1(self, d, items):
        for ck in items:
            if "_pre" in ck:
                self.a1_pre_visit(d, ck["_pre"])
                continue
            self.cur_src = ck
            ended = ck["plan_end_date"] and ck["plan_end_date"] < ck["service_date"]
            ap = self.W.appt[ck["appointment_id"]]
            rules = [self.rule("R-COV-ACTIVE", not ended, (f"ends {ck['plan_end_date']}" if ck["plan_end_date"] else "no end date"), f">= {ck['service_date']}", "high", self.generic["R-COV-ACTIVE"]),
                     self.rule("R-AAA-REJECT", not ck["is_aaa_reject"], "no reject", "no reject", "medium")]
            refs = dict(patient_id=ck["patient_id"], payer_id=ck["payer_id"], appointment_id=ck["appointment_id"], provider_id=ap["provider_id"])
            amt = q(self.W.appt_expected[ck["appointment_id"]])
            if ended:
                self.emit("A1", "eligibility_review", "appointment", ck["appointment_id"], d, "flag", amt, rules, refs, f"Coverage ended {ck['plan_end_date']} before the visit on {ck['service_date']}",
                          finding=dict(finding_type="coverage_ended", finding_status="open", upstream_stage="eligibility", is_preventable=True, severity="high", amount_at_risk=amt,
                                       deadline_date=ck["service_date"], summary=f"Coverage ended {ck['plan_end_date']}, before the visit on {ck['service_date']}", resolve_with_task="corrected"),
                          task=dict(ttype="coverage_follow_up", role="front_desk", priority="hi", title="Coverage has ended: confirm new insurance before the visit"), conf=.95)
            elif self.r.random() < .03:
                self.emit("A1", "eligibility_review", "appointment", ck["appointment_id"], d, "clear", 0, rules, refs, "Coverage active", conf=.97, kind="clear")

    def a2_scheduled(self, d, ap):
        """Scheduled appointment, every planned line: a service on the payer's authorization list with no authorization covering the visit, one that ends within 14 days of the visit, or one nearly used up."""
        W = self.W
        self.cur_src = ap
        pc, adate = W.payer_code[ap["payer_id"]], ap["appointment_date"]
        problems, rules = [], []
        for ln_, cp, units in W.appt_lines.get(ap["appointment_id"], ()):
            code = W.cpt[cp]
            if code not in AUTH_REQUIRED.get(pc, ()):
                continue
            cover = [a for a in W.auth_by_key.get((ap["patient_id"], ap["payer_id"], cp), ()) if a["status"] == "approved" and a["decision_date"] is not None and a["decision_date"] <= d
                     and a["valid_from"] <= adate <= a["valid_to"]]
            if not cover:
                rules.append(self.rule("R-AUTH-ON-FILE", False, f"{code}: no approved authorization covers {adate}", "approved authorization on file", "high"))
                problems.append(("authorization_missing", f"{code} needs an authorization and none covers the visit"))
                continue
            a = max(cover, key=lambda x: x["valid_to"])
            left = (a["valid_to"] - adate).days
            used = sum((u or 0) for sd, _c, u, _cl, p2 in W.line_hist.get((ap["patient_id"], cp), ()) if p2 == ap["payer_id"] and a["valid_from"] <= sd <= d)
            after = a["units_approved"] - used - (units or 0)
            rules.append(self.rule("R-AUTH-ON-FILE", True, f"{code}: authorization to {a['valid_to']}", "approved authorization on file", "high"))
            rules.append(self.rule("R-AUTH-EXPIRY", left > A2_EXPIRY_DAYS, f"ends {left} days after the visit", f"> {A2_EXPIRY_DAYS} days", "medium"))
            rules.append(self.rule("R-AUTH-UNITS", after > A2_LOW_UNITS, f"{after} units left after this visit", f"> {A2_LOW_UNITS}", "medium"))
            if left <= A2_EXPIRY_DAYS:
                problems.append(("authorization_expiring", f"{code}: authorization ends {left} days after the visit"))
            if after <= A2_LOW_UNITS:
                problems.append(("authorization_units_low", f"{code}: {max(after, 0)} units left after this visit"))
        if not problems:
            return
        ftype, txt = problems[0]
        txt = f"{txt} ({adate})"
        amt = q(W.appt_expected[ap["appointment_id"]])
        self.emit("A2", "scheduled_auth_review", "appointment", ap["appointment_id"], d, "flag", amt, rules, dict(patient_id=ap["patient_id"], payer_id=ap["payer_id"], appointment_id=ap["appointment_id"], provider_id=ap["provider_id"]),
                  txt, finding=dict(finding_type=ftype, finding_status="open", upstream_stage="authorization", is_preventable=True, severity="high", amount_at_risk=amt, deadline_date=adate, summary=txt,
                                    resolve_with_task="extension_requested"),
                  task=dict(ttype="authorization_check", role="front_desk", priority="hi", title="Authorization problem before the visit: " + ftype.replace("authorization_", "").replace("_", " ")), conf=.88)

    def a2(self, d, items):
        for it in items:
            if isinstance(it, dict):
                self.a2_scheduled(d, it["_sched"])
                continue
            ap, n, aid = it
            self.cur_src = (ap, n, aid)
            au = self.W.auth[aid]
            amt = q(self.W.appt_expected[ap["appointment_id"]])
            self.emit("A2", "authorization_review", "appointment", ap["appointment_id"], d, "flag", amt,
                      [self.rule("R-AUTH-VISITS", False, f"visit {n}", f"<= {au['units_approved']}", "high", self.generic["R-AUTH-VISITS"])],
                      dict(patient_id=ap["patient_id"], payer_id=ap["payer_id"], appointment_id=ap["appointment_id"], provider_id=ap["provider_id"], authorization_id=aid),
                      f"Authorization allows {au['units_approved']} visits; visit {n} is on {ap['appointment_date']}",
                      finding=dict(finding_type="authorization_exhausted", finding_status="open", upstream_stage="authorization", is_preventable=True, severity="high", amount_at_risk=amt,
                                   deadline_date=ap["appointment_date"], summary=f"Authorization allows {au['units_approved']} visits; this is visit {n}", resolve_with_task="extension_requested"),
                      task=dict(ttype="authorization_check", role="front_desk", priority="hi", title="Request more visits before the next appointment"), conf=.9)

    def a3_unbilled(self, d, e):
        """A visit with no bill 4 days on (insurance only): the biller is asked to enter the charge. An unsigned note also goes to the provider, as for any visit."""
        W = self.W
        self.cur_src = e
        unsigned = not e["note_signed_date"] or e["note_signed_date"] > d
        amt = q(W.appt_expected.get(e["appointment_id"], 0))
        refs = dict(patient_id=e["patient_id"], payer_id=e["payer_id"], provider_id=e["rendering_provider_id"], encounter_id=e["encounter_id"])
        days = (d - e["encounter_date"]).days
        txt = f"Visit on {e['encounter_date']} has no charge {days} days later (note {'unsigned' if unsigned else 'signed'})"
        rules = [self.rule("R-CHARGE-ENTERED", False, f"no bill {days} days after the visit", f"a charge within {A3_UNBILLED_DAYS} days", "high"),
                 self.rule("R-NOTE-SIGNED", not unsigned, "unsigned" if unsigned else f"signed {e['note_signed_date']}", "signed", "medium")]
        self.emit("A3", "unbilled_visit_review", "encounter", e["encounter_id"], d, "flag", amt, rules, refs, txt,
                  finding=dict(finding_type="unbilled_visit", finding_status="open", upstream_stage="charge_entry", is_preventable=True, severity="high", amount_at_risk=amt, summary=txt, resolve_with_task="charge_entered"),
                  task=dict(ttype="unbilled_visit", role="biller", priority="md", title="Visit has no charge: enter the charge or explain why"), conf=.9)
        if unsigned:
            self.emit("A3", "documentation_review", "encounter", e["encounter_id"], d, "flag", amt, [self.rule("R-NOTE-SIGNED", False, "unsigned", "signed within 2 days", "medium")], refs,
                      f"Note unsigned {days} days after the visit ({W.prov_name.get(e['rendering_provider_id'], '')})",
                      finding=dict(finding_type="unsigned_note", finding_status="open", upstream_stage="documentation", is_preventable=True, severity="medium", amount_at_risk=amt, summary="Note not signed; there is no charge"),
                      task=dict(ttype="unsigned_note", role="provider", priority="md", title="Sign the visit note"), conf=.97)

    def a3(self, d, items):
        for e in items:
            if "_unbilled" in e:
                self.a3_unbilled(d, e["_unbilled"])
                continue
            self.cur_src = e
            if e["note_signed_date"] and e["note_signed_date"] <= d:
                continue
            bill = self.W.bill_by_enc[e["encounter_id"]]
            unsigned = not e["note_signed_date"]
            fdict = dict(finding_type="unsigned_note", finding_status="open", upstream_stage="documentation", is_preventable=True, severity="medium", amount_at_risk=q(bill["total_billed"]),
                         summary="Note not signed; the charge is held")
            dec, fid, tid = self.emit("A3", "documentation_review", "encounter", e["encounter_id"], d, "flag", bill["total_billed"],
                                      [self.rule("R-NOTE-SIGNED", False, "unsigned", "signed within 2 days", "medium")],
                                      dict(patient_id=e["patient_id"], payer_id=e["payer_id"], provider_id=e["rendering_provider_id"], encounter_id=e["encounter_id"]),
                                      f"Note unsigned 3 days after the visit ({self.W.prov_name.get(e['rendering_provider_id'], '')})", finding=fdict,
                                      task=dict(ttype="unsigned_note", role="provider", priority="md", title="Sign the visit note"), conf=.97)
            if e["note_signed_date"]:
                frow = self.S.rows["agent_finding"][-1]
                self.sched_at(e["note_signed_date"], lambda day, frow=frow: self.upd("agent_finding", frow, finding_status="resolved", resolved_date=day, resolution="signed"))

    def a4(self, d, items):
        W = self.W
        for e in items:
            self.cur_src = e
            for ln in W.enc_lines[e["encounter_id"]]:
                kc = W.cpt[ln["cpt_code_id"]]
                if kc in ("97161", "97162", "97163", "97165", "97166") and ln["documented_level"]:
                    billed = {"97161": 1, "97165": 1, "97162": 2, "97166": 2, "97163": 3}[kc]
                    if billed != ln["documented_level"]:
                        ot = kc in ("97165", "97166")
                        suggest = (("97165", "97166", "97166") if ot else ("97161", "97162", "97163"))[ln["documented_level"] - 1]
                        diff = q(W.fee[suggest] - W.fee[kc])
                        over = diff < 0
                        self.emit("A4", "code_review", "encounter", e["encounter_id"], d, "suggest", abs(diff),
                                  [self.rule("R-EVAL-LEVEL", False, f"billed {kc}", f"documentation supports {suggest}", "high" if over else "medium")],
                                  dict(patient_id=e["patient_id"], payer_id=e["payer_id"], provider_id=e["rendering_provider_id"], encounter_id=e["encounter_id"]),
                                  f"{kc} billed, documentation supports {suggest}" + (" (billed higher: compliance risk)" if over else ""),
                                  finding=dict(finding_type="code_level_mismatch", finding_status="open", upstream_stage="coding", is_preventable=True, severity="high" if over else "medium",
                                               amount_at_risk=abs(diff), suggested_value=suggest, value_difference=diff, is_compliance_risk=over,
                                               summary=f"{kc} billed, documentation supports {suggest}" + (" (billed higher: compliance risk)" if over else ""), resolve_with_task="reviewed"),
                                  task=dict(ttype="code_review", role="coder", priority="md", title=f"Review evaluation level: {kc} vs {suggest}"),
                                  values=[] if over else [("detected", "charge_capture", diff, d, True, None)], approval=dict(type="code_change", role="coder", rate=.75), conf=.82)

    def a5(self, d, items):
        W = self.W
        for cl in items:
            self.cur_src = cl
            if A5_NEXT_BIZ and self.remit.get(cl["claim_id"], d) < d:      # the payer had already answered before this (next-business-day) review: nothing left to predict
                continue
            e = W.enc[cl["encounter_id"]]
            code = W.payer_code[cl["payer_id"]]
            lines = W.cd[cl["claim_id"]]
            results, fails = [], []
            if e["authorization_id"]:
                au = W.auth[e["authorization_id"]]
                n = sum(1 for x in W.auth_dates[au["authorization_id"]] if x <= e["encounter_date"])
                bad = n > au["units_approved"]
                results.append(self.rule("R-AUTH-VISITS", not bad, f"visit {n}", f"<= {au['units_approved']}", "high", self.generic["R-AUTH-VISITS"]))
                if bad:
                    fails.append(("198", .92))
            cv = W.cov.get(cl["coverage_id"]) or {"termination_date": None}      # a claim can carry no coverage row (3 in R2): treated as no end date
            bad = bool(cv["termination_date"] and cv["termination_date"] < e["encounter_date"])
            results.append(self.rule("R-COV-ACTIVE", not bad, (f"ended {cv['termination_date']}" if cv["termination_date"] else "no end date"), f">= {e['encounter_date']}", "high", self.generic["R-COV-ACTIVE"]))
            if bad:
                fails.append(("27", .95))
            L = self.learned.get(code)
            if L and L["since"] <= d:
                if L["carc"] == "50":
                    vn, poc = self.visit_no(e), self.has_poc(e)
                    if poc is None:                 # no plan_of_care documents exist at all: unknown, not "missing". The rule abstains.
                        bad = False
                    else:
                        bad = vn >= L["threshold"] and not poc
                        results.append(self.rule("R-UHC-POC-V", not bad, f"visit {vn}, plan of care {'on file' if poc else 'missing'}", f"visit < {L['threshold']} or plan on file", "high", L["id"]))
                else:
                    l97 = [x for x in lines if W.cpt[x["cpt_code_id"]] == "97530"]
                    pair = any(W.cpt[x["cpt_code_id"]] == "97140" for x in lines) and l97
                    mods = {x["modifier_2_id"] for x in l97} | {x["modifier_1_id"] for x in l97}
                    bad = bool(pair) and not (mods & {W.mod.get("XU"), W.mod.get("59")} - {None})
                    results.append(self.rule("R-AET-XU", not bad, "97140+97530 without XU/59" if bad else "ok", "distinct-service modifier", "high", L["id"]))
                if bad:
                    fails.append((L["carc"], .85))
            pr_, pf_ = pattern_checks(W, cl, d)              # the five generator patterns, on what is known today (R2 only)
            results += [(c_, r_, o_, e_, sv_, self.generic.get(c_)) for c_, r_, o_, e_, sv_, _ in pr_]
            fails += [(carc_, p_) for carc_, p_, _rule in pf_]
            if fails:
                carc_c, p = max(fails, key=lambda x: x[1])
                carcs = list(dict.fromkeys(c_ for c_, _ in sorted(fails, key=lambda x: -x[1])))      # every CARC predicted, most likely first
                carc_txt = ", ".join(carcs)
                failed = [x[0] for x in results if x[1] == "fail"]
                exp_allowed = sum((x["expected_allowed"] or 0) for x in lines)
                dec, fid, tid = self.emit("A5", "prerelease_review", "claim", cl["claim_id"], d, "hold", cl["total_charge"], results, self.refs_of(cl),
                                          f"Would hold {cl['claim_number']}: CARC {carc_txt} risk ({', '.join(failed)})",
                                          finding=dict(finding_type="predicted_denial", finding_status="open", upstream_stage=W.carc.get(W.carc_id.get(carc_c), {}).get("upstream_stage"), is_preventable=True,
                                                       severity="high", amount_at_risk=q(cl["total_charge"]), predicted_probability=D(str(p)).quantize(D("0.0001")),
                                                       predicted_reason_category=W.carc.get(W.carc_id.get(carc_c), {}).get("reason_category"), predicted_allowed_amount=q(exp_allowed),
                                                       summary=f"Predicted CARC {carc_txt}: {', '.join(failed)}"),
                                          task=dict(ttype="claim_hold_review", role="biller", priority="hi", title=f"Review before release: CARC {carc_txt} risk"), conf=p, kind="hold")
                self.mirror_find[cl["claim_id"]] = (self.S.rows["agent_finding"][-1], set(carcs))
            elif self.r.random() < .03:
                self.emit("A5", "prerelease_review", "claim", cl["claim_id"], d, "release", cl["total_charge"], results, self.refs_of(cl), f"Released {cl['claim_number']}: all checks pass", conf=.9, kind="clear")

    def a6(self, d, items):
        for cl_id, x in items:
            self.cur_src = (cl_id, x)
            cl = self.W.claim[cl_id]
            self.emit("A6", "rejection_review", "claim", cl_id, d, "flag", cl["total_charge"], [self.rule("R-277CA-ACCEPT", False, x["rejection_reason"], "accepted", "high")], self.refs_of(cl),
                      f"{cl['claim_number']} rejected at the clearinghouse: {x['rejection_reason']}",
                      finding=dict(finding_type="clearinghouse_rejection", finding_status="open", upstream_stage="billing", is_preventable=True, severity="high", amount_at_risk=cl["total_charge"],
                                   deadline_date=next_biz(d, 1), summary=f"Rejected at the clearinghouse: {x['rejection_reason']}", resolve_with_task="corrected"),
                      task=dict(ttype="fix_rejection", role="biller", priority="hi", title="Correct and resubmit the rejected claim"),
                      approval=dict(type="resubmit", role="billing_lead", by="B03", rate=.98), writeback=("PM", "task_note"), conf=.95,
                      values=[("detected", "cash_acceleration", cl["total_charge"], d, True, None)])

    def a7(self, d, items):
        W = self.W
        for cl in items:
            self.cur_src = cl
            if cl["claim_id"] in self.remit and self.remit[cl["claim_id"]] <= d:
                continue
            code = W.payer_code[cl["payer_id"]]
            turn = W.payer[cl["payer_id"]]["standard_turnaround_days"]
            days = (d - cl["submitted_date"]).days
            filing = W.payer[cl["payer_id"]]["filing_days"]
            deadline = cl["service_date_from"] + dt.timedelta(days=filing)
            risk = (deadline - d).days
            self.board["accepted"] = max(0, self.board["accepted"] - 1); self.board["noresp"] += 1
            dec, fid, tid = self.emit("A7", "claim_follow_up", "claim", cl["claim_id"], d, "flag", cl["total_charge"],
                      [self.rule("R-PAYER-RESPONSE", False, f"{days} days, no response", f"<= {turn + A7_GRACE} days", "high"), self.rule("R-FILING-WINDOW", risk > 30, f"{risk} days left", "> 30", "high")],
                      self.refs_of(cl), f"{cl['claim_number']}: no payer response after {days} days; filing window ends {deadline}",
                      finding=dict(finding_type="no_payer_response", finding_status="open", upstream_stage="billing", is_preventable=False, severity="high" if risk <= 30 else "medium",
                                   amount_at_risk=cl["total_charge"], deadline_date=deadline, summary=f"No payer response after {days} days; filing window ends {deadline}"),
                      task=dict(ttype="claim_follow_up", role="ar_specialist", priority="hi" if risk <= 30 else "md", title="Call the payer or resubmit: no response"), conf=.88,
                      values=[("detected", "claim_recovery", cl["total_charge"], d, True, None)])
            if tid is not None:
                self.a7_open[cl["claim_id"]] = (self.task_rows[tid], self.S.rows["agent_finding"][-1])

    def a7_answered(self, d, claim_id):
        """The payer answered a claim A7 had flagged: if the follow-up is still waiting, it closes itself (nothing left to chase) and leaves the backlog."""
        it = self.a7_open.pop(claim_id, None)
        if it is None:
            return
        trow, frow = it
        if trow["task_status"] != "open":
            return
        pool = self.pools.get(trow["owner_role"])
        if pool is not None:
            pool.discard(trow["agent_task_id"])
        self.upd("agent_task", trow, task_status="done", completed_date=d, outcome="no_action_needed", minutes_spent=0)
        if frow["finding_status"] != "resolved":
            self.upd("agent_finding", frow, finding_status="resolved", resolved_date=d, resolution="payer_answered")

    def a8(self, d, items):
        W = self.W
        for dn in items:
            self.cur_src = dn
            self.denials_seen.append(dn)
            cl = W.claim[dn["claim_id"]]
            cr = W.carc[dn["adjustment_reason_id"]]
            cc = cr["carc_code"]
            dl = dn["appeal_deadline"]
            sev = "high" if (dl - d).days <= 30 else "medium"
            appealable = cr["is_appealable"]
            role = "denial_specialist" if appealable else cr["owner_role"] if cr["owner_role"] in ROLE_STAFF else "biller"
            will_appeal = dn["denial_id"] in W.appeal
            dec, fid, tid = self.emit("A8", "denial_triage", "denial", dn["denial_id"], d, "route", dn["denied_amount"],
                                      [self.rule("R-CARC-ROUTE", True, f"CARC {cc}", cr["owner_role"], "medium"), self.rule("R-APPEAL-WINDOW", dl > d, f"deadline {dl}", "open", "high")],
                                      self.refs_of(cl, denial_id=dn["denial_id"]), f"{cl['claim_number']} denied CARC {cc}: {cr['short_label']}; owner {cr['owner_role']}",
                                      finding=dict(finding_type="denial", finding_status="open", upstream_stage=dn["upstream_stage"], is_preventable=dn["is_preventable"], severity=sev,
                                                   amount_at_risk=dn["denied_amount"], deadline_date=dl, summary=f"CARC {cc}: {cr['short_label']}; owner {cr['owner_role']}"),
                                      task=dict(ttype="denial_work", role=role, priority="hi" if sev == "high" else "md", title=f"Work the denial: {cr['short_label']}"[:100]),
                                      values=[("detected", "denial_recovery", dn["denied_amount"], d, False, None)], conf=.9, kind="denial",
                                      approval=dict(type="appeal_send", role="denial_specialist", by="D01", rate=.95) if (appealable and will_appeal) else None, writeback=("portal", "appeal_submit"))
            frow = self.S.rows["agent_finding"][-1]
            if dn["resolved_date"] and dn["outcome"] in ("overturned", "written_off"):
                self.sched_at(dn["resolved_date"], lambda day, dn=dn, frow=frow, dec=dec, fid=fid, cl=cl: self.denial_resolved(day, dn, frow, dec, fid, cl))

    def denial_resolved(self, day, dn, frow, dec, fid, cl):
        rec = dn["outcome"] == "overturned"
        self.upd("agent_finding", frow, finding_status="resolved", resolved_date=day, resolution="recovered" if rec else "written_off", amount_recovered=dn["recovered_amount"] if rec else D(0))
        if rec:
            txn = self.W.tx_den.get(dn["denial_id"])
            self.add_value("A8", "confirmed" if txn else "pending", "denial_recovery", dn["recovered_amount"], day, False, txn, "denial", dn["denial_id"], fid, dec,
                           self.refs_of(cl, denial_id=dn["denial_id"]), day)
            self.day_items.append(dict(a="A8", txt=f"{cl['claim_number']}: denial overturned, ${float(dn['recovered_amount']):,.0f} recovered" + ("" if txn else " (cash paid, remit not posted: pending)"),
                                       amt=float(dn["recovered_amount"]), kind="win", ent="denial", id=dn["denial_id"], claim=cl["claim_id"]))

    def a9(self, d):
        W = self.W
        if not is_biz(d):
            return
        for carc_c, (rcode, fam, req) in TEMPLATES.items():
            for pc, pid in W.payer_id.items():
                if pc in self.learned:
                    continue
                if carc_c == "50" and "plan_of_care" not in W.doc_types:      # the rule can only be checked against plan-of-care documents; none exist, so do not learn it
                    continue
                recent = [x for x in self.denials_seen if x["payer_id"] == pid and W.carc[x["adjustment_reason_id"]]["carc_code"] == carc_c and (d - x["denial_date"]).days <= 60]
                if len(recent) < 10:
                    continue
                thr = min(self.visit_no(W.enc[W.claim[x["claim_id"]]["encounter_id"]]) for x in recent) if carc_c == "50" else None
                appr = next_biz(d, 5)
                prid, prow = self.add("payer_rule", d, rule_code=rcode + (str(thr) if thr else ""), rule_family=fam, rule_action="hold_for_review", rule_source_code="learned", payer_id=pid,
                                      adjustment_reason_id=W.carc_id[carc_c], requirement_code=req, unit_limit=thr, evidence_claim_count=len(recent), evidence_denied_count=len(recent),
                                      evidence_denied_amount=q(sum(x["denied_amount"] for x in recent)), evidence_from_date=min(x["denial_date"] for x in recent), evidence_to_date=d,
                                      owner_role="biller", severity="high", is_enabled=False, is_synthetic=True, approval_status="proposed", effective_from=appr)
                self.learned[pc] = dict(id=prid, since=appr, threshold=thr, carc=carc_c, row=prow)
                self.sched_at(appr, lambda day, prow=prow, pc=pc: self.upd("payer_rule", prow, is_enabled=True, approval_status="approved", approved_by_staff_id=self.W.staff["M01"], approved_date=day,
                                                                      effective_from=day, last_confirmed_date=day))
                amt = sum(x["denied_amount"] for x in recent)
                self.cur_src = dict(recent=recent, thr=thr, carc=carc_c, pc=pc, pid=pid)
                self.emit("A9", "rule_proposal", "payer_rule", prid, d, "proposed", amt, [self.rule("PATTERN-CLUSTER", False, f"{len(recent)} denials in 60 days", ">= 10", "high")], dict(payer_id=pid),
                          f"{len(recent)} CARC {carc_c} denials from {pc} in 60 days: proposes rule {rcode}{thr or ''}",
                          finding=dict(finding_type="rule_proposal", finding_status="open", upstream_stage="billing", is_preventable=True, severity="high", amount_at_risk=q(amt),
                                       summary=f"{len(recent)} CARC {carc_c} denials from {pc} in 60 days; proposed rule {rcode}", resolve_with_task="approved"),
                          task=dict(ttype="rule_review", role="manager", priority="md", title=f"Approve rule {rcode} for {pc}"), approval=dict(type="rule_activation", role="manager", by="M01", rate=1.0),
                          conf=.9, kind="learn")

    def a10(self, d, items):
        W = self.W
        for cl_id in items:
            cl = W.claim[cl_id]
            for ln in W.cd[cl_id]:
                if ln["allowed_amount"] is None or not ln["expected_allowed"]:
                    continue
                exp = ln["expected_allowed"] * (D("0.85") if W.mod["CQ"] in (ln["modifier_1_id"], ln["modifier_2_id"]) else D(1))
                gap = q(exp - ln["allowed_amount"])
                if gap > q(exp * D("0.03")):
                    self.cur_src = (cl, ln)
                    deadline = d + dt.timedelta(days=W.payer[cl["payer_id"]]["appeal_days"])
                    self.emit("A10", "payment_audit", "claim_detail", ln["claim_detail_id"], d, "flag", gap, [self.rule("R-CONTRACT-RATE", False, f"allowed {ln['allowed_amount']}", f"{q(exp)}", "high")],
                              self.refs_of(cl), f"{cl['claim_number']} {W.cpt[ln['cpt_code_id']]} paid ${float(gap):,.2f} below the contract",
                              finding=dict(finding_type="underpayment", finding_status="open", upstream_stage="payment", is_preventable=False, severity="medium", amount_at_risk=gap,
                                           deadline_date=deadline, summary=f"{W.cpt[ln['cpt_code_id']]} paid {gap} below the contract rate"),
                              task=dict(ttype="dispute_package", role="billing_lead", priority="md", title="Dispute the underpayment with the payer"),
                              approval=dict(type="dispute_send", role="billing_lead", by="B03", rate=.9), writeback=("portal", "dispute_submit"), conf=.93,
                              values=[("detected", "underpayment", gap, d, False, None)])

    def a11(self, d, items):
        for p in items:
            self.cur_src = p
            if p["unapplied_amount"] and p["unapplied_amount"] > 0:
                self.emit("A11", "remit_reconciliation", "payment", p["payment_id"], d, "flag", p["unapplied_amount"], [self.rule("R-REMIT-POSTED", False, f"posted {p['posted_amount']}", f"{p['payment_amount']}", "high")],
                          dict(payer_id=p["payer_id"]), f"Payer paid ${float(p['payment_amount']):,.0f} on {p['payment_date']} but nothing was posted",
                          finding=dict(finding_type="unposted_remit", finding_status="open", upstream_stage="payment", is_preventable=True, severity="high", amount_at_risk=p["unapplied_amount"],
                                       summary="Payer paid but the remit was not posted to the ledger", resolve_with_task="posted"),
                          task=dict(ttype="post_remit", role="payment_poster", priority="hi", title="Post the remit"), conf=.99, values=[("detected", "unposted_cash", p["unapplied_amount"], d, False, None)])
            elif p["payment_source"] == "payer" and self.r.random() < .04:
                self.emit("A11", "remit_reconciliation", "payment", p["payment_id"], d, "match", 0, [self.rule("R-REMIT-POSTED", True, "posted in full", "posted in full", "high")],
                          dict(payer_id=p["payer_id"]), "Remit matched: posted in full", conf=.99, kind="clear")

    def a12(self, d, items):
        for a in items:
            self.cur_src = a
            level = 0 if a["days_outstanding"] < 60 else 1 if a["days_outstanding"] < 90 else 2
            sid, srow = self.add("patient_statement", d, statement_number=f"STM-{self.counts['patient_statement']:06d}", patient_id=a["patient_id"], statement_date=d, statement_amount=a["balance"],
                                 channel=self.r.choice(["mail", "email", "portal"]), statement_status="sent", practice_id=self.W.practice, bill_id=a["bill_id"], claim_id=a["claim_id"],
                                 due_date=d + dt.timedelta(days=30), sent_at=dt.datetime.combine(d, dt.time(8, 0)), status_date=d, dunning_level=level)
            if self.r.random() < A12_TASK_RATE:
                self.emit("A12", "balance_follow_up", "ar", a["ar_id"], d, "flag", a["balance"], [self.rule("R-BALANCE-AGE", False, f"{a['days_outstanding']} days", "<= 60", "medium")],
                          dict(patient_id=a["patient_id"], payer_id=a["payer_id"]), f"Patient balance ${float(a['balance']):,.0f}: statement sent",
                          finding=dict(finding_type="patient_balance", finding_status="open", upstream_stage="patient", is_preventable=False, severity="low", amount_at_risk=a["balance"],
                                       summary=f"Patient balance {a['balance']} open {a['days_outstanding']} days"),
                          task=dict(ttype="patient_follow_up", role="patient_billing" if CAPACITY else "biller", priority="lo", title="Follow up on the patient balance"), conf=.85)

    def a13(self, d, items):
        for en in items:
            self.cur_src = en
            days = (en["expires_date"] - d).days
            self.emit("A13", "enrollment_review", "enrollment", en["enrollment_id"], d, "flag", 0, [self.rule("R-ENROLL-EXPIRY", False, f"expires {en['expires_date']}", "> 60 days", "high")],
                      dict(provider_id=en["provider_id"], payer_id=en["payer_id"]), f"{self.W.prov_name.get(en['provider_id'], 'Provider')} enrolment with {self.W.payer_code[en['payer_id']]} expires in {days} days",
                      finding=dict(finding_type="enrollment_expiring", finding_status="open", upstream_stage="credentialing", is_preventable=True, severity="high", deadline_date=en["expires_date"],
                                   summary=f"Enrolment expires in {days} days"), task=dict(ttype="revalidation", role="manager", priority="hi", title="Start revalidation"), conf=.96)

    def a14(self, d):
        W = self.W
        if d.weekday() == 0:           # Monday: the week's cash forecast per payer
            for pc, pid in W.payer_id.items():
                if W.payer[pid]["payer_type"] == "self_pay" or d < A14_FROM:
                    continue
                w0, w1 = d + dt.timedelta(days=1), d + dt.timedelta(days=7)
                turn = W.payer[pid]["standard_turnaround_days"]
                if turn is None:                 # same gap as A7: no payer turnaround, no forecast window
                    continue
                exp, cnt = D(0), 0
                for cl in self.claims_by_payer[pid]:
                    if cl["submitted_date"] > d or cl["submitted_date"] < d - dt.timedelta(days=75) or (cl["claim_id"] in self.remit and self.remit[cl["claim_id"]] <= d):
                        continue
                    if w0 <= next_biz(cl["submitted_date"], turn + 2) <= w1:
                        exp += sum((x["expected_allowed"] or 0) for x in W.cd[cl["claim_id"]]) * D("0.93")
                        cnt += 1
                fid, frow = self.add("agent_forecast", d, forecast_type="weekly_cash", as_of_date=d, target_start_date=w0, target_end_date=w1, expected_amount=q(exp), low_amount=q(exp * D("0.70")),
                                     high_amount=q(exp * D("1.30")), probability=D("0.8"), claim_count=cnt, practice_id=W.practice, payer_id=pid, interval_level=D("0.80"), model_name="rules", code_version=VERSION)
                if w1 <= TODAY:
                    self.sched_at(w1, lambda day, frow=frow, pid=pid, w0=w0, w1=w1: self.forecast_actual(day, frow, pid, w0, w1))
        for t in list(self.task_rows.values()):
            if t["task_status"] == "open" and t["due_date"] < d - dt.timedelta(days=3) and t["escalation_level"] == 0 and t["version"] == 1 and t["owner_role"] != "provider":
                self.upd("agent_task", t, escalation_level=1, reminder_count=1)
                self.day_items.append(dict(a="A14", txt=f"Escalated overdue task: {t['title']}", amt=float(t["amount_at_stake"] or 0), kind="flag", ent="task", id=t["agent_task_id"], claim=t["claim_id"]))
                self.agent_stat["A14"]["dec"] += 1

    def forecast_actual(self, day, frow, pid, w0, w1):
        act = sum((p["payment_amount"] for p in self.pays[pid] if w0 <= p["payment_date"] <= w1), D(0))
        self.upd("agent_forecast", frow, actual_amount=q(act), actual_known_date=day, within_range=frow["low_amount"] <= act <= frow["high_amount"])

    def a15(self, d):
        W = self.W
        if d.weekday() != 0 or d < A15_FROM:
            return
        cells = defaultdict(lambda: [D(0), D(0), 0])
        for cl in W.t["claim"]:
            rd = self.remit.get(cl["claim_id"])
            if not rd or rd > d or rd < d - dt.timedelta(days=60):
                continue
            for ln in W.cd[cl["claim_id"]]:
                if ln["allowed_amount"] is not None and ln["expected_allowed"]:
                    e = ln["expected_allowed"] * (D("0.85") if W.mod["CQ"] in (ln["modifier_1_id"], ln["modifier_2_id"]) else D(1))
                    c = cells[(cl["payer_id"], ln["cpt_code_id"])]
                    c[0] += ln["allowed_amount"]; c[1] += e; c[2] += 1
        for (pid, cid), (got, exp, n) in cells.items():
            if n >= 20 and exp > 0 and got / exp < D("0.95") and (d - self.flagged_cells.get((pid, cid), dt.date(2000, 1, 1))).days > 30:
                self.flagged_cells[(pid, cid)] = d
                self.cur_src = dict(pid=pid, cid=cid, n=n, got=got, exp=exp)
                self.emit("A15", "revenue_assurance", "payer_cpt", cid, d, "flag", q(exp - got), [self.rule("R-REALISATION", False, f"{(got / exp * 100):.1f}% of contract", ">= 95%", "high")], dict(payer_id=pid),
                          f"{W.payer_code[pid]} pays {(got / exp * 100):.1f}% of the contract on {W.cpt[cid]} ({n} lines, 60 days)",
                          finding=dict(finding_type="realisation_variance", finding_status="open", upstream_stage="payment", is_preventable=False, severity="high", amount_at_risk=q(exp - got),
                                       summary=f"{W.payer_code[pid]} pays {(got / exp * 100):.1f}% of the contract on {W.cpt[cid]} over {n} lines (60 days)"),
                          task=dict(ttype="dispute_package", role="billing_lead", priority="hi", title="Investigate payer-wide underpayment"), conf=.9)

    # ================================================================== one simulated day
    def world_events(self, d):
        """Releases the day's real events from the history; returns the feed items and moves the board."""
        W = self.W
        out, n = [], defaultdict(int)
        b = self.board
        for e in self.E["visit"].get(d, []):
            b["visit"] += 1; n["visits"] += 1
            out.append(dict(k="visit", txt=f"Visit {e['encounter_type'].replace('_', ' ')} with {W.prov_name.get(e['rendering_provider_id'], '')}", claim=None))
        for e in self.E["note"].get(d, []):
            n["notes"] += 1
        for bl in self.E["charged"].get(d, []):
            b["visit"] = max(0, b["visit"] - 1); b["charged"] += 1; n["charged"] += 1
            self.cycle["charge_lag"].append((d - bl["service_date"]).days)
            c = W.claim_by_enc.get(bl["encounter_id"])
            out.append(dict(k="charged", txt=f"Charge entered ${float(bl['total_billed']):,.0f}", claim=c["claim_id"] if c else None))
        for c in self.E["submitted"].get(d, []):
            b["charged"] = max(0, b["charged"] - 1); b["submitted"] += 1; n["submitted"] += 1
            out.append(dict(k="submitted", txt=f"{c['claim_number']} submitted to {W.payer[c['payer_id']]['payer_name']} ${float(c['total_charge']):,.0f}", claim=c["claim_id"]))
        for cl, x in self.E["hist"].get(d, []):
            c = W.claim[cl]
            et = x["event_type"]
            if et == "accepted_277ca":
                b["submitted"] = max(0, b["submitted"] - 1); b["accepted"] += 1
                out.append(dict(k="accepted", txt=f"{c['claim_number']} accepted by the clearinghouse", claim=cl))
            elif et == "rejected_277ca":
                b["rejected"] += 1
                out.append(dict(k="rejected", txt=f"{c['claim_number']} rejected: {x['rejection_reason']}", claim=cl))
            elif et == "resubmitted":
                b["rejected"] = max(0, b["rejected"] - 1)
                out.append(dict(k="submitted", txt=f"{c['claim_number']} resubmitted", claim=cl))
            elif et == "remit_835":
                self.a7_answered(d, cl)
                b["accepted"] = max(0, b["accepted"] - 1)
                if x["status_after"] == "paid":
                    b["paid"] += 1; n["paid"] += 1
                    out.append(dict(k="paid", txt=f"{c['claim_number']} paid in full by {W.payer[c['payer_id']]['payer_name']}", claim=cl))
                else:
                    b["denied"] += 1; n["denied"] += 1
                    out.append(dict(k="denied", txt=f"{c['claim_number']}: {W.payer[c['payer_id']]['payer_name']} {x['status_after']}", claim=cl))
                self.cycle["remit_days"].append((d - c["submitted_date"]).days)
                mf = self.mirror_find.get(cl)
                dn = bool(W.den_by_claim.get(cl))
                if mf is not None:
                    mrow, mcarcs = mf
                    hit = any(W.carc[x["adjustment_reason_id"]]["carc_code"] in mcarcs for x in W.den_by_claim.get(cl, ()))      # confirmed = denied with a CARC the hold named
                    self.mirror["tp" if hit else "fp"] += 1
                    self.upd("agent_finding", mrow, finding_status="confirmed" if hit else "unconfirmed", resolved_date=d, resolution="denied_confirmed" if hit else "no_denial")
                else:
                    self.mirror["fn" if dn else "tn"] += 1
        for p in self.E["cash"].get(d, []):
            n["cash"] += 1
        for ap, kind in self.E["appeal"].get(d, []):
            out.append(dict(k="appeal", txt=f"Appeal {'sent' if kind == 'sent' else 'won' if kind == 'won' else 'lost'}", claim=None))
        n["total"] = len(out)
        return out, dict(n)

    def work_pools(self, d):
        """Each role's staff clear their daily capacity from the backlog (working days only), before today's new tasks exist."""
        if not is_biz(d):
            return
        for role in sorted(self.pools):
            for fin in self.pools[role].work(d):
                fin(d)

    def backlog(self):
        """Open items per role right now (the finite-capacity backlog)."""
        return {role: len(p.items) for role, p in self.pools.items()}

    def run_day(self, d):
        t0 = time.perf_counter()
        self.day_items = []
        self.new_today = set()
        self.updates = []
        self.work_pools(d)
        while self.sched and self.sched[0][0] <= d:
            _, _, fn = heapq.heappop(self.sched)
            fn(d)
        world, wc = self.world_events(d)
        ms = {}
        if is_biz(d):
            for code in NAMES:
                rid, rrow = self.add("agent_run", d, agent_code=code, agent_name=NAMES[code], run_mode="shadow", trigger_type="schedule", started_at=dt.datetime.combine(d, dt.time(6, 0)),
                                     run_status="ok", practice_id=self.W.practice, items_in=0, decisions_made=0, error_count=0, code_version=VERSION)
                self.runs[code] = (rid, rrow)
            steps = [("A1", self.a1), ("A2", self.a2), ("A3", self.a3), ("A4", self.a4), ("A5", self.a5), ("A6", self.a6), ("A7", self.a7), ("A8", self.a8), ("A10", self.a10), ("A11", self.a11),
                     ("A12", self.a12), ("A13", self.a13)]
            for code, fn in steps:
                items = self.T[code].get(d, [])
                t1 = time.perf_counter()
                self._t_last = t1
                before = self.agent_stat[code]["dec"]
                if items:
                    fn(d, items)
                el = (time.perf_counter() - t1) * 1000
                ms[code] = el
                self.agent_stat[code]["ms"] += el
                self.agent_stat[code]["items"] += len(items)
            for code, fn in (("A9", self.a9), ("A14", self.a14), ("A15", self.a15)):
                t1 = time.perf_counter()
                self._t_last = t1
                fn(d)
                el = (time.perf_counter() - t1) * 1000
                ms[code] = el
                self.agent_stat[code]["ms"] += el
            for code, (rid, rrow) in self.runs.items():
                el = ms.get(code, 0.0)
                rrow["ended_at"] = rrow["started_at"] + dt.timedelta(seconds=max(1, round(el / 1000 + 1)))
        for it in self.day_items:
            it.setdefault("ms", 0)
        # snapshot rows for the writer
        batch = {}
        for n in AGENT_TABLES:
            rows = self.S.rows[n]
            if len(rows) > self.mark[n]:
                batch[n] = [dict(x) for x in rows[self.mark[n]:]]
                self.mark[n] = len(rows)
                if n == "agent_decision":      # decisions, findings and tasks point at each other: insert first, link afterwards
                    for cp in batch[n]:
                        if cp["finding_id"] or cp["task_id"]:
                            self.updates.append(("agent_decision", cp["agent_decision_id"], dict(finding_id=cp["finding_id"], task_id=cp["task_id"])))
                            cp["finding_id"] = cp["task_id"] = None
        if self.write and (batch or self.updates):
            self.wq.put((batch, list(self.updates)))
        self.day_ms = (time.perf_counter() - t0) * 1000
        return world, wc

    def packet(self, d, world, wc):
        td = self.cycle["task_days"]
        med = lambda xs: sorted(xs)[len(xs) // 2] if xs else None
        # keep the feed readable: all agent reactions, plus a sample of the world events
        sample = world if len(world) <= 24 else self.r.sample(world, 24)
        return dict(type="day", date=d.isoformat(), day_no=self.day_no, total_days=self.total_days, board=dict(self.board), world=sample, wc=wc,
                    agents=self.day_items[:80], agents_total=len(self.day_items),
                    stats={a: dict(dec=s["dec"], find=s["find"], tasks=s["tasks"], avg_ms=round(s["ms"] / s["items"], 3) if s["items"] else 0, last=s["last"], name=NAMES[a]) for a, s in self.agent_stat.items()},
                    tables={n: self.counts[n] for n in AGENT_TABLES}, written={n: self.written[n] for n in AGENT_TABLES},
                    value={k: float(v) for k, v in self.value.items()}, mirror=dict(self.mirror),
                    cycle=dict(charge_lag=round(sum(self.cycle["charge_lag"]) / len(self.cycle["charge_lag"]), 1) if self.cycle["charge_lag"] else None,
                               remit_days=round(sum(self.cycle["remit_days"]) / len(self.cycle["remit_days"]), 1) if self.cycle["remit_days"] else None,
                               task_days={a: med(v) for a, v in td.items()}), day_ms=round(self.day_ms, 1))

    # ================================================================== run control
    def prepare(self):
        """Clears every agent output table (the history stays) and sets up the learned-rule state."""
        self._reset_state()
        if self.write:
            if is_r2():
                raise RuntimeError("write mode is not enabled for krisnnai_r2 yet (the R2 agent_* tables are written in a later step); run with write=False / --dry")
            conn, db = connect_replay()
            assert db.startswith("krisnnai_canonical") or db == "krisnnai_r2"
            cur = conn.cursor()
            for sql in ("UPDATE appeal SET agent_decision_id = NULL, agent_approval_id = NULL",
                        "UPDATE agent_decision SET finding_id = NULL, task_id = NULL, supersedes_decision_id = NULL",
                        "UPDATE agent_finding SET agent_decision_id = NULL, previous_agent_finding_id = NULL",
                        "UPDATE agent_task SET agent_decision_id = NULL, agent_finding_id = NULL, previous_agent_task_id = NULL"):
                cur.execute(sql)
            for n in ("agent_writeback", "agent_value", "agent_approval", "agent_decision_details", "agent_forecast", "patient_statement", "agent_task", "agent_finding",
                      "agent_decision", "agent_run", "payer_rule"):
                cur.execute(f'DELETE FROM "{n}"')
            conn.commit(); conn.close()
        for code, fam, act in [("R-AUTH-VISITS", "authorization", "hold_for_review"), ("R-COV-ACTIVE", "eligibility", "hold_for_review")]:
            rid, _ = self.add("payer_rule", START, rule_code=code, rule_family=fam, rule_action=act, rule_source_code="built_in", is_enabled=True, is_synthetic=True, approval_status="approved",
                              effective_from=RULES_FROM, owner_role="front_desk", severity="high", approved_by_staff_id=self.W.staff["M01"], approved_date=RULES_FROM)
            self.generic[code] = rid
        if is_r2():          # the A5 pattern rules, as built-in payer_rule rows so each check can point at its rule
            for code, fam, carc in PATTERN_RULES:
                rid, _ = self.add("payer_rule", START, rule_code=code, rule_family=fam, rule_action="hold_for_review", rule_source_code="built_in", is_enabled=True, is_synthetic=True,
                                  approval_status="approved", effective_from=RULES_FROM, owner_role="biller", severity="high", approved_by_staff_id=self.W.staff["M01"], approved_date=RULES_FROM,
                                  adjustment_reason_id=self.W.carc_id.get(carc))
                self.generic[code] = rid

    def writer(self):
        conn, db = connect_replay()
        cur = conn.cursor()
        import io, csv
        while True:
            item = self.wq.get()
            batches = [item]
            while not self.wq.empty():
                batches.append(self.wq.get_nowait())
            if any(b is None for b in batches):
                batches = [b for b in batches if b is not None]
                done = True
            else:
                done = False
            try:
                merged = defaultdict(list)
                ups = []
                for rows, u in batches:
                    for n, lst in rows.items():
                        merged[n].extend(lst)
                    ups.extend(u)
                for n in AGENT_TABLES:
                    if not merged.get(n):
                        continue
                    cols = [c["name"] for c in self.S.T[n]["cols"]]
                    buf = io.StringIO()
                    w = csv.writer(buf, lineterminator="\n")
                    for r_ in merged[n]:
                        w.writerow([self.S._cell(r_.get(c)) for c in cols])
                    buf.seek(0)
                    cur.copy_expert(f'COPY "{n}" ({",".join(chr(34) + c + chr(34) for c in cols)}) FROM STDIN WITH (FORMAT csv, NULL \'\\N\')', buf)
                    self.written[n] += len(merged[n])
                groups = defaultdict(list)
                for t, pk, cols in ups:
                    groups[(t, tuple(sorted(cols)))].append((pk, cols))
                for (t, cnames), lst in groups.items():
                    pkc = self.S.pk[t]
                    cur.execute(f'CREATE TEMP TABLE _u AS SELECT "{pkc}", ' + ",".join(f'"{c}"' for c in cnames) + f' FROM "{t}" WITH NO DATA')
                    buf = io.StringIO()
                    w = csv.writer(buf, lineterminator="\n")
                    for pk, cols in lst:
                        w.writerow([pk] + [self.S._cell(cols[c]) for c in cnames])
                    buf.seek(0)
                    cur.copy_expert(f'COPY _u ("{pkc}",' + ",".join(f'"{c}"' for c in cnames) + ") FROM STDIN WITH (FORMAT csv, NULL '\\N')", buf)
                    cur.execute(f'UPDATE "{t}" x SET ' + ",".join(f'"{c}" = u."{c}"' for c in cnames) + f' FROM _u u WHERE x."{pkc}" = u."{pkc}"')
                    cur.execute("DROP TABLE _u")
                conn.commit()
            except Exception as ex:      # keep the run alive; surface the problem to the UI
                conn.rollback()
                self.publish(dict(type="error", msg=f"database write failed: {ex}"))
            if done:
                for n in AGENT_TABLES:
                    if self.counts[n]:
                        cur.execute(f"SELECT setval(pg_get_serial_sequence('\"{n}\"', '{self.S.pk[n]}'), (SELECT max(\"{self.S.pk[n]}\") FROM \"{n}\"))")
                conn.commit(); conn.close()
                return

    def run(self, speed=1.0):
        self.speed = speed
        self.stop_flag.clear()
        self.status = "preparing"
        self.publish(dict(type="status", status="preparing"))
        self.prepare()
        wt = None
        if self.write:
            wt = threading.Thread(target=self.writer, daemon=True)
            wt.start()
        self.status = "running"
        d = START
        self.publish(dict(type="status", status="running", total_days=self.total_days))
        while d <= TODAY and not self.stop_flag.is_set():
            while self.pause_flag.is_set() and not self.stop_flag.is_set():
                self.status = "paused"
                time.sleep(.1)
            self.status = "running"
            self.day_no += 1
            t0 = time.perf_counter()
            world, wc = self.run_day(d)
            self.publish(self.packet(d, world, wc))
            if self.speed < 500:
                delay = 1.0 / self.speed - (time.perf_counter() - t0)
                if delay > 0:
                    end = time.time() + delay
                    while time.time() < end and not self.stop_flag.is_set():
                        time.sleep(min(.05, max(0, end - time.time())))
            d += dt.timedelta(days=1)
        self.status = "finished" if d > TODAY else "stopped"
        if wt:
            self.wq.put(None)
            wt.join()
        self.publish(dict(type="status", status=self.status, tables={n: self.counts[n] for n in AGENT_TABLES}, written={n: self.written[n] for n in AGENT_TABLES}))


if __name__ == "__main__":
    from world import World
    dry = "--dry" in sys.argv
    t = time.time()
    W = World(log=lambda m: None)
    R = Replay(W, write=not dry)
    last = {}
    def pub(p):
        if p["type"] == "day":
            last.update(p)
    R.publish = pub
    R.run(speed=1000)
    print("seconds", round(time.time() - t, 1), "status", R.status)
    print({n: len(R.S.rows[n]) for n in AGENT_TABLES})
    errs = R.S.check()
    print("check errors:", len(errs), errs[:8])
    print("mirror:", R.mirror, "value:", {k: float(v) for k, v in R.value.items()})
    print("learned:", {k: (v["since"], v["threshold"]) for k, v in R.learned.items()})
    print("board:", dict(R.board))
