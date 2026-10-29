-- First-pass paid rate = claims whose first remit is processed (CLP02 1-3) with a payment above 0,
-- divided by claims that have at least one remit.
WITH {{prelude}}
SELECT COUNT(*) AS adjudicated_claims,
       COALESCE(SUM(CASE WHEN fr.claim_status_code IN ('1', '2', '3') AND fr.total_paid > 0 THEN 1 ELSE 0 END), 0)
           AS first_pass_paid_claims,
       CASE WHEN COUNT(*) = 0 THEN NULL
            ELSE 1.0 * (SUM(CASE WHEN fr.claim_status_code IN ('1', '2', '3') AND fr.total_paid > 0 THEN 1 ELSE 0 END)
                     ) / COUNT(*)
       END AS first_pass_paid_rate
FROM first_remit fr
