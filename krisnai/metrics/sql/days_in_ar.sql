-- Days in AR = open AR at as_of / (charges submitted in the last 90 days / 90).
-- Open AR is the sum of claim_balance (see _prelude.sql); rejected claims are not AR.
WITH {{prelude}},
ar AS (
    SELECT COALESCE(SUM(balance), 0) AS open_ar FROM claim_balance
),
charges AS (
    SELECT COALESCE(SUM(kc.total_charge), 0) AS charges_90
    FROM known_claim kc
    WHERE kc.submitted_on IS NOT NULL
      AND kc.submitted_on <= :as_of
      AND {days_between(kc.submitted_on, :as_of)} < 90
)
SELECT ar.open_ar AS open_ar,
       c.charges_90 AS charges_last_90_days,
       CASE WHEN c.charges_90 = 0 THEN NULL
            ELSE 1.0 * (ar.open_ar) / (1.0 * (c.charges_90) / 90)
       END AS days_in_ar
FROM ar
CROSS JOIN charges c
