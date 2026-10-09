-- Underpayment $ = sum over paid remit lines of max(0, fee schedule allowed x units - (line paid + line patient share)).
-- Lines with no fee-schedule row for payer + CPT + first modifier on the service date are counted in
-- lines_without_fee and left out of the dollars (never guessed). Fee row = latest effective_date in force.
WITH {{prelude}},
line_pay AS (
    SELECT kr.id AS remit_id, kr.payer_id AS payer_id, rl.id AS remit_line_id, rl.cpt AS cpt,
           COALESCE(rl.modifier_1, '') AS modifier,
           COALESCE(rl.units, 1) AS units,
           rl.paid AS paid,
           COALESCE(rl.service_date, kr.service_date, kr.payment_date) AS dos,
           (SELECT COALESCE(SUM(a.amount), 0) FROM eff_adj a
            WHERE a.tenant_id = :tenant_id AND a.remit_line_id = rl.id AND a.group_code = 'PR') AS line_pr
    FROM known_remit kr
    JOIN remit_line rl ON rl.tenant_id = kr.tenant_id AND rl.remit_id = kr.id
    WHERE kr.claim_status_code <> '22' AND rl.paid > 0
),
fee_eff AS (
    SELECT lp.remit_line_id AS remit_line_id, MAX(f.effective_date) AS eff
    FROM line_pay lp
    JOIN fee_schedule f ON f.tenant_id = :tenant_id AND f.payer_id = lp.payer_id AND f.cpt = lp.cpt
                       AND f.modifier = lp.modifier AND f.effective_date <= lp.dos
                       AND (f.end_date IS NULL OR f.end_date >= lp.dos)
    GROUP BY lp.remit_line_id
),
priced AS (
    SELECT lp.remit_line_id AS remit_line_id, lp.paid AS paid, lp.line_pr AS line_pr,
           f.allowed_amount * lp.units AS expected,
           ROUND(f.allowed_amount * lp.units - (lp.paid + lp.line_pr), 2) AS gap
    FROM line_pay lp
    LEFT JOIN fee_eff fe ON fe.remit_line_id = lp.remit_line_id
    LEFT JOIN fee_schedule f ON f.tenant_id = :tenant_id AND f.payer_id = lp.payer_id AND f.cpt = lp.cpt
                            AND f.modifier = lp.modifier AND f.effective_date = fe.eff
)
SELECT COUNT(*) AS paid_lines,
       COALESCE(SUM(CASE WHEN p.expected IS NULL THEN 1 ELSE 0 END), 0) AS lines_without_fee,
       COALESCE(SUM(CASE WHEN p.gap > 0 THEN 1 ELSE 0 END), 0) AS underpaid_lines,
       COALESCE(SUM(CASE WHEN p.gap > 0 THEN p.gap ELSE 0 END), 0) AS underpayment_amount
FROM priced p
