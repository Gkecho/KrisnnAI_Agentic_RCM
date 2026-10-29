# Notes A: agent_value and agent_forecast (group GA)

TBD entry `agent_value` is replaced by two new tables. 95 Remapped rows covered: 67 Derived, 24 Renamed, 3 Exact, 1 Added, 0 Dropped.

## agent_value (27 columns, append-only ledger)
- One row = one dollar event of one agent on one entity at one stage (detected, worked, submitted, accepted, recovered, avoided). Following a finding from found to paid = several rows linked by agent_finding_id.
- Used by agents: Detective/Scout (detected, recovered, holdout), Auditor (detected, worked, accepted, recovered, incremental), Advocate (stages, recovered, incremental), Hunter (recovered after action), Mirror (incremental vs control), Coach (holdout flag). About 8 agents, 17 rows map to real columns.
- Proof: transaction_id points to the 835 payment in `transactions`. One payment is counted once (the Detective rule "capped at the finding amount").
- Fallback ladder: 1 agent logs stages and a later transactions row confirms; 2 claim paid after action, is_estimate = 1; 3 detected only, reported as unconfirmed.
- Decisions: Mandatory = agent_code, value_stage, amount, value_date, entity_type, entity_id. Old "paid" stage = recovered. "Incremental" is a column, not a stage. practice_id added to the draft (reports by practice, like other GA tables). amount is never negative; a takeback is a new row with value_kind = reversal. Rates, counts and "recovery $" are views over this table.

## agent_forecast (29 columns, versioned)
- One row = one stored prediction. forecast_type: cash_week, cash_28d, cash_later, claim_week_chance, recoverable_month. Range is 80% (interval_level default 0.80).
- Used by Captain (weekly chances, weeks, 28 days, later, backtest), Detective/Scout (recoverable forecast), Bookkeeper (forecast vs cash received). 11 rows map to real columns.
- actual_amount is filled later from 835 payments in `transactions` (bank deposit feed removed). Filling it is a new version (versioned audit), so the original prediction stays as made and backtests score what was said then. within_range stores the hit; WAPE and coverage are views.
- Decisions: added claim_count (the "claims" figure), practice_id, interval_level (optional). cash_28d is its own row because low/high do not add up from weeks. cash_later has no natural end date: default as_of_date + 365. claim_week_chance has one row per claim per week; expected_amount = chance times balance. These row counts can be large; a retention rule may be needed later.

## Derived, not stored (67 rows)
All KPI, rate, count, run-total and metric-list rows (fact_kpi_value, dim_metric) are views; each row's note names the source tables (claim, claim_status_history, transactions, ar, denial, agent_decision, agent_finding, agent_task, payment, contract_rate). dim_metric has no table (the metric list is code).
- Daily signal history (Captain) and baseline KPI snapshot (Detective): rebuildable from known_at on the source tables. Default: not stored. Revisit only if source values are restated after the fact.
- Slice rows (key, level, baseline/recent realisation, drop, volume/mix/rate effect, seasonality, sample size): views. Only the slice attributes of stored dollars map: payer_id, cpt_code_id, provider_id on agent_value.

## REMAP key format (flag to integrator)
Many rows share the same (old table, old column) such as (fact_kpi_value, value), so a 2-tuple key would overwrite rows. REMAP keys are 4-tuples: (old table, old column, Agent, Field). k[0] and k[1] are still the old table and column.

## Tables not created
None skipped. patient-share and cash-application items did not need new tables.

## Recommendations for locked tables (not made)
- agent_finding.amount_recovered duplicates the ledger. Suggest keeping it as a cached roll-up only, or retire it once agent_value exists.
- transactions has no agent link; none needed (agent_value.transaction_id points the other way).
