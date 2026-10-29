from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill
from openpyxl.styles.borders import Side
from openpyxl.utils import get_column_letter

F, NAVY = "Arial", "1F3864"
thin = Side(style="thin", color="BFBFBF"); BD = Border(left=thin, right=thin, top=thin, bottom=thin)
M_, I_, O_ = "Mandatory", "Important", "Optional"
PFILL = {M_: "E2EFDA", I_: "FFF2CC", O_: "EDEDED", "Not yet reviewed": "DDEBF7"}

# ---- reference tables (proposed, not yet reviewed). id = internal identity; code = the public or client business code
REFS = {
    "practice": ("practice_id", "Billing entity inside a client (tax ID / group). The client itself is tenant_id.", M_, [("practice_number", "VARCHAR(50)", "Client's code for the practice", True), ("practice_name", "NVARCHAR(200)", "Name", False), ("tax_id", "CHAR(9)", "EIN", True), ("group_npi", "CHAR(10)", "Group NPI", False)]),
    "patient": ("patient_id", "A patient. The client's patient number is stored as a salted hash only.", M_, [("patient_number_hash", "BINARY(32)", "Salted hash of the client's patient number", True), ("age_band", "VARCHAR(10)", "Age band, never a birth date", False), ("sex", "CHAR(1)", "M, F, U", False)]),
    "payer": ("payer_id", "An insurer.", M_, [("payer_code", "VARCHAR(50)", "Public payer ID used by the clearinghouse", False), ("payer_name", "NVARCHAR(200)", "Name", False), ("payer_type", "VARCHAR(20)", "commercial, medicare, medicaid, tricare, workers_comp, auto, self_pay", False), ("filing_days", "SMALLINT", "Timely filing limit", False), ("appeal_days", "SMALLINT", "Appeal window", False)]),
    "provider": ("provider_id", "A clinician or group.", M_, [("npi", "CHAR(10)", "National provider ID (public)", False), ("provider_name", "NVARCHAR(200)", "Name", False), ("specialty_id", "INT", "Main specialty", False), ("provider_type", "VARCHAR(20)", "individual, group", False)]),
    "cpt_code": ("cpt_code_id", "A procedure code (CPT or HCPCS). Code numbers and short own-words labels only; CPT descriptions are AMA-licensed and not stored.", M_, [("code", "VARCHAR(5)", "Procedure code", False), ("code_set_year", "SMALLINT", "Code set year", False), ("category", "VARCHAR(30)", "E/M, radiology, therapy, lab, procedure", False), ("em_level", "TINYINT", "1 to 5 for E/M codes", False), ("unit_limit_per_day", "SMALLINT", "Maximum units per day", False)]),
    "diagnosis_code": ("diagnosis_code_id", "An ICD-10-CM diagnosis code.", M_, [("icd10_code", "VARCHAR(8)", "Diagnosis code", False), ("code_set_year", "SMALLINT", "Code set year", False), ("is_chronic", "BIT", "Chronic condition", False)]),
    "facility": ("facility_id", "A location where service happens.", I_, [("facility_number", "VARCHAR(50)", "Client's location code", False), ("facility_name", "NVARCHAR(200)", "Name", False), ("facility_npi", "CHAR(10)", "Facility NPI", False)]),
    "specialty": ("specialty_id", "A clinical specialty.", I_, [("specialty_code", "VARCHAR(20)", "Specialty or taxonomy group", False), ("specialty_name", "NVARCHAR(100)", "Name", False)]),
    "place_of_service": ("place_of_service_id", "CMS place-of-service code.", I_, [("pos_code", "CHAR(2)", "POS code", False), ("pos_name", "NVARCHAR(100)", "Name", False)]),
    "modifier": ("modifier_id", "A procedure modifier.", I_, [("modifier_code", "CHAR(2)", "Modifier", False), ("modifier_group", "VARCHAR(20)", "pricing, laterality, other", False)]),
    "coverage": ("coverage_id", "One insurance policy for a patient: plan and order of coverage.", I_, [("payer_id", "INT", "Insurer", False), ("plan_type", "VARCHAR(20)", "PPO, HMO, Medicare Advantage ...", False), ("coverage_order", "TINYINT", "1 primary, 2 secondary, 3 tertiary", False), ("relationship_to_holder", "VARCHAR(10)", "self, spouse, child, other", False), ("effective_date", "DATE", "Policy start", False), ("termination_date", "DATE", "Policy end", False), ("member_number_hash", "BINARY(32)", "Salted hash of the member ID", True)]),
    "authorization": ("authorization_id", "A prior authorization as the payer issued it.", I_, [("authorization_number", "VARCHAR(50)", "Number the payer issued", True), ("payer_id", "INT", "Payer", False), ("cpt_code_id", "INT", "Procedure authorized", False), ("valid_from", "DATE", "Approved from", False), ("valid_to", "DATE", "Approved to", False), ("units_approved", "INT", "Units certified", False), ("status", "VARCHAR(20)", "requested, pended, certified, not_certified, expired", False)]),
    "fee_list": ("fee_list_id", "The practice's own fee list: what the provider charges per unit. Billed amount = units x this fee.", I_, [("fee_list_name", "VARCHAR(50)", "Name of the fee list", False), ("cpt_code_id", "INT", "Procedure", False), ("modifier_id", "INT", "Modifier, if the fee depends on it", False), ("fee_per_unit", "DECIMAL(12,2)", "Charge per unit", False), ("effective_from", "DATE", "From", False), ("effective_to", "DATE", "To; blank = open", False)]),
    "adjustment_reason": ("adjustment_reason_id", "A payer adjustment or denial reason (CARC), used by transactions and denials.", I_, [("carc_code", "VARCHAR(10)", "Reason code", False), ("reason_category", "VARCHAR(30)", "How the practice routes it", False), ("is_denial", "BIT", "A denial rather than a contractual or patient adjustment", False)]),
}

# ---- the eight locked tables
S = "source"
def common(t, versioned=True, tenant=True):
    c = [(f"{t}_id", "BIGINT", M_, "", False, "Internal identity ID. Every join and link between tables uses this, so the client's number never has to be shown or masked in analytics.", "Generated by us"),
         ("tenant_id", "INT", M_, "", False, "The client organisation the row belongs to.", "Always set by us")]
    return c


def audit(t, versioned=True):
    c = []
    if versioned:
        c += [("version", "SMALLINT", M_, "", False, "1 for the first row; higher for each change.", "Always set by us"),
              ("is_current", "BIT", M_, "", False, "1 on the latest version. Counts use current rows only.", "Always set by us"),
              (f"previous_{t}_id", "BIGINT", I_, "", False, f"Internal ID of the version this row replaced. Following this chain decodes every cancellation, reschedule or replacement.", "Blank on the first version"),
              ("replaced_date", "DATE", I_, "", False, "Date this version was replaced or ended.", "Blank while current")]
    c += [("source", "VARCHAR(20)", M_, "", False, "Where the row came from: feed, API, PM export, rebuilt from another record.", "Always set by us"),
          ("is_reconstructed", "BIT", M_, "", False, "1 if the row was rebuilt from other data, so reports can mark it less reliable.", "Always set by us"),
          ("known_at", "DATETIME2(0)", M_, "", False, "When the data became known (point in time).", "Always set by us"),
          ("loaded_at", "DATETIME2(0)", M_, "", False, "When the row was loaded.", "Always set by us")]
    return c


def L(name, typ, pri, link, desc, fb, restricted=False):
    return (name, typ, pri, link, restricted, desc, fb)


def copies(spec_provider="provider_id", specialty_pri=I_):
    return [L("practice_id", "INT", I_, "practice", "Copied from the header, so reports by practice never join up.", "Always set by us"),
            L("patient_id", "BIGINT", I_, "patient", "Copied from the header.", "Always set by us"),
            L("payer_id", "INT", I_, "payer", "Copied from the header, as of this stage.", "Always set by us"),
            L(spec_provider, "INT", I_, "provider", "Copied from the header.", "Always set by us"),
            L("specialty_id", "INT", specialty_pri, "specialty", "Copied from the provider's specialty; fast specialty reports.", "From the provider")]


T = {}   # table -> dict(priority, group, purpose, metrics, fallback, cols)

T["appointment"] = dict(priority=I_, group="1 Appointment", pair="header", what="One row per appointment version (a cancel or reschedule keeps the old row and adds a new one).",
    purpose="The booking. Drives the pre-visit eligibility and authorization work, and the no-show and lead-time numbers. Not needed for revenue metrics, so Important, not Mandatory.",
    metrics="No-show rate, cancellation rate, lead time, eligibility-verified-before-visit rate, appointment-to-claim days",
    fallback="1 scheduler API / HL7 / FHIR, 2 PM export, 3 rebuild from encounters (loses booking date, cancels, no-shows, pre-visit work)",
    cols=common("appointment") + [
        L("appointment_number", "VARCHAR(50)", M_, "", "The client's own appointment ID. Restricted: used only to match the source system.", "Hash of patient, provider, date, time", True),
        L("practice_id", "INT", M_, "practice", "Billing entity.", "Client default"), L("patient_id", "BIGINT", M_, "patient", "The patient.", "Hash of member ID"),
        L("appointment_date", "DATE", M_, "", "Visit date; sets the 3-day and 1-day check timing.", "None"),
        L("appointment_status", "VARCHAR(20)", M_, "", "Booked, confirmed, arrived, completed, cancelled, no_show, rescheduled.", "Derived: an encounter exists means completed; date passed with none means no_show (assumed)"),
        L("provider_id", "INT", I_, "provider", "Scheduled provider; utilization and no-shows by provider.", "Practice default"), L("specialty_id", "INT", O_, "specialty", "Specialty of the scheduled provider.", "From the provider"),
        L("payer_id", "INT", I_, "payer", "Insurer on file at booking. Not borrowed from the claim: no claim exists yet, and none ever will for a no-show.", "Payer on the patient's last claim (marked assumed)"),
        L("coverage_id", "INT", I_, "coverage", "The policy the eligibility check will test.", "Patient's current coverage"),
        L("facility_id", "INT", I_, "facility", "Site capacity.", "Practice default"), L("start_time", "TIME(0)", I_, "", "Day utilization and ordering.", "Date only"),
        L("booked_date", "DATE", I_, "", "Lead time; the pre-visit checks key off it.", "First date we saw it"),
        L("appointment_type", "VARCHAR(20)", I_, "", "New, follow_up, procedure, preventive, telehealth, emergency.", "New if no history, else follow_up"),
        L("cancelled_date", "DATE", I_, "", "Cancellation lead time.", "Blank"), L("original_appointment_date", "DATE", I_, "", "Date before any reschedule.", "Derived from the chain"),
        L("reschedule_count", "SMALLINT", I_, "", "How often it moved.", "Count the chain"),
        L("eligibility_state", "VARCHAR(20)", I_, "", "Not checked, verified, problem. Rebuilt from the eligibility records so the front desk board reads one table.", "Rebuild from eligibility records"),
        L("authorization_state", "VARCHAR(20)", I_, "", "Not needed, needed and missing, in place. Rebuilt from authorizations.", "Rebuild from authorizations"),
        L("copay_due", "DECIMAL(12,2)", I_, "", "Expected copay at the visit.", "From the last eligibility answer"),
        L("cancel_reason", "VARCHAR(50)", O_, "", "Cancellation analysis.", "Blank"), L("booked_via", "VARCHAR(20)", O_, "", "Phone, portal, walk-in, referral.", "Blank"),
        L("referring_provider_id", "INT", O_, "provider", "HMO referrals.", "Blank")] + audit("appointment"))

T["appointment_details"] = dict(priority=O_, group="1 Appointment", pair="detail", what="One row per service planned for the appointment.",
    purpose="What is expected at the visit. Optional: most schedulers hold an appointment type, not a procedure. Where missing, a typical code is inferred and marked.",
    metrics="Authorization coverage before the visit, patient estimate, revenue forecast from the schedule, planned-versus-performed drift",
    fallback="1 scheduler procedure, 2 typical code per appointment type (inferred), 3 patient's most frequent code (inferred)",
    cols=common("appointment_detail") + [
        L("appointment_id", "BIGINT", M_, "appointment", "Ties the planned service to its appointment.", "Always set by us"), L("line_number", "SMALLINT", M_, "", "Position within the appointment.", "Order in the feed")]
        + copies("provider_id", O_) + [
        L("planned_cpt_code_id", "INT", I_, "cpt_code", "Drives the authorization check, patient estimate and eligibility service type.", "Typical code for the appointment type (inferred)"),
        L("is_inferred", "BIT", M_, "", "Whether the planned code was given or guessed, so a guess is never treated as known.", "Always set by us"),
        L("planned_units", "DECIMAL(7,2)", I_, "", "Units for the estimate.", "1"),
        L("expected_charge", "DECIMAL(12,2)", I_, "", "Units x the fee list; estimate and forecast.", "Fee list, else payer's typical charge"),
        L("expected_allowed", "DECIMAL(12,2)", I_, "", "Contract rate; estimates the patient's share.", "Payer's typical allowed amount"),
        L("auth_required", "VARCHAR(10)", I_, "", "Yes, no, unknown. Unknown is never read as no.", "Unknown"),
        L("authorization_id", "BIGINT", O_, "authorization", "Authorization on file.", "Match on patient, code, dates"),
        L("planned_diagnosis_code_id", "INT", O_, "diagnosis_code", "Some referrals and authorizations need it.", "Patient's recent diagnoses"),
        L("planned_provider_id", "INT", O_, "provider", "When a different provider performs the service.", "Appointment's provider"),
        L("room_or_equipment", "VARCHAR(50)", O_, "", "Capacity planning.", "Blank"), L("duration_minutes", "SMALLINT", O_, "", "Slot length.", "Blank")] + audit("appointment_detail", False))

T["encounter"] = dict(priority=I_, group="2 Encounter", pair="header", what="One row per visit version.",
    purpose="The visit that happened. Powers documentation, coding and charge-capture work. Revenue metrics work without it, so Important.",
    metrics="Visits per provider, bill lag, signature lag, documentation completeness, missed charges, appointment-to-visit conversion, payer mix, telehealth share",
    fallback="1 EHR (FHIR / REST / HL7), 2 PM visit or charge export, 3 rebuild from claims (loses notes, status, time), 4 completed appointment as a stand-in",
    cols=common("encounter") + [
        L("encounter_number", "VARCHAR(50)", M_, "", "The client's own visit ID. Restricted.", "Hash of patient, provider, date", True),
        L("practice_id", "INT", M_, "practice", "Billing entity.", "Client default"), L("patient_id", "BIGINT", M_, "patient", "The patient.", "Hash of member ID"),
        L("encounter_date", "DATE", M_, "", "Date of service; bill lag and timely filing start here.", "Claim or charge date"),
        L("rendering_provider_id", "INT", M_, "provider", "Who saw the patient; productivity and documentation owner.", "Billing provider"),
        L("encounter_status", "VARCHAR(20)", M_, "", "In progress, completed, note pending, signed, charge ready.", "Derived from whether a note and charge exist"),
        L("appointment_id", "BIGINT", I_, "appointment", "Appointment-to-visit conversion. Blank for walk-ins.", "Match on patient, provider, date"),
        L("payer_id", "INT", I_, "payer", "Insurer at the visit; eligibility on the date of service.", "Appointment's payer, then last claim's"),
        L("coverage_id", "INT", I_, "coverage", "The policy in force at the visit.", "Appointment's coverage"),
        L("facility_id", "INT", I_, "facility", "Site reporting.", "Practice default"), L("place_of_service_id", "INT", I_, "place_of_service", "Pricing differences.", "Office (11)"),
        L("specialty_id", "INT", I_, "specialty", "Specialty reports.", "From the provider"),
        L("encounter_type", "VARCHAR(20)", I_, "", "New, established, preventive, emergency, telehealth; sets the expected visit level.", "From appointment type or code family"),
        L("visit_minutes", "SMALLINT", I_, "", "Time-based coding; productivity.", "Minutes in the note"),
        L("note_status", "VARCHAR(20)", I_, "", "None, draft, signed, amended. Counts only, never note text. Rebuilt from the note records.", "Blank; the documentation agent cannot run without it"),
        L("note_signed_date", "DATE", I_, "", "Signature timing.", "Blank"), L("signature_lag_days", "SMALLINT", I_, "", "Visit to signed note.", "Derived"),
        L("elements_documented", "TINYINT", I_, "", "Count of note elements present; documentation completeness.", "Blank"),
        L("charge_status", "VARCHAR(20)", I_, "", "Not entered, entered, held, billed. Detects bill lag and missed charges.", "Whether a bill exists"),
        L("coding_status", "VARCHAR(20)", I_, "", "Not reviewed, suggested, accepted, changed.", "Not reviewed"),
        L("principal_diagnosis_code_id", "INT", I_, "diagnosis_code", "Condition-level analysis; the line-level diagnoses are in the details.", "First diagnosis in the details"),
        L("authorization_id", "BIGINT", I_, "authorization", "Ties the visit to its authorization.", "Match on patient, code, dates"),
        L("supervising_provider_id", "INT", O_, "provider", "Supervised visits.", "Blank"), L("referring_provider_id", "INT", O_, "provider", "HMO referrals.", "Blank")] + audit("encounter"))

T["encounter_details"] = dict(priority=I_, group="2 Encounter", pair="detail", what="One row per service performed at the visit.",
    purpose="What was done. The place where missed charges, over- and under-coding, and missing laterality are found.",
    metrics="Procedure volume and mix by provider, visit level vs what the note supports, missing laterality or modifier rate, procedures with no documentation, missed charges, time vs units, authorization coverage, planned vs performed drift",
    fallback="1 EHR procedures / charge capture, 2 PM charge entry lines, 3 rebuild from claim lines, 4 single inferred line from the visit type",
    cols=common("encounter_detail") + [
        L("encounter_id", "BIGINT", M_, "encounter", "Ties each performed service to its visit.", "Always set by us"), L("line_number", "SMALLINT", M_, "", "Position within the visit.", "Order in the feed")]
        + copies("provider_id") + [
        L("cpt_code_id", "INT", M_, "cpt_code", "The service performed, as entered. The coder's suggestion lives in the coding review records; the final code sits on the bill line.", "Bill or claim line code (rebuilt)"),
        L("units", "DECIMAL(7,2)", M_, "", "Quantity performed.", "1"),
        L("service_date", "DATE", I_, "", "Per-line date for multi-day services.", "Encounter date"),
        L("rendering_provider_id", "INT", I_, "provider", "When another clinician performed this line.", "Encounter provider"),
        L("diagnosis_1_id", "INT", I_, "diagnosis_code", "Main diagnosis supporting this service; medical-necessity checks.", "Encounter's principal diagnosis"),
        L("diagnosis_2_id", "INT", O_, "diagnosis_code", "Second diagnosis.", "Blank"), L("diagnosis_3_id", "INT", O_, "diagnosis_code", "Third diagnosis.", "Blank"), L("diagnosis_4_id", "INT", O_, "diagnosis_code", "Fourth diagnosis.", "Blank"),
        L("modifier_1_id", "INT", I_, "modifier", "Pricing and common denial causes.", "Blank (coding agent flags gaps)"), L("modifier_2_id", "INT", I_, "modifier", "Second modifier.", "Blank"),
        L("laterality", "CHAR(1)", I_, "", "Left, right, both. Required for many codes; a common denial.", "Blank (flagged)"),
        L("procedure_documented", "BIT", I_, "", "Whether the note supports the procedure. Worked out from the note records.", "Unknown"),
        L("documented_level", "TINYINT", I_, "", "Visit level (1 to 5) the note supports; compared with the level entered. A number only.", "Unknown"),
        L("time_minutes", "SMALLINT", I_, "", "Units for timed codes.", "Use units"),
        L("authorization_id", "BIGINT", I_, "authorization", "Authorization coverage per service.", "Match on patient, code, dates"),
        L("auth_required", "VARCHAR(10)", I_, "", "Yes, no, unknown.", "Unknown"),
        L("line_status", "VARCHAR(20)", I_, "", "Performed, ordered, not done.", "Performed"),
        L("expected_charge", "DECIMAL(12,2)", I_, "", "Units x fee list; the missed-charge value.", "Fee list"),
        L("place_of_service_id", "INT", O_, "place_of_service", "When different from the visit.", "Visit's"), L("ordering_provider_id", "INT", O_, "provider", "Who ordered it.", "Blank"),
        L("drug_code", "VARCHAR(11)", O_, "", "Drug-billing specialties.", "Blank")] + audit("encounter_detail", False))

T["bill"] = dict(priority=I_, group="3 Bill", pair="header", what="One row per bill, normally one per visit. Late charges are added as lines.",
    purpose="What the practice charged, whether or not a payer is ever asked. A bill can become one claim, several claims, a patient statement, or nothing.",
    metrics="Bill lag, documentation-to-ready lag, bill-to-claim lag, charges not yet claimed, held charges by reason, gross charges, encounters with no bill, self-pay share, expected revenue",
    fallback="1 PM charge export, 2 EHR charge items, 3 rebuild from claims (loses bill lag and holds), 4 expected charges from encounter_details (no entered date)",
    cols=common("bill") + [
        L("bill_number", "VARCHAR(50)", M_, "", "The client's own charge or bill ID. Restricted.", "Visit ID plus a sequence", True),
        L("practice_id", "INT", M_, "practice", "Billing entity.", "Client default"), L("patient_id", "BIGINT", M_, "patient", "The patient.", "Hash of member ID"),
        L("encounter_id", "BIGINT", M_, "encounter", "Ties the bill to the visit.", "Match on patient, provider, date"),
        L("service_date", "DATE", M_, "", "Start of bill lag and timely filing.", "Encounter or claim date"),
        L("charge_entered_date", "DATE", M_, "", "First entry. Bill lag is this minus the service date.", "PM posting date, or the claim's creation date"),
        L("bill_status", "VARCHAR(20)", M_, "", "Drafted, held, ready, billed, partly_billed, patient_billed, written_off, voided. Worked out, not typed.", "Derived from whether a claim exists"),
        L("bill_type", "VARCHAR(20)", M_, "", "Insurance, self_pay, courtesy, workers_comp_or_auto. Explains why some bills never become a claim.", "Insurance if a payer exists, else self_pay"),
        L("total_billed", "DECIMAL(12,2)", M_, "", "Gross charges: sum of lines.", "Sum of the bill lines"),
        L("billing_provider_id", "INT", I_, "provider", "Billing enrollment; charges by provider.", "Practice default"), L("rendering_provider_id", "INT", I_, "provider", "Who performed the service.", "Encounter provider"),
        L("specialty_id", "INT", I_, "specialty", "Specialty reports.", "From the provider"),
        L("payer_id", "INT", I_, "payer", "Where the bill will go first.", "Encounter's payer"), L("coverage_id", "INT", I_, "coverage", "Policy to bill.", "Encounter's coverage"),
        L("facility_id", "INT", I_, "facility", "Site reporting.", "Practice default"), L("place_of_service_id", "INT", I_, "place_of_service", "Pricing.", "Office (11)"),
        L("ready_to_bill_date", "DATE", I_, "", "When the note is signed and coding is done. Splits bill lag into documentation delay and billing delay.", "Same as the charge entered date"),
        L("hold_reason", "VARCHAR(30)", I_, "", "Missing note, authorization, coding or diagnosis.", "Blank (agents derive it)"), L("hold_date", "DATE", I_, "", "When the hold began.", "Blank"),
        L("last_charge_date", "DATE", I_, "", "Late charges added after the first entry.", "First entry date"),
        L("claims_created", "SMALLINT", I_, "", "Claim rollup: shows billed-but-not-claimed. Rebuilt from the claim table.", "Rebuild from claims"),
        L("latest_claim_status", "VARCHAR(20)", I_, "", "Claim rollup.", "Rebuild from claims"), L("first_claim_submitted_date", "DATE", I_, "", "Bill-to-claim lag.", "Rebuild from claims"),
        L("expected_allowed", "DECIMAL(12,2)", I_, "", "Expected revenue before payment.", "Payer's typical allowed amount"),
        L("entered_by_role", "VARCHAR(30)", O_, "", "Productivity by role.", "Blank"), L("no_charge_amount", "DECIMAL(12,2)", O_, "", "Courtesy or write-off before a claim.", "Blank"),
        L("patient_statement_flag", "BIT", O_, "", "Billed to the patient.", "Blank")] + audit("bill"))

T["bill_details"] = dict(priority=I_, group="3 Bill", pair="detail", what="One row per charge line on a bill.",
    purpose="The final, priced charge line after coding. The first place a dollar amount appears: units x the fee.",
    metrics="Gross charges by procedure/provider/payer, billed vs contract gap, charge capture rate, unclaimed lines and dollars, coding change rate, late charges, modifier and laterality coverage, fee list compliance",
    fallback="1 PM charge lines, 2 EHR charge items, 3 rebuild from claim lines (loses entered dates and holds), 4 planned charges from encounter_details x fee list (expected only)",
    cols=common("bill_detail") + [
        L("bill_id", "BIGINT", M_, "bill", "Ties the charge to its bill.", "Always set by us"), L("line_number", "SMALLINT", M_, "", "Position within the bill.", "Order in the feed")]
        + copies("provider_id") + [
        L("cpt_code_id", "INT", M_, "cpt_code", "The final billed code that will be claimed.", "Encounter line code, or claim line code"),
        L("units", "DECIMAL(7,2)", M_, "", "Quantity billed.", "1"),
        L("fee_per_unit", "DECIMAL(12,2)", M_, "", "The fee used, saved on the line. Fee lists change, so history must not move.", "Charge / units, or the fee list for that date"),
        L("billed_amount", "DECIMAL(12,2)", M_, "", "Units x fee. Base of every charge metric.", "Computed; else the claim line charge"),
        L("line_status", "VARCHAR(20)", M_, "", "Drafted, held, ready, claimed, patient_billed, written_off, voided. Worked out, not typed.", "From whether a claim line exists"),
        L("service_date", "DATE", I_, "", "Per-line date.", "Bill date"),
        L("modifier_1_id", "INT", I_, "modifier", "Final billed modifier.", "From the encounter line"), L("modifier_2_id", "INT", I_, "modifier", "Second modifier.", "Blank"),
        L("modifier_3_id", "INT", I_, "modifier", "Third modifier.", "Blank"), L("modifier_4_id", "INT", I_, "modifier", "Fourth modifier.", "Blank"),
        L("diagnosis_1_id", "INT", I_, "diagnosis_code", "Final supporting diagnosis.", "Encounter line's"), L("diagnosis_2_id", "INT", O_, "diagnosis_code", "Second diagnosis.", "Blank"),
        L("diagnosis_3_id", "INT", O_, "diagnosis_code", "Third diagnosis.", "Blank"), L("diagnosis_4_id", "INT", O_, "diagnosis_code", "Fourth diagnosis.", "Blank"),
        L("rendering_provider_id", "INT", I_, "provider", "When different from the bill.", "Bill's provider"),
        L("encounter_detail_id", "BIGINT", I_, "encounter_details", "Performed-to-billed traceability; missed-charge detection.", "Match on visit, code, date"),
        L("charge_entered_date", "DATE", I_, "", "Detects late charges.", "The bill's entered date"),
        L("cpt_as_entered_id", "INT", I_, "cpt_code", "The code before coding review: the audit trail.", "Encounter line code"),
        L("code_changed", "BIT", I_, "", "1 if coding changed the code.", "Derived"),
        L("change_approved_by", "VARCHAR(50)", I_, "", "Pseudonymous approver of a code change. A change with no approver is flagged (codes change only with a named approval).", "Blank; no approver means flagged"),
        L("fee_list_id", "INT", I_, "fee_list", "Which fee list and version priced the line.", "Fee list in force on the date"),
        L("expected_allowed", "DECIMAL(12,2)", I_, "", "Contract allowed for the line; expected revenue and underpayment check.", "Payer's typical allowed amount"),
        L("hold_reason", "VARCHAR(30)", I_, "", "One line can be stuck while the others go.", "The bill's hold reason"),
        L("authorization_id", "BIGINT", I_, "authorization", "Authorization on the line.", "Match on patient, code, dates"),
        L("claims_on", "SMALLINT", I_, "", "Claim rollup: how many claims carry the line. Rebuilt from claim_details.", "Rebuild from claim lines"),
        L("latest_claim_line_status", "VARCHAR(20)", I_, "", "Claim rollup.", "Rebuild from claim lines"), L("claimed_date", "DATE", I_, "", "First claimed.", "Rebuild from claim lines"),
        L("drug_code", "VARCHAR(11)", O_, "", "Drug-billing specialties.", "Blank"), L("drug_units", "DECIMAL(12,3)", O_, "", "Drug units.", "Blank"),
        L("place_of_service_id", "INT", O_, "place_of_service", "When different from the bill.", "Bill's"), L("entered_by_role", "VARCHAR(30)", O_, "", "Productivity.", "Blank"),
        L("no_charge_amount", "DECIMAL(12,2)", O_, "", "Courtesy or write-off before a claim.", "Blank")] + audit("bill_detail", False))

T["claim"] = dict(priority=M_, group="3 Bill", pair="header", what="One row per claim submission to a payer (a replacement is a new row).",
    purpose="The request to one payer. The hottest table: kept narrow, with payment totals rolled up from the payment records.",
    metrics="Denial rate, first-pass acceptance, clean-claim rate, days in AR, claim lag, timely-filing risk, payer mix, collection rate",
    fallback="1 837 from the clearinghouse, 2 PM claim export, 3 rebuild from the 835 (claim id, charge, paid, status; no submission date or diagnoses), 4 charge records plus an assumed payer",
    cols=common("claim") + [
        L("claim_number", "VARCHAR(50)", M_, "", "The client's claim ID (CLM01). Joins the 837, 277CA, 835 and PM. Restricted.", "Payer claim number, or a hash of patient, date, payer, amount (low confidence)", True),
        L("practice_id", "INT", M_, "practice", "All reports by practice.", "Client default"), L("payer_id", "INT", M_, "payer", "Who we billed.", "Payer on the 835 or 277CA"),
        L("patient_id", "BIGINT", M_, "patient", "Duplicates; patient-level balances.", "Hash of member ID"),
        L("billing_provider_id", "INT", M_, "provider", "Whose NPI and tax ID billed; enrollment problems.", "Practice default"),
        L("service_date_from", "DATE", M_, "", "Timely filing, aging.", "Encounter date, or the 835 date"),
        L("submitted_date", "DATE", M_, "", "Claim lag, days in AR.", "Acknowledgement date or file date"),
        L("total_charge", "DECIMAL(12,2)", M_, "", "Base for denial and collection rates. Must equal the sum of the lines.", "Sum of claim_details"),
        L("claim_status", "VARCHAR(20)", M_, "", "Submitted, accepted, rejected, pending, paid, partly_paid, denied, closed, voided. The work queue filter.", "Derived from acknowledgement and payment events"),
        L("rendering_provider_id", "INT", I_, "provider", "Denials and productivity by provider.", "Encounter provider, or billing provider"),
        L("facility_id", "INT", I_, "facility", "Site reporting.", "Practice default"), L("place_of_service_id", "INT", I_, "place_of_service", "Pricing differences.", "Office (11)"),
        L("specialty_id", "INT", I_, "specialty", "Specialty reports.", "From the provider"), L("coverage_id", "INT", I_, "coverage", "Policy billed.", "Encounter's coverage"),
        L("claim_sequence", "VARCHAR(10)", I_, "", "Primary, secondary, tertiary: secondary billing and coordination of benefits.", "Primary"),
        L("frequency_code", "CHAR(1)", I_, "", "1 original, 7 replacement, 8 void: so resubmits do not double-count.", "Original"),
        L("payer_claim_number", "VARCHAR(50)", I_, "", "Payer's claim number (ICN). Matches appeals and resubmits. Restricted.", "Match on claim number, payer, date, amount", True),
        L("bill_id", "BIGINT", I_, "bill", "Traces the claim back to the charge.", "Match on patient, date, code"), L("encounter_id", "BIGINT", I_, "encounter", "Traces the claim back to the visit.", "Match on patient, date, code"),
        L("principal_diagnosis_code_id", "INT", I_, "diagnosis_code", "Condition-level analysis.", "First diagnosis on line 1"),
        L("prior_auth_number", "VARCHAR(50)", I_, "", "REF*G1: ties an authorization to the claim; reason code 197 denials. Restricted.", "Match the authorization table", True),
        L("authorization_id", "BIGINT", I_, "authorization", "Internal link to the authorization.", "Match on patient, code, dates"),
        L("paid_amount", "DECIMAL(12,2)", I_, "", "Rollup of payments. Rebuilt nightly; never the source of truth.", "Rebuild from payments"),
        L("patient_responsibility", "DECIMAL(12,2)", I_, "", "Rollup: patient share.", "Rebuild from payments"), L("adjusted_amount", "DECIMAL(12,2)", I_, "", "Rollup: contractual write-downs.", "Rebuild from payments"),
        L("denied_amount", "DECIMAL(12,2)", I_, "", "Rollup: denied.", "Rebuild from payments"), L("balance", "DECIMAL(12,2)", I_, "", "Rollup: still open.", "Rebuild from payments"),
        L("last_payment_date", "DATE", I_, "", "Rollup: latest payment.", "Rebuild from payments"), L("last_status_date", "DATE", I_, "", "Rollup: latest status event.", "Rebuild from events"),
        L("claim_type", "VARCHAR(15)", O_, "", "Professional or institutional.", "Professional"), L("accident_related", "VARCHAR(10)", O_, "", "Accident indicator; some specialties.", "Blank"),
        L("referral_provider_id", "INT", O_, "provider", "Referral; some specialties.", "Blank"), L("batch_control_number", "VARCHAR(20)", O_, "", "Matches 999 and 277CA acknowledgements.", "Blank")] + audit("claim"))

T["claim_details"] = dict(priority=M_, group="3 Bill", pair="detail", what="One row per service line on a claim submission.",
    purpose="What each line was, and what happened to it. Where denial reasons attach, because payers answer line by line.",
    metrics="Denial rate by procedure, first-pass acceptance by procedure, underpayment, realisation, modifier problems, unit limits, coding review, procedure mix and revenue by provider",
    fallback="1 837 lines, 2 PM charge lines, 3 835 lines (code, units, charge, paid, reasons; no diagnosis pointers; line numbers may differ), 4 bill lines plus an assumed payer",
    cols=common("claim_detail") + [
        L("claim_id", "BIGINT", M_, "claim", "Ties the line to its claim.", "Always set by us"), L("line_number", "SMALLINT", M_, "", "The same procedure can appear twice with different modifiers or sides.", "Order in the file")]
        + [L("practice_id", "INT", I_, "practice", "Copied from the claim.", "Always set by us"), L("payer_id", "INT", I_, "payer", "Copied from the claim; procedure-by-payer reports skip the join.", "Always set by us"),
           L("patient_id", "BIGINT", I_, "patient", "Copied from the claim.", "Always set by us"), L("billing_provider_id", "INT", I_, "provider", "Copied from the claim.", "Always set by us"),
           L("specialty_id", "INT", I_, "specialty", "Copied from the provider.", "From the provider")] + [
        L("cpt_code_id", "INT", M_, "cpt_code", "Procedure level: denials, contract pricing, coding review.", "835 line (original submitted code kept); else the bill line"),
        L("units", "DECIMAL(7,2)", M_, "", "Pricing and unit-limit checks.", "835 line units; else 1"),
        L("charge_amount", "DECIMAL(12,2)", M_, "", "Base for line realisation and denial rates.", "Units x fee list, or the 835 line charge"),
        L("line_status", "VARCHAR(20)", M_, "", "Submitted, rejected, pending, paid, partly_paid, denied, adjusted. Worked out from events.", "Derived from the line amounts"),
        L("paid_amount", "DECIMAL(12,2)", M_, "", "Collections. Empty until paid (mandatory once paid).", "From the 835 line"),
        L("service_date", "DATE", I_, "", "Matches the 835 line; multi-day services.", "Claim service date"),
        L("modifier_1_id", "INT", I_, "modifier", "Pricing and denial causes.", "Blank"), L("modifier_2_id", "INT", I_, "modifier", "Second modifier.", "Blank"),
        L("modifier_3_id", "INT", I_, "modifier", "Third modifier.", "Blank"), L("modifier_4_id", "INT", I_, "modifier", "Fourth modifier.", "Blank"),
        L("diagnosis_pointers", "VARCHAR(4)", I_, "", "Which claim diagnoses support this line.", "First diagnosis on the claim"),
        L("primary_diagnosis_code_id", "INT", I_, "diagnosis_code", "The diagnosis the first pointer points to, saved on the line.", "First diagnosis on the claim"),
        L("rendering_provider_id", "INT", I_, "provider", "Procedure productivity; line-level in the 837.", "Claim rendering provider"),
        L("allowed_amount", "DECIMAL(12,2)", I_, "", "What the payer will pay for the line; underpayment and realisation.", "Paid + patient share (approximate)"),
        L("patient_responsibility", "DECIMAL(12,2)", I_, "", "Patient balance and statements.", "Charge - allowed - denied"),
        L("contractual_adjustment", "DECIMAL(12,2)", I_, "", "Write-down to the contract rate.", "Charge - allowed"),
        L("denied_amount", "DECIMAL(12,2)", I_, "", "Denial rate by procedure.", "From the 835 line"),
        L("primary_denial_reason_id", "INT", I_, "adjustment_reason", "First denial reason; the full list is in the denial records.", "First reason code on the 835 line"),
        L("expected_allowed", "DECIMAL(12,2)", I_, "", "Contract allowed at submission; underpayment is a subtraction.", "Payer's typical allowed amount"),
        L("bill_detail_id", "BIGINT", I_, "bill_details", "Traces the line back to the charge; bill lag and missed charges.", "Match on visit, code, date"),
        L("line_control_number", "VARCHAR(30)", I_, "", "The practice's own line ID; matches 835 lines when the payer reorders or splits lines. Restricted.", "Match on code, modifiers, date, charge", True),
        L("drug_code", "VARCHAR(11)", O_, "", "Drug-billing specialties.", "Blank"), L("drug_units", "DECIMAL(12,3)", O_, "", "Drug units.", "Blank"),
        L("line_flags", "VARCHAR(30)", O_, "", "Emergency, family planning, EPSDT.", "Blank")] + audit("claim_detail", False))

ALLOWED = [
    ("appointment_status", "booked, confirmed, arrived, completed, cancelled, no_show, rescheduled"),
    ("appointment_type", "new, follow_up, procedure, preventive, telehealth, emergency"),
    ("encounter_status", "in_progress, completed, note_pending, signed, charge_ready"),
    ("note_status", "none, draft, signed, amended"), ("charge_status", "not_entered, entered, held, billed"), ("coding_status", "not_reviewed, suggested, accepted, changed"),
    ("bill_status", "drafted, held, ready, billed, partly_billed, patient_billed, written_off, voided"), ("bill_type", "insurance, self_pay, courtesy, workers_comp_or_auto"),
    ("bill_details.line_status", "drafted, held, ready, claimed, patient_billed, written_off, voided"),
    ("claim_status", "submitted, accepted, rejected, pending, paid, partly_paid, denied, closed, voided"), ("claim_sequence", "primary, secondary, tertiary"),
    ("claim_details.line_status", "submitted, rejected, pending, paid, partly_paid, denied, adjusted"),
    ("encounter_details.line_status", "performed, ordered, not_done"), ("auth_required", "yes, no, unknown"), ("laterality", "L, R, B"),
    ("source", "scheduler, ehr, pm_export, x12_837, x12_835, api, rebuilt_from_835, rebuilt_from_claims, rebuilt_from_encounters, manual"),
]

# ============================================================================================ WORKBOOK
wb = Workbook()


def H(ws, row, labels, widths):
    for i, h in enumerate(labels, 1):
        c = ws.cell(row=row, column=i, value=h); c.font = Font(name=F, bold=True, color="FFFFFF", size=10); c.fill = PatternFill("solid", fgColor=NAVY); c.border = BD; c.alignment = Alignment(wrap_text=True, vertical="center")
    for i, w in enumerate(widths, 1): ws.column_dimensions[get_column_letter(i)].width = w


def row_(ws, r, vals, fillcol=None):
    for i, v in enumerate(vals, 1):
        c = ws.cell(row=r, column=i, value=v); c.font = Font(name=F, size=10); c.border = BD; c.alignment = Alignment(wrap_text=True, vertical="top")
    if fillcol:
        col = PFILL.get(str(vals[fillcol - 1]))
        if col: ws.cell(row=r, column=fillcol).fill = PatternFill("solid", fgColor=col)


def title(ws, t, n):
    ws["A1"] = t; ws["A1"].font = Font(name=F, bold=True, size=14, color=NAVY); ws["A2"] = n; ws["A2"].font = Font(name=F, italic=True, size=10, color="595959")


ws = wb.active; ws.title = "Read me"
title(ws, "KrisnnAI core tables: locked so far", "Header and detail pairs along the claim journey, with the shared reference tables. Locked = reviewed field by field and agreed.")
H(ws, 4, ["Topic", "Detail"], [28, 150])
nlocked = len(T); ncols = sum(len(t["cols"]) for t in T.values())
info = [
    ("What is locked", f"{nlocked} tables ({ncols} columns): appointment, appointment_details, encounter, encounter_details, bill, bill_details, claim, claim_details. Header = one row per appointment / visit / bill / claim submission. Details = one row per line (planned service, performed service, charge line, claim line)."),
    ("Bill is not a claim", "A bill is the practice's record of a charge, with or without a payer. A claim is a request to one payer. One bill can become several claims (primary, secondary, resubmits) or none (self-pay, courtesy). The gap between them gives bill lag, bill-to-claim lag and unclaimed charges."),
    ("Two IDs in every table", "<table>_id is an internal identity ID: every join and link between tables uses it. <table>_number is the client's own ID, kept once in a restricted column. Analytics never need the client number, so it never has to be masked in reports or logs."),
    ("Restricted columns", "Client numbers (appointment_number, encounter_number, bill_number, claim_number), payer_claim_number, prior_auth_number, line_control_number and authorization_number are HIPAA-linked. Show them in no report or log. Patient and member numbers are stored as salted hashes only, per the project rule."),
    ("Cancelled and rescheduled", "Nothing is overwritten. A change closes the old row (is_current = 0, replaced_date set) and adds a new row whose previous_<table>_id points to it. Following the chain by internal ID decodes every cancel, reschedule, replacement claim or re-created bill. See the Change tracking sheet."),
    ("Reference IDs in every table", "Practice, patient, payer, provider, specialty, facility, place of service, procedure code, diagnosis code and modifier appear as _id links wherever a table needs them. Detail tables copy practice, patient, payer, provider and specialty from their header so reports never join up to find them. The Where each ID appears sheet shows the grid."),
    ("Priorities", "Table priority: Mandatory (cannot compute revenue metrics without it), Important (powers the prevention agents), Optional (load if the client has it). Field priority: Mandatory (row unusable without it), Important (accuracy drops but a fallback exists), Optional. Every field lists its fallback."),
    ("Still to review", "Phase 4: payer transactions, denials and AR. The reference tables (proposed on their own sheet, not yet reviewed field by field). The agent tables (decisions, findings, tasks)."),
    ("Dates", "Dates are DATE columns joined to a calendar by date, not by an ID."),
    ("Caveat", "A design on paper: no SQL has been run. Standards details behind some columns come from general knowledge. Demo data is synthetic."),
]
for i, r in enumerate(info, 5): row_(ws, i, r)

ws = wb.create_sheet("Tables")
title(ws, "Tables", "Locked tables first, then the reference tables they link to, then what is still to review.")
H(ws, 4, ["Order", "Table", "Journey phase", "Header or detail", "What one row is", "Priority", "Status", "Why it exists", "Metrics served", "If the client does not send it"], [7, 24, 14, 12, 52, 12, 22, 60, 60, 62])
r = 5
for n, (name, t) in enumerate(T.items(), 1):
    row_(ws, r, [n, name, t["group"], t["pair"], t["what"], t["priority"], "Locked", t["purpose"], t["metrics"], t["fallback"]], 6); r += 1
for n, (name, (idc, what, pri, cols)) in enumerate(REFS.items(), len(T) + 1):
    row_(ws, r, [n, name, "Reference", "reference", what, pri, "Proposed, not yet reviewed", "Shared lookup used by the tables above.", "Slices every metric.", "Client reference list, or built from public code sets (CPT, ICD-10, POS, CARC)"], 6); r += 1
for name, what in [("payer_transactions", "What the payer paid, line by line, from the remittance."), ("denials", "One denied amount on one transaction line, with reason and deadline."), ("ar", "What is still owed, by claim line, per day.")]:
    row_(ws, r, [r - 4, name, "4 Transactions, denials, AR", "to review", what, "Not yet reviewed", "Not yet reviewed", "Phase 4 of the journey.", "", ""], 6); r += 1
for c, w in {"A": 7}.items(): pass
ws.freeze_panes = "C5"; ws.auto_filter.ref = f"A4:J{r-1}"

ws = wb.create_sheet("Columns")
title(ws, "Columns of the locked tables", "Every column with type, priority, what it links to, why it exists and what to use if the client does not send it. Restricted = client identifier, never shown in reports or logs.")
H(ws, 4, ["Table", "Column", "Type", "Priority", "Links to", "Restricted", "Why we need it", "If the client does not send it"], [22, 30, 16, 12, 22, 11, 80, 56])
r = 5
for name, t in T.items():
    for (c, typ, pri, link, restricted, desc, fb) in t["cols"]:
        row_(ws, r, [name, c, typ, pri, link, "yes" if restricted else "", desc, fb], 4); r += 1
ws.freeze_panes = "C5"; ws.auto_filter.ref = f"A4:H{r-1}"

ws = wb.create_sheet("Where each ID appears")
title(ws, "Where each reference ID appears", "For each reference table, the column that carries it in each locked table. A blank means that table does not need it.")
names = list(T)
H(ws, 4, ["Reference table", *names], [24] + [26] * len(names))
r = 5
for ref in REFS:
    vals = [ref]
    for n in names:
        cols = [c[0] for c in T[n]["cols"] if c[3] == ref]
        vals.append(", ".join(cols))
    row_(ws, r, vals); r += 1
row_(ws, r, ["(internal ID of another locked table)"] + [", ".join(c[0] + " > " + c[3] for c in T[n]["cols"] if c[3] in T) for n in names]); r += 1
ws.freeze_panes = "B5"

ws = wb.create_sheet("Reference tables")
title(ws, "Reference tables (proposed, not yet reviewed)", "Each has an internal ID (used for all links) and a business code. These need a field-by-field review like the locked tables.")
H(ws, 4, ["Table", "Priority", "Column", "Type", "Description", "Restricted"], [22, 12, 28, 16, 90, 11])
r = 5
for name, (idc, what, pri, cols) in REFS.items():
    row_(ws, r, [name, pri, idc, "INT", f"Internal identity ID. {what}", ""], 2); r += 1
    for (c, typ, desc, restr) in cols:
        row_(ws, r, [name, pri, c, typ, desc, "yes" if restr else ""], 2); r += 1
ws.freeze_panes = "C5"; ws.auto_filter.ref = f"A4:F{r-1}"

ws = wb.create_sheet("Change tracking")
title(ws, "How cancellations, reschedules and replacements are held", "Rows are never overwritten. The internal ID chain shows the whole history.")
H(ws, 4, ["Step", "What happens", "appointment_id", "appointment_number (client's)", "status", "is_current", "previous_appointment_id", "appointment_date", "replaced_date"], [6, 52, 16, 22, 14, 11, 22, 16, 14])
ex = [
    (1, "Booked for 4 Nov.", 1001, "A-5521", "booked", 0, "", "2026-11-04", "2026-10-30"),
    (2, "Patient moves it to 9 Nov. The old row closes; a new row is added and points back.", 1002, "A-5521", "booked", 0, 1001, "2026-11-09", "2026-11-07"),
    (3, "On 7 Nov the patient cancels. Again the old row closes and a new row records the cancellation.", 1003, "A-5521", "cancelled", 1, 1002, "2026-11-09", ""),
    (4, "Rebooked for 20 Nov by the front desk. The scheduler may reuse the number or issue a new one; either way the chain links by internal ID.", 1004, "A-5530", "booked", 1, 1003, "2026-11-20", ""),
]
for i, v in enumerate(ex, 5): row_(ws, i, v)
ws.cell(row=10, column=1, value="Reading the chain: follow previous_appointment_id back from any row to the first booking. reschedule_count = number of links; original_appointment_date = the first row's date. The same pattern holds for claims (a replacement claim points to the one it replaced), bills (a voided and re-created bill) and encounters (a re-opened visit). Counts and rates use is_current = 1; first-pass metrics read the first row of each chain.").font = Font(name=F, size=10)
ws.cell(row=10, column=1).alignment = Alignment(wrap_text=True, vertical="top"); ws.merge_cells("A10:I12")

ws = wb.create_sheet("Allowed values")
title(ws, "Allowed values for coded columns", "Short coded lists kept as text on the row, so there is no extra lookup table for them.")
H(ws, 4, ["Column", "Allowed values"], [34, 140])
for i, v in enumerate(ALLOWED, 5): row_(ws, i, v)

wb.save(OUT)
print("saved", OUT, "| locked tables", len(T), "| columns", ncols, "| reference tables", len(REFS))
for n, t in T.items(): print(f"  {n:22s} {len(t['cols']):3d} columns  {t['priority']}")
