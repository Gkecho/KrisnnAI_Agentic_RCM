-- Charge lag = average days from service date to the date the claim was submitted (BHT04), claims submitted by as_of.
WITH {{prelude}}
SELECT COUNT(*) AS claims,
       AVG(1.0 * ({days_between(kc.service_date, kc.submitted_on)})) AS avg_charge_lag_days
FROM known_claim kc
WHERE kc.service_date IS NOT NULL
  AND kc.submitted_on IS NOT NULL
  AND kc.submitted_on <= :as_of
