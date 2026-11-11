"""Stage 6a: patient billing for krisnnai_r2 - transfers, statements, payments, payment plans, collection placements, contact preferences.

Run after load_denials.py (that stage restores the ledger and removes everything this one adds, so run this one again after it).

1. Transfers: the ledger kept the patient's insurance share inside the payer balance. For each claim with a patient share a payer-to-patient transfer (an out row and an in row) is
   booked on the date the share became known, so payer balance is what insurance owes and patient balance is what patients owe.
2. Collection items: every claim's patient share and every open self-pay bill. Each gets up to 4 statements (first 7 days after the balance is known, then every 30 days). After
   each statement a share of the patients pays (insured 45/25/15/8%, self-pay 18/12/8/4%; one payment in ten is only half). At the second statement a balance of $300 or more may go
   on a payment plan (20%). Balances of $50 or more still open 120 days after the first statement are placed with a collection agency, which recovers 20% of them.
3. Contact preferences: one row per patient.
Every rule above is our assumption, not data. Money is real ledger entries (source 'billing_sim') and payment rows, so a rerun deletes them and rebuilds. Nothing is written off:
what is not paid stays open (hard rule 4). All randomness is a hash of the item, so a rerun gives the same result.

    python tools/synthea/load_patient_billing.py --reset
"""
import datetime as dt
import hashlib
import sys
from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal

from r2load import Loader, connect

TODAY = dt.date(2026, 11, 6)
SRC = "billing_sim"
CENT = Decimal("0.01")
P_PAY = {"C": (.45, .25, .15, .08), "B": (.18, .12, .08, .04)}  # chance a patient pays after statement 1..4: claim share (insured) or self-pay bill
PLAN_MIN, PLACE_MIN, P_PLAN, P_RECOVER = Decimal(300), Decimal(50), .20, .20


def u(key, salt):
    """Repeatable pseudo-random number in [0, 1)."""
    return int(hashlib.md5(f"{key}|{salt}".encode()).hexdigest()[:7], 16) / 16 ** 7


def money(x):
    return Decimal(x).quantize(CENT, ROUND_HALF_UP)


def allocate(amount, remaining):
    """Splits a payment over lines in proportion to what each still owes; the last line takes the rounding."""
    total = sum(remaining)
    out, left = [], amount
    for i, r in enumerate(remaining):
        share = left if i == len(remaining) - 1 else min(r, money(amount * r / total))
        share = min(share, r)
        out.append(share)
        left -= share
    return out


class Sim:
    def __init__(self, L, cur, guarantor, pref):
        self.L, self.cur, self.guarantor, self.pref = L, cur, guarantor, pref
        self.ledger, self.payments, self.stmts, self.plans, self.places = [], [], [], [], []
        cur.execute("select coalesce(max(ledger_entry_id), 0) from ledger_entry")
        self.led = cur.fetchone()[0]
        cur.execute("select coalesce(max(payment_id), 0) from payment")
        self.pid = cur.fetchone()[0]
        self.sid = self.plan_id = self.plc_id = 0

    def ledger_row(self, it, line, **kw):
        self.led += 1
        base = dict(ledger_entry_id=self.led, transaction_number=f"TXN-{self.led}", practice_id=it["practice"], patient_id=it["patient"], bill_line_id=line["bill_line_id"],
                    claim_line_id=line.get("claim_line_id"), claim_id=it.get("claim_id"), payer_id=it["payer"], provider_id=line["provider"], specialty_id=line["specialty"],
                    cpt_code_id=line["cpt"], posted_by_role="system", source=SRC)
        self.ledger.append({**base, **kw})

    def transfer(self, it, line, date):
        amt = line["amount"]
        for party, eff, sub in (("payer", -amt, "to_patient"), ("patient", amt, "from_payer")):
            self.ledger_row(it, line, transaction_type="transfer", transaction_subtype=sub, amount=amt, balance_effect=eff, transaction_date=date, posted_date=date,
                            responsible_party=party, from_party="payer", to_party="patient")

    def pay(self, it, date, amount, method, point, number):
        """One payment row, spread over the item's lines."""
        self.pid += 1
        shares = allocate(amount, [ln["rem"] for ln in it["lines"]])
        self.payments.append(dict(payment_id=self.pid, payment_number=number, practice_id=it["practice"], payment_source="patient", payment_date=date, payment_amount=amount, payment_method=method,
                                  patient_id=it["patient"], guarantor_id=self.guarantor[it["patient"]], collection_point=point, payment_type=method, received_date=date, posted_date=date,
                                  credit_debit="C", has_remittance=False, claim_count=0, posted_amount=amount, unapplied_amount=0, plb_amount=0, reconciles=True, is_void=False, source=SRC))
        for ln, s in zip(it["lines"], shares):
            if s > 0:
                self.ledger_row(it, ln, transaction_type="payment", amount=s, balance_effect=-s, transaction_date=date, posted_date=date, responsible_party="patient",
                                payment_method=method, payment_id=self.pid, payment_number=number)
                ln["rem"] -= s
        it["rem"] -= amount

    def place(self, it, placed):
        """Agency placement of what is still open; returns nothing, records the placement and any recovery."""
        if it["rem"] < PLACE_MIN or placed > TODAY:
            return None
        self.plc_id += 1
        row = dict(collection_placement_id=self.plc_id, placement_number=f"PLC-{self.plc_id:07d}", guarantor_id=self.guarantor[it["patient"]], patient_id=it["patient"],
                   agency_code="AGENCY-A" if u(it["key"], "ag") < .5 else "AGENCY-B", placement_type="third_party", is_third_party=True, placed_date=placed, placed_amount=it["rem"],
                   recovered_amount=0, agency_fee_amount=0, placement_status="active", credit_reported=False, practice_id=it["practice"])
        if u(it["key"], "rec") < P_RECOVER:
            rdate = placed + dt.timedelta(days=30 + int(u(it["key"], "rd") * 60))
            if rdate <= TODAY:
                amt = it["rem"]
                row.update(recovered_amount=amt, agency_fee_amount=money(amt * Decimal("0.25")), placement_status="paid_in_full", closed_date=rdate)
                self.pay(it, rdate, amt, "agency", "agency", f"AG-{self.plc_id:07d}")
        elif placed + dt.timedelta(days=180) <= TODAY:
            row.update(placement_status="recalled", recall_date=placed + dt.timedelta(days=180), recall_reason="no_recovery", closed_date=placed + dt.timedelta(days=180))
        self.places.append(row)
        return row

    def plan(self, it, start):
        """Payment plan from `start`: monthly instalments; 60% complete, 25% default part-way, 15% pay one late."""
        self.plan_id += 1
        total = it["rem"]
        n = 6 if total < 900 else 12
        inst = money(total / n)
        due = [start + dt.timedelta(days=30 * j) for j in range(n)]
        auto = u(it["key"], "auto") < .35
        b, m = u(it["key"], "planb"), 1 + int(u(it["key"], "planm") * (n - 2))
        paid_n, missed, last_missed, status, end = 0, 0, None, "active", None
        for j in range(n):
            amount = inst if j < n - 1 else total - inst * (n - 1)
            pay_date = due[j] + dt.timedelta(days=0 if auto else int(u(it["key"], f"pl{j}") * 5))
            if .6 <= b < .85 and j >= m:  # defaults: misses every instalment from m on
                if due[j] <= TODAY:
                    missed += 1
                    last_missed = due[j]
                if missed == 2:
                    status, end = "defaulted", due[j]
                    break
                continue
            if b >= .85 and j == m:  # one late instalment
                pay_date = due[j] + dt.timedelta(days=20)
                if due[j] <= TODAY:
                    missed += 1
                    last_missed = due[j]
            if pay_date <= TODAY:
                self.pay(it, pay_date, amount, "ach" if auto else "card", "plan", f"PP-{self.plan_id:06d}-{j + 1:02d}")
                paid_n += 1
                end = pay_date
        if status == "active" and paid_n == n:
            status = "completed"
        elif status == "active":
            end = None
        nxt = due[paid_n] if status == "active" and paid_n < n else None
        row = dict(payment_plan_id=self.plan_id, payment_plan_number=f"PLAN-{self.plan_id:06d}", patient_id=it["patient"], guarantor_id=self.guarantor[it["patient"]], plan_status=status,
                   start_date=start, total_amount=total, practice_id=it["practice"], instalment_amount=inst, instalment_count=n, frequency="monthly", next_due_date=nxt,
                   missed_instalments=missed, last_missed_date=last_missed, autopay_enrolled=auto, end_date=end if status != "active" else None)
        self.plans.append(row)
        return row, (end if status == "defaulted" else None)

    def run(self, it):
        kind, p = it["kind"], P_PAY[it["kind"]]
        first = it["d0"] + dt.timedelta(days=7)
        stm, plan, placement = [], None, None
        k = 0
        while k < 4:
            sdate = first + dt.timedelta(days=30 * k)
            if sdate > TODAY or it["rem"] <= 0:
                break
            self.sid += 1
            stm.append(dict(patient_statement_id=self.sid, statement_number=f"STM-{self.sid:07d}", patient_id=it["patient"], guarantor_id=self.guarantor[it["patient"]], statement_date=sdate,
                            statement_amount=it["rem"], channel=self.pref[it["patient"]], statement_status="sent", practice_id=it["practice"], bill_id=it["bill_id"], claim_id=it.get("claim_id"),
                            due_date=sdate + dt.timedelta(days=30), sent_at=dt.datetime(sdate.year, sdate.month, sdate.day, 9, 0, 0), status_date=sdate, dunning_level=k,
                            previous_patient_statement_id=stm[-1]["patient_statement_id"] if stm else None))
            if k == 1 and it["rem"] >= PLAN_MIN and u(it["key"], "plan") < P_PLAN and sdate + dt.timedelta(days=5) <= TODAY:
                plan, defaulted = self.plan(it, sdate + dt.timedelta(days=5))
                stm[-1]["payment_plan_id"] = plan["payment_plan_id"]
                if defaulted and it["rem"] >= PLACE_MIN:
                    placement = self.place(it, defaulted + dt.timedelta(days=30))
                break
            if u(it["key"], f"pay{k}") < p[k]:
                amt = it["rem"] if u(it["key"], f"part{k}") >= .1 else money(it["rem"] / 2)
                pdate = sdate + dt.timedelta(days=3 + int(u(it["key"], f"pd{k}") * 25))
                if pdate <= TODAY:
                    method = "card" if u(it["key"], f"m{k}") < .7 else "check"
                    self.pay(it, pdate, amt, method, "statement", f"PT-{kind}{it['bill_id'] if kind == 'B' else it['claim_id']}-{k + 1}")
                    stm[-1]["status_date"] = pdate
            k += 1
        if plan is None and it["rem"] >= PLACE_MIN and len(stm) == 4:
            placement = self.place(it, first + dt.timedelta(days=120))
        # statement status as of today
        if placement and stm:
            stm[-1]["collection_placement_id"] = placement["collection_placement_id"]
        for i, s in enumerate(stm):
            if i < len(stm) - 1:
                s["statement_status"] = "superseded"
            elif it["rem"] <= 0:
                s["statement_status"] = "paid"
            elif placement:
                s["statement_status"] = "collections"
            elif plan:
                s["statement_status"] = "in_plan"
            elif s["due_date"] < TODAY:
                s["statement_status"] = "overdue"
        self.stmts.extend(stm)


def refresh_selfpay(cur):
    """Self-pay bill and line status from what the ledger says (also undoes a previous run when the simulated rows have just been deleted)."""
    cur.execute("select payer_id from payer where payer_type = 'self_pay'")
    selfpay = cur.fetchone()[0]
    cur.execute(f"""UPDATE bill_line bl SET line_status = CASE WHEN x.b <= 0.005 THEN 'paid' ELSE 'open' END
                    FROM (select bill_line_id, sum(balance_effect) b from ledger_entry where responsible_party = 'patient' group by 1) x WHERE x.bill_line_id = bl.bill_line_id AND bl.payer_id = {selfpay}""")
    cur.execute(f"""UPDATE bill b SET bill_status = CASE WHEN EXISTS (select 1 from bill_line l where l.bill_id = b.bill_id and l.line_status <> 'paid') THEN 'open' ELSE 'paid' END WHERE b.payer_id = {selfpay}""")


def flush(L, table, rows, size=50000):
    n = 0
    for i in range(0, len(rows), size):
        n += L.rows(table, rows[i:i + size])
    return n


def main():
    reset = "--reset" in sys.argv
    conn = connect()
    cur = conn.cursor()
    cur.execute("SET session_replication_role = replica")
    q = lambda s: (cur.execute(s), cur.fetchall())[1]
    if reset:
        cur.execute(f"DELETE FROM ledger_entry WHERE source = '{SRC}'")
        cur.execute(f"DELETE FROM payment WHERE source = '{SRC}'")
        for t in ["patient_statement", "payment_plan", "collection_placement", "patient_contact_preference"]:
            cur.execute(f'DELETE FROM "{t}"')
        refresh_selfpay(cur)
    else:
        assert q(f"select count(*) from ledger_entry where source = '{SRC}'")[0][0] == 0, "already loaded; use --reset"
    L = Loader(conn)

    # contact preferences
    pats = q("select patient_id, guarantor_id, first_seen_date from patient order by patient_id")
    guarantor, pref, rows = {}, {}, []
    for pid, gid, seen in pats:
        guarantor[pid] = gid
        opt, text = u(pid, "oo") < .03, u(pid, "oo") >= .03 and u(pid, "tx") < .6
        r = u(pid, "ch")
        pref[pid] = "mail" if opt else "mail" if r < .45 else "portal" if r < .70 else "email" if r < .90 else ("text" if text else "email")
        rows.append(dict(patient_contact_preference_id=pid, patient_id=pid, opt_out=opt, text_consent=text, preferred_channel=pref[pid], quiet_hours_start=21, quiet_hours_end=8,
                         contact_time_zone="America/Chicago", address_status="bad" if u(pid, "ad") < .03 else "valid", has_phone=u(pid, "ph") > .08, autodial_consent=text and u(pid, "au") < .5,
                         consent_date=seen, consent_source="intake", consent_wording_version="v1", opt_out_date=(seen + dt.timedelta(days=30)) if opt and seen else None,
                         has_authorized_rep=False, guarantor_id=gid))
    n = {"patient_contact_preference": flush(L, "patient_contact_preference", rows)}

    sim = Sim(L, cur, guarantor, pref)
    items = []
    for cid, clid, blid, pr, pat, prac, payer, bill, cpt, prov, spec, d in q(
            """SELECT cl.claim_id, cl.claim_line_id, cl.bill_line_id, cl.patient_responsibility, c.patient_id, c.practice_id, c.payer_id, c.bill_id, cl.cpt_code_id, cl.rendering_provider_id,
                      cl.specialty_id, x.d
               FROM claim_line cl JOIN claim c ON c.claim_id = cl.claim_id
               JOIN (select claim_line_id, min(transaction_date) d from ledger_entry where transaction_subtype = 'patient_responsibility' group by 1) x ON x.claim_line_id = cl.claim_line_id
               WHERE cl.patient_responsibility > 0 ORDER BY cl.claim_id"""):
        line = dict(claim_line_id=clid, bill_line_id=blid, amount=pr, rem=pr, provider=prov, specialty=spec, cpt=cpt)
        items.append(dict(kind="C", key=f"C{cid}", claim_id=cid, bill_id=bill, patient=pat, practice=prac, payer=payer, lines=[line], rem=pr, d0=d))
    byb = {}
    for bill, pat, prac, payer, blid, amt, cpt, prov, spec, d in q(
            """SELECT b.bill_id, b.patient_id, b.practice_id, b.payer_id, bl.bill_line_id, bl.billed_amount, bl.cpt_code_id, bl.provider_id, bl.specialty_id, ch.d
               FROM bill b JOIN payer p ON p.payer_id = b.payer_id JOIN bill_line bl ON bl.bill_id = b.bill_id
               JOIN (select bill_line_id, max(transaction_date) d from ledger_entry where transaction_type = 'charge' group by 1) ch ON ch.bill_line_id = bl.bill_line_id
               WHERE p.payer_type = 'self_pay' AND b.bill_status = 'open' ORDER BY b.bill_id, bl.line_number"""):
        it = byb.setdefault(bill, dict(kind="B", key=f"B{bill}", bill_id=bill, patient=pat, practice=prac, payer=payer, lines=[], rem=Decimal(0), d0=d))
        it["lines"].append(dict(bill_line_id=blid, amount=amt, rem=amt, provider=prov, specialty=spec, cpt=cpt))
        it["rem"] += amt
        it["d0"] = max(it["d0"], d)
    items += byb.values()
    for it in items:
        if it["kind"] == "C":
            sim.transfer(it, it["lines"][0], it["d0"])
        sim.run(it)

    n["ledger_entry"] = flush(L, "ledger_entry", sim.ledger)
    n["payment"] = flush(L, "payment", sim.payments)
    n["patient_statement"] = flush(L, "patient_statement", sim.stmts)
    n["payment_plan"] = flush(L, "payment_plan", sim.plans)
    n["collection_placement"] = flush(L, "collection_placement", sim.places)

    # what the ledger now says about claims and self-pay bills
    cur.execute("UPDATE claim SET balance = patient_responsibility + denied_amount WHERE claim_status <> 'submitted'")
    cur.execute("""UPDATE claim c SET balance = c.balance - x.p FROM (select claim_id, sum(amount) p from ledger_entry where transaction_type = 'payment' and responsible_party = 'patient'
                   and claim_id is not null group by 1) x WHERE x.claim_id = c.claim_id AND c.claim_status <> 'submitted'""")
    refresh_selfpay(cur)
    conn.commit()

    for t, c in n.items():
        print(f"{t:28s}{c:>10,}")
    for sql in ["select statement_status, count(*), round(sum(statement_amount)) from patient_statement group by 1 order by 2 desc",
                "select plan_status, count(*), round(sum(total_amount)) from payment_plan group by 1",
                "select placement_status, count(*), round(sum(placed_amount)), round(sum(recovered_amount)) from collection_placement group by 1",
                "select responsible_party, round(sum(balance_effect)) from ledger_entry group by 1",
                "select kind, count(*), round(sum(rem)) from (select 'claim share' kind, balance rem from claim where claim_status <> 'submitted' and patient_responsibility > 0) x group by 1"]:
        print(q(sql))


if __name__ == "__main__":
    main()
