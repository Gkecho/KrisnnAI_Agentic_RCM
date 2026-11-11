"""Solution-level seed for the query registry: one named query per data section of fin_data.js.

These are the queries the exporter used to hold as inline ``SQL_*`` constants (metric definitions: docs/fin_metrics.md).
Binds: ``:tenant_id`` (always), ``:asof`` (the data date) and ``:d`` (an as-of date for point-in-time queries).
Every select column has an alias because the registry validates the result columns by name and order; the Python
builders read them by position, so an edit may change HOW a column is computed, never WHICH columns come back.
"""

from __future__ import annotations

from typing import Any

SOLUTION = ("krisnnai_rcm_analytics", "KrisnnAI RCM analytics")
PARENT_APP = ("financial", "Financial")
APPS = [
    ("overview", "Overview"),
    ("billing", "Billing"),
    ("payments", "Payments"),
    ("ar", "A/R"),
    ("denials", "Denials"),
    ("patient", "Patient"),
    ("payers", "Payers"),
]
DEMO_CUSTOMER = ("1", "Demo practice (tenant 1)")
DEMO_ROLES = [("billing_manager", "Billing manager"), ("practice_manager", "Practice manager")]

# Lower edges of the 2nd..6th bucket, used with width_bucket(): 0-30 -> 0 ... 181+ -> 5.
EDGES = "ARRAY[31, 61, 91, 121, 181]"

LINE_FACTS_CTE = """
WITH patient_paid AS (          -- patient payments that the ledger ties to a claim line
    SELECT claim_line_id, SUM(amount) AS paid
    FROM ledger_entry
    WHERE tenant_id = :tenant_id AND transaction_type = 'payment' AND responsible_party = 'patient'
      AND claim_line_id IS NOT NULL AND transaction_date <= :asof
    GROUP BY claim_line_id
),
agency_patient AS (             -- patients with an active collection placement
    SELECT DISTINCT patient_id
    FROM collection_placement
    WHERE tenant_id = :tenant_id AND placement_status = 'active' AND placed_date <= :asof
),
line AS (
    SELECT p.payer_code,
           TO_CHAR(cl.service_date, 'YYYY-MM') AS service_month,
           cl.charge_amount,
           cl.line_status,
           cl.paid_amount,
           cl.contractual_adjustment,
           cl.patient_responsibility,
           d.denial_status,
           COALESCE(pp.paid, 0) AS patient_paid,
           (ap.patient_id IS NOT NULL) AS at_agency
    FROM claim_line cl
    JOIN payer p ON p.payer_id = cl.payer_id AND p.tenant_id = :tenant_id
    LEFT JOIN denial d ON d.claim_line_id = cl.claim_line_id AND d.tenant_id = :tenant_id
    LEFT JOIN patient_paid pp ON pp.claim_line_id = cl.claim_line_id
    LEFT JOIN agency_patient ap ON ap.patient_id = cl.patient_id
    WHERE cl.tenant_id = :tenant_id AND cl.service_date <= :asof
)
"""

_Q: dict[str, dict[str, Any]] = {}


def q(
    query_id: str,
    title: str,
    apps: list[str],
    charts: list[str],
    columns: str,
    sql: str,
    params: str = "tenant_id,asof",
) -> None:
    _Q[query_id] = {
        "title": title,
        "owner_app": apps[0],
        "apps": apps,
        "charts": charts,
        "params": params.split(","),
        "columns": [tuple(c.split(":")) for c in columns.split(",")],
        "sql": sql.strip() + "\n",
    }


q(
    "payers.list",
    "Payer list",
    ["overview", "billing", "payments", "ar", "denials", "patient", "payers"],
    ["Payer filter (all pages)"],
    "payer_code:text,payer_name:text,payer_type:text",
    """
SELECT payer_code AS payer_code, payer_name AS payer_name, payer_type AS payer_type
FROM payer
WHERE tenant_id = :tenant_id AND payer_type <> 'self_pay'
ORDER BY payer_code
""",
)

q(
    "headline.claims",
    "Headline: claims, patients, charged",
    ["overview"],
    ["Headline tiles"],
    "claims:int,patients:int,charged:money,first_month:text",
    """
SELECT COUNT(*) AS claims, COUNT(DISTINCT patient_id) AS patients, COALESCE(SUM(total_charge), 0) AS charged,
       TO_CHAR(MIN(service_date_from), 'YYYY-MM') AS first_month
FROM claim
WHERE tenant_id = :tenant_id AND service_date_from <= :asof
""",
)

q(
    "headline.ledger",
    "Ledger by who owes (as of a date)",
    ["overview"],
    ["Headline tiles"],
    "responsible_party:text,transaction_type:text,amount:money,balance_effect:money",
    """
-- Ledger as of a date: payments and balance effect by who owes (payer / patient).
SELECT responsible_party AS responsible_party, transaction_type AS transaction_type,
       COALESCE(SUM(amount), 0) AS amount, COALESCE(SUM(balance_effect), 0) AS balance_effect
FROM ledger_entry
WHERE tenant_id = :tenant_id AND transaction_date <= :d
GROUP BY responsible_party, transaction_type
""",
    params="tenant_id,d",
)

q(
    "headline.denials",
    "Headline: denial total",
    ["overview"],
    ["Headline tiles"],
    "denials:int,denied:money",
    """
SELECT COUNT(*) AS denials, COALESCE(SUM(denied_amount), 0) AS denied
FROM denial
WHERE tenant_id = :tenant_id AND denial_date <= :asof
""",
)

q(
    "flow.links",
    "Money flow (Sankey) totals per payer",
    ["overview"],
    ["Money flow Sankey (all payers and per payer)"],
    "payer_code:text,charged:money,payer_paid:money,contractual:money,patient_share:money,patient_paid:money,"
    "at_agency:money,denied_recovered:money,denied_lost:money,denied_open:money,in_process:money",
    LINE_FACTS_CTE
    + """
SELECT payer_code AS payer_code,
       SUM(charge_amount)                                                             AS charged,
       -- adjudicated lines that were never denied
       SUM(paid_amount)             FILTER (WHERE kind = 'paid')                      AS payer_paid,
       SUM(contractual_adjustment)  FILTER (WHERE kind = 'paid')                      AS contractual,
       SUM(patient_responsibility)  FILTER (WHERE kind = 'paid')                      AS patient_share,
       SUM(patient_paid)            FILTER (WHERE kind = 'paid')                      AS patient_paid,
       SUM(patient_responsibility - patient_paid)
                                    FILTER (WHERE kind = 'paid' AND at_agency)        AS at_agency,
       -- lines that were denied at some point (charge is the denied dollar amount)
       SUM(charge_amount)           FILTER (WHERE kind = 'denied' AND dclass = 'recovered') AS denied_recovered,
       SUM(charge_amount)           FILTER (WHERE kind = 'denied' AND dclass = 'lost')      AS denied_lost,
       SUM(charge_amount)           FILTER (WHERE kind = 'denied' AND dclass = 'open')      AS denied_open,
       SUM(charge_amount)           FILTER (WHERE kind = 'in_process')                AS in_process
FROM (
    SELECT *,
           CASE WHEN denial_status IS NOT NULL OR line_status = 'denied' THEN 'denied'
                WHEN line_status = 'open' THEN 'in_process'
                ELSE 'paid' END AS kind,
           CASE WHEN denial_status = 'overturned' THEN 'recovered'
                WHEN denial_status IN ('upheld', 'deadline_missed', 'non_appealable') THEN 'lost'
                ELSE 'open' END AS dclass
    FROM line
) x
GROUP BY payer_code
ORDER BY payer_code
""",
)

q(
    "lag.paid",
    "Payment lag triangle: paid dollars",
    ["overview"],
    ["Payment lag triangle"],
    "service_month:text,payer_code:text,lag_bucket:int,paid:money",
    f"""
-- Payments (payer + patient) tied to a claim line, bucketed by days from service date to payment date.
SELECT TO_CHAR(cl.service_date, 'YYYY-MM') AS service_month,
       p.payer_code AS payer_code,
       WIDTH_BUCKET(le.transaction_date - cl.service_date, {EDGES}) AS lag_bucket,
       SUM(le.amount) AS paid
FROM ledger_entry le
JOIN claim_line cl ON cl.claim_line_id = le.claim_line_id AND cl.tenant_id = :tenant_id
JOIN payer p ON p.payer_id = cl.payer_id AND p.tenant_id = :tenant_id
WHERE le.tenant_id = :tenant_id AND le.transaction_type = 'payment' AND le.transaction_date <= :asof
GROUP BY 1, 2, 3
ORDER BY 1, 2, 3
""",
)

q(
    "lag.charged",
    "Payment lag triangle: charged, contractual, denied-final",
    ["overview"],
    ["Payment lag triangle"],
    "service_month:text,payer_code:text,charged:money,contractual:money,denied_final:money",
    LINE_FACTS_CTE
    + """
SELECT service_month AS service_month, payer_code AS payer_code,
       SUM(charge_amount) AS charged,
       SUM(contractual_adjustment) FILTER (WHERE denial_status IS NULL OR denial_status = 'overturned') AS contractual,
       SUM(charge_amount)          FILTER (WHERE denial_status IN ('upheld', 'deadline_missed', 'non_appealable')
                                            OR (line_status = 'denied' AND denial_status IS NULL)) AS denied_final
FROM line
GROUP BY service_month, payer_code
ORDER BY service_month, payer_code
""",
)

q(
    "billing.monthly",
    "Billing: claims and charges by service month",
    ["billing"],
    ["Monthly claims and charges"],
    "m:text,claims:int,charged:money,paid:int,partial:int,submitted:int,denied:int",
    """
SELECT TO_CHAR(service_date_from, 'YYYY-MM') AS m, COUNT(*) AS claims, SUM(total_charge) AS charged,
       COUNT(*) FILTER (WHERE claim_status = 'paid') AS paid,
       COUNT(*) FILTER (WHERE claim_status = 'partial') AS partial,
       COUNT(*) FILTER (WHERE claim_status = 'submitted') AS submitted,
       COUNT(*) FILTER (WHERE claim_status = 'denied') AS denied
FROM claim
WHERE tenant_id = :tenant_id AND service_date_from <= :asof
GROUP BY 1
ORDER BY 1
""",
)

q(
    "billing.top_cpt",
    "Billing: top 12 CPT codes by charges",
    ["billing"],
    ["Top CPT codes"],
    "code:text,short_label:text,lines:int,charged:money",
    """
SELECT cpt.code AS code, cpt.short_label AS short_label, COUNT(*) AS lines, SUM(cl.charge_amount) AS charged
FROM claim_line cl
JOIN cpt_code cpt ON cpt.cpt_code_id = cl.cpt_code_id AND cpt.tenant_id = :tenant_id
WHERE cl.tenant_id = :tenant_id AND cl.service_date <= :asof
GROUP BY cpt.code, cpt.short_label
ORDER BY SUM(cl.charge_amount) DESC, cpt.code
LIMIT 12
""",
)

q(
    "payments.monthly",
    "Payments by month and who paid",
    ["payments"],
    ["Monthly payments"],
    "m:text,responsible_party:text,amount:money",
    """
SELECT TO_CHAR(transaction_date, 'YYYY-MM') AS m, responsible_party AS responsible_party, SUM(amount) AS amount
FROM ledger_entry
WHERE tenant_id = :tenant_id AND transaction_type = 'payment' AND transaction_date <= :asof
GROUP BY 1, 2
ORDER BY 1, 2
""",
)

q(
    "payments.tie_out",
    "Payments tie-out (payments, remittance, ledger)",
    ["payments"],
    ["Tie-out panel"],
    "payments_total:money,remittance_total:money,ledger_total:money",
    """
SELECT
  (SELECT COALESCE(SUM(posted_amount), 0) FROM payment
    WHERE tenant_id = :tenant_id AND payment_source = 'payer' AND NOT is_void
      AND payment_date <= :asof) AS payments_total,
  (SELECT COALESCE(SUM(rc.paid_amount), 0) FROM remittance_claim rc
    JOIN payment p ON p.payment_id = rc.payment_id AND p.tenant_id = :tenant_id
    WHERE rc.tenant_id = :tenant_id AND p.payment_date <= :asof) AS remittance_total,
  (SELECT COALESCE(SUM(amount), 0) FROM ledger_entry
    WHERE tenant_id = :tenant_id AND transaction_type = 'payment' AND responsible_party = 'payer'
      AND transaction_date <= :asof) AS ledger_total
""",
)

q(
    "ar.matrix",
    "A/R matrix per owner, payer and age bucket (point in time)",
    ["ar"],
    ["A/R aging heatmap"],
    "balance_owner:text,payer_code:text,bucket:int,balance:money",
    f"""
-- Open balance per owner / payer / age bucket on one as-of date, straight from the point-in-time snapshot.
SELECT s.balance_owner AS balance_owner, p.payer_code AS payer_code,
       WIDTH_BUCKET(s.days_outstanding, {EDGES}) AS bucket, SUM(s.balance) AS balance
FROM ar_snapshot s
JOIN payer p ON p.payer_id = s.payer_id AND p.tenant_id = :tenant_id
WHERE s.tenant_id = :tenant_id AND s.as_of_date = :d
GROUP BY 1, 2, 3
""",
    params="tenant_id,d",
)

q(
    "denials.status",
    "Denials by status (waterfall source)",
    ["denials"],
    ["Denial waterfall"],
    "denial_status:text,denials:int,denied:money,recovered_count:int,recovered:money",
    """
SELECT denial_status AS denial_status, COUNT(*) AS denials, SUM(denied_amount) AS denied,
       COUNT(*) FILTER (WHERE recovered_amount > 0) AS recovered_count, COALESCE(SUM(recovered_amount), 0) AS recovered
FROM denial
WHERE tenant_id = :tenant_id AND denial_date <= :asof
GROUP BY denial_status
""",
)

q(
    "denials.matrix",
    "Denials by reason (CARC) and payer",
    ["denials"],
    ["Reason x payer matrix", "Denials by reason"],
    "carc_code:text,short_label:text,is_appealable:bool,payer_code:text,denials:int,denied:money,preventable:money",
    """
SELECT ar.carc_code AS carc_code, ar.short_label AS short_label, ar.is_appealable AS is_appealable,
       p.payer_code AS payer_code, COUNT(*) AS denials, SUM(d.denied_amount) AS denied,
       COALESCE(SUM(d.denied_amount) FILTER (WHERE d.is_preventable), 0) AS preventable
FROM denial d
JOIN adjustment_reason ar ON ar.adjustment_reason_id = d.adjustment_reason_id AND ar.tenant_id = :tenant_id
JOIN payer p ON p.payer_id = d.payer_id AND p.tenant_id = :tenant_id
WHERE d.tenant_id = :tenant_id AND d.denial_date <= :asof
GROUP BY 1, 2, 3, 4
ORDER BY 1, 4
""",
)

q(
    "denials.preventable",
    "Denied dollars: preventable vs other",
    ["denials"],
    ["Preventable split"],
    "preventable:money,other:money",
    """
SELECT COALESCE(SUM(denied_amount) FILTER (WHERE is_preventable), 0) AS preventable,
       COALESCE(SUM(denied_amount) FILTER (WHERE NOT is_preventable), 0) AS other
FROM denial
WHERE tenant_id = :tenant_id AND denial_date <= :asof
""",
)

q(
    "denials.monthly",
    "Denials by service month",
    ["denials"],
    ["Monthly denial rate"],
    "m:text,denied:money,denials:int,adjudicated:int",
    """
-- Denied lines are attributed to the service month of the line so numerator and denominator share a month.
SELECT TO_CHAR(cl.service_date, 'YYYY-MM') AS m,
       COALESCE(SUM(d.denied_amount), 0) AS denied,
       COUNT(d.denial_id) AS denials,
       COUNT(*) FILTER (WHERE cl.line_status <> 'open') AS adjudicated
FROM claim_line cl
LEFT JOIN denial d ON d.claim_line_id = cl.claim_line_id AND d.tenant_id = :tenant_id
WHERE cl.tenant_id = :tenant_id AND cl.service_date <= :asof
GROUP BY 1
ORDER BY 1
""",
)

q(
    "patient.statements",
    "Patient statements by dunning level and status",
    ["patient"],
    ["Collection ladder"],
    "dunning_level:int,statement_status:text,statements:int,amount:money",
    """
SELECT dunning_level AS dunning_level, statement_status AS statement_status, COUNT(*) AS statements,
       COALESCE(SUM(statement_amount), 0) AS amount
FROM patient_statement
WHERE tenant_id = :tenant_id AND statement_date <= :asof
GROUP BY 1, 2
ORDER BY 1, 2
""",
)

q(
    "patient.plans",
    "Payment plans by status",
    ["patient"],
    ["Collection ladder", "Plans panel"],
    "plan_status:text,plans:int,total:money",
    """
SELECT plan_status AS plan_status, COUNT(*) AS plans, COALESCE(SUM(total_amount), 0) AS total
FROM payment_plan
WHERE tenant_id = :tenant_id AND start_date <= :asof
GROUP BY 1
""",
)

q(
    "patient.agency",
    "Collection agency placements by status",
    ["patient"],
    ["Collection ladder", "Agency panel"],
    "placement_status:text,placements:int,placed:money,recovered:money,fees:money",
    """
SELECT placement_status AS placement_status, COUNT(*) AS placements, COALESCE(SUM(placed_amount), 0) AS placed,
       COALESCE(SUM(recovered_amount), 0) AS recovered, COALESCE(SUM(agency_fee_amount), 0) AS fees
FROM collection_placement
WHERE tenant_id = :tenant_id AND placed_date <= :asof
GROUP BY 1
""",
)

q(
    "patient.estimates",
    "Patient estimates vs actual",
    ["patient"],
    ["Estimate accuracy panel"],
    "estimates:int,matched:int,estimated:money,actual:money,median_abs_error:float",
    """
WITH actual AS (                -- what the patient was finally billed, per encounter (paid / partial claims only)
    SELECT encounter_id, SUM(patient_responsibility) AS actual_patient
    FROM claim
    WHERE tenant_id = :tenant_id AND claim_status IN ('paid', 'partial') AND encounter_id IS NOT NULL
    GROUP BY encounter_id
),
matched AS (
    SELECT pe.estimated_patient_amount AS est, a.actual_patient AS act
    FROM patient_estimate pe
    JOIN encounter e ON e.appointment_id = pe.appointment_id AND e.tenant_id = :tenant_id
    JOIN actual a ON a.encounter_id = e.encounter_id
    WHERE pe.tenant_id = :tenant_id AND pe.estimate_type = 'insured' AND pe.estimate_date <= :asof
)
SELECT (SELECT COUNT(*) FROM patient_estimate WHERE tenant_id = :tenant_id AND estimate_date <= :asof) AS estimates,
       COUNT(*) AS matched, COALESCE(SUM(est), 0) AS estimated, COALESCE(SUM(act), 0) AS actual,
       COALESCE(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY ABS(est - act)::double precision), 0) AS median_abs_error
FROM matched
""",
)

q(
    "scorecard.claims",
    "Payer scorecard: claims, paid rate, days to pay",
    ["payers", "overview"],
    ["Payer scorecard"],
    "payer_code:text,m:text,claims:int,charged:money,adjudicated_charged:money,adjudicated_paid:money,median_days:float",
    """
WITH first_pay AS (             -- first payer payment per claim
    SELECT claim_id, MIN(transaction_date) AS first_paid
    FROM ledger_entry
    WHERE tenant_id = :tenant_id AND transaction_type = 'payment' AND responsible_party = 'payer'
      AND claim_id IS NOT NULL AND transaction_date <= :asof
    GROUP BY claim_id
)
SELECT p.payer_code AS payer_code, TO_CHAR(c.service_date_from, 'YYYY-MM') AS m,
       COUNT(*) AS claims, SUM(c.total_charge) AS charged,
       SUM(c.total_charge) FILTER (WHERE c.claim_status IN ('paid', 'partial', 'denied')) AS adjudicated_charged,
       SUM(c.paid_amount)  FILTER (WHERE c.claim_status IN ('paid', 'partial', 'denied')) AS adjudicated_paid,
       PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY (fp.first_paid - c.submitted_date)::double precision) AS median_days
FROM claim c
JOIN payer p ON p.payer_id = c.payer_id AND p.tenant_id = :tenant_id
LEFT JOIN first_pay fp ON fp.claim_id = c.claim_id
WHERE c.tenant_id = :tenant_id AND c.service_date_from <= :asof
GROUP BY ROLLUP (p.payer_code, TO_CHAR(c.service_date_from, 'YYYY-MM'))
""",
)

q(
    "scorecard.lines",
    "Payer scorecard: denied lines / adjudicated lines",
    ["payers", "overview"],
    ["Payer scorecard", "Headline denial rate"],
    "payer_code:text,m:text,denials:int,adjudicated:int",
    """
SELECT p.payer_code AS payer_code, TO_CHAR(cl.service_date, 'YYYY-MM') AS m,
       COUNT(d.denial_id) AS denials, COUNT(*) FILTER (WHERE cl.line_status <> 'open') AS adjudicated
FROM claim_line cl
JOIN payer p ON p.payer_id = cl.payer_id AND p.tenant_id = :tenant_id
LEFT JOIN denial d ON d.claim_line_id = cl.claim_line_id AND d.tenant_id = :tenant_id
WHERE cl.tenant_id = :tenant_id AND cl.service_date <= :asof
GROUP BY ROLLUP (p.payer_code, TO_CHAR(cl.service_date, 'YYYY-MM'))
""",
)

SEED: dict[str, dict[str, Any]] = _Q
