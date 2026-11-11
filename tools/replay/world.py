"""The world: the loaded history, read back from PostgreSQL into memory with date indexes.

Only the columns the replay needs are read. Nothing here changes the database.
"""
import datetime as dt
import os
from collections import defaultdict
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "synth"))
from core import connect  # noqa: E402

R2_DB = "krisnnai_r2"


def replay_db():
    """Database the replay reads. Unset (default) = whatever core.connect() uses today (krisnnai_canonical). KRISNNAI_REPLAY_DB=krisnnai_r2 selects R2 through the canon_compat views."""
    v = os.environ.get("KRISNNAI_REPLAY_DB", "").strip()
    if v and v != R2_DB:
        raise ValueError(f"KRISNNAI_REPLAY_DB must be unset or exactly {R2_DB!r}")
    return v or None


def is_r2():
    return replay_db() == R2_DB


def connect_replay():
    """Like core.connect(), but honours KRISNNAI_REPLAY_DB: for R2 it connects to krisnnai_r2 and points search_path at canon_compat (views only, tenant 1)."""
    if not is_r2():
        return connect()
    os.environ["KRISNNAI_PG_DB"] = R2_DB
    conn, db = connect()
    assert db == R2_DB, db
    cur = conn.cursor()
    cur.execute("SET search_path TO canon_compat")
    conn.commit()
    return conn, db

COLS = {
    "payer": "*", "cpt_code": "cpt_code_id, code, is_timed", "patient": "patient_id", "fee_list": "cpt_code_id, fee_per_unit", "adjustment_reason": "*", "modifier": "*", "staff": "*", "provider": "provider_id, provider_name, provider_type",
    "appointment": "appointment_id, patient_id, appointment_date, appointment_status, provider_id, payer_id, coverage_id, booked_date",
    "appointment_details": "appointment_id, line_number, authorization_id, expected_charge",
    "eligibility_check": "eligibility_check_id, appointment_id, coverage_id, patient_id, payer_id, check_date, service_date, plan_end_date, is_aaa_reject",
    "authorization": "authorization_id, units_approved, payer_id", "coverage": "coverage_id, termination_date",
    "encounter": "encounter_id, patient_id, encounter_date, encounter_type, authorization_id, note_status, note_signed_date, signature_lag_days, rendering_provider_id, payer_id, appointment_id",
    "encounter_details": "encounter_id, cpt_code_id, documented_level, modifier_1_id, modifier_2_id",
    "document": "patient_id, document_type, document_date, document_status",
    "bill": "bill_id, encounter_id, patient_id, payer_id, charge_entered_date, total_billed, bill_status, bill_type, rendering_provider_id, service_date",
    "claim": "claim_id, claim_number, payer_id, patient_id, encounter_id, bill_id, authorization_id, coverage_id, service_date_from, submitted_date, total_charge, rendering_provider_id",
    "claim_details": "claim_detail_id, claim_id, cpt_code_id, modifier_1_id, modifier_2_id, allowed_amount, expected_allowed, paid_amount, charge_amount, denied_amount, patient_responsibility",
    "claim_status_history": "claim_id, event_type, event_date, status_after, is_rejection, rejection_reason",
    "transactions": "transaction_id, denial_id, transaction_type, transaction_date",
    "denial": "denial_id, claim_id, claim_detail_id, payer_id, denial_date, denied_amount, adjustment_reason_id, denial_status, appeal_deadline, upstream_stage, is_preventable, owner_role, resolved_date, outcome, recovered_amount",
    "appeal": "appeal_id, denial_id, submitted_date, decision_date, is_overturned, recovered_amount, appeal_status",
    "payment": "payment_id, payer_id, payment_source, payment_date, payment_amount, posted_amount, unapplied_amount",
    "ar": "ar_id, bill_id, claim_id, patient_id, payer_id, balance_owner, balance, days_outstanding, service_date",
    "enrollment": "enrollment_id, provider_id, payer_id, event_type, expires_date",
}


class World:
    def __init__(self, log=print):
        self.conn, self.db = connect_replay()
        self.conn.set_session(readonly=True)
        cur = self.conn.cursor()
        self.t = {}
        cols_by = dict(COLS)
        if is_r2():
            cols_by["ar"] += ", as_of_date, snapshot_type"       # the R2 compat view exposes every snapshot; the engine picks the latest one known on each replay date
        for n, cols in cols_by.items():
            log(f"reading {n}")
            cur.execute(f'SELECT {cols} FROM "{n}"')
            names = [c[0] for c in cur.description]
            self.t[n] = [dict(zip(names, row)) for row in cur.fetchall()]
        cur.execute("SELECT practice_id FROM practice LIMIT 1")
        self.practice = cur.fetchone()[0]
        self.has_ext = is_r2()
        self.ext = {"line_units": [], "claim_dx": [], "auth": [], "appt_lines": [], "elig_other": []}
        if self.has_ext:
            # Facts the A5 pattern rules need that canon_compat does not expose (units per line, the claim's principal diagnosis, authorization windows).
            # Read-only SELECTs on the R2 tables, tenant 1, schema-qualified. All of it is known when the claim is released (rule 9 is applied by the engine, by date).
            log("reading claim_line units, claim diagnosis, authorization windows")
            cur.execute("SELECT claim_line_id, units FROM public.claim_line WHERE tenant_id = 1")
            self.ext["line_units"] = cur.fetchall()
            cur.execute("SELECT c.claim_id, d.icd10_code FROM public.claim c LEFT JOIN public.diagnosis_code d ON d.diagnosis_code_id = c.principal_diagnosis_code_id WHERE c.tenant_id = 1")
            self.ext["claim_dx"] = cur.fetchall()
            cur.execute('SELECT patient_id, payer_id, primary_cpt_code_id, authorization_status, valid_from, valid_to, units_approved, decision_date FROM public."authorization" WHERE tenant_id = 1')
            self.ext["auth"] = cur.fetchall()
            # scheduled (future) appointments: every planned line, and eligibility checks that name another payer as primary
            cur.execute("SELECT appointment_id, line_number, planned_cpt_code_id, planned_units FROM public.appointment_line WHERE tenant_id = 1 AND appointment_id IN "
                        "(SELECT appointment_id FROM public.appointment WHERE tenant_id = 1 AND appointment_status = 'scheduled')")
            self.ext["appt_lines"] = cur.fetchall()
            cur.execute("SELECT eligibility_check_id, other_payer_id FROM public.eligibility_check WHERE tenant_id = 1 AND other_payer_id IS NOT NULL")
            self.ext["elig_other"] = cur.fetchall()
        self.conn.close()
        t = self.t
        self.doc_types = {d["document_type"] for d in t["document"]}
        self.payer_code = {p["payer_id"]: p["payer_code"] for p in t["payer"]}
        self.payer_id = {v: k for k, v in self.payer_code.items()}
        self.payer = {p["payer_id"]: p for p in t["payer"]}
        self.cpt = {c["cpt_code_id"]: c["code"] for c in t["cpt_code"]}
        self.cpt_id = {v: k for k, v in self.cpt.items()}
        self.fee = {self.cpt[f["cpt_code_id"]]: f["fee_per_unit"] for f in t["fee_list"]}
        self.carc = {a["adjustment_reason_id"]: a for a in t["adjustment_reason"]}
        self.carc_id = {a["carc_code"]: a["adjustment_reason_id"] for a in t["adjustment_reason"]}
        self.mod = {m["modifier_code"]: m["modifier_id"] for m in t["modifier"]}
        self.staff = {s_["staff_number"]: s_["staff_id"] for s_ in t["staff"]}
        self.enc = {e["encounter_id"]: e for e in t["encounter"]}
        self.claim = {c["claim_id"]: c for c in t["claim"]}
        self.appt = {a["appointment_id"]: a for a in t["appointment"]}
        self.auth = {a["authorization_id"]: a for a in t["authorization"]}
        self.cov = {c["coverage_id"]: c for c in t["coverage"]}
        self.bill_by_enc = {b["encounter_id"]: b for b in t["bill"]}
        self.claim_by_enc = {c["encounter_id"]: c for c in t["claim"]}
        self.prov_name = {p["provider_id"]: p["provider_name"] for p in t["provider"]}
        self.enc_lines = defaultdict(list)
        for x in t["encounter_details"]:
            self.enc_lines[x["encounter_id"]].append(x)
        self.cd = defaultdict(list)
        for x in t["claim_details"]:
            self.cd[x["claim_id"]].append(x)
        self.den_by_claim = defaultdict(list)
        for d in t["denial"]:
            self.den_by_claim[d["claim_id"]].append(d)
        self.hist = defaultdict(list)
        for x in t["claim_status_history"]:
            self.hist[x["claim_id"]].append(x)
        self.pat_enc = defaultdict(list)
        for e in sorted(t["encounter"], key=lambda e: e["encounter_date"]):
            self.pat_enc[e["patient_id"]].append(e)
        self.pat_doc = defaultdict(list)
        for d in t["document"]:
            self.pat_doc[d["patient_id"]].append(d)
        self.auth_dates = defaultdict(list)
        for e in t["encounter"]:
            if e["authorization_id"]:
                self.auth_dates[e["authorization_id"]].append(e["encounter_date"])
        for v in self.auth_dates.values():
            v.sort()
        self.appeal = {a["denial_id"]: a for a in t["appeal"]}
        self.tx_den = {x["denial_id"]: x["transaction_id"] for x in t["transactions"] if x["denial_id"] and x["transaction_type"] == "payment"}
        self.appt_expected = defaultdict(lambda: 0)
        self.appt_auth = {}
        for x in t["appointment_details"]:
            self.appt_expected[x["appointment_id"]] += x["expected_charge"] or 0
            if x["authorization_id"] and (x["line_number"] == 1 or (self.has_ext and x["appointment_id"] not in self.appt_auth)):      # R2: any line of the appointment, not only line 1
                self.appt_auth[x["appointment_id"]] = x["authorization_id"]
        # A5 pattern-rule facts (empty outside R2: the rules then abstain, unknown is not "missing")
        self.line_units = dict(self.ext["line_units"])
        self.claim_dx = dict(self.ext["claim_dx"])
        self.auth_by_key = defaultdict(list)
        for pt, py, cp, st, vf, vt, ua, dd in self.ext["auth"]:
            self.auth_by_key[(pt, py, cp)].append(dict(status=st, valid_from=vf, valid_to=vt, units_approved=ua or 0, decision_date=dd))
        self.appt_lines = defaultdict(list)          # scheduled appointment -> [(line_number, cpt_code_id, planned_units)], all lines
        for aid, ln_, cp, u in sorted(self.ext["appt_lines"], key=lambda x: (x[0], x[1])):
            self.appt_lines[aid].append((ln_, cp, u))
        self.elig_other = dict(self.ext["elig_other"])    # eligibility_check_id -> payer the check named as primary instead
        self.checks_by_appt = defaultdict(list)
        for ck in t["eligibility_check"]:
            self.checks_by_appt[ck["appointment_id"]].append(ck)
        self.line_hist = defaultdict(list)           # (patient, cpt_id) -> [(service_date, claim_detail_id, units, claim_id, payer_id)] in service order
        if self.has_ext:
            for c in t["claim"]:
                for ln in self.cd[c["claim_id"]]:
                    self.line_hist[(c["patient_id"], ln["cpt_code_id"])].append((c["service_date_from"], ln["claim_detail_id"], self.line_units.get(ln["claim_detail_id"]), c["claim_id"], c["payer_id"]))
            for v in self.line_hist.values():
                v.sort(key=lambda x: (x[0], x[1]))
        self.last_day = max(c["event_date"] for c in t["claim_status_history"])
        parents = ["payer", "provider", "appointment", "encounter", "bill", "claim", "denial", "authorization", "cpt_code", "staff", "patient", "coverage", "claim_details"]
        self.ids = {n: {r[n + "_id"] if n != "claim_details" else r["claim_detail_id"] for r in t[n]} for n in parents if n in t}
        self.ids["claim_detail"] = self.ids.pop("claim_details")
        self.ids["practice"] = {self.practice}
        self.ids["transactions"] = {x["transaction_id"] for x in t["transactions"]}
