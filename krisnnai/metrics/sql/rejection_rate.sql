-- Rejection rate = claims rejected by the 999 or returned / not found by the 277CA, divided by claims submitted.
WITH {{prelude}}
SELECT COUNT(*) AS submitted_claims,
       COALESCE(SUM(rc.by_999), 0) AS rejected_by_999,
       COALESCE(SUM(rc.by_277ca), 0) AS rejected_by_277ca,
       COALESCE(SUM(CASE WHEN rc.by_999 = 1 OR rc.by_277ca = 1 THEN 1 ELSE 0 END), 0) AS rejected_claims,
       CASE WHEN COUNT(*) = 0 THEN NULL
            ELSE 1.0 * (SUM(CASE WHEN rc.by_999 = 1 OR rc.by_277ca = 1 THEN 1 ELSE 0 END)) / COUNT(*)
       END AS rejection_rate
FROM rejected_claim rc
