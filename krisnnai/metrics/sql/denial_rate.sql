-- Denial rate = claims whose first remit is denied (CLP02 = 4), divided by claims that have a remit.
-- Count and dollars (billed charge). One row per slice:
--   overall            all claims
--   payer              per payer id code; the denominator is that payer's adjudicated claims
--   carc, cpt          per denial reason (CAS reason code) / procedure code among denied claims;
--                      the denominator stays the overall adjudicated total, so the rate is a share of all claims
WITH {{prelude}},
adjudicated AS (
    SELECT fr.id AS remit_id, fr.claim_id AS claim_id, fr.payer_id AS payer_id, kc.total_charge AS total_charge,
           CASE WHEN fr.claim_status_code = '4' THEN 1 ELSE 0 END AS is_denied
    FROM first_remit fr
    JOIN known_claim kc ON kc.id = fr.claim_id
),
denied AS (
    SELECT a.remit_id AS remit_id, a.claim_id AS claim_id, a.total_charge AS total_charge
    FROM adjudicated a
    WHERE a.is_denied = 1
),
totals AS (
    SELECT COUNT(*) AS n, COALESCE(SUM(total_charge), 0) AS charge FROM adjudicated
),
slices AS (
    SELECT 'overall' AS dimension, 'all' AS dim_key,
           COALESCE(SUM(a.is_denied), 0) AS denied_claims,
           COALESCE(SUM(CASE WHEN a.is_denied = 1 THEN a.total_charge ELSE 0 END), 0) AS denied_charge,
           COUNT(*) AS adjudicated_claims,
           COALESCE(SUM(a.total_charge), 0) AS adjudicated_charge
    FROM adjudicated a
    UNION ALL
    SELECT 'payer', py.payer_id_code,
           SUM(a.is_denied),
           SUM(CASE WHEN a.is_denied = 1 THEN a.total_charge ELSE 0 END),
           COUNT(*),
           SUM(a.total_charge)
    FROM adjudicated a
    JOIN payer py ON py.tenant_id = :tenant_id AND py.id = a.payer_id
    GROUP BY py.payer_id_code
    UNION ALL
    SELECT 'carc', x.reason_code, COUNT(*), SUM(x.total_charge), t.n, t.charge
    FROM (SELECT DISTINCT d.claim_id AS claim_id, ea.reason_code AS reason_code, d.total_charge AS total_charge
          FROM denied d
          JOIN eff_adj ea ON ea.tenant_id = :tenant_id AND ea.remit_id = d.remit_id) x
    CROSS JOIN totals t
    GROUP BY x.reason_code, t.n, t.charge
    UNION ALL
    SELECT 'cpt', y.cpt, COUNT(*), SUM(y.line_charge), t.n, t.charge
    FROM (SELECT d.claim_id AS claim_id, rl.cpt AS cpt, SUM(rl.charge) AS line_charge
          FROM denied d
          JOIN remit_line rl ON rl.tenant_id = :tenant_id AND rl.remit_id = d.remit_id
          GROUP BY d.claim_id, rl.cpt) y
    CROSS JOIN totals t
    GROUP BY y.cpt, t.n, t.charge
)
SELECT s.dimension, s.dim_key, s.denied_claims, s.denied_charge, s.adjudicated_claims, s.adjudicated_charge,
       CASE WHEN s.adjudicated_claims = 0 THEN NULL
            ELSE 1.0 * (s.denied_claims) / s.adjudicated_claims END AS denial_rate_count,
       CASE WHEN s.adjudicated_charge = 0 THEN NULL
            ELSE 1.0 * (s.denied_charge) / s.adjudicated_charge END AS denial_rate_dollars
FROM slices s
