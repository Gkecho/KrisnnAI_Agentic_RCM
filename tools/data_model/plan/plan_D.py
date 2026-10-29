# Agent K=D: appeal, patient_statement, payment_plan, patient_contact_preference, payment_adjustment
TBD_DONE = ["appeal", "patient_statement", "payment_plan", "patient_contact_preference", "payment_adjustment"]


def _copies():
    return [L("practice_id", "INT", I_, "practice", "Copied, so reports by practice never join up.", "Always set by us"),
            L("patient_id", "BIGINT", I_, "patient", "Copied from the denial.", "From the denial"),
            L("payer_id", "INT", I_, "payer", "Copied, so win rates by payer need no join.", "From the denial")]


# ------------------------------------------------------------------------------------------ appeal
add("appeal", I_, G4, "event",
    "One appeal filed (or being prepared) against one denial at one level: first appeal, second appeal or external review. A status change is a new version.",
    "Today the denial table keeps only one outcome per denial. A denial can be appealed more than once, and the Advocate and Auditor need the clock, deadline, amount disputed, evidence count, payer case number and result of each round. The denial row keeps the final outcome; this table keeps the rounds behind it.",
    "Overturn rate by payer, reason and level, appeal cycle time, appeals sent before deadline, amount disputed vs recovered, appeals per denial, win history (earlier same payer and reason appeals that were won)",
    "1 appeal worklist or PM appeal log, 2 payer portal or 835/277 follow-up with the payer case number, 3 rebuilt from denial (outcome, appeal_deadline, resubmitted_claim_id) as one row per denial, level first",
    common("appeal") + [
        L("appeal_number", "VARCHAR(50)", O_, "", "The practice's own appeal tracking number, if it has one. Restricted.", "Blank", True),
        L("denial_id", "BIGINT", M_, "denial", "The denial being appealed. Every appeal belongs to one denial.", "Always set by us"),
        L("appeal_level", "VARCHAR(15)", M_, "", "First, second or external_review.", "First"),
        L("appeal_status", "VARCHAR(12)", M_, "", "Drafted, approved, sent, answered, closed.", "Drafted"),
        L("clock_start_date", "DATE", M_, "", "Date the payer told the practice about the denial (or the decision on the earlier round). The appeal clock starts here.", "denial.clock_start_date, else denial_date"),
        L("deadline_date", "DATE", M_, "", "Last day to file this appeal, from the payer rule or contract.", "denial.appeal_deadline"),
        L("claim_id", "BIGINT", I_, "claim", "Claim behind the denial, for quick reports.", "From the denial"),
        L("submitted_date", "DATE", I_, "", "Date the appeal went out. Blank while still a draft.", "Blank"),
        L("submission_channel", "VARCHAR(10)", I_, "", "Portal, fax, mail, 275 or FHIR.", "Portal"),
        L("amount_disputed", "DECIMAL(12,2)", I_, "", "Dollars actually disputed in this round. Can be less than the denied amount.", "denial.denied_amount"),
        L("evidence_count", "SMALLINT", I_, "", "How many documents were attached (note, authorization, EOB, policy). A count only, never the documents.", "Blank"),
        L("letter_hash", "BINARY(32)", I_, "", "Fingerprint of the final letter after human edits. Proves which letter went out without storing it.", "Blank"),
        L("payer_reference", "VARCHAR(50)", I_, "", "The payer's case or reference number for the appeal. Restricted.", "Blank", True),
        L("decision_date", "DATE", I_, "", "Date the payer answered.", "Blank until answered"),
        L("payer_decision", "VARCHAR(20)", I_, "", "Overturned, partly_overturned, upheld or no_answer.", "Blank until answered"),
        L("is_overturned", "BIT", I_, "", "1 if the denial was overturned in this round (fully or partly). Yes/no outcome used in overturn rate.", "Derived from payer_decision"),
        L("recovered_amount", "DECIMAL(12,2)", I_, "", "Dollars recovered from this round, from the ledger.", "Blank"),
        L("agent_decision_id", "BIGINT", I_, "agent_decision", "The agent decision that drafted the appeal.", "Blank"),
        L("agent_approval_id", "BIGINT", I_, "agent_approval", "The human review that approved the appeal or the write-off instead.", "Blank"),
    ] + _copies() + audit("appeal"))

# ------------------------------------------------------------------------------------------ patient_statement
add("patient_statement", I_, G4, "event",
    "One statement or patient balance notice sent (or tried) to one patient: date, amount shown, channel, dunning level and delivery status. A status change is a new version.",
    "Lets the Concierge know what the patient has already been sent, how many reminders, and how it was delivered, so the next message is right and collection-law timing (validation notice, dispute window) is kept. Replaces the single last_statement_date on ar.",
    "Statements sent, statements per balance, dunning level reached, returned or bounced mail, days from statement to payment, patient collection rate by dunning level, contact attempts in a period",
    "1 PM or statement vendor feed with statement and status events, 2 statement date and amount rebuilt from patient transactions, 3 ar.last_statement_date as a single row",
    common("patient_statement") + [
        L("statement_number", "VARCHAR(50)", O_, "", "The number printed on the statement, if the practice has one. Restricted.", "Blank", True),
        L("patient_id", "BIGINT", M_, "patient", "The patient who got the statement.", "Hash of member ID"),
        L("statement_date", "DATE", M_, "", "Date printed on the statement.", "Send date"),
        L("statement_amount", "DECIMAL(12,2)", M_, "", "Balance shown on the statement.", "Patient balance on the statement date"),
        L("channel", "VARCHAR(10)", M_, "", "Mail, portal, sms, phone or none.", "Mail"),
        L("statement_status", "VARCHAR(12)", M_, "", "Sent, delivered, bounced, returned, disputed, plan or hardship.", "Sent"),
        L("practice_id", "INT", I_, "practice", "Copied, for reports by practice.", "Always set by us"),
        L("bill_id", "BIGINT", I_, "bill", "The bill the balance mostly belongs to. Blank for an account-level statement.", "Blank"),
        L("claim_id", "BIGINT", I_, "claim", "Claim the statement refers to, when the feed gives one.", "Blank"),
        L("due_date", "DATE", I_, "", "Payment due date printed.", "Statement date plus 30 days"),
        L("sent_at", "DATETIME2(0)", I_, "", "When the message actually went out (channel and send time).", "Statement date"),
        L("status_date", "DATE", I_, "", "Date of the latest status (delivered, returned, disputed).", "Statement date"),
        L("dunning_level", "TINYINT", I_, "", "0 first statement, then 1, 2, 3 for each firmer reminder.", "Count of earlier statements for the balance"),
        L("validation_notice_date", "DATE", O_, "", "Date of the Reg F validation notice, if this statement carried one.", "Blank"),
        L("dispute_window_end_date", "DATE", O_, "", "Last day the patient may dispute the debt (Reg F).", "Validation notice date plus 30 days"),
        L("payment_plan_id", "BIGINT", O_, "payment_plan", "The payment plan the patient is on, if any.", "Blank"),
    ] + audit("patient_statement"))

# ------------------------------------------------------------------------------------------ payment_plan
add("payment_plan", I_, G4, "header",
    "One payment plan agreed with a patient: total, instalment size, how many instalments are missed and whether autopay is on. A change is a new version.",
    "Patient balances on a plan behave differently from other patient AR: they pay in small steps and drop out if instalments are missed. The Concierge and the AR forecast need to see plan size, missed instalments and autopay. Instalments themselves are patient payments already in transactions, so there is no instalment table.",
    "Patients on plans, plan balance, missed instalment rate, plan default rate, plans completed, autopay share, expected monthly plan cash",
    "1 PM or billing system plan record, 2 patient payment feed grouped by account with a fixed amount each month, 3 none",
    common("payment_plan") + [
        L("payment_plan_number", "VARCHAR(50)", O_, "", "The practice's own plan number. Restricted.", "Blank", True),
        L("patient_id", "BIGINT", M_, "patient", "The patient who owns the plan.", "Hash of member ID"),
        L("plan_status", "VARCHAR(10)", M_, "", "Active, completed, defaulted or cancelled.", "Active"),
        L("start_date", "DATE", M_, "", "First instalment date or agreement date.", "Date of first payment"),
        L("total_amount", "DECIMAL(12,2)", M_, "", "Balance put on the plan.", "Patient balance at start"),
        L("practice_id", "INT", I_, "practice", "Copied, for reports by practice.", "Always set by us"),
        L("instalment_amount", "DECIMAL(12,2)", I_, "", "Agreed amount per instalment.", "Total amount divided by instalment count"),
        L("instalment_count", "SMALLINT", I_, "", "Number of instalments agreed.", "Blank"),
        L("frequency", "VARCHAR(10)", I_, "", "Weekly, biweekly or monthly.", "Monthly"),
        L("next_due_date", "DATE", I_, "", "Next instalment due date. The AR forecast reads it.", "Last payment date plus one period"),
        L("missed_instalments", "SMALLINT", I_, "", "Instalments missed as known on the row date. Kept because it depends on what was known then.", "Counted from due dates vs payments"),
        L("last_missed_date", "DATE", O_, "", "Due date of the latest missed instalment.", "Blank"),
        L("autopay_enrolled", "BIT", I_, "", "Whether recurring payment is set up. A flag only; card or bank details are never stored.", "0 (not enrolled)"),
        L("end_date", "DATE", O_, "", "Date the plan completed, defaulted or was cancelled.", "Blank while active"),
    ] + audit("payment_plan"))

# ------------------------------------------------------------------------------------------ patient_contact_preference
add("patient_contact_preference", I_, G4, "header",
    "The contact consent and preferences of one patient, as flags only. No phone numbers, emails or addresses. A change (new consent, opt-out) is a new version, so consent history is kept.",
    "Statements and reminders must respect consent (text and auto-dialed call rules, do-not-contact, who may be spoken to). The Concierge reads these flags before any outreach. The actual contact details stay in the practice system; we only know that they exist.",
    "Patients reachable by channel, opt-out rate, text consent coverage, returned-mail rate, outreach blocked by consent, patients with a guarantor or authorized representative",
    "1 PM patient demographics and consent fields reduced to flags, 2 consent captured by the patient portal, 3 none: assume no text consent and mail only",
    common("patient_contact_preference") + [
        L("patient_id", "BIGINT", M_, "patient", "The patient these preferences belong to.", "Hash of member ID"),
        L("opt_out", "BIT", M_, "", "1 if the patient asked not to be contacted. Stops all outreach.", "0"),
        L("text_consent", "BIT", M_, "", "1 if the patient agreed to be texted.", "0 (no consent)"),
        L("preferred_channel", "VARCHAR(10)", I_, "", "Mail, portal, sms or phone.", "Mail"),
        L("quiet_hours_start", "TINYINT", I_, "", "Hour of the day (0 to 23) when contact must stop.", "Blank (practice default)"),
        L("quiet_hours_end", "TINYINT", I_, "", "Hour of the day (0 to 23) when contact may resume.", "Blank (practice default)"),
        L("address_status", "VARCHAR(10)", I_, "", "Valid, returned or unknown: whether mail reaches the patient. The address itself is not stored.", "Unknown"),
        L("has_phone", "BIT", I_, "", "1 if a phone number or email is on file. The value is not stored.", "0"),
        L("autodial_consent", "BIT", I_, "", "1 if the patient agreed to auto-dialed or recorded calls.", "0 (no consent)"),
        L("consent_date", "DATE", I_, "", "Date the latest consent was given.", "Blank"),
        L("consent_source", "VARCHAR(20)", O_, "", "Where consent was captured: form, portal, verbal.", "Blank"),
        L("consent_wording_version", "VARCHAR(10)", O_, "", "Version of the consent wording shown. Needed to prove what the patient agreed to.", "Blank"),
        L("opt_out_date", "DATE", I_, "", "Date the patient opted out.", "Blank"),
        L("has_authorized_rep", "BIT", I_, "", "1 if the patient allows us to talk to a family member or other representative.", "0"),
        L("guarantor_hash", "BINARY(32)", I_, "", "Salted hash of the person billed when it is not the patient. Never the name.", "Blank (patient is the guarantor)", True),
    ] + audit("patient_contact_preference"))

# ------------------------------------------------------------------------------------------ payment_adjustment
add("payment_adjustment", O_, G4, "detail",
    "One provider-level adjustment on a payment that is not tied to a claim: a takeback, interest, recoupment or penalty (the 835 PLB segment).",
    "payment.plb_amount holds only the total. To explain why a deposit is lower or higher than the claims inside it, we need the kinds and amounts behind that total. The sum of these rows must equal payment.plb_amount.",
    "Cash reconciliation (payment amount vs claims plus these rows), recoupments and takebacks by payer, interest received, unexplained payment differences",
    "1 835 PLB segments, 2 PM payment record with adjustment lines, 3 none: only payment.plb_amount",
    common("payment_adjustment") + [
        L("payment_id", "BIGINT", M_, "payment", "The payment (EFT or check) the adjustment came in.", "Always set by us"),
        L("adjustment_type", "VARCHAR(15)", M_, "", "Takeback, recoupment, interest, penalty, bonus or other.", "Other"),
        L("amount", "DECIMAL(12,2)", M_, "", "Signed amount: negative takes money away from the deposit.", "From the source"),
        L("adjustment_date", "DATE", M_, "", "Date of the adjustment (payment date if the source gives none).", "Payment date"),
        L("plb_reason_code", "VARCHAR(5)", I_, "", "The 835 PLB reason code (for example WO for overpayment recovery, L6 for interest).", "Blank"),
        L("practice_id", "INT", I_, "practice", "Copied from the payment.", "From the payment"),
        L("payer_id", "INT", I_, "payer", "Copied from the payment, for takebacks by payer.", "From the payment"),
        L("payee_provider_id", "INT", O_, "provider", "Provider the adjustment applies to, when the payer names one.", "Payment payee"),
    ] + audit("payment_adjustment", False))

# ------------------------------------------------------------------------------------------ REMAP
_A, _S, _P, _C = "appeal", "patient_statement", "payment_plan", "patient_contact_preference"
_fa, _fb, _dc = "fact_appeal_event", "fact_patient_balance_event", "dim_patient_contact"
REMAP = {
    (_fa, "appeal_ref"): (_A, "appeal_id", "Renamed", "Our id for one appeal. A7 and A10 reuse it as the review or dispute reference; the human review link is appeal.agent_approval_id."),
    (_fa, "clock_start_date_key"): (_A, "clock_start_date", "Renamed", "Date the payer told us about the denial."),
    (_fa, "deadline_date_key"): (_A, "deadline_date", "Renamed", "Appeal deadline (A8 and A10)."),
    (_fa, "letter_hash"): (_A, "letter_hash", "Exact", "Fingerprint of the final letter; text itself never stored."),
    (_fa, "appeal_type_key"): (_A, "appeal_level", "Renamed", "First, second, external review."),
    (_fa, "status_key"): (_A, "appeal_status", "Renamed", "Drafted to closed. A8 payer decision and overturned flag use payer_decision and is_overturned (Added)."),
    (_fa, "event_date_key"): (_A, "submitted_date", "Renamed", "Submission date (A8, A10). Payer answer date is decision_date (Added)."),
    (_fa, "channel_key"): (_A, "submission_channel", "Renamed", "Portal, fax, mail, 275, FHIR."),
    (_fa, "payer_reference"): (_A, "payer_reference", "Exact", "Payer case number; restricted."),
    (_fa, "evidence_count"): (_A, "evidence_count", "Exact", "Count of attached documents only."),
    (_fa, "amount_disputed"): (_A, "amount_disputed", "Exact", "Dollars actually disputed."),
    (_fa, "payer_decision"): (_A, "payer_decision", "Added", "Overturned, partly overturned, upheld, no answer; split out of status_key."),
    (_fa, "decision_date"): (_A, "decision_date", "Added", "Date the payer answered; split out of event_date_key."),
    (_fa, "denial_overturned_flag"): (_A, "is_overturned", "Added", "Yes/no outcome per appeal; the denial table keeps the final outcome."),
    (_fb, "channel_key"): (_S, "channel", "Renamed", "Statement channel (mail, portal, sms, phone, none)."),
    (_fb, "status_key"): (_S, "statement_status", "Renamed", "Sent, delivered, bounced, returned, disputed, plan, hardship. Delivery receipt lands here."),
    (_fb, "channel_and_send_time"): (_S, "sent_at", "Added", "Send time chosen; channel is statement.channel."),
    (_fb, "patient_reply_text"): (_S, "", "Dropped", "Free text written by the patient may hold patient content; only the status (for example disputed) is kept."),
    (_dc, "preferred_channel_key"): (_C, "preferred_channel", "Renamed", "Flag only."),
    (_dc, "quiet_hours"): (_C, "quiet_hours_start", "Partial", "Split into quiet_hours_start and quiet_hours_end (hour of day)."),
    (_dc, "address_status"): (_C, "address_status", "Exact", "Valid / returned / unknown; no address stored."),
    (_dc, "has_phone"): (_C, "has_phone", "Exact", "Flag that a phone or email exists; values not stored."),
    (_dc, "text_consent"): (_C, "text_consent", "Exact", "Yes/no; date, source and wording version are consent_date, consent_source, consent_wording_version."),
    (_dc, "autodial_consent"): (_C, "autodial_consent", "Added", "Auto-dialed call consent half of the text/auto-dial field."),
    (_dc, "opt_out"): (_C, "opt_out", "Exact", "Do-not-contact flag; date is opt_out_date."),
    (_dc, "guarantor_ref_hash"): (_C, "guarantor_hash", "Renamed", "Salted hash only."),
    (_dc, "authorized_rep"): (_C, "has_authorized_rep", "Renamed", "Flag only."),
    (_dc, "autopay_enrolled"): (_P, "autopay_enrolled", "Exact", "Autopay flag now on payment_plan (as decided in the gap review)."),
}
