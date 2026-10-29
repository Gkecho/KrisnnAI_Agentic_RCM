# Notes, agent B: document, order, referral, claim_attachment designed; estimate and encounter_diagnosis not created

Module: `plan\plan_B.py`. Validator: OK. TBD_DONE = document, order, referral, claim_attachment, estimate, encounter_diagnosis.
Only `document` had Remapped "Planned table" rows (70). Order, referral and claim_attachment are designed because those 70 rows hold their fields
(orders, referrals and records requests were crammed into the old fact_document). I re-pointed those rows to the new tables. The other
17 REMAP entries are old fact_document / fact_note rows that were "No home" or "By design" with no final table; they now have homes. 87 REMAP entries in total.

## document (42 columns, Important, group "2 Encounter", header, versioned)
One row is one document record in the EMR: visit note, consent, advance notice, plan of care, result, letter, cover note or document pack. Metadata only.
- Needed: the encounter has only a status, a signed date and a count. Note Chaser needs type, author, full signature time, co-signature, addendum, late entry, lock, content hash, which elements are present.
  Code Whisperer needs HPI/ROS counts and decision-making levels. Permit Clerk and Auditor need to know which supporting documents exist and are signed.
- Agents: Note Chaser (A3, about 50 rows), Permit Clerk (A2, 8), Code Whisperer (A4, 7), Auditor (A10, 1).
- Decisions: one status column covers notes, consents and results (values listed in the description). Elements are one code list (`elements_documented`), not a per-element table
  (old fact_note_element is not recreated): the 12 yes/no element rows map to codes in that list. `elements_required`, `elements_missing` and the completeness score are Derived
  (rules plus a view; the check result already lives in agent_decision_details). Links: encounter, authorization, claim (all optional). Addendum date = the addendum row's `signed_at`.
- Dropped: attachment size (operational), the text of procedure notes (never stored). Nothing else dropped.

## order (28 columns, Optional, group "2 Encounter", header, versioned)
One row is one clinical order (lab, imaging, procedure, equipment, therapy, referral out). `order` is an SQL reserved word; always quote it.
- Needed: Note Chaser reads order id, type, status, signed date, ordering provider, diagnosis, result status (7 rows). Also "orders with no charge" and the authorization link from the TBD list.
  Not a document column set because an order has its own life (draft to resulted).
- Link to `encounter_details` (the line with line_status = ordered): from there bill_details shows whether a charge followed. Links to `document` for the signed order and the result.
- Decision: only the main diagnosis (order_diagnosis_codes was "No home" before; now Partial).

## referral (29 columns, Important, group "1 Appointment", header, versioned)
One row is one referral into the practice, with valid dates and visits allowed/used.
- Needed: coverage only has `requires_referral`; Note Chaser needs status, referring provider, dates, visits (6 rows). Visits remaining = allowed - used (a view).
- Default taken: visits_used is source-reported, falling back to a count of completed appointments inside the dates.

## claim_attachment (34 columns, Optional, group "3 Bill and claim", header, versioned)
One row is one payer records request (or one attachment announcement) for one claim. A request that covers several claims is several rows sharing `payer_reference_number`.
- Needed: Note Chaser (A3) has about 25 rows about payer records requests, 12 of which had no home before: received date, channel, due and extended due date, requesting unit,
  payer reference, request text hash, response sent date/method/tracking/pages, acknowledgement, PWK type/transmission/control number.
- Hash, size and page count of what was sent live on the linked `document` row (`content_hash`), so the same file is not described twice.
- Restricted columns: claim_attachment_number, payer_reference_number, response_tracking_number, attachment_control_number.

## Decided NOT to create
- **estimate**: no agent row needs it (0 Remapped rows). `appointment_details.expected_charge` / `expected_allowed` and `appointment.copay_due` (appointment is versioned, so
  what was estimated then is kept) already give an estimate; actual patient share is in transactions (responsible_party = patient). Estimate accuracy is a view over those.
  Only the good-faith-estimate compliance part (self-pay, No Surprises Act) is uncovered; see recommendation 3.
- **encounter_diagnosis**: no agent row needs it. A claim line points to at most four diagnoses, held in `encounter_details.diagnosis_1-4`; risk adjustment can take the distinct set
  across an encounter's lines (a view) plus `encounter.principal_diagnosis_code_id`. Revisit only if a client needs diagnoses that are on no line (5 to 12 on the claim header).

## Old tables checked (fact_document, fact_note, fact_note_element, fact_auth_request_line)
All 70 Planned-table rows are re-pointed (Exact 14, Renamed 34, Partial 31 incl. extras, Added 5, Derived 3 across all 87 entries). fact_auth_request_line rows already map to `authorization`
(not mine); the three left with no final table there (service_from/to, urgency, HCR reason) look like `authorization.valid_from/valid_to`, `urgency` and `decision_reason_code`; flagged for whoever owns authorization.
REMAP keys are (old table, "old column | Agent: field") because one old column (for example document_ref) serves many fields.

## Recommendations for locked tables (not made)
1. `appointment` and `encounter`: add optional `referral_id` (FK referral). Without it, visits_used can only be inferred by dates.
2. `encounter.elements_documented` (TINYINT count) stays as a summary; define it as the number of codes in `document.elements_documented`.
3. If good-faith-estimate compliance is wanted later: `appointment` optional `estimate_sent_date` and `estimate_amount`, instead of a table.
4. Allowed values sheet: add document_class, document_type, document_status, order_type, order_status, referral_status, request_type, response_status.
