-- Shared building blocks that every KPI file pulls in (the prelude placeholder in each file).
-- Inputs are the tenant id and the as_of date. Point-in-time rule: a row counts only when its event was known
-- on or before as_of. The date_of and days_between helpers are swapped per database by krisnai/metrics/loader.py.

known_claim AS (            -- claims submitted and known by as_of (voids, frequency 8, are left out)
    SELECT c.*
    FROM claim c
    JOIN event e ON e.tenant_id = c.tenant_id AND e.id = c.event_id
    WHERE c.tenant_id = :tenant_id
      AND c.frequency_code <> '8'
      AND {date_of(e.known_at)} <= :as_of
),
known_remit AS (            -- 835 claim payments known by as_of, with the payer and payment date
    SELECT r.*, p.payer_id AS payer_id, p.payment_date AS payment_date
    FROM remit r
    JOIN payment p ON p.tenant_id = r.tenant_id AND p.id = r.payment_id
    JOIN event e ON e.tenant_id = r.tenant_id AND e.id = r.event_id
    WHERE r.tenant_id = :tenant_id
      AND {date_of(e.known_at)} <= :as_of
),
first_remit AS (            -- the first adjudication of each matched claim (reversals, CLP02 = 22, are ignored)
    SELECT t.*
    FROM (
        SELECT kr.*,
               ROW_NUMBER() OVER (PARTITION BY kr.claim_id ORDER BY kr.payment_date, kr.id) AS rn
        FROM known_remit kr
        WHERE kr.claim_id IS NOT NULL
          AND kr.claim_status_code <> '22'
    ) t
    WHERE t.rn = 1
),
eff_adj AS (                -- CAS pairs; line-level wins, claim-level is used only when a remit has no line-level CAS
    SELECT a.*
    FROM adjustment a
    WHERE a.tenant_id = :tenant_id
      AND (a.remit_line_id IS NOT NULL
           OR NOT EXISTS (SELECT 1 FROM adjustment l
                          WHERE l.tenant_id = a.tenant_id AND l.remit_id = a.remit_id
                            AND l.remit_line_id IS NOT NULL))
),
rejected_claim AS (         -- 1 when the 999 rejected the file or the 277CA returned / lost the claim
    SELECT kc.id AS claim_id,
           CASE WHEN EXISTS (
                    SELECT 1 FROM ack_277ca a
                    JOIN event ae ON ae.tenant_id = a.tenant_id AND ae.id = a.event_id
                    WHERE a.tenant_id = :tenant_id AND a.claim_id = kc.id
                      AND a.status_category IN ('A3', 'A4')
                      AND {date_of(ae.known_at)} <= :as_of)
                THEN 1 ELSE 0 END AS by_277ca,
           CASE WHEN EXISTS (
                    SELECT 1 FROM ack_999 k
                    JOIN event ke ON ke.tenant_id = k.tenant_id AND ke.id = k.event_id
                    JOIN event ce ON ce.tenant_id = kc.tenant_id AND ce.id = kc.event_id
                    WHERE k.tenant_id = :tenant_id AND k.transaction_status = 'R'
                      AND k.acked_st02 = ce.st02 AND k.acked_gs06 = ce.gs06
                      AND {date_of(ke.known_at)} <= :as_of)
                THEN 1 ELSE 0 END AS by_999
    FROM known_claim kc
),
claim_paid AS (             -- payer payments and patient share per claim, all known remits (reversals net out)
    SELECT kr.claim_id AS claim_id,
           SUM(kr.total_paid) AS paid,
           SUM(kr.patient_responsibility) AS pr
    FROM known_remit kr
    WHERE kr.claim_id IS NOT NULL
    GROUP BY kr.claim_id
),
claim_adj AS (              -- non-patient adjustments per claim (CO, OA, PI, CR); PR is already in CLP05
    SELECT kr.claim_id AS claim_id, SUM(a.amount) AS adj
    FROM known_remit kr
    JOIN eff_adj a ON a.tenant_id = kr.tenant_id AND a.remit_id = kr.id
    WHERE kr.claim_id IS NOT NULL AND a.group_code <> 'PR'
    GROUP BY kr.claim_id
),
claim_balance AS (          -- what the payer still owes: charge - paid - adjustments - patient share, never below 0
    SELECT x.claim_id AS claim_id,
           x.payer_id AS payer_id,
           x.age_date AS age_date,
           CASE WHEN ROUND(x.raw_balance, 2) > 0 THEN ROUND(x.raw_balance, 2) ELSE 0 END AS balance
    FROM (
        SELECT kc.id AS claim_id,
               kc.payer_id AS payer_id,
               COALESCE(kc.service_date, kc.submitted_on) AS age_date,
               kc.total_charge - COALESCE(cp.paid, 0) - COALESCE(cp.pr, 0) - COALESCE(ca.adj, 0) AS raw_balance
        FROM known_claim kc
        LEFT JOIN claim_paid cp ON cp.claim_id = kc.id
        LEFT JOIN claim_adj ca ON ca.claim_id = kc.id
        WHERE NOT EXISTS (SELECT 1 FROM rejected_claim rc
                          WHERE rc.claim_id = kc.id AND (rc.by_999 = 1 OR rc.by_277ca = 1))
    ) x
)
