-- Clean claim rate = claims with no 999 rejection and no 277CA A3/A4, divided by claims submitted.
WITH {{prelude}}
SELECT COUNT(*) AS submitted_claims,
       COALESCE(SUM(CASE WHEN rc.by_999 = 0 AND rc.by_277ca = 0 THEN 1 ELSE 0 END), 0) AS clean_claims,
       CASE WHEN COUNT(*) = 0 THEN NULL
            ELSE 1.0 * (SUM(CASE WHEN rc.by_999 = 0 AND rc.by_277ca = 0 THEN 1 ELSE 0 END)) / COUNT(*)
       END AS clean_claim_rate
FROM rejected_claim rc
