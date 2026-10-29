-- AR > 90 = open balance of claims older than 90 days (as_of minus service date) / total open AR.
WITH {{prelude}}
SELECT COALESCE(SUM(cb.balance), 0) AS open_ar,
       COALESCE(SUM(CASE WHEN {days_between(cb.age_date, :as_of)} > 90 THEN cb.balance ELSE 0 END), 0) AS ar_over_90,
       CASE WHEN COALESCE(SUM(cb.balance), 0) = 0 THEN NULL
            ELSE 1.0 * (SUM(CASE WHEN {days_between(cb.age_date, :as_of)} > 90 THEN cb.balance ELSE 0 END)
                     ) / SUM(cb.balance)
       END AS ar_over_90_share
FROM claim_balance cb
