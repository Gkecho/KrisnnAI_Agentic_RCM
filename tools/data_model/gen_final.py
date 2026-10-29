import os, re, collections

HERE = os.path.dirname(os.path.abspath(__file__))
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill
from openpyxl.styles.borders import Side
from openpyxl.utils import get_column_letter

# ---- reuse the eight journey tables and helpers already written in gen_core.py
src = open(os.path.join(HERE, "gen_core.py"), encoding="utf-8").read()
ns: dict = {}
exec(src.split("# ============================================================================================ WORKBOOK")[0], ns)
T, common, audit, L = ns["T"], ns["common"], ns["audit"], ns["L"]
M_, I_, O_ = ns["M_"], ns["I_"], ns["O_"]
import os as _o0
OUT = _o0.environ.get("KRISNNAI_OUT") or _o0.path.join(os.path.normpath(os.path.join(HERE, "..", "..", "docs", "data_model")), "KrisnnAI-Canonical-Data-Model.xlsx")
F, NAVY = "Arial", "1F3864"
thin = Side(style="thin", color="BFBFBF"); BD = Border(left=thin, right=thin, top=thin, bottom=thin)
PFILL = {M_: "E2EFDA", I_: "FFF2CC", O_: "EDEDED", "TBD": "DDEBF7"}
SFILL = {"Locked": "E2EFDA", "New: designed this round, not yet reviewed": "FCE4D6"}
LOCKED = NEW = "Locked"

for name in T:
    T[name]["status"] = LOCKED
for n in ("bill", "bill_details", "claim", "claim_details"):
    T[n]["group"] = "3 Bill and claim"


def ref_audit():
    return [L("is_active", "BIT", M_, "", "Lifecycle: 0 once retired.", "Always set by us"), L("source", "VARCHAR(20)", M_, "", "Where the row came from.", "Always set by us"),
            L("known_at", "DATETIME2(0)", M_, "", "When the data became known.", "Always set by us"), L("loaded_at", "DATETIME2(0)", M_, "", "When the row was loaded.", "Always set by us")]


def add(name, priority, group, pair, what, purpose, metrics, fallback, cols, status=LOCKED):
    T[name] = dict(priority=priority, group=group, pair=pair, what=what, purpose=purpose, metrics=metrics, fallback=fallback, cols=cols, status=status)



G4 = "4 Transactions, denials, AR"
# =============================================================================================== PHASE 4
add("transactions", M_, G4, "ledger", "One row per money movement on a charge line: charge, payment, adjustment, write-off, refund, transfer, opening balance.",
    "The ledger. Append-only and signed: a correction is a new reversing row. The single source of truth for balances.",
    "Collections, net and gross collection rate, adjustment, write-off and refund rates, days to payment, payer vs patient collections, posting lag, monthly charges-payments-adjustments-refunds chart, AR roll-forward inputs",
    "1 PM ledger export, 2 the 835 plus a patient payment feed, 3 claim line totals as summary rows, 4 balance-only import as opening-balance rows",
    common("transaction") + [
        L("transaction_number", "VARCHAR(50)", M_, "", "The client's posting ID. Makes loads repeatable. Restricted.", "Hash of payment, line, type, amount", True),
        L("practice_id", "INT", M_, "practice", "Reports by practice.", "Client default"), L("patient_id", "BIGINT", M_, "patient", "Patient accounts.", "Hash of member ID"),
        L("bill_detail_id", "BIGINT", M_, "bill_details", "The charge line the money acts on.", "Rebuilt from the claim line (flagged)"),
        L("transaction_type", "VARCHAR(20)", M_, "", "Charge, payment, adjustment, write_off, refund, transfer, opening_balance.", "Derived from the source code"),
        L("amount", "DECIMAL(12,2)", M_, "", "Amount as posted.", "From the source"), L("balance_effect", "DECIMAL(12,2)", M_, "", "Signed effect on the balance, so balance = a simple sum.", "Computed from type"),
        L("transaction_date", "DATE", M_, "", "Business date of the event.", "Payment or file date"),
        L("responsible_party", "VARCHAR(10)", M_, "", "Payer or patient: the AR split.", "Insurance payments mean payer; copays mean patient"),
        L("claim_detail_id", "BIGINT", I_, "claim_details", "Payer-side tracing. Blank for self-pay.", "Match on charge line"), L("claim_id", "BIGINT", I_, "claim", "Payer-side tracing.", "Match on charge line"),
        L("transaction_subtype", "VARCHAR(30)", I_, "", "Contractual, denial, bad debt, charity, overpayment recoupment, patient refund and so on.", "Derived from the reason code"),
        L("posted_date", "DATE", I_, "", "When posted; backdating and posting lag.", "Transaction date"),
        L("payer_id", "INT", I_, "payer", "Copied from the charge.", "Always set by us"), L("provider_id", "INT", I_, "provider", "Copied from the charge.", "Always set by us"),
        L("specialty_id", "INT", I_, "specialty", "Copied from the provider.", "From the provider"), L("cpt_code_id", "INT", I_, "cpt_code", "Copied from the charge.", "Always set by us"),
        L("adjustment_reason_id", "INT", I_, "adjustment_reason", "Reason for an adjustment: contractual, patient, other.", "Contractual when charge - allowed"),
        L("group_code", "CHAR(2)", I_, "", "CO, PR, OA, PI, CR.", "From the reason"), L("denial_id", "BIGINT", I_, "denial", "Links the movement to the denial record.", "Blank"),
        L("payment_id", "BIGINT", I_, "payment", "The payment (EFT, check, card) the money came in.", "Match on payment number"),
        L("payment_method", "VARCHAR(15)", I_, "", "EFT, check, virtual card, card, cash.", "Blank"),
        L("payment_number", "VARCHAR(50)", I_, "", "Trace or check number. Restricted.", "Blank", True),
        L("approved_by", "VARCHAR(50)", I_, "", "Pseudonymous approver. Write-offs and refunds need a named approver; one without is flagged.", "Blank means flagged"),
        L("approved_date", "DATE", I_, "", "When approved.", "Blank"),
        L("reverses_transaction_id", "BIGINT", I_, "transactions", "The row this reverses.", "Blank"), L("is_reversal", "BIT", I_, "", "1 on a reversing row.", "0"),
        L("batch_number", "VARCHAR(30)", O_, "", "Posting batch.", "Blank"), L("posted_by_role", "VARCHAR(30)", O_, "", "Posting analysis.", "Blank"), L("refund_reason", "VARCHAR(30)", O_, "", "Why refunded.", "Blank")] + audit("transaction", False))

add("denial", M_, G4, "header", "One row per denied amount on one claim line, per remittance. Status changes are kept as versions.",
    "The payer's decision not to pay (a rejection, which bounces before judgment, is not a denial). Carries reason, deadlines, cause and recovery.",
    "Denial rate by reason, payer, provider, specialty, procedure; preventable share; overturn and recovery rate; days to resolve; open denials nearing deadline; repeat denials; denials by journey stage",
    "1 the 835 reason codes and remarks, 2 PM denial worklist, 3 denied amount from claim lines with reason unknown, 4 lines paid zero with no contractual explanation (low confidence)",
    common("denial") + [
        L("claim_id", "BIGINT", M_, "claim", "The claim submission that was denied.", "Match on payer claim number and line"), L("claim_detail_id", "BIGINT", M_, "claim_details", "The line. A whole-claim denial is spread over its lines.", "Match on payer claim number and line"),
        L("practice_id", "INT", M_, "practice", "Copied from the claim.", "Always set by us"), L("patient_id", "BIGINT", M_, "patient", "Copied from the claim.", "Always set by us"), L("payer_id", "INT", M_, "payer", "Copied from the claim.", "Always set by us"),
        L("denial_date", "DATE", M_, "", "The payer's decision date.", "Payment or file date"), L("denied_amount", "DECIMAL(12,2)", M_, "", "Base of the denial rate.", "Charge - paid - contractual"),
        L("adjustment_reason_id", "INT", M_, "adjustment_reason", "Main reason code: denial by reason without joining the details.", "First reason on the remittance; else unknown"),
        L("denial_status", "VARCHAR(25)", M_, "", "Open, corrected_resubmitted, appealed, written_off, recovered, closed, expired.", "Open"),
        L("first_denial_id", "BIGINT", I_, "denial", "First version of this denial; the details attach to it.", "Own ID on the first version"),
        L("transaction_id", "BIGINT", I_, "transactions", "The ledger row that carried the denial.", "Match on line, date, amount"), L("bill_detail_id", "BIGINT", I_, "bill_details", "The charge line behind it.", "Via the claim line"),
        L("group_code", "CHAR(2)", I_, "", "CO, PR, OA, PI, CR.", "From the reason"), L("reason_category", "VARCHAR(30)", I_, "", "Eligibility, authorization, coding, documentation, billing, medical necessity, timely filing, duplicate, coordination of benefits.", "Mapped from the reason code"),
        L("clock_start_date", "DATE", I_, "", "Appeal clock starts (denial notice).", "Payment date"), L("appeal_deadline", "DATE", I_, "", "Deadline and money at risk.", "Payment date + payer appeal days"),
        L("root_cause", "VARCHAR(30)", I_, "", "Why it happened.", "Rule table from reason"), L("upstream_stage", "VARCHAR(15)", I_, "", "Which journey stage could have caught it.", "Rule table from reason"),
        L("is_preventable", "BIT", I_, "", "Could have been caught before sending.", "Rule table from reason"), L("is_technical", "BIT", I_, "", "Fixable without a clinical decision.", "From the reason"),
        L("owner_role", "VARCHAR(20)", I_, "", "Billing, coding, front desk, provider.", "From the reason category"),
        L("resolved_date", "DATE", I_, "", "Days to resolve.", "Blank"), L("outcome", "VARCHAR(20)", I_, "", "Overturned, corrected, written off, accepted.", "Blank"),
        L("recovered_amount", "DECIMAL(12,2)", I_, "", "Recovery. Rebuilt from the ledger.", "Rebuild from transactions"),
        L("is_repeat", "BIT", I_, "", "Same line denied again.", "Derived"), L("denial_count_on_line", "SMALLINT", I_, "", "Times this line has been denied.", "Derived"),
        L("resubmitted_claim_id", "BIGINT", I_, "claim", "The replacement claim.", "Match on the claim chain"),
        L("cpt_code_id", "INT", I_, "cpt_code", "Copied for reports.", "Always set by us"), L("provider_id", "INT", I_, "provider", "Copied for reports.", "Always set by us"), L("specialty_id", "INT", I_, "specialty", "Copied for reports.", "Always set by us"),
        L("is_claim_level", "BIT", I_, "", "Spread from a whole-claim denial.", "Derived"),
        L("units_denied", "DECIMAL(7,2)", O_, "", "Partial-unit denials.", "Blank"), L("authorization_id", "BIGINT", O_, "authorization", "Authorization denials.", "Blank")] + audit("denial"))

add("denial_details", M_, G4, "detail", "One row per reason code or remark code behind a denial.",
    "What makes a denial actionable. Reasons and remarks share one table, told apart by a type column, because a remark belongs to the line, not to one reason.",
    "Denied dollars by reason (correct with several reasons), top reasons by payer and procedure, remark patterns, appealable mix, suggested-action mix, reasons that appear together",
    "1 the 835 reason and remark segments, 2 PM denial detail export, 3 one row per denial with the main reason and the full amount, 4 an unknown-reason row",
    common("denial_detail") + [
        L("denial_id", "BIGINT", M_, "denial", "The denial (first version) it explains.", "Always set by us"), L("detail_seq", "SMALLINT", M_, "", "Order within the denial.", "Order in the file"),
        L("detail_type", "VARCHAR(10)", M_, "", "Reason or remark.", "Always set by us"),
        L("adjustment_reason_id", "INT", M_, "adjustment_reason", "The reason code (mandatory on reason rows).", "Unknown reason"), L("remark_code_id", "INT", M_, "remark_code", "The remark code (mandatory on remark rows).", "Blank"),
        L("group_code", "CHAR(2)", I_, "", "CO, PR, OA, PI, CR.", "From the reason"), L("reason_amount", "DECIMAL(12,2)", I_, "", "Amount tied to this reason; sums to the denial amount.", "All on the main reason"),
        L("is_amount_allocated", "BIT", I_, "", "1 if we assigned the amount because the payer gave one total.", "Always set by us"), L("reason_units", "DECIMAL(7,2)", I_, "", "Units tied to the reason.", "Blank"),
        L("is_primary", "BIT", I_, "", "The main reason.", "Largest amount, else first"), L("reason_category", "VARCHAR(30)", I_, "", "Copied from the reason.", "Mapped from the reason"),
        L("is_appealable", "BIT", I_, "", "Rule output.", "Unknown"), L("suggested_action", "VARCHAR(25)", I_, "", "Fix and resubmit, appeal, write-off review, bill patient, informational. A proposal only.", "Unknown"),
        L("denial_date", "DATE", I_, "", "Copied for reports.", "Always set by us"), L("practice_id", "INT", I_, "practice", "Copied.", "Always set by us"), L("payer_id", "INT", I_, "payer", "Copied.", "Always set by us"),
        L("cpt_code_id", "INT", I_, "cpt_code", "Copied.", "Always set by us"), L("claim_detail_id", "BIGINT", I_, "claim_details", "Copied.", "Always set by us"), L("provider_id", "INT", I_, "provider", "Copied.", "Always set by us"),
        L("specialty_id", "INT", I_, "specialty", "Copied.", "Always set by us"), L("patient_id", "BIGINT", I_, "patient", "Copied.", "Always set by us"),
        L("payer_reason_code", "VARCHAR(20)", O_, "", "Payer-specific code.", "Blank"), L("remark_qualifier", "VARCHAR(5)", O_, "", "Which code list.", "Blank"),
        L("documents_needed", "VARCHAR(30)", O_, "", "What proof is needed.", "Blank"), L("reason_corrected", "BIT", O_, "", "Which reason was fixed.", "Blank")] + audit("denial_detail", False))

add("ar_interval", M_, G4, "roll-forward", "One row per charge line per period (month by default).",
    "The roll-forward of a charge line: opening balance plus movements equals closing balance, split payer and patient and aged into buckets. Built incrementally; a backdated posting rebuilds that period and later ones.",
    "AR total and by bucket, share over 90 and 120 days, days in AR, the roll-forward report, payer vs patient AR, unbilled AR, credit balances, AR by provider and procedure",
    "1 PM AR aging report or ledger per period, 2 computed from transactions (best), 3 claim-level balances only (movements estimated), 4 go-live aging report as an opening balance",
    common("ar_interval") + [
        L("bill_detail_id", "BIGINT", M_, "bill_details", "The charge line (the account).", "Rebuilt from the claim line"),
        L("period_start_date", "DATE", M_, "", "Start of the period.", "Calendar month"), L("period_end_date", "DATE", M_, "", "End of the period.", "Calendar month"), L("period_type", "VARCHAR(10)", M_, "", "Month or week.", "Month"),
        L("practice_id", "INT", M_, "practice", "Reports by practice.", "Copied from the charge"), L("patient_id", "BIGINT", M_, "patient", "Patient accounts.", "Copied from the charge"),
        L("opening_balance", "DECIMAL(12,2)", M_, "", "Prior period's closing; the first period starts from the charge or an opening-balance row.", "Zero or the opening-balance import"),
        L("charges", "DECIMAL(12,2)", M_, "", "Charges posted in the period.", "Summed from transactions"), L("payments", "DECIMAL(12,2)", M_, "", "Payments in the period.", "Summed from transactions"),
        L("adjustments", "DECIMAL(12,2)", M_, "", "Adjustments in the period.", "Summed from transactions"), L("write_offs", "DECIMAL(12,2)", M_, "", "Write-offs in the period.", "Summed from transactions"),
        L("refunds", "DECIMAL(12,2)", M_, "", "Refunds in the period.", "Summed from transactions"), L("closing_balance", "DECIMAL(12,2)", M_, "", "Opening plus movements.", "Computed"),
        L("payer_balance", "DECIMAL(12,2)", M_, "", "Closing owed by the payer.", "Responsible party on the ledger"), L("patient_balance", "DECIMAL(12,2)", M_, "", "Closing owed by the patient.", "Responsible party on the ledger"),
        L("payer_bucket", "VARCHAR(10)", M_, "", "Current, 0-30, 31-60, 61-90, 91-120, 120+.", "Computed"), L("patient_bucket", "VARCHAR(10)", M_, "", "Same buckets for the patient balance.", "Computed"),
        L("aging_basis", "VARCHAR(20)", M_, "", "What the aging clock started from, so the definition never changes silently.", "Date of service"),
        L("reconciles", "BIT", M_, "", "1 when closing equals the ledger sum.", "Always computed by us"),
        L("prior_period_ar_interval_id", "BIGINT", I_, "ar_interval", "Links the roll-forward chain.", "Match on line and prior period"),
        L("payer_days", "SMALLINT", I_, "", "Days the payer balance has aged.", "Computed"), L("patient_days", "SMALLINT", I_, "", "Days the patient balance has aged; the clock restarts at transfer.", "Computed"),
        L("payer_aging_date", "DATE", I_, "", "Payer clock start.", "Date of service"), L("patient_aging_date", "DATE", I_, "", "Patient clock start.", "Transfer date"),
        L("unbilled_balance", "DECIMAL(12,2)", I_, "", "Charges not yet on a claim.", "Charges with no claim line"),
        L("payments_payer", "DECIMAL(12,2)", I_, "", "Movement split.", "Total only"), L("payments_patient", "DECIMAL(12,2)", I_, "", "Movement split.", "Total only"),
        L("adjustments_contractual", "DECIMAL(12,2)", I_, "", "Movement split.", "Total only"), L("adjustments_denial", "DECIMAL(12,2)", I_, "", "Movement split.", "Total only"),
        L("adjustments_other", "DECIMAL(12,2)", I_, "", "Movement split.", "Total only"), L("transfers_to_patient", "DECIMAL(12,2)", I_, "", "Moved from payer to patient.", "Total only"),
        L("transfers_to_secondary", "DECIMAL(12,2)", I_, "", "Moved to a secondary payer.", "Total only"),
        L("claim_id", "BIGINT", I_, "claim", "Current claim.", "Match on charge line"), L("claim_detail_id", "BIGINT", I_, "claim_details", "Current claim line.", "Match on charge line"),
        L("claim_status", "VARCHAR(20)", I_, "", "Status at period end.", "From the claim"), L("payer_id", "INT", I_, "payer", "Payer responsible at period end.", "Copied from the charge"),
        L("open_denied_amount", "DECIMAL(12,2)", I_, "", "Denial-related AR.", "From denial"), L("is_in_denial", "BIT", I_, "", "An open denial exists.", "From denial"),
        L("expected_collectible", "DECIMAL(12,2)", I_, "", "Net AR: contract expected minus paid.", "Balance x historical collection rate (assumed)"),
        L("last_payment_date", "DATE", I_, "", "Stalled accounts.", "From the ledger"), L("last_activity_date", "DATE", I_, "", "Stalled accounts.", "From the ledger"), L("last_statement_date", "DATE", I_, "", "Statement timing.", "Blank"),
        L("is_credit", "BIT", I_, "", "Closing below zero: refund candidates.", "Derived"), L("ledger_balance", "DECIMAL(12,2)", I_, "", "Ledger sum to period end (visible check).", "Always computed by us"),
        L("variance_amount", "DECIMAL(12,2)", I_, "", "Closing minus ledger.", "Always computed by us"), L("is_restated", "BIT", I_, "", "Rebuilt after a backdated posting.", "Always set by us"),
        L("period_status", "VARCHAR(10)", I_, "", "Open or closed.", "Open"),
        L("provider_id", "INT", I_, "provider", "Copied.", "Always set by us"), L("specialty_id", "INT", I_, "specialty", "Copied.", "Always set by us"), L("cpt_code_id", "INT", I_, "cpt_code", "Copied.", "Always set by us"),
        L("facility_id", "INT", I_, "facility", "Copied.", "Always set by us"), L("service_date", "DATE", I_, "", "Copied.", "Always set by us"),
        L("collections_agency_flag", "BIT", O_, "", "Placed with a collections agency.", "Blank"), L("statement_count", "SMALLINT", O_, "", "Statements sent.", "Blank")] + audit("ar_interval"))

add("ar", M_, G4, "snapshot", "One row per open balance, per owner (payer, patient, unbilled), per as-of date.",
    "The position at a date. Daily for 90 days, weekly for 13 months, month-end forever. Month-end rows are frozen as reported. Reconciles to ar_interval at period end.",
    "AR by bucket, payer and owner every day, share over 90 and 120 days, daily days-in-AR trend, unbilled AR and filing risk, credit balances, patient AR, follow-up queue, cash forecast input",
    "1 PM AR aging daily or weekly, 2 built from transactions and claims (best), 3 claim balances bucketed from the sent date, 4 go-live aging report as the first snapshot",
    common("ar") + [
        L("as_of_date", "DATE", M_, "", "The snapshot date.", "Run date"), L("snapshot_type", "VARCHAR(10)", M_, "", "Daily, weekly, month_end.", "Daily"),
        L("snapshot_run_id", "BIGINT", M_, "", "The run that wrote the row. A rerun replaces its own date atomically, so no duplicates.", "Always set by us"),
        L("bill_id", "BIGINT", M_, "bill", "The account's visit.", "Via the claim"), L("balance_owner", "VARCHAR(10)", M_, "", "Payer, patient or unbilled.", "Responsible party on the ledger"),
        L("balance", "DECIMAL(12,2)", M_, "", "Open amount for that owner.", "Sum of transactions to the date"),
        L("practice_id", "INT", M_, "practice", "Reports by practice.", "Copied from the bill"), L("patient_id", "BIGINT", M_, "patient", "Patient accounts.", "Copied from the bill"),
        L("aging_date", "DATE", M_, "", "When this row's clock started.", "Date of service"), L("days_outstanding", "SMALLINT", M_, "", "Age of the balance.", "Computed"),
        L("aging_bucket", "VARCHAR(10)", M_, "", "Current, 0-30, 31-60, 61-90, 91-120, 120+.", "Computed"), L("aging_basis", "VARCHAR(20)", M_, "", "What the clock started from.", "Date of service"),
        L("claim_id", "BIGINT", I_, "claim", "The claim on payer rows; blank for unbilled and self-pay.", "Match on charge line"), L("payer_id", "INT", I_, "payer", "Who owes, or the expected payer on unbilled rows.", "Copied from the bill"),
        L("claim_status", "VARCHAR(20)", I_, "", "Where the claim stands.", "From the claim"), L("claim_sequence", "VARCHAR(10)", I_, "", "Primary or secondary.", "From the claim"),
        L("submitted_date", "DATE", I_, "", "Date sent.", "From the claim"), L("expected_collectible", "DECIMAL(12,2)", I_, "", "Net AR.", "Balance x historical collection rate (assumed)"),
        L("last_payment_date", "DATE", I_, "", "Stalled accounts.", "From the ledger"), L("last_activity_date", "DATE", I_, "", "Stalled accounts.", "From the ledger"),
        L("days_since_activity", "SMALLINT", I_, "", "Follow-up queue.", "Computed"), L("last_statement_date", "DATE", I_, "", "Patient statement timing.", "Blank"),
        L("open_denied_amount", "DECIMAL(12,2)", I_, "", "Denial-related AR.", "From denial"), L("is_in_denial", "BIT", I_, "", "Open denial exists.", "From denial"),
        L("is_credit", "BIT", I_, "", "Balance below zero.", "Derived"), L("filing_deadline", "DATE", I_, "", "Service date plus the payer's filing limit.", "Payer's limit"),
        L("provider_id", "INT", I_, "provider", "Copied.", "Always set by us"), L("specialty_id", "INT", I_, "specialty", "Copied.", "Always set by us"),
        L("facility_id", "INT", I_, "facility", "Copied.", "Always set by us"), L("service_date", "DATE", I_, "", "Copied.", "Always set by us"),
        L("primary_cpt_code_id", "INT", O_, "cpt_code", "Procedure view.", "Blank"), L("change_since_last_snapshot", "DECIMAL(12,2)", O_, "", "Trend.", "Blank"),
        L("collections_agency_flag", "BIT", O_, "", "Patient collections.", "Blank"), L("next_action_date", "DATE", O_, "", "Worklists.", "Blank")] + audit("ar", False))

# =============================================================================================== NEW THIS ROUND
add("claim_status_history", I_, "3 Bill and claim", "event log", "One row per status event on a claim submission: sent, acknowledged, rejected, status answer, adjudicated, resubmitted, voided.",
    "The claim row holds only the current status. This is the history behind it. Append-only.",
    "First-pass acceptance, clean-claim rate, rejection turnaround (rejection to resubmission), time to acceptance, time to adjudication, rejection reasons, lost claims (no acknowledgement after N days), resubmission count",
    "1 999, 277CA and 277 files from the clearinghouse, 2 PM claim history log, 3 minimal events inferred from claim dates (sent, adjudicated; rejections lost), 4 none: current status only and the metrics report unavailable",
    common("claim_status_history") + [
        L("claim_id", "BIGINT", M_, "claim", "The claim submission the event is about.", "Match on claim number"),
        L("event_type", "VARCHAR(20)", M_, "", "Submitted, ack_999, ack_277ca, status_inquiry, status_response, adjudicated, resubmitted, voided.", "Derived from the source file type"),
        L("event_date", "DATE", M_, "", "When it happened.", "File date"), L("status_after", "VARCHAR(20)", M_, "", "The claim status after this event.", "Derived from the event"),
        L("practice_id", "INT", M_, "practice", "Copied from the claim.", "Always set by us"), L("payer_id", "INT", M_, "payer", "Copied from the claim.", "Always set by us"), L("patient_id", "BIGINT", M_, "patient", "Copied from the claim.", "Always set by us"),
        L("event_ts", "DATETIME2(0)", I_, "", "Exact time, for turnaround in hours.", "Event date"), L("response_sequence", "SMALLINT", I_, "", "Order of responses; the first acknowledgement decides first-pass acceptance.", "Order by date"),
        L("status_category", "VARCHAR(10)", I_, "", "Payer status category from the 277.", "Blank"), L("status_code", "VARCHAR(10)", I_, "", "Payer status code from the 277.", "Blank"),
        L("is_rejection", "BIT", I_, "", "A technical bounce, before the payer judged the claim.", "Derived from the status"),
        L("rejection_reason", "VARCHAR(20)", I_, "", "Error or reason code from the 999 or 277CA.", "Blank"), L("rejection_category", "VARCHAR(30)", I_, "", "Member ID, provider ID, diagnosis, missing information, duplicate, payer ID.", "Mapped from the reason"),
        L("is_technical", "BIT", I_, "", "Fixable without a clinical decision.", "From the reason"), L("owner_role", "VARCHAR(20)", I_, "", "Who fixes it.", "From the category"), L("fix_by_date", "DATE", I_, "", "Target to fix and resend.", "Blank"),
        L("channel", "VARCHAR(20)", I_, "", "Clearinghouse, payer portal, phone, fax.", "Clearinghouse"),
        L("payer_claim_number", "VARCHAR(50)", I_, "", "Payer's number, assigned on acceptance. Restricted.", "Blank", True),
        L("billing_provider_id", "INT", I_, "provider", "Copied from the claim.", "Always set by us"), L("specialty_id", "INT", I_, "specialty", "Copied.", "Always set by us"),
        L("reported_paid_amount", "DECIMAL(12,2)", O_, "", "Paid amount stated on a status answer before the remittance arrives.", "Blank"),
        L("acked_control_number", "VARCHAR(30)", O_, "", "Control number a 999 or 277CA acknowledges.", "Blank"), L("clearinghouse_batch_number", "VARCHAR(30)", O_, "", "Batch the claim travelled in.", "Blank")] + audit("claim_status_history", False), status=NEW)

add("payment", I_, G4, "header", "One row per payment received: payer EFT, check or virtual card, or a patient payment. A reissue or void is a new version.",
    "The payment header. Transactions carry the money by charge line; this holds the total, so postings can be reconciled and posting lag measured.",
    "Posting lag, unapplied cash, payments by method and payer, takebacks, remittance adoption (electronic vs paper), days from sent to payment",
    "1 835 headers plus a patient payment feed, 2 PM payment or deposit batch export, 3 rebuilt from transactions grouped by payment number (total = sum of lines; unapplied unknown), 4 none",
    common("payment") + [
        L("payment_number", "VARCHAR(50)", M_, "", "Trace or check number. Restricted.", "Hash of payer, date, amount", True),
        L("practice_id", "INT", M_, "practice", "Reports by practice.", "Client default"),
        L("payment_source", "VARCHAR(10)", M_, "", "Payer or patient.", "Payer"), L("payment_date", "DATE", M_, "", "Payment effective date.", "File date"),
        L("payment_amount", "DECIMAL(12,2)", M_, "", "Total of the payment.", "Sum of linked transactions"), L("payment_method", "VARCHAR(15)", M_, "", "EFT, check, virtual card, card, cash, other.", "Other"),
        L("payer_id", "INT", I_, "payer", "Blank for patient payments.", "Payer on the remittance"), L("payment_type", "VARCHAR(10)", I_, "", "Payment, takeback, refund.", "Payment"),
        L("received_date", "DATE", I_, "", "When the money or remittance arrived.", "Payment date"), L("posted_date", "DATE", I_, "", "When posted; posting lag.", "Latest posting on its transactions"),
        L("credit_debit", "CHAR(1)", I_, "", "C for money in; D for a takeback.", "C"),
        L("has_remittance", "BIT", I_, "", "Electronic remittance received (vs paper explanation).", "0"),
        L("claim_count", "SMALLINT", I_, "", "Claims covered.", "Count of linked claims"), L("posted_amount", "DECIMAL(12,2)", I_, "", "Rollup of linked transactions.", "Rebuild from transactions"),
        L("unapplied_amount", "DECIMAL(12,2)", I_, "", "Payment minus posted.", "Rebuild from transactions"), L("plb_amount", "DECIMAL(12,2)", I_, "", "Provider-level adjustments on the payment (takebacks, interest).", "Blank"),
        L("reconciles", "BIT", I_, "", "1 when posted equals the payment total.", "Always computed by us"), L("is_void", "BIT", I_, "", "Voided or bounced.", "0"),
        L("payee_provider_id", "INT", O_, "provider", "Payee.", "Blank")] + audit("payment"), status=NEW)

add("data_feed", I_, "Data operations", "registry", "One row per feed a client provides (or does not): which canonical table it fills, from where, how often, how complete.",
    "The data inventory. Tells every report which tables are loaded and which fallback step each table is on, so a missing feed shows 'unavailable', never a misleading zero.",
    "Data availability by client and table, completeness, freshness, onboarding progress, metric availability flags, which fallback each client runs on",
    "1 recorded at onboarding, then updated automatically by the loader",
    common("data_feed") + [
        L("table_name", "VARCHAR(40)", M_, "", "The canonical table the feed fills.", "Set at onboarding"), L("feed_name", "VARCHAR(80)", M_, "", "Plain name, e.g. 'PM claims export'.", "Set at onboarding"),
        L("source_system", "VARCHAR(20)", M_, "", "Scheduler, ehr, pm, clearinghouse, payer_portal, manual, public_list.", "Set at onboarding"),
        L("feed_status", "VARCHAR(15)", M_, "", "Active, paused, failed, not_provided.", "Not provided"),
        L("fallback_level", "TINYINT", M_, "", "0 = primary source; 1 and up = the fallback step in use (see each table's ladder).", "0"),
        L("practice_id", "INT", I_, "practice", "Blank = whole client.", "Whole client"), L("source_kind", "VARCHAR(15)", I_, "", "Api, hl7, file_drop, database_view, upload, public.", "Blank"),
        L("load_frequency", "VARCHAR(10)", I_, "", "Realtime, hourly, daily, weekly, monthly, one_time.", "Daily"),
        L("first_data_date", "DATE", I_, "", "Earliest business date loaded.", "Blank"), L("last_data_date", "DATE", I_, "", "Latest business date loaded.", "Blank"), L("last_load_at", "DATETIME2(0)", I_, "", "Last successful load.", "Blank"),
        L("rows_loaded", "BIGINT", I_, "", "Rows loaded to date.", "Counted by the loader"), L("completeness_pct", "DECIMAL(5,2)", I_, "", "Loaded versus a control total at the source.", "Blank (unknown)"),
        L("freshness_hours", "SMALLINT", I_, "", "Hours since the last load.", "Computed"), L("reliability_default", "DECIMAL(3,2)", I_, "", "Confidence of rows from this feed (1.0 primary; lower for rebuilt).", "1.0 / lower for fallbacks"),
        L("expected_row_count", "BIGINT", O_, "", "Control total.", "Blank")] + audit("data_feed"), status=NEW)

add("appointment_slot", O_, "1 Appointment", "capacity", "One row per slot: provider, day, start time, length, type and status. A change of state is a new version.",
    "Capacity. An empty slot has no appointment, so this cannot be derived from appointments.",
    "Utilization, fill rate, unused capacity, time to next available, cancellation refill rate, no-show impact on capacity",
    "1 scheduler slot or availability API / template export, 2 provider working hours in practice_settings minus booked appointment lengths (an estimate), 3 none",
    common("appointment_slot") + [
        L("practice_id", "INT", M_, "practice", "Reports by practice.", "Client default"), L("provider_id", "INT", M_, "provider", "Whose schedule.", "Practice default"),
        L("slot_date", "DATE", M_, "", "Slot day.", "None"), L("start_time", "TIME(0)", M_, "", "Slot start.", "None"), L("duration_minutes", "SMALLINT", M_, "", "Slot length.", "Template default"),
        L("slot_status", "VARCHAR(10)", M_, "", "Open, booked, held, blocked.", "Open"),
        L("slot_number", "VARCHAR(50)", I_, "", "The scheduler's slot ID. Restricted.", "Hash of provider, date, time", True), L("facility_id", "INT", I_, "facility", "Site capacity.", "Practice default"),
        L("specialty_id", "INT", I_, "specialty", "Copied from the provider.", "From the provider"), L("slot_type", "VARCHAR(15)", I_, "", "New_patient, follow_up, procedure, telehealth, any, block.", "Any"),
        L("appointment_id", "BIGINT", I_, "appointment", "The appointment filling the slot.", "Match on provider, date, time"), L("created_date", "DATE", I_, "", "When the slot was opened for booking; time to next available.", "Blank"),
        L("room_or_resource", "VARCHAR(50)", O_, "", "Room or equipment.", "Blank"), L("is_overbook", "BIT", O_, "", "Overbooked slot.", "Blank")] + audit("appointment_slot"), status=NEW)

# =============================================================================================== AGENT OUTPUT TABLES
GA = "5 Agent outputs"
LINKS = lambda: [
    L("practice_id", "INT", I_, "practice", "Reports by practice.", "From the entity the agent worked on"), L("patient_id", "BIGINT", I_, "patient", "Patient level view.", "From the entity"),
    L("payer_id", "INT", I_, "payer", "Reports by payer.", "From the entity"), L("provider_id", "INT", I_, "provider", "Reports by provider.", "From the entity"),
    L("specialty_id", "INT", I_, "specialty", "Reports by specialty.", "From the provider"),
    L("appointment_id", "BIGINT", I_, "appointment", "The appointment concerned, when there is one.", "Blank"), L("encounter_id", "BIGINT", I_, "encounter", "The visit concerned.", "Blank"),
    L("bill_id", "BIGINT", I_, "bill", "The bill concerned.", "Blank"), L("claim_id", "BIGINT", I_, "claim", "The claim concerned.", "Blank"),
    L("denial_id", "BIGINT", I_, "denial", "The denial concerned.", "Blank"), L("authorization_id", "BIGINT", I_, "authorization", "The authorization concerned.", "Blank")]
NOTE_ = "Agent output: written by the agent as it runs, never rebuilt from the canonical tables. Agents never write into the canonical tables; an approved change returns through the normal load as a new version row."

add("agent_run", M_, GA, "run log", "One row per execution of one agent: what started it, how it ended and what it cost.",
    NOTE_ + " The anchor for cost per agent and per claim, and for replaying a run.",
    "Runs by agent, success and failure rate, run time, cost per run and per claim, shadow versus live volume, model used, items handled per run",
    "1 written by the agent runtime, 2 reconstructed from decision timestamps (cost unknown)",
    common("agent_run") + [
        L("agent_code", "VARCHAR(5)", M_, "", "Which agent, A1 to A15.", "Always set by us"), L("agent_name", "VARCHAR(40)", I_, "", "Display name.", "From the code"),
        L("run_mode", "VARCHAR(10)", M_, "", "Shadow (proposals only), assisted or live.", "Shadow"), L("trigger_type", "VARCHAR(15)", M_, "", "Schedule, event, manual, retry.", "Schedule"),
        L("started_at", "DATETIME2(0)", M_, "", "Start time.", "First decision time"), L("ended_at", "DATETIME2(0)", I_, "", "End time.", "Blank while running"),
        L("run_status", "VARCHAR(12)", M_, "", "Running, succeeded, partial, failed, cancelled.", "Running"),
        L("practice_id", "INT", I_, "practice", "Blank for a run across practices.", "Blank"), L("items_in", "INT", I_, "", "Entities the run looked at.", "Counted"), L("decisions_made", "INT", I_, "", "Decisions written.", "Counted"),
        L("error_count", "INT", I_, "", "Entities that failed.", "0"), L("error_summary", "VARCHAR(200)", O_, "", "Short error class, never raw data.", "Blank"),
        L("model_name", "VARCHAR(40)", I_, "", "Model used, if any.", "Blank"), L("input_tokens", "BIGINT", I_, "", "For cost.", "Blank"), L("output_tokens", "BIGINT", I_, "", "For cost.", "Blank"),
        L("cost_amount", "DECIMAL(12,4)", I_, "", "Cost of the run, in dollars.", "Blank (cost unavailable)"), L("trigger_run_id", "BIGINT", O_, "agent_run", "The run that started this one.", "Blank"),
        L("code_version", "VARCHAR(30)", O_, "", "Agent version, for replay.", "Blank")] + audit("agent_run", False))

add("agent_decision", M_, GA, "header", "One row per decision an agent reached about one entity (claim, appointment, authorization and so on).",
    NOTE_ + " The decision record: what was decided, on what, how sure, and whether anything left the system.",
    "Decisions by agent and type, confidence, agreement with staff, shadow versus acted, overturned decisions, time from trigger to decision, volume by practice and payer",
    "1 written by the agent, 2 decisions rebuilt from findings (rules and confidence lost)",
    common("agent_decision") + [
        L("agent_run_id", "BIGINT", M_, "agent_run", "The run that made it.", "Always set by us"), L("agent_code", "VARCHAR(5)", M_, "", "Copied from the run.", "Always set by us"),
        L("decision_type", "VARCHAR(30)", M_, "", "Eligibility_ok, needs_auth, hold_claim, appeal, code_change, write_off_review and so on.", "Always set by us"),
        L("entity_type", "VARCHAR(20)", M_, "", "Which table the decision is about.", "Always set by us"), L("entity_id", "BIGINT", M_, "", "Internal ID in that table.", "Always set by us"),
        L("outcome", "VARCHAR(15)", M_, "", "Proceed, hold, flag, propose_change, no_action, needs_human.", "Needs_human"), L("decided_at", "DATETIME2(0)", M_, "", "When decided.", "Run time"),
        L("run_mode", "VARCHAR(10)", M_, "", "Copied: shadow decisions are never acted on.", "Shadow"),
        L("confidence", "DECIMAL(5,4)", I_, "", "0 to 1. Blank when the agent is rule-based only.", "Blank"), L("reason_summary", "VARCHAR(300)", I_, "", "Short plain reason; never patient text.", "Blank"),
        L("rules_checked", "SMALLINT", I_, "", "Rules evaluated (the details hold each one).", "Count of details"), L("rules_failed", "SMALLINT", I_, "", "Rules that failed.", "Count of details"),
        L("amount_at_stake", "DECIMAL(12,2)", I_, "", "Dollars the decision protects or affects.", "Blank"), L("data_fallback_level", "TINYINT", I_, "", "Lowest fallback step of any input used: tells readers how reliable it was.", "Blank"),
        L("human_outcome", "VARCHAR(15)", I_, "", "Accepted, changed, rejected, ignored: agreement with staff.", "Blank"), L("human_outcome_date", "DATE", I_, "", "When staff answered.", "Blank"),
        L("supersedes_decision_id", "BIGINT", I_, "agent_decision", "A newer decision replaces an older one; the old row stays.", "Blank"), L("is_current", "BIT", I_, "", "1 on the latest decision for the entity and type.", "1"),
        L("task_id", "BIGINT", I_, "agent_task", "The task raised from it.", "Blank"), L("finding_id", "BIGINT", I_, "agent_finding", "The finding behind it.", "Blank"),
        L("input_hash", "BINARY(32)", O_, "", "Hash of the inputs, so a replay can prove it saw the same data.", "Blank")] + LINKS() + audit("agent_decision", False))

add("agent_decision_details", M_, GA, "detail", "One row per rule or check evaluated inside a decision.",
    NOTE_ + " Explains a decision. Without it nobody can tell which rule fired.",
    "Rule hit rates, rules that most often block, rule disagreement with staff, rules never firing, rules by payer",
    "1 written by the agent, 2 none: reason_summary on the decision only",
    common("agent_decision_detail") + [
        L("agent_decision_id", "BIGINT", M_, "agent_decision", "The decision it explains.", "Always set by us"), L("check_seq", "SMALLINT", M_, "", "Order within the decision.", "Always set by us"),
        L("rule_code", "VARCHAR(40)", M_, "", "Rule or check evaluated.", "Always set by us"), L("check_result", "VARCHAR(10)", M_, "", "Pass, fail, warn, skipped, unknown.", "Unknown"),
        L("agent_code", "VARCHAR(5)", I_, "", "Copied.", "Always set by us"), L("rule_version", "VARCHAR(20)", I_, "", "Version of the rule at the time.", "Blank"),
        L("rule_source", "VARCHAR(20)", I_, "", "Payer policy, public rule, client rule, learned.", "Blank"), L("severity", "VARCHAR(10)", I_, "", "Block, review, info.", "Info"),
        L("observed_value", "VARCHAR(100)", I_, "", "What was seen, as short text. Never a name, date of birth or raw member number.", "Blank"), L("expected_value", "VARCHAR(100)", I_, "", "What the rule wanted.", "Blank"),
        L("input_table", "VARCHAR(40)", I_, "", "Canonical table the input came from.", "Blank"), L("input_fallback_level", "TINYINT", I_, "", "Fallback step of that input (matches data_feed).", "Blank"),
        L("practice_id", "INT", I_, "practice", "Copied.", "Always set by us"), L("payer_id", "INT", I_, "payer", "Copied.", "Always set by us"), L("cpt_code_id", "INT", I_, "cpt_code", "Copied when relevant.", "Blank"),
        L("evidence_ref", "VARCHAR(100)", O_, "", "Pointer to evidence, never its content.", "Blank")] + audit("agent_decision_detail", False))

add("agent_finding", I_, GA, "event", "One issue an agent found: a missed charge, underpayment, preventable denial, coding gap, document gap and so on.",
    NOTE_ + " The measurable problem list. Findings are what the value metrics are built on.",
    "Findings by type, amount at risk, preventable share, fix rate, time to fix, findings by journey stage, repeat issues, value recovered",
    "1 written by the agent, 2 none",
    common("agent_finding") + [
        L("agent_run_id", "BIGINT", M_, "agent_run", "The run that found it.", "Always set by us"), L("agent_code", "VARCHAR(5)", M_, "", "Which agent.", "Always set by us"),
        L("finding_type", "VARCHAR(30)", M_, "", "Missed_charge, underpayment, preventable_denial, coding_gap, documentation_gap, eligibility_gap, auth_gap, timely_filing_risk and so on.", "Always set by us"),
        L("entity_type", "VARCHAR(20)", M_, "", "Table the issue is about.", "Always set by us"), L("entity_id", "BIGINT", M_, "", "Internal ID in that table.", "Always set by us"),
        L("found_date", "DATE", M_, "", "When found.", "Run date"), L("finding_status", "VARCHAR(12)", M_, "", "Open, accepted, fixed, dismissed, expired.", "Open"),
        L("amount_at_risk", "DECIMAL(12,2)", I_, "", "Dollars at risk if left.", "Blank"), L("amount_recovered", "DECIMAL(12,2)", I_, "", "Dollars recovered or avoided, from the ledger.", "Blank"),
        L("upstream_stage", "VARCHAR(15)", I_, "", "Journey stage that could have caught it.", "Blank"), L("is_preventable", "BIT", I_, "", "Could have been caught earlier.", "Blank"),
        L("severity", "VARCHAR(10)", I_, "", "High, medium, low.", "Medium"), L("deadline_date", "DATE", I_, "", "Filing or appeal limit.", "Blank"),
        L("resolved_date", "DATE", I_, "", "Time to fix.", "Blank"), L("resolution", "VARCHAR(20)", I_, "", "Fixed, written_off, not_an_issue, expired.", "Blank"),
        L("agent_decision_id", "BIGINT", I_, "agent_decision", "The decision that raised it.", "Blank"), L("finding_hash", "BINARY(32)", I_, "", "Same issue seen again maps to the same hash: no duplicates.", "Blank"),
        L("summary", "VARCHAR(300)", O_, "", "Short plain description; no patient text.", "Blank")] + LINKS() + audit("agent_finding"))

add("agent_task", I_, GA, "work item", "One work item for a person or another agent. A status change is a new version.",
    NOTE_ + " Worklists and who owns what. Roles only, never named people.",
    "Open tasks by role, task age, completion rate, overdue tasks, tasks by agent and type, workload by role",
    "1 written by the agent, 2 none",
    common("agent_task") + [
        L("task_type", "VARCHAR(30)", M_, "", "Fix_claim, appeal, chase_note, verify_coverage, request_auth, review_write_off and so on.", "Always set by us"),
        L("owner_role", "VARCHAR(20)", M_, "", "Billing, coding, front desk, provider, manager, or an agent.", "Billing"), L("task_status", "VARCHAR(12)", M_, "", "Open, in_progress, done, cancelled, blocked.", "Open"),
        L("created_date", "DATE", M_, "", "When raised.", "Run date"), L("agent_code", "VARCHAR(5)", M_, "", "Raising agent.", "Always set by us"),
        L("entity_type", "VARCHAR(20)", M_, "", "Table the task is about.", "Always set by us"), L("entity_id", "BIGINT", M_, "", "Internal ID in that table.", "Always set by us"),
        L("agent_decision_id", "BIGINT", I_, "agent_decision", "The decision that raised it.", "Blank"), L("agent_finding_id", "BIGINT", I_, "agent_finding", "The finding that raised it.", "Blank"),
        L("priority", "VARCHAR(8)", I_, "", "High, normal, low.", "Normal"), L("due_date", "DATE", I_, "", "Target date.", "Blank"), L("completed_date", "DATE", I_, "", "Time to complete.", "Blank"),
        L("assigned_to", "VARCHAR(50)", I_, "", "Pseudonymous assignee, never a name.", "Blank"), L("amount_at_stake", "DECIMAL(12,2)", I_, "", "Dollars involved.", "Blank"),
        L("outcome", "VARCHAR(20)", I_, "", "Done, no_action_needed, declined.", "Blank"), L("title", "VARCHAR(100)", O_, "", "Short label; no patient text.", "Blank")] + LINKS() + audit("agent_task"))

add("agent_approval", M_, GA, "audit", "One row per approval or rejection of a proposed change. Append-only.",
    NOTE_ + " The audit trail for anything that changes money or records. Write-offs and refunds need a named approver (rule 4).",
    "Approval rate, time to approve, changes made without approval (must be zero), approvals by role, rejected proposals",
    "1 written when staff approve, 2 none: without it a proposal cannot be acted on",
    common("agent_approval") + [
        L("agent_decision_id", "BIGINT", M_, "agent_decision", "The proposal being approved.", "Always set by us"), L("approval_type", "VARCHAR(25)", M_, "", "Write_off, refund, claim_change, code_change, send_to_payer, setting_change.", "Always set by us"),
        L("approval_status", "VARCHAR(10)", M_, "", "Approved, rejected, expired.", "Always set by us"), L("approved_by", "VARCHAR(50)", M_, "", "Pseudonymous approver. Must be set for approved rows.", "None: the row is refused"),
        L("approver_role", "VARCHAR(20)", M_, "", "Role at the time.", "Always set by us"), L("approval_date", "DATE", M_, "", "When answered.", "Always set by us"),
        L("agent_task_id", "BIGINT", I_, "agent_task", "The task it closed.", "Blank"), L("amount_approved", "DECIMAL(12,2)", I_, "", "Dollars approved.", "Blank"),
        L("limit_checked", "BIT", I_, "", "Within the approver's limit.", "Always set by us"), L("reason_code", "VARCHAR(20)", I_, "", "Why approved or rejected.", "Blank"),
        L("entity_type", "VARCHAR(20)", I_, "", "Table affected.", "Always set by us"), L("entity_id", "BIGINT", I_, "", "Internal ID affected.", "Always set by us"),
        L("practice_id", "INT", I_, "practice", "Copied.", "Always set by us"), L("approval_ts", "DATETIME2(0)", I_, "", "Exact time.", "Blank")] + audit("agent_approval", False))

add("agent_writeback", M_, GA, "outbox", "One row per thing sent out to the PM, EHR, clearinghouse or payer, and what came back. A retry is a new version.",
    NOTE_ + " Proves what left the system. Shadow mode rows are logged as not sent.",
    "Writebacks by target and type, success rate, retries, shadow versus sent, time from approval to send, failures needing attention",
    "1 written by the agent runtime, 2 none",
    common("agent_writeback") + [
        L("agent_decision_id", "BIGINT", M_, "agent_decision", "The decision it carries out.", "Always set by us"), L("target_system", "VARCHAR(15)", M_, "", "Pm, ehr, clearinghouse, payer_portal, scheduler.", "Always set by us"),
        L("writeback_type", "VARCHAR(30)", M_, "", "Note, task, 270, 278, 837_correction, status_update, appeal_packet and so on.", "Always set by us"),
        L("send_status", "VARCHAR(12)", M_, "", "Not_sent_shadow, queued, sent, acknowledged, failed.", "Not_sent_shadow"), L("attempted_at", "DATETIME2(0)", M_, "", "Time of the attempt.", "Always set by us"),
        L("agent_approval_id", "BIGINT", I_, "agent_approval", "Required for money or record changes.", "Blank"), L("agent_code", "VARCHAR(5)", I_, "", "Copied.", "Always set by us"),
        L("entity_type", "VARCHAR(20)", I_, "", "Table concerned.", "Always set by us"), L("entity_id", "BIGINT", I_, "", "Internal ID concerned.", "Always set by us"),
        L("attempt_no", "SMALLINT", I_, "", "Retry count.", "1"), L("response_code", "VARCHAR(20)", I_, "", "Acknowledgement or error class.", "Blank"),
        L("response_at", "DATETIME2(0)", I_, "", "Time of the reply.", "Blank"), L("external_ref", "VARCHAR(50)", I_, "", "The target system's reference. Restricted.", "Blank", True),
        L("payload_hash", "BINARY(32)", I_, "", "Hash of what was sent. Payloads themselves are not stored.", "Blank"), L("practice_id", "INT", I_, "practice", "Copied.", "Always set by us"),
        L("claim_id", "BIGINT", I_, "claim", "Copied when relevant.", "Blank"), L("appointment_id", "BIGINT", I_, "appointment", "Copied when relevant.", "Blank")] + audit("agent_writeback"))

AGENT_T = [n for n in T if n.startswith("agent_")]
for n in AGENT_T: T[n]["status"] = NEW

# =============================================================================================== REFERENCE TABLES
GR = "Reference"
def addr(name, pri, what, purpose, metrics, fb, cols):
    add(name, pri, GR, "reference", what, purpose, metrics, fb, common(name) + cols + ref_audit())

addr("practice", M_, "A billing entity inside a client.", "Every table links to it. The client itself is tenant_id.", "All reports by practice", "1 onboarding form, 2 billing provider loop of the 837, 3 tenant defaults", [
    L("practice_number", "VARCHAR(50)", M_, "", "The client's code for the practice.", "The tax ID"), L("practice_name", "NVARCHAR(200)", I_, "", "Display.", "Client name"),
    L("tax_id", "CHAR(9)", I_, "", "Billing entity on claims and contracts. Restricted.", "From the claim's billing provider loop", True), L("group_npi", "CHAR(10)", I_, "", "Billing NPI for group claims.", "Most common billing NPI on claims"),
    L("time_zone", "VARCHAR(40)", I_, "", "Day cut-offs for aging, lag and snapshots.", "Client default"), L("fiscal_year_start_month", "TINYINT", I_, "", "Fiscal reporting.", "1"),
    L("go_live_date", "DATE", I_, "", "Where history starts and opening balances apply.", "Earliest data date")])
addr("provider", M_, "A clinician or group.", "Productivity, denials by clinician, enrollment.", "Productivity, denials by provider, charges by provider", "1 PM or EHR provider list, 2 public NPI registry by NPI, 3 provider IDs seen on claims", [
    L("npi", "CHAR(10)", M_, "", "National provider ID; links scheduler, EHR, claims and payer.", "From claims; else a flagged placeholder"), L("provider_number", "VARCHAR(50)", I_, "", "The scheduler or EHR's own provider code.", "The NPI"),
    L("provider_type", "VARCHAR(12)", I_, "", "Individual or group.", "Inferred from how the NPI is used"), L("specialty_id", "INT", I_, "specialty", "Main specialty.", "Mapped from the taxonomy"),
    L("taxonomy_code", "VARCHAR(12)", I_, "", "Enrollment and specialty mapping.", "The 837 provider segment"), L("credential", "VARCHAR(10)", I_, "", "MD, DO, NP, PA.", "From the taxonomy"),
    L("provider_name", "NVARCHAR(200)", I_, "", "Display.", "Label from the last digits of the NPI"), L("practice_id", "INT", I_, "practice", "Home practice; each transaction still carries the practice billed.", "Most common practice on claims"),
    L("start_date", "DATE", I_, "", "Productivity window.", "First claim date"), L("end_date", "DATE", I_, "", "Productivity window.", "Last claim date"), L("supervising_provider_id", "INT", O_, "provider", "Supervised clinicians.", "Blank")])
addr("payer", M_, "An insurer.", "Payer mix, denial deadlines, coordination-of-benefits rules.", "Payer mix, denial and acceptance by payer, filing and appeal risk", "1 clearinghouse payer list, 2 PM payer table, 3 payer name and ID from claims and remittances", [
    L("payer_code", "VARCHAR(50)", M_, "", "Public payer ID used by the clearinghouse.", "ID on the 835 or 837"), L("payer_name", "NVARCHAR(200)", M_, "", "Display.", "Name on the 835"),
    L("payer_number", "VARCHAR(50)", I_, "", "The PM's own payer code.", "The payer code"), L("payer_type", "VARCHAR(20)", M_, "", "Commercial, medicare, medicaid, tricare, workers_comp, auto, self_pay.", "Inferred from the name, flagged assumed"),
    L("parent_payer", "NVARCHAR(200)", I_, "", "Rolls plans up to an organisation.", "The payer name"), L("filing_days", "SMALLINT", I_, "", "Timely-filing limit.", "365, flagged default"),
    L("corrected_claim_days", "SMALLINT", I_, "", "Window for corrected claims.", "Same as filing days"), L("appeal_days", "SMALLINT", I_, "", "Appeal deadline.", "180, flagged default"),
    L("standard_turnaround_days", "SMALLINT", O_, "", "Authorization planning.", "Blank"), L("supports_electronic_auth", "BIT", O_, "", "Authorization planning.", "Blank"),
    L("state", "CHAR(2)", O_, "", "Regional rules.", "Blank"), L("dispute_contact", "NVARCHAR(200)", O_, "", "Role mailbox or portal, never a person.", "Blank")])
addr("cpt_code", M_, "A procedure code (CPT or HCPCS). Effective-dated.", "Procedure level reporting and pricing. CPT descriptions are AMA-licensed and not stored.", "Procedure mix, denials by procedure, contract pricing, productivity", "1 client code list, 2 public CMS HCPCS and relative value files, 3 codes seen on claims", [
    L("code", "VARCHAR(5)", M_, "", "The 5-character code.", "Codes seen on claims"), L("code_type", "VARCHAR(5)", M_, "", "CPT or HCPCS.", "Letter first means HCPCS"),
    L("effective_from", "DATE", M_, "", "Which year's meaning applies.", "January 1 of the code set year"), L("effective_to", "DATE", M_, "", "End of validity.", "Blank while open"),
    L("short_label", "VARCHAR(60)", I_, "", "Our own words.", "Code 99213"), L("category", "VARCHAR(20)", I_, "", "E/M, radiology, lab, therapy, surgery, anesthesia, medicine, drug.", "From the public code ranges"),
    L("em_level", "TINYINT", I_, "", "Visit level 1 to 5.", "From the last digit"), L("is_add_on", "BIT", I_, "", "Needs a primary code.", "Public add-on list"), L("is_timed", "BIT", I_, "", "Units come from time.", "Public timed-code list"),
    L("unit_limit_per_day", "SMALLINT", I_, "", "CMS unit limit.", "Blank"), L("laterality_required", "BIT", I_, "", "Needs left or right.", "Blank (flagged)"), L("work_rvu", "DECIMAL(8,2)", I_, "", "Provider productivity.", "Blank"),
    L("global_period_days", "SMALLINT", O_, "", "Surgical bundling denials.", "Blank"), L("is_unrecognized", "BIT", I_, "", "Flagged placeholder for an unknown code.", "Always set by us")])
addr("diagnosis_code", M_, "An ICD-10-CM diagnosis code. Effective-dated.", "Condition analysis and medical-necessity checks. The text is public.", "Diagnosis mix, denials by diagnosis, medical necessity", "1 client list, 2 public CMS ICD-10-CM release, 3 codes seen on claims", [
    L("icd10_code", "VARCHAR(8)", M_, "", "Saved without the dot.", "Codes seen on claims"), L("effective_from", "DATE", M_, "", "Updated each October 1.", "October 1 of the code set year"), L("effective_to", "DATE", M_, "", "End of validity.", "Blank while open"),
    L("description", "VARCHAR(255)", I_, "", "Public description.", "Blank"), L("category", "VARCHAR(30)", I_, "", "Chapter and block.", "Derived"), L("is_billable", "BIT", I_, "", "Header codes cause rejections.", "Derived from code length"),
    L("is_chronic", "BIT", I_, "", "Condition analysis.", "Blank"), L("is_unspecified", "BIT", I_, "", "Coding specificity.", "Blank"), L("parent_code", "VARCHAR(8)", O_, "", "Less specific parent.", "Blank"),
    L("hcc_category", "VARCHAR(10)", O_, "", "Risk adjustment.", "Blank"), L("is_unrecognized", "BIT", I_, "", "Flagged placeholder.", "Always set by us")])
addr("modifier", I_, "A procedure modifier.", "Modifiers change payment and cause many denials.", "Modifier-related denials, laterality coverage", "1 client list, 2 public modifier list, 3 values seen on claims", [
    L("modifier_code", "CHAR(2)", M_, "", "The 2-character modifier.", "Codes seen on claims"), L("modifier_group", "VARCHAR(20)", I_, "", "Pricing, anatomical, telehealth, anesthesia, informational.", "From the public list"),
    L("affects_payment", "BIT", I_, "", "Whether it changes payment.", "Blank"), L("payment_adjustment_pct", "DECIMAL(5,2)", O_, "", "For example 50% for a reduced service.", "Blank"),
    L("short_label", "VARCHAR(60)", I_, "", "Our own words.", "The code"), L("effective_from", "DATE", I_, "", "Lifecycle.", "Always set by us"), L("effective_to", "DATE", I_, "", "Lifecycle.", "Blank")])
addr("place_of_service", I_, "A CMS place-of-service code.", "Changes payment rates (facility vs non-facility).", "Site reporting, rate differences", "1 client list, 2 public CMS list, 3 values seen on claims", [
    L("pos_code", "CHAR(2)", M_, "", "CMS 2-digit code.", "Office (11)"), L("pos_name", "VARCHAR(80)", I_, "", "Public name.", "From the CMS list"), L("setting", "VARCHAR(15)", I_, "", "Office, outpatient, inpatient, ER, home, telehealth.", "Derived"),
    L("is_facility", "BIT", I_, "", "Rate differences.", "From the code"), L("is_telehealth", "BIT", I_, "", "Rule differences.", "From the code"), L("effective_from", "DATE", I_, "", "Lifecycle.", "Always set by us"), L("effective_to", "DATE", I_, "", "Lifecycle.", "Blank")])
addr("specialty", I_, "A clinical specialty.", "Specialty reports, payer rules, benchmarks.", "Denial, productivity and AR by specialty", "1 provider taxonomy mapped to a specialty, 2 client list, 3 inferred from the provider's dominant procedure category", [
    L("specialty_code", "VARCHAR(20)", M_, "", "A short standard code.", "Slug of the name"), L("specialty_name", "NVARCHAR(100)", M_, "", "Display.", "From the code"), L("specialty_group", "VARCHAR(15)", I_, "", "Primary care, medical, surgical, behavioral, therapy, diagnostic.", "Blank"),
    L("is_primary_care", "BIT", I_, "", "Benchmarks and HMO rules.", "From the group"), L("cms_specialty_code", "VARCHAR(5)", O_, "", "Medicare list.", "Blank"), L("taxonomy_prefix", "VARCHAR(12)", O_, "", "Maps a taxonomy to the specialty.", "Blank")])
addr("facility", I_, "A location where service happens.", "Site reporting and capacity. A practice is the billing entity; a facility is a site.", "Visits and charges by site, capacity", "1 PM location list, 2 service-facility loop on claims, 3 one default facility per practice", [
    L("facility_number", "VARCHAR(50)", M_, "", "The client's location code.", "Name of the site"), L("facility_name", "NVARCHAR(200)", I_, "", "Display.", "The number"), L("practice_id", "INT", I_, "practice", "Owning practice.", "The single practice"),
    L("facility_type", "VARCHAR(20)", I_, "", "Office, clinic, hospital outpatient, surgery center, urgent care, lab, imaging, home, telehealth.", "From the usual place of service"),
    L("default_place_of_service_id", "INT", I_, "place_of_service", "Usual place-of-service code.", "Office (11)"), L("facility_npi", "CHAR(10)", I_, "", "Service facility NPI.", "From claims"), L("state", "CHAR(2)", I_, "", "State rules.", "Practice state"),
    L("open_date", "DATE", I_, "", "Site history.", "First activity"), L("close_date", "DATE", I_, "", "Site history.", "Last activity"), L("zip", "VARCHAR(5)", O_, "", "Location detail.", "Blank"), L("rooms", "SMALLINT", O_, "", "Capacity.", "Blank"), L("time_zone", "VARCHAR(40)", O_, "", "Inherits the practice's.", "Blank")])
addr("patient", M_, "A patient. No names, birth dates, addresses or raw member numbers are stored.", "Hashed at the loading boundary with a per-client salt; the raw value never lands in a table or log.", "Patient-level balances, new vs established, age at service", "1 PM or EHR patient list (hashed at load), 2 claims, 3 the patient control number on the remittance, hashed", [
    L("patient_number_hash", "BINARY(32)", M_, "", "Salted hash of the client's patient number. The only link back to the source. Restricted.", "Hash of member ID", True),
    L("master_patient_hash", "BINARY(32)", I_, "", "The same person across member IDs or practices.", "Same as the patient hash"), L("merged_into_patient_id", "BIGINT", I_, "patient", "Duplicate records merged at the source.", "Blank"),
    L("birth_year", "SMALLINT", I_, "", "Year only; age at service.", "Blank (age unknown)"), L("is_age_90_plus", "BIT", I_, "", "Ages above 89 are grouped as 90+.", "Derived"), L("sex", "CHAR(1)", I_, "", "M, F, U. Gender-specific procedure edits.", "U"),
    L("state", "CHAR(2)", I_, "", "State rules and regional reports.", "Practice state"), L("primary_practice_id", "INT", I_, "practice", "Home practice.", "Most common practice"),
    L("first_seen_date", "DATE", I_, "", "New vs established.", "First encounter"), L("last_seen_date", "DATE", I_, "", "Lapsed patients.", "Last encounter"), L("primary_coverage_id", "BIGINT", I_, "coverage", "Current primary coverage.", "Latest claim's coverage"),
    L("is_self_pay", "BIT", I_, "", "No active coverage.", "Derived"), L("zip3", "CHAR(3)", O_, "", "Geography.", "Blank"), L("language", "VARCHAR(20)", O_, "", "Communication.", "Blank"), L("is_deceased", "BIT", O_, "", "Stops statements.", "Blank")])
add("coverage", I_, GR, "reference", "One insurance policy for a patient, per period. A change closes the old row and adds a new one.", "Powers eligibility work and coordination-of-benefits checks. History kept because insurance at booking can differ from insurance at billing.",
    "Coverage gaps at booking, coordination-of-benefits order problems, payer mix by plan type, self-pay share, insurance changes between booking and billing", "1 PM or EHR insurance records, 2 eligibility responses, 3 claims (payer, sequence, date range), 4 payer only",
    common("coverage") + [
        L("patient_id", "BIGINT", M_, "patient", "Whose policy.", "From the claim"), L("payer_id", "INT", M_, "payer", "The insurer.", "From the claim"),
        L("member_number_hash", "BINARY(32)", M_, "", "Hash of the member ID. The raw ID is never stored; eligibility reads it from the source at send time. Restricted.", "Hash from the claim", True),
        L("coverage_order", "TINYINT", M_, "", "1 primary, 2 secondary, 3 tertiary.", "1; or the sequence on the claim"), L("effective_date", "DATE", M_, "", "Policy start.", "First claim date for the payer"),
        L("termination_date", "DATE", I_, "", "Policy end; blank while open.", "Last claim date, flagged"), L("plan_type", "VARCHAR(25)", I_, "", "PPO, HMO, EPO, POS, Medicare Advantage, traditional Medicare, Medicaid managed care.", "Inferred from the payer type"),
        L("plan_name", "NVARCHAR(100)", I_, "", "Display.", "Blank"), L("group_number_hash", "BINARY(32)", I_, "", "Group identification. Restricted.", "Blank", True),
        L("relationship_to_holder", "VARCHAR(10)", I_, "", "Self, spouse, child, other: sets the dependent level.", "Self"),
        L("last_verified_date", "DATE", I_, "", "When coverage was last checked.", "Blank"), L("last_verified_status", "VARCHAR(12)", I_, "", "Active, inactive, not found.", "Blank"),
        L("requires_referral", "BIT", O_, "", "HMO referral rules.", "From plan type"), L("pcp_provider_id", "INT", O_, "provider", "HMO primary care provider.", "Blank"),
        L("copay_amount", "DECIMAL(12,2)", O_, "", "Latest verified benefit.", "Blank"), L("coinsurance_pct", "DECIMAL(5,4)", O_, "", "Latest verified benefit.", "Blank"), L("deductible_remaining", "DECIMAL(12,2)", O_, "", "Latest verified benefit.", "Blank"),
        L("subscriber_hash", "BINARY(32)", O_, "", "Links family members under one subscriber. Restricted.", "Same as the member hash", True)] + audit("coverage"))
add("authorization", I_, GR, "reference", "A prior authorization as the payer issued it. An extension or revision closes the old row and adds a new one.", "Supports the authorization work and denial prevention.",
    "Authorization coverage, turnaround days, approval rate, expiring authorizations, units used vs approved, denials with and without authorization", "1 PM authorization table, 2 portal or 278 responses, 3 authorization number seen on claims (no window or units), 4 none: state stays unknown",
    common("authorization") + [
        L("authorization_number", "VARCHAR(50)", M_, "", "The payer's number; a pending request uses our request reference. Restricted.", "Our request reference", True),
        L("patient_id", "BIGINT", M_, "patient", "Whose authorization.", "From the request"), L("payer_id", "INT", M_, "payer", "With which payer.", "From the request"), L("practice_id", "INT", M_, "practice", "Reports by practice.", "From the request"),
        L("authorization_status", "VARCHAR(15)", M_, "", "Requested, pended, certified, modified, not_certified, cancelled, expired.", "Requested"),
        L("coverage_id", "BIGINT", I_, "coverage", "The policy it applies to.", "Patient's current coverage"), L("primary_cpt_code_id", "INT", I_, "cpt_code", "The main procedure authorized.", "From the first claim line"),
        L("units_approved", "INT", I_, "", "Overuse and remaining units.", "Blank"), L("units_used", "INT", I_, "", "Rebuilt from claims.", "Blank"), L("valid_from", "DATE", I_, "", "The approved window.", "Blank, flagged"), L("valid_to", "DATE", I_, "", "The approved window.", "Blank, flagged"),
        L("request_date", "DATE", I_, "", "Turnaround time.", "Blank"), L("decision_date", "DATE", I_, "", "Turnaround time.", "Blank"), L("authorization_type", "VARCHAR(15)", I_, "", "Outpatient, inpatient, referral, predetermination, retro.", "Outpatient"),
        L("requesting_provider_id", "INT", I_, "provider", "Who asked.", "Encounter provider"), L("rendering_provider_id", "INT", I_, "provider", "Who will perform.", "Encounter provider"),
        L("urgency", "VARCHAR(10)", O_, "", "Standard or expedited.", "Blank"), L("request_channel", "VARCHAR(10)", O_, "", "X12, portal, phone, fax.", "Blank"), L("decision_reason_code", "VARCHAR(20)", O_, "", "Reason the payer gave.", "Blank"),
        L("diagnosis_code_id", "INT", O_, "diagnosis_code", "Diagnosis on the request.", "Blank"), L("facility_id", "INT", O_, "facility", "Location.", "Blank")] + audit("authorization"))
addr("fee_list", I_, "The practice's own fee list. Billed amount = units x this fee. Effective-dated.", "Audit and expected-charge checks; bill lines still store the fee used.", "Charge compliance, fee changes, revenue forecast from planned services", "1 PM charge master export, 2 inferred from recent bill lines (flagged), 3 charge divided by units from claim lines, 4 none", [
    L("practice_id", "INT", M_, "practice", "The practice the list belongs to.", "Client default"), L("fee_list_name", "VARCHAR(50)", M_, "", "Standard, self-pay, hospital-based.", "Standard"),
    L("cpt_code_id", "INT", M_, "cpt_code", "The procedure.", "Codes seen on bill lines"), L("fee_per_unit", "DECIMAL(12,2)", M_, "", "The charge per unit.", "Most common charge per unit on recent bill lines (flagged)"),
    L("effective_from", "DATE", M_, "", "When the fee took effect.", "Earliest bill line using it"), L("is_inferred", "BIT", M_, "", "1 when estimated.", "Always set by us"),
    L("effective_to", "DATE", I_, "", "Blank while open.", "Blank"), L("modifier_id", "INT", I_, "modifier", "For fees that depend on the modifier.", "Blank"), L("is_default", "BIT", I_, "", "The list used when none is named.", "The only list"),
    L("facility_id", "INT", O_, "facility", "Location-specific fees.", "Blank"), L("fee_basis", "VARCHAR(15)", O_, "", "Flat, or a multiple of Medicare.", "Flat")])
addr("contract_rate", I_, "What a payer has agreed to allow per unit. Effective-dated.", "Base for expected allowed, underpayment and realisation. Learned rates are always flagged.", "Expected allowed, underpayment, realisation, payer rate comparison", "1 contract fee schedule file, 2 payer published schedule or the public CMS Medicare schedule, 3 learned from remittances (flagged, with confidence), 4 none: blank and flagged", [
    L("practice_id", "INT", M_, "practice", "Whose contract.", "From the claims"), L("payer_id", "INT", M_, "payer", "Whose contract.", "From the claims"), L("cpt_code_id", "INT", M_, "cpt_code", "The procedure.", "Codes seen on remittances"),
    L("allowed_per_unit", "DECIMAL(12,2)", M_, "", "The allowed dollars per unit.", "Learned"), L("effective_from", "DATE", M_, "", "When the rate applies from.", "Earliest paid line used"),
    L("rate_source", "VARCHAR(20)", M_, "", "Contract, payer_fee_schedule, medicare_schedule, learned: a learned estimate is never presented as the contract.", "Learned"), L("is_inferred", "BIT", M_, "", "1 when we estimated the rate.", "Always set by us"),
    L("effective_to", "DATE", I_, "", "Blank while open.", "Blank"), L("modifier_id", "INT", I_, "modifier", "Modifier-dependent rates.", "Blank"), L("rate_setting", "VARCHAR(12)", I_, "", "Facility or non-facility.", "From the place of service"),
    L("contract_number", "VARCHAR(50)", I_, "", "Ties to the contract document.", "Blank"), L("rate_basis", "VARCHAR(20)", I_, "", "Fixed, percent of Medicare, percent of billed, per diem.", "Fixed"),
    L("lesser_of_billed", "BIT", I_, "", "Payer pays the lesser of billed and allowed.", "0"), L("confidence", "DECIMAL(5,4)", I_, "", "For learned rates: reliability.", "Computed"), L("sample_size", "INT", I_, "", "For learned rates: lines used.", "Computed"),
    L("plan_type", "VARCHAR(25)", O_, "", "Plan-specific rates.", "Blank"), L("provider_id", "INT", O_, "provider", "Provider-specific rates.", "Blank"), L("specialty_id", "INT", O_, "specialty", "Specialty-specific rates.", "Blank"),
    L("multi_procedure_reduction_pct", "DECIMAL(5,2)", O_, "", "Multiple-procedure reduction.", "Blank"), L("dispute_days", "SMALLINT", O_, "", "Dispute window.", "Blank")])
addr("adjustment_reason", M_, "A payer adjustment or denial reason code (CARC). Effective-dated.", "Decides what counts as a denial in the whole model. The classification columns are an editable default rule table and never trigger actions.", "Denial classification, routing, appealable mix", "1 public X12 code list, 2 our default classification, 3 client overrides, 4 codes seen on remittances classed unknown", [
    L("carc_code", "VARCHAR(10)", M_, "", "The reason code.", "Codes seen on remittances"), L("effective_from", "DATE", M_, "", "The list changes during the year.", "Date of first use"), L("effective_to", "DATE", M_, "", "End of validity.", "Blank while open"),
    L("reason_class", "VARCHAR(20)", M_, "", "Denial, contractual, patient_responsibility, other_adjustment, informational. A PR group always means patient responsibility.", "Unknown"),
    L("short_label", "VARCHAR(60)", I_, "", "Our own words.", "The code"), L("reason_category", "VARCHAR(30)", I_, "", "Eligibility, authorization, coding, documentation, timely filing, duplicate, coordination of benefits, bundling, technical.", "Unknown"),
    L("suggested_action", "VARCHAR(25)", I_, "", "Fix and resubmit, appeal, write-off review, bill patient, informational. A proposal only.", "Unknown"), L("owner_role", "VARCHAR(20)", I_, "", "Billing, coding, front desk, provider, patient.", "Billing"),
    L("upstream_stage", "VARCHAR(15)", I_, "", "Which journey stage could have caught it.", "Unknown"), L("is_appealable", "BIT", I_, "", "Default.", "Unknown"), L("is_technical", "BIT", I_, "", "Default.", "Unknown"),
    L("is_preventable_default", "BIT", I_, "", "Default.", "Unknown"), L("typical_group", "CHAR(2)", O_, "", "Usual group code.", "Blank"), L("is_unrecognized", "BIT", M_, "", "Flagged placeholder for an unknown code.", "Always set by us")])
addr("remark_code", I_, "A remittance remark (RARC). Effective-dated.", "Adds detail to a reason; attaches to the line, not to one reason.", "Remark patterns, documentation-needed denials", "1 public remark code list, 2 our default categorization, 3 codes seen on remittances typed unknown", [
    L("rarc_code", "VARCHAR(10)", M_, "", "The remark code.", "Codes seen on remittances"), L("effective_from", "DATE", M_, "", "The list is updated regularly.", "Date of first use"), L("effective_to", "DATE", M_, "", "End of validity.", "Blank while open"),
    L("code_qualifier", "VARCHAR(5)", I_, "", "Which code list.", "Standard remark list"), L("short_label", "VARCHAR(60)", I_, "", "Our own words.", "The code"), L("remark_type", "VARCHAR(15)", I_, "", "Alert, informational, supplemental, action required.", "Unknown"),
    L("suggests_action", "VARCHAR(25)", I_, "", "Documentation needed, correct and resubmit, appeal, none. A proposal only.", "Unknown"), L("documents_needed", "VARCHAR(30)", O_, "", "Which records the remark implies.", "Blank"),
    L("related_reason_code", "VARCHAR(10)", O_, "", "Common pairing with a reason.", "Blank"), L("is_unrecognized", "BIT", M_, "", "Flagged placeholder.", "Always set by us")])
addr("practice_settings", I_, "One row per setting, effective-dated. Tenant-wide default overridable per practice.", "The per-client numbers (aging clock, missed-charge delay, retention) so nothing is hard-coded. Built-in defaults apply if a client has none.", "Drives lag, aging and snapshot definitions", "Built-in defaults", [
    L("practice_id", "INT", I_, "practice", "Blank means the client-wide default.", "Client-wide"), L("setting_key", "VARCHAR(50)", M_, "", "The setting.", "Built-in default"), L("setting_value", "VARCHAR(100)", M_, "", "Its value.", "Built-in default"),
    L("value_type", "VARCHAR(10)", M_, "", "Number, days, percent, text, list.", "Built-in default"), L("effective_from", "DATE", M_, "", "History of changes.", "Go-live date"), L("effective_to", "DATE", M_, "", "Blank while current.", "Blank"),
    L("set_by_role", "VARCHAR(20)", I_, "", "Who set it.", "Blank"), L("approved_by", "VARCHAR(50)", I_, "", "Pseudonymous approver for changes that affect reporting.", "Blank")])

# =============================================================================================== VALIDATION
names = set(T)
bad = [(t, c[0], c[3]) for t, d in T.items() for c in d["cols"] if c[3] and c[3] not in names]
print("unresolved links:", bad)
assert not bad
for t, d in T.items():
    cn = [c[0] for c in d["cols"]]
    dup = {x for x in cn if cn.count(x) > 1}
    assert not dup, (t, dup)

TBD = [
    ("referral", "1-2", "Referrals into the practice: referring provider, valid dates, visits allowed and used", "Important for HMO and specialty clinics", "Referral-related denial prevention, visits remaining", "coverage.requires_referral, appointment.referring_provider_id", "Referral flag on coverage only"),
    ("eligibility_check", "1", "History of payer eligibility answers (271)", "Important", "Pre-visit verification, coverage problems, benefits for estimates", "coverage.last_verified_*, appointment.eligibility_state", "Latest status on coverage only"),
    ("estimate", "1", "Expected patient cost and good-faith estimates, versus actual", "Optional", "Estimate accuracy, self-pay compliance", "appointment_details.expected_*, appointment.copay_due", "Not available"),
    ("document", "2", "Metadata for notes, orders, consents and results: type, status, signed dates (never the content)", "Important", "Documentation chase, signature lag", "encounter.note_*", "Summary on encounter only"),
    ("encounter_diagnosis", "2", "Full diagnosis list beyond four per line", "Optional", "Risk adjustment", "encounter_details.diagnosis_1-4", "Four per line"),
    ("order", "2", "Lab, imaging and referral orders", "Optional", "Orders with no charge; authorization linkage", "encounter_details.ordering_provider_id", "Not available"),
    ("claim_attachment", "3", "Records requests and attachments sent", "Optional", "Payer-records workflow", "claim (batch/control numbers)", "Not available"),
    ("payment_adjustment", "4", "Provider-level adjustments: takebacks, interest, recoupments not tied to a claim", "Optional", "Cash reconciliation", "payment.plb_amount", "Total only on payment"),
    ("patient_statement", "4", "Statements sent: date, amount, channel, dunning level", "Optional", "Patient collection work", "ar.last_statement_date, ar_interval.last_statement_date", "Last statement date only"),
    ("payment_plan", "4", "Patient plans and missed instalments", "Optional", "Patient AR forecasting", "ar (patient owner)", "Not available"),
    ("appeal", "4", "Appeal cases: submitted, outcome, recovered", "Optional", "Overturn rate, appeal cycle time", "denial.outcome, denial.recovered_amount", "Outcome on denial only"),
    ("enrollment", "cross", "Provider-payer enrollment status and revalidation dates", "Optional", "Enrollment-related denials", "provider, payer", "Not available"),
    ("payer_rule", "cross", "Authorization-required rules, bundling pairs, medical-necessity pairs, unit limits", "Important", "Prevention checks before claims go out", "authorization, cpt_code (unit limit), adjustment_reason", "Prevention runs with fewer rules"),
    ("calendar", "cross", "Dates with holidays and business days", "Important", "Lag and aging in business days", "all DATE columns", "Calendar days only"),
    ("staff", "cross", "Pseudonymous approvers and task owners, never names", "Important", "Approval trail, workload", "transactions.approved_by, bill_details.change_approved_by, practice_settings.approved_by", "Approver stored as a pseudonymous text"),
    ("agent_value", "5", "Ledger of dollars recovered or avoided and which agent gets credit", "Optional", "Agent value reporting", "agent_finding.amount_recovered, transactions", "Value read from agent_finding only"),
]

SOURCES = [
    ("EHR via FHIR API", "Patient, Practitioner/Organization, Appointment, Encounter, Coverage (limited), Procedure / ChargeItem where offered, DocumentReference (metadata)", "appointment, appointment_details (if services listed), encounter, encounter_details, patient, provider, facility, coverage", "FHIR ids go to *_number (restricted); patient number is hashed at load", "Often no money, claim or payment data; no fee list. Bill and claim tables come from the PM."),
    ("EHR via HL7 v2", "SIU (scheduling), ADT (visit), DFT (charges), MDM (document metadata)", "appointment, appointment_slot (some), encounter, bill_details (from DFT)", "Message control and visit numbers go to *_number", "Diagnosis lists and authorizations are uneven; confirm per interface spec."),
    ("PM system export, file drop or database view", "Charges, claims, payments, adjustments, AR aging, patient and insurance records, fee schedule, provider and payer lists", "bill, bill_details, claim, claim_details, transactions, ar, practice, provider, payer, patient, coverage, authorization, fee_list, facility", "PM ids go to *_number; the same internal IDs drive every join", "Quality varies; each table has a fallback ladder and a reliability flag."),
    ("Scheduling system", "Appointments, templates and open slots", "appointment, appointment_details, appointment_slot", "Appointment ids to appointment_number", "Few carry a procedure: planned services are inferred and flagged."),
    ("Clearinghouse X12", "837 claims, 999 and 277CA acknowledgements, 277 status, 835 remittance, 271 eligibility, 278 authorization", "claim, claim_details (837); claim_status_history (999, 277CA, 277); payment, transactions, denial, denial_details (835); coverage verification fields (271); authorization (278)", "Control numbers to *_number columns; payer claim number restricted", "Holds no appointments or clinical data."),
    ("Payer portals and manual upload", "Authorization status, claim status, fee schedules, contract rates", "authorization, claim_status_history, contract_rate, fee_list", "Reference numbers restricted", "Manual: stamped source = manual and a lower reliability."),
    ("Public code sets", "CPT/HCPCS lists and relative values, ICD-10-CM, modifiers, place of service, CARC and RARC, payer lists, NPI registry", "cpt_code, diagnosis_code, modifier, place_of_service, adjustment_reason, remark_code, payer, provider", "No client data", "CPT descriptions are AMA-licensed and not stored."),
    ("Client documents", "Contracts and fee schedules", "contract_rate, fee_list", "Contract numbers restricted", "Reading contracts with a model needs an approved BAA."),
]

SETTINGS = [
    ("Aging basis: payer balance", "Date of service", "ar_interval, ar"), ("Aging basis: patient balance", "Transfer date", "ar_interval, ar"), ("Aging bucket edges", "30, 60, 90, 120", "ar_interval, ar"),
    ("Missed-charge delay", "3 days (placeholder)", "encounter, bill"), ("Eligibility re-check days", "3 and 1 (as built)", "Eligibility work"), ("Authorization check days", "7 and 2 (as built)", "Authorization work"),
    ("Filing warning", "30 days (as built)", "bill, ar"), ("Appeal warning", "14 days (placeholder)", "denial"), ("Snapshot retention", "Daily 90 days, weekly 13 months, month-end forever", "ar"),
    ("Small-balance review threshold", "$5 (placeholder)", "Patient billing"), ("Provider working hours", "Blank (needed to estimate capacity without slots)", "appointment_slot fallback"),
]

ALLOWED = ns["ALLOWED"] + [
    ("transactions.transaction_type", "charge, payment, adjustment, write_off, refund, transfer, opening_balance"), ("responsible_party / balance_owner", "payer, patient (unbilled on ar)"),
    ("denial_status", "open, corrected_resubmitted, appealed, written_off, recovered, closed, expired"), ("denial_details.detail_type", "reason, remark"),
    ("adjustment_reason.reason_class", "denial, contractual, patient_responsibility, other_adjustment, informational"), ("group_code", "CO, PR, OA, PI, CR"),
    ("period_type", "month, week"), ("aging_bucket", "current, 0-30, 31-60, 61-90, 91-120, 120+"), ("snapshot_type", "daily, weekly, month_end"),
    ("claim_status_history.event_type", "submitted, ack_999, ack_277ca, status_inquiry, status_response, adjudicated, resubmitted, voided"),
    ("payment.payment_method", "eft, check, virtual_card, card, cash, other"), ("payment.payment_source", "payer, patient"), ("payment.payment_type", "payment, takeback, refund"),
    ("appointment_slot.slot_status", "open, booked, held, blocked"), ("appointment_slot.slot_type", "new_patient, follow_up, procedure, telehealth, any, block"),
    ("agent_run.run_mode", "shadow, assisted, live"), ("agent_decision.outcome", "proceed, hold, flag, propose_change, no_action, needs_human"), ("agent_decision.human_outcome", "accepted, changed, rejected, ignored"),
    ("agent_finding.finding_status", "open, accepted, fixed, dismissed, expired"), ("agent_task.task_status", "open, in_progress, done, cancelled, blocked"), ("agent_approval.approval_status", "approved, rejected, expired"),
    ("agent_writeback.send_status", "not_sent_shadow, queued, sent, acknowledged, failed"), ("agent_decision_details.check_result", "pass, fail, warn, skipped, unknown"),
    ("data_feed.feed_status", "active, paused, failed, not_provided"), ("data_feed.source_system", "scheduler, ehr, pm, clearinghouse, payer_portal, manual, public_list"),
    ("data_feed.source_kind", "api, hl7, file_drop, database_view, upload, public"), ("data_feed.load_frequency", "realtime, hourly, daily, weekly, monthly, one_time"),
    ("data_feed.fallback_level", "0 = primary source; 1 and up = the fallback step in use on that table's ladder"),
    ("authorization_status", "requested, pended, certified, modified, not_certified, cancelled, expired"), ("coverage.plan_type", "PPO, HMO, EPO, POS, Medicare Advantage, traditional Medicare, Medicaid managed care, other"),
    ("payer.payer_type", "commercial, medicare, medicaid, tricare, workers_comp, auto, self_pay"), ("suggested_action", "fix_and_resubmit, appeal, write_off_review, bill_patient, informational"),
]

# ======================= AGENT-FIELD REVIEW: changes approved table by table (see gap_decisions.md)
AG = {"Gatekeeper": "A1", "Permit Clerk": "A2", "Note Chaser": "A3", "Code Whisperer": "A4", "Mirror": "A5", "Courier": "A6", "Hunter": "A7",
      "Advocate": "A8", "Coach": "A9", "Auditor": "A10", "Bookkeeper": "A11", "Concierge": "A12", "Credentialing": "A13", "Captain": "A14",
      "Detective / Scout": "A15"}
NEWF = {}   # (table, column) -> (kind, why, agents)


def _ag(s):
    return ", ".join(f"{a.strip()} ({AG[a.strip()]})" for a in s.split(","))


def newcol(table, name, typ, desc, fb, why, agents, link="", pri=None):
    cols = T[table]["cols"]
    assert name not in [c[0] for c in cols], (table, name)
    i = next(k for k, c in enumerate(cols) if c[0] in ("version", "source"))
    cols.insert(i, L(name, typ, pri or O_, link, desc, fb))
    NEWF[(table, name)] = ("NEW", why, _ag(agents))


def retext(table, name, old, new, why, agents):
    cols = T[table]["cols"]
    for k, c in enumerate(cols):
        if c[0] == name:
            assert old in c[5], (table, name)
            cols[k] = c[:5] + (c[5].replace(old, new), c[6])
            NEWF[(table, name)] = ("CHANGED", why, _ag(agents))
            return
    raise KeyError((table, name))


# ---- claim
newcol("claim", "signature_on_file", "CHAR(1)", "Y, N or U (unknown): the provider's signature is on file, as the 837 states.", "Unknown (U)",
       "Claims without a signature on file can be rejected or denied. The 837 already carries it.", "Mirror")
newcol("claim", "onset_date", "DATE", "Date the condition began, when the claim states one.", "Blank",
       "Coding review needs the onset date to judge whether the diagnosis and visit type fit.", "Code Whisperer")
newcol("claim", "late_filing_reason", "VARCHAR(30)", "Documented reason a late claim is still acceptable (for example payer error, coverage dispute).", "Blank",
       "Tells a late claim that is still payable apart from one that is lost; without it every late claim looks the same.", "Mirror")
# ---- transactions
newcol("transactions", "remark_code_id", "INT", "Remark (RARC) that explains an adjustment or denial further.", "Blank",
       "A denial reason alone often cannot be fixed; the remark says what is missing. Reached from a denial through denial.transaction_id.", "Advocate", link="remark_code")
# ---- authorization
newcol("authorization", "units_requested", "INT", "Units or visits the practice asked for.", "Blank",
       "Only the approved and used units were held, so 'approved fewer than requested' could not be seen. It is a common cause of later denials.", "Permit Clerk")
newcol("authorization", "place_of_service_id", "INT", "Place-of-service code on the request (for example 11 office, 22 outpatient hospital).", "Blank",
       "Payers approve an authorization for one setting and deny when the claim's setting differs; facility alone does not give the code the payer checks.", "Permit Clerk", link="place_of_service")
# ---- reference tables
newcol("cpt_code", "unit_limit_basis", "VARCHAR(20)", "How the unit limit applies: per line, per day or per date of service.", "Blank",
       "unit_limit_per_day holds the number; without the basis the limit cannot be tested correctly.", "Mirror")
newcol("payer", "filing_clock_basis", "VARCHAR(30)", "Which date starts the timely-filing clock: service date, discharge date, claim received and so on.", "Service date",
       "filing_days is the limit; without the start date the deadline cannot be worked out.", "Mirror")
# ---- agent_decision
newcol("agent_decision", "recheck_condition", "VARCHAR(100)", "What must be true for this decision to count as closed (for example task done and the rules pass again).", "Blank",
       "Every agent closes its cards only after a re-check; the condition was only in the agent's own notes.",
       "Advocate, Auditor, Bookkeeper, Captain, Coach, Concierge, Courier, Credentialing, Detective / Scout, Hunter, Mirror")
newcol("agent_decision", "recheck_result", "VARCHAR(20)", "Result of the re-check: passed, failed or pending.", "Pending",
       "Shows whether a card actually cleared, not only that a person closed it. The human outcome is held separately.",
       "Advocate, Auditor, Bookkeeper, Captain, Coach, Concierge, Courier, Credentialing, Detective / Scout, Hunter, Mirror")
newcol("agent_decision", "prompt_hash", "VARCHAR(64)", "Hash of the prompt sent to the model for this decision. Blank when no model was used.", "Blank",
       "Proves exactly what the model was asked, without keeping the text (which is built from payer code, CARC, CPT codes and amounts only).", "Advocate, Auditor")
# ---- agent_finding
newcol("agent_finding", "suggested_value", "VARCHAR(100)", "What the agent suggests (for example a visit code and diagnoses).", "Blank",
       "Coding review compares what was billed with what is suggested; this held only as free text before.", "Code Whisperer")
newcol("agent_finding", "final_value", "VARCHAR(100)", "What the person finally approved.", "Blank",
       "Shows how often suggestions are accepted or changed.", "Code Whisperer")
newcol("agent_finding", "value_difference", "DECIMAL(12,2)", "Dollar difference at the contract rate between what was billed and what is suggested.", "Blank",
       "Sizes the opportunity or the over-coding exposure in dollars.", "Code Whisperer")
newcol("agent_finding", "is_compliance_risk", "BIT", "1 when the finding is an over-coding risk; 0 when it is an opportunity.", "0",
       "Separates compliance exposure from missed revenue so the two are never mixed in one total.", "Code Whisperer")
newcol("agent_finding", "predicted_probability", "DECIMAL(5,4)", "Predicted chance that the claim is denied.", "Blank",
       "The claim twin's main output; lets us check later whether predictions came true.", "Mirror")
newcol("agent_finding", "predicted_reason_category", "VARCHAR(30)", "Most likely denial reason group.", "Blank",
       "Tells the team what to fix before the claim goes out.", "Mirror")
newcol("agent_finding", "predicted_allowed_amount", "DECIMAL(12,2)", "Allowed amount the twin expects.", "Blank",
       "Compared with the real allowed amount to find underpayment and to test the twin.", "Mirror")
newcol("agent_finding", "predicted_patient_responsibility", "DECIMAL(12,2)", "Copay, coinsurance and deductible the twin expects the patient to owe.", "Blank",
       "Feeds the patient estimate and is checked against the real patient amount.", "Mirror")
# ---- agent_task
newcol("agent_task", "minutes_spent", "INT", "Minutes a person spent on the item.", "Blank",
       "Workload and cost per task; the only way to show hours saved.", "Captain")
newcol("agent_task", "contact_channel", "VARCHAR(30)", "How the payer was reached: portal, phone, fax, clearinghouse, EMR inbox.", "Blank",
       "Shows which route actually gets answers, and how often manual calls are still needed.", "Detective / Scout, Hunter")
newcol("agent_task", "escalation_level", "SMALLINT", "0 provider, 1 provider again, 2 practice manager, 3 medical director.", "0",
       "Shows how far a stuck item climbed before it was done. Levels still to be confirmed.", "Note Chaser")
newcol("agent_task", "reminder_count", "SMALLINT", "How many reminders were sent for the item.", "0",
       "Measures chasing effort and which items need more than one reminder.", "Note Chaser")
# ---- description change
retext("claim_status_history", "status_code", "Payer status code from the 277.", "Payer status code from the 277. For ack_999 events it holds A (accepted), E (accepted with errors) or R (rejected).",
       "The 999 acceptance code had no column, so 'accepted with errors' would have been lost.", "Courier")

# ---- planned tables and settings
TBD = [(r[0], r[1], r[2], r[3], r[4], r[5] + ("; trace_number (270/271 reference, TRG + appointment id)" if r[0] == "eligibility_check" else ""), r[6]) for r in TBD]
TBD.append(("patient_contact_preference", "3", "Patient contact consent and preferences as flags only: channel, quiet hours, text consent, opt-out, authorized representative, guarantor (hashed). No phone numbers or addresses.",
            "Optional", "Statements and reminders that respect consent", "patient (language), payment_plan (autopay)", "Not available; Concierge outreach waits for this table"))
SETTINGS.append(("Clearinghouse interchange IDs (sender and receiver)", "Per connection", "practice_settings"))
NEWLIST = sorted(NEWF.items())
# ======================= PLANNED-TABLE REVIEW: tables designed by four design modules (plan/plan_A..D.py)
import os as _os
PLAN_NEW = "New: designed this round, not yet reviewed"
PLAN_REMAP = {}   # module letter -> REMAP dict
PLAN_DONE = []
_PD = _os.path.join(HERE, "plan")
for _k in "".join(c for c in "ABCD" if c not in _os.environ.get("KRISNNAI_SKIP_PLAN", "")):  # test_plan.py skips the module under test
    _before = set(T)
    _path = _os.path.join(_PD, f"plan_{_k}.py")
    exec(compile(open(_path, encoding="utf-8").read(), _path, "exec"), globals())
    for _n in T:
        if _n not in _before:
            T[_n]["status"] = PLAN_NEW
    PLAN_REMAP[_k] = dict(REMAP)
    PLAN_DONE += list(TBD_DONE)
TBD = [r for r in TBD if r[0] not in PLAN_DONE]
PLAN_TABLES = [n for n in T if T[n]["status"] == PLAN_NEW]

# ======================= LOCKED-TABLE CHANGES approved after the planned-table review, then everything locked
_RULE_AGENTS = "Advocate, Bookkeeper, Captain, Coach, Code Whisperer, Concierge, Courier, Hunter, Mirror, Permit Clerk"
newcol("appointment", "referral_id", "BIGINT", "The referral this visit was booked under, when there is one.", "Blank",
       "Visits used on a referral can be counted from the visits themselves, not guessed from dates.", "Note Chaser", link="referral")
newcol("encounter", "referral_id", "BIGINT", "The referral this visit was performed under, when there is one.", "Blank",
       "Visits used on a referral can be counted from the visits themselves, not guessed from dates.", "Note Chaser", link="referral")
newcol("agent_decision_details", "payer_rule_id", "BIGINT", "The exact version of the payer rule this check ran against.", "Blank",
       "rule_code alone does not say which version of the rule was in force; this pins it so a decision can be replayed and audited.", _RULE_AGENTS, link="payer_rule")


def relink_staff(table, name, why, agents):
    cols = T[table]["cols"]
    for k, c in enumerate(cols):
        if c[0] == name:
            cols[k] = (c[0], "BIGINT", c[2], "staff", c[4], c[5].rstrip(".") + ". Holds the staff_id of the pseudonymous person.", c[6])
            NEWF[(table, name)] = ("CHANGED", why, _ag(agents))
            return
    raise KeyError((table, name))


_W = "Was free text; now a staff_id link, so the approval trail and workload join to the staff table and one person is always the same person."
relink_staff("transactions", "approved_by", _W, "Captain")
relink_staff("bill_details", "change_approved_by", _W, "Captain")
relink_staff("practice_settings", "approved_by", _W, "Captain")
relink_staff("agent_approval", "approved_by", _W, "Advocate, Auditor, Captain, Coach, Code Whisperer, Concierge, Courier, Credentialing, Detective / Scout, Mirror, Note Chaser")
relink_staff("agent_task", "assigned_to", _W, "Advocate, Bookkeeper, Captain, Courier, Hunter, Mirror")
NEWLIST = sorted(NEWF.items())

# lock everything
for _n in PLAN_TABLES:
    T[_n]["status"] = LOCKED
PLAN_TABLES_ALL = list(PLAN_TABLES)
PLAN_TABLES = []

# ======================= ID TYPES: one rule so every link can be a real foreign key
# Small lookup tables get INT keys; every column that links to a table takes the type of that table's key.
SMALL_REF = ["practice", "provider", "payer", "specialty", "cpt_code", "diagnosis_code", "modifier", "facility", "place_of_service", "adjustment_reason", "remark_code", "fee_list"]
for _n in SMALL_REF:
    _c = T[_n]["cols"][0]
    T[_n]["cols"][0] = (_c[0], "INT") + _c[2:]
ID_FIXED = []
for _n, _t in T.items():
    for _k, _c in enumerate(_t["cols"]):
        if _c[3] and _c[3] in T and _c[1] != T[_c[3]]["cols"][0][1]:
            ID_FIXED.append((_n, _c[0], _c[1], T[_c[3]]["cols"][0][1]))
            _t["cols"][_k] = (_c[0], T[_c[3]]["cols"][0][1]) + _c[2:]

# =============================================================================================== WORKBOOK
wb = Workbook()


def H(ws, row, labels, widths):
    for i, h in enumerate(labels, 1):
        c = ws.cell(row=row, column=i, value=h); c.font = Font(name=F, bold=True, color="FFFFFF", size=10); c.fill = PatternFill("solid", fgColor=NAVY); c.border = BD; c.alignment = Alignment(wrap_text=True, vertical="center")
    for i, w in enumerate(widths, 1): ws.column_dimensions[get_column_letter(i)].width = w


def R(ws, r, vals, fills=()):
    for i, v in enumerate(vals, 1):
        c = ws.cell(row=r, column=i, value=v); c.font = Font(name=F, size=10); c.border = BD; c.alignment = Alignment(wrap_text=True, vertical="top")
    for col in fills:
        f = PFILL.get(str(vals[col - 1])) or SFILL.get(str(vals[col - 1]))
        if f: ws.cell(row=r, column=col).fill = PatternFill("solid", fgColor=f)


def title(ws, t, n):
    ws["A1"] = t; ws["A1"].font = Font(name=F, bold=True, size=14, color=NAVY); ws["A2"] = n; ws["A2"].font = Font(name=F, italic=True, size=10, color="595959")


order = ["1 Appointment", "2 Encounter", "3 Bill and claim", G4, GA, "Reference", "Data operations"]
def sortkey(n):
    d = T[n]; g = order.index(d["group"]) if d["group"] in order else 9
    return (g, 0 if d["pair"] in ("header", "ledger", "reference") else 1, list(T).index(n))
tables = sorted(T, key=sortkey)
ncols = sum(len(d["cols"]) for d in T.values())
new = [n for n in T if T[n]["status"] == NEW]
nref = sum(1 for d in T.values() if d["group"] == "Reference")

ws = wb.active; ws.title = "Read me"
title(ws, "KrisnnAI canonical data model", "A source-neutral model for revenue cycle data. Any EMR, PM, scheduler or clearinghouse feeds the same tables; what a source cannot supply uses a fallback and is flagged.")
H(ws, 4, ["Topic", "Detail"], [30, 160])
info = [
    ("What this is", f"{len(T)} tables ({ncols} columns): {len(T) - nref - 1} journey, event, agent and operations tables, {nref} reference tables, and 1 data registry. Every table is locked: {len(T) - len(PLAN_TABLES_ALL)} were reviewed field by field, one at a time, and the {len(PLAN_TABLES_ALL)} tables designed in the planned-table review ({', '.join(PLAN_TABLES_ALL)}) were locked together."),
    ("Agent-field review", f"After mapping every agent field onto this model, {sum(1 for v in NEWF.values() if v[0]=='NEW')} columns were added (all Optional) and {sum(1 for v in NEWF.values() if v[0]=='CHANGED')} existing columns were reworded or relinked. They are marked in the Columns sheet and listed in the Added in review sheet, each with why it was added and which agents want it."),
    ("The journey", "1 Appointment, 2 Encounter, 3 Bill and claim, 4 Transactions, denials, AR, then 5 Agent outputs (what our agents decide and do). Each stage is a header table plus a detail table (planned, performed, charged, claimed services). A bill is the practice's own charge, with or without a payer; a claim is a request to one payer. Money is a signed ledger (transactions); denials and AR hang off it."),
    ("Two IDs in every table", "<table>_id is an internal identity ID: every join uses it. <table>_number is the client's own ID in a restricted column. Analytics never need the client number, so it never has to be masked in reports or logs."),
    ("Restricted columns", "Client numbers, payer claim number, prior authorization numbers, line control numbers, tax ID and hashes of patient and member numbers. Never shown in a report or log. No names, birth dates, addresses or raw member numbers are stored; patient and member numbers are salted hashes created at the loading boundary."),
    ("Change tracking", "Nothing is overwritten on journey tables. A change closes the old row (is_current = 0, replaced_date) and adds a new row whose previous_<table>_id points back. Following the chain decodes every cancellation, reschedule, replacement claim and re-created bill. Counts use is_current = 1."),
    ("Detail rows and new versions", "Default applied, please confirm: when a new version of appointment, encounter or bill is created, its detail rows are copied forward to it (they are small). Claims create their own lines. Denial is the exception: its reasons stay with the first version and later versions point to it by first_denial_id."),
    ("History rules for reference data", "Reference tables are overwritten when they change (every transaction already copies the as-of value). Exceptions that keep effective dates or a version chain: cpt_code, diagnosis_code, modifier, place_of_service, adjustment_reason, remark_code (code sets change yearly), coverage, authorization, fee_list, contract_rate and practice_settings."),
    ("Reference IDs in every table", "Practice, patient, payer, provider, specialty, facility, place of service, procedure code, diagnosis code and modifier appear as _id links wherever a table needs them; detail tables copy practice, patient, payer, provider and specialty from their header. See Where each ID appears."),
    ("Priorities", "Table: Mandatory (cannot compute revenue metrics without it), Important (powers the prevention work), Optional (load if the client has it). Field: Mandatory (row unusable without it), Important (accuracy drops but a fallback exists), Optional. Every table and field lists its fallback."),
    ("Fallbacks and data_feed", "Each table has a ladder of sources from best to weakest. data_feed records, per client and table, which feed exists, from when to when, how complete, and which fallback step is in use. A metric reading a missing feed reports 'unavailable', never zero."),
    ("TBD tables", "Sixteen further tables are reserved and not yet designed (see the TBD tables sheet), with the columns in the locked tables where each will plug in."),
    ("Not in this model", "Agent input views (they are built from these tables and hold nothing new). Bank deposits (agreed not needed). Note text and clinical content (only status, dates, counts and a hash)."),
    ("Caveats", "A design on paper: no SQL has been run, and no real EMR or PM has been mapped against it yet; the Source compatibility sheet states the intended mapping. Code sets must be loaded. Standards details come from general knowledge. Demo data is synthetic."),
]
for i, r_ in enumerate(info, 5): R(ws, i, r_)

ws = wb.create_sheet("Tables")
title(ws, "Tables", "Journey, event and operations tables first, then reference tables. Status shows what has been reviewed.")
H(ws, 4, ["Order", "Table", "Group", "Kind", "What one row is", "Priority", "Status", "Why it exists", "Metrics served", "Fallback ladder (best to weakest)"], [7, 24, 22, 12, 52, 12, 24, 58, 58, 66])
for n, name in enumerate(tables, 1):
    d = T[name]; R(ws, 4 + n, [n, name, d["group"], d["pair"], d["what"], d["priority"], d["status"], d["purpose"], d["metrics"], d["fallback"]], (6, 7))
ws.freeze_panes = "C5"; ws.auto_filter.ref = f"A4:J{4 + len(tables)}"

ws = wb.create_sheet("Columns")
title(ws, "Columns", "Every column: type, priority, link, why we need it, and what to use if the source does not send it. Restricted = never shown in reports or logs.")
H(ws, 4, ["Table", "Column", "Type", "Priority", "Links to", "Restricted", "Why we need it", "If the source does not send it", "In review", "Why added or changed, and which agents want it"], [24, 30, 16, 12, 22, 11, 80, 56, 11, 90])
r = 5
for name in tables:
    for (c, typ, pri, link, restricted, desc, fb) in T[name]["cols"]:
        nf = NEWF.get((name, c))
        R(ws, r, [name, c, typ, pri, link, "yes" if restricted else "", desc, fb, nf[0] if nf else "", (nf[1] + " Wanted by: " + nf[2]) if nf else ""], (4,))
        if nf:
            for cc in range(1, 11):
                ws.cell(r, cc).fill = PatternFill("solid", fgColor="FFF2CC")
        r += 1
ws.freeze_panes = "C5"; ws.auto_filter.ref = f"A4:J{r-1}"

ws = wb.create_sheet("Added in review")
title(ws, "Added in review", "Columns added (NEW) or reworded (CHANGED) after mapping every agent field onto the model. Why it was needed and which agents want it.")
H(ws, 4, ["Table", "Column", "Type", "Priority", "In review", "Why it was added or changed", "Agents that want it"], [24, 30, 16, 12, 11, 90, 70])
colinfo = {(n, c[0]): c for n in T for c in T[n]["cols"]}
for k, ((tb, cn), (kind, why, ags)) in enumerate(NEWLIST, 5):
    ci = colinfo[(tb, cn)]
    R(ws, k, [tb, cn, ci[1], ci[2], kind, why, ags], (4,))
ws.freeze_panes = "C5"

ws = wb.create_sheet("Where each ID appears")
title(ws, "Where each reference ID appears", "For each reference table, the column that carries it in every other table. Blank = that table does not need it.")
nonref = [n for n in tables if T[n]["group"] != "Reference"]
refs = [n for n in tables if T[n]["group"] == "Reference"]
H(ws, 4, ["Reference table", *nonref], [22] + [24] * len(nonref))
for i, ref in enumerate(refs, 5):
    R(ws, i, [ref] + [", ".join(c[0] for c in T[n]["cols"] if c[3] == ref) for n in nonref])
ws.freeze_panes = "B5"

ws = wb.create_sheet("Source compatibility")
title(ws, "Fitting any EMR, PM or clearinghouse", "Which source usually fills which tables, and how client identifiers are handled. Intended mapping; not yet proven against a real system.")
H(ws, 4, ["Source type", "What it typically supplies", "Tables it fills", "Identifiers", "Known gaps"], [32, 62, 70, 52, 60])
for i, r_ in enumerate(SOURCES, 5): R(ws, i, r_)

ws = wb.create_sheet("TBD tables")
title(ws, "TBD tables (reserved, not yet designed)", "To discuss after the tables requested so far. The right column shows where each will plug into the locked tables, so nothing needs re-working.")
H(ws, 4, ["Table", "Phase", "What it would hold", "Tier", "What it would enable", "Plugs into (already reserved)", "Until then"], [24, 8, 62, 22, 52, 62, 44])
for i, r_ in enumerate(TBD, 5): R(ws, i, r_)

ws = wb.create_sheet("Settings catalog")
title(ws, "Starting values for practice_settings", "Built-in defaults used when a client sets nothing. 'As built' = taken from the working code; others are placeholders.")
H(ws, 4, ["Setting", "Default", "Used by"], [40, 60, 40])
for i, r_ in enumerate(SETTINGS, 5): R(ws, i, r_)

ws = wb.create_sheet("Change tracking")
title(ws, "How cancellations, reschedules and replacements are held", "Rows are never overwritten. The internal ID chain shows the whole history.")
H(ws, 4, ["Step", "What happens", "appointment_id", "appointment_number (client's)", "status", "is_current", "previous_appointment_id", "appointment_date", "replaced_date"], [6, 60, 16, 22, 14, 11, 22, 16, 14])
for i, v in enumerate([
    (1, "Booked for 4 Nov.", 1001, "A-5521", "booked", 0, "", "2026-11-04", "2026-10-30"),
    (2, "Patient moves it to 9 Nov. The old row closes; a new row points back.", 1002, "A-5521", "booked", 0, 1001, "2026-11-09", "2026-11-07"),
    (3, "On 7 Nov the patient cancels. A new row records the cancellation.", 1003, "A-5521", "cancelled", 1, 1002, "2026-11-09", ""),
    (4, "Rebooked for 20 Nov. The scheduler may reuse the number or issue a new one; the chain links by internal ID either way.", 1004, "A-5530", "booked", 1, 1003, "2026-11-20", ""),
], 5): R(ws, i, v)
c = ws.cell(row=10, column=1, value="Reading the chain: follow previous_appointment_id back from any row to the first booking. The same pattern covers claims (a replacement claim points to the one it replaced), bills (a voided and re-created bill), encounters (a re-opened visit), coverage, authorizations and payments. Counts and rates use is_current = 1; first-pass metrics read the first row of each chain.")
c.font = Font(name=F, size=10); c.alignment = Alignment(wrap_text=True, vertical="top"); ws.merge_cells("A10:I12")

ws = wb.create_sheet("Allowed values")
title(ws, "Allowed values for coded columns", "Short coded lists kept as text on the row, so there is no extra lookup table for them.")
H(ws, 4, ["Column", "Allowed values"], [38, 140])
for i, v in enumerate(ALLOWED, 5): R(ws, i, v)

wb.save(OUT)
print("saved", OUT)
print("tables", len(T), "| columns", ncols, "| reference", nref, "| new", new)
cnt = collections.Counter(d["priority"] for d in T.values()); print(dict(cnt))
txt = " ".join(str(v) for w in wb for row in w.iter_rows(values_only=True) for v in row if isinstance(v, str))
print("tag words:", len(re.findall(r"(?i)\b(fact|facts|dim|dimension|dimensions)\b|fact_|dim_", txt)))
