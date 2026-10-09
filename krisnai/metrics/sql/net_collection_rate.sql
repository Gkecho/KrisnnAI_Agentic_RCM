-- Net collection rate = payer payments / (billed charges - contractual adjustments), claims with a remit.
-- Contractual = CAS group CO reason 45. Patient payments are not in the data, so the second rate also counts
-- the patient share (CLP05) as collectable.
WITH {{prelude}},
contractual AS (
    SELECT kr.claim_id AS claim_id, SUM(a.amount) AS amt
    FROM known_remit kr
    JOIN eff_adj a ON a.tenant_id = kr.tenant_id AND a.remit_id = kr.id
    WHERE kr.claim_id IS NOT NULL AND a.group_code = 'CO' AND a.reason_code = '45'
    GROUP BY kr.claim_id
),
base AS (
    SELECT COUNT(*) AS claims,
           COALESCE(SUM(kc.total_charge), 0) AS charges,
           COALESCE(SUM(COALESCE(ct.amt, 0)), 0) AS contractual,
           COALESCE(SUM(COALESCE(cp.paid, 0)), 0) AS payments,
           COALESCE(SUM(COALESCE(cp.pr, 0)), 0) AS patient_responsibility
    FROM first_remit fr
    JOIN known_claim kc ON kc.id = fr.claim_id
    LEFT JOIN contractual ct ON ct.claim_id = fr.claim_id
    LEFT JOIN claim_paid cp ON cp.claim_id = fr.claim_id
)
SELECT b.claims, b.charges, b.contractual, b.payments, b.patient_responsibility,
       CASE WHEN b.charges - b.contractual = 0 THEN NULL
            ELSE 1.0 * (b.payments) / (b.charges - b.contractual) END AS net_collection_rate,
       CASE WHEN b.charges - b.contractual = 0 THEN NULL
            ELSE 1.0 * (b.payments + b.patient_responsibility) / (b.charges - b.contractual)
       END AS net_collection_rate_with_patient_share
FROM base b
