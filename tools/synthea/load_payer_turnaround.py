"""Sets payer.standard_turnaround_days in krisnnai_r2 (tenant 1) to the OBSERVED median number of days from claim.submitted_date to the claim's first payer payment.

This value is derived from the generated (Synthea) data, not a contract term and not a real payer standard. It is a static per-payer parameter computed over the whole
history, so using it in a replay on earlier dates is mild look-ahead; treat it as a stand-in until real payer turnaround standards are loaded.

First payer payment = earliest payment.payment_date (payment_source = 'payer') among the payments that remit the claim (remittance_claim). Median = percentile_cont(0.5), rounded to whole days.
Payers with no payer payments (SELF, no insurance) are left unchanged (NULL).
Writes ONLY the standard_turnaround_days column, for tenant_id = 1. Rerunnable: it recomputes and sets the same values. Credentials come from the existing connect() helper and are never printed.

Usage:  python tools/synthea/load_payer_turnaround.py            (apply)
        python tools/synthea/load_payer_turnaround.py --dry      (show the values, change nothing)
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "synth"))
os.environ["KRISNNAI_PG_DB"] = "krisnnai_r2"
from core import connect  # noqa: E402

TENANT = 1
MEDIANS = """
SELECT cl.payer_id, round((percentile_cont(0.5) WITHIN GROUP (ORDER BY f.first_paid - cl.submitted_date))::numeric)::int AS median_days, count(*) AS claims
FROM (SELECT rc.claim_id, min(p.payment_date) AS first_paid
      FROM remittance_claim rc JOIN payment p ON p.payment_id = rc.payment_id AND p.tenant_id = rc.tenant_id
      WHERE rc.tenant_id = %(t)s AND p.payment_source = 'payer' GROUP BY rc.claim_id) f
JOIN claim cl ON cl.claim_id = f.claim_id
WHERE cl.tenant_id = %(t)s AND cl.submitted_date IS NOT NULL AND f.first_paid >= cl.submitted_date
GROUP BY cl.payer_id
"""


def main():
    dry = "--dry" in sys.argv
    conn, db = connect()
    assert db == "krisnnai_r2", db
    cur = conn.cursor()
    cur.execute(MEDIANS, dict(t=TENANT))
    vals = {r[0]: (r[1], r[2]) for r in cur.fetchall()}
    cur.execute("SELECT payer_id, payer_code FROM payer WHERE tenant_id = %s ORDER BY payer_id", (TENANT,))
    for pid, code in cur.fetchall():
        v = vals.get(pid)
        print(f"{code:10s} {'-' if v is None else v[0]:>4} days   ({0 if v is None else v[1]:,} claims)" + ("" if v else "   no payer payments: left NULL"))
        if v and not dry:
            cur.execute("UPDATE payer SET standard_turnaround_days = %s WHERE payer_id = %s AND tenant_id = %s", (v[0], pid, TENANT))
    if dry:
        conn.rollback()
    else:
        conn.commit()
    conn.close()


if __name__ == "__main__":
    main()
