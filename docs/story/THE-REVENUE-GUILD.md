# The Revenue Guild of Maple Street

*A story about fifteen agents, the leaks they hunt, and the officers who hold the keys.*

Everything here is fiction built on the real design. Powers are what each agent really does (see `docs/ROADMAP.md`). Weaknesses are the real limits. The "grimoire" of each character is the real tables it reads and writes in the canonical model. Patients are synthetic and appear only as hashes.

---

## Part 1. The world

**The Realm.** Maple Street Clinic (synthetic) lives in a kingdom where money must travel a long road: from a patient's booking, through a visit, across the Relay Tower (the clearinghouse), into the Great Houses (the payers), and back as coin with a sealed letter explaining what was paid and why. At every bridge on that road, small amounts of gold fall into the river. These are **the Leaks**.

**The Guild.** Fifteen agents of KrisnnAI, each born to guard one stretch of the road. They are quick, tireless, and they never sleep. They are not the rulers of the realm. They are advisors, scouts and drafters.

**The Officers.** The humans of the clinic. Officers hold the keys, make the calls, and put their names to anything that moves gold. The Guild serves them.

**The Four Oaths** every agent swears:

1. **We look, we do not touch.** No agent writes into the clinic's own books (the PM and EHR). It reads, and it leaves notes and tasks.
2. **No gold moves without a name.** A code is never changed, and a refund or write-off never made, without a named officer's approval.
3. **Every deed is written down.** Each decision goes into the *Ledger of Deeds* (the decision record): what was seen, which rule fired, when it was known, who approved. No entry, no action.
4. **Earn your rank.** Every new power starts in the *Shadow Grounds*, where the agent only writes what it *would* do and sends nothing. Rank is earned with evidence.

**The Ranks** (autonomy levels): **L0 Observer**, **L1 Advisor**, **L2 Drafter**, **L3 Runner** (acts after a named approval), **L4 Bounded Sovereign** (acts alone inside limits the client sets). *Today every agent stands at L0 in the Shadow Grounds.*

**Rules first, magic second.** Deadlines, contract maths and required fields are plain arithmetic. An agent reaches for a model only to read, sort, predict or draft, and no patient detail leaves the realm without an approved seal.

---

## Part 2. The Guild

Each sheet gives the **role**, **power**, **signature move**, **trait**, **weakness** (a real limit today), the **villain** it hunts, its **officer partner**, and its **grimoire** (tables). All agents are L0 in shadow mode unless noted.

### Before the visit

**A1. The Gatekeeper** *(Pre-Visit Financial Clearance)*
- **Power:** Sees whether a traveler's coverage will hold on the day of the visit.
- **Signature move:** Spots a new booking, sends a coverage question across the Relay Tower (a 270) for every policy the traveler holds, reads the answer (a 271), and asks again 3 days and 1 day before the visit.
- **Trait:** Punctual to the minute. Politely suspicious. Never assumes a card means coverage.
- **Weakness:** Trusts the answer it is given; a vague 271 leaves it guessing. The real clearinghouse bridge is not built yet.
- **Villain:** *The Lapsed Policy*, who lets a visit happen on coverage that ended last month.
- **Officer partner:** The Front Desk Officer.
- **Grimoire:** reads `appointment`, `coverage`, `patient`; writes `eligibility_check`, `agent_finding`, `agent_task`.

**A2. The Permit Clerk** *(Authorization Intelligence)*
- **Power:** Knows which procedures the Great Houses demand a permit for, and whether the permit is still valid.
- **Signature move:** Checks at 7 days and 2 days before a visit: none requested, denied, expired, units used up, still pending.
- **Trait:** Fussy about paperwork, calm under deadlines, always has a form in hand.
- **Weakness:** Cannot walk into a payer's portal; it prepares the request, an officer files it.
- **Villain:** *The Missing Permit*, who turns a healthy visit into an unpayable one.
- **Officer partner:** The Authorization Officer.
- **Grimoire:** reads `authorization`, `referral`, `payer_rule`, `appointment_details`; writes `agent_task`, `agent_finding`.

### After the visit

**A3. The Note Chaser** *(Documentation Completeness)*
- **Power:** Finds the notes nobody signed and the charges nobody entered, before the claim goes stale.
- **Signature move:** Climbs the escalation ladder: the provider, the provider again, the practice manager, the medical director (levels still to be confirmed).
- **Trait:** Relentless but never rude. Remembers every promise made in the hallway.
- **Weakness:** Reads note *status and elements*, never note text. It cannot judge whether the medicine is good, only whether the scroll is complete.
- **Villain:** *The Unsigned Scroll*, and her sister *The Late Charge*.
- **Officer partner:** The Provider (the clinician) and the Practice Manager.
- **Grimoire:** reads `encounter`, `document`, `bill_details`; writes `agent_task`, `agent_finding`.

**A4. The Code Whisperer** *(Coding and Charge Integrity Copilot)*
- **Power:** Hears when the code on a visit does not match what was documented, in either direction.
- **Signature move:** Whispers "this looks undercoded" or "this looks overcoded," with the dollar difference at the contract rate.
- **Trait:** Humble. Speaks only in suggestions. Cares more about being right than being first.
- **Weakness:** The liability boundary is absolute: it never changes a code. Its level table is a placeholder and it does not yet reason about diagnoses or modifiers.
- **Villain:** *Level Drift*, a quiet creature that makes visits look smaller, or bolder, than they were.
- **Officer partner:** The Coding Officer, who alone decides.
- **Grimoire:** reads `encounter_details`, `bill_details`, `document`; writes `agent_finding` (suggested and final values, compliance-risk flag).

### Before the claim leaves

**A5. The Mirror** *(Claim Prevention and Digital Twin)*
- **Power:** Holds up a looking glass to a claim and shows how the Great Houses will treat it.
- **Signature move:** Runs the claim through the rules and the twin, and reports the chance of denial, the likely reason, and the amount it expects to be allowed.
- **Trait:** Honest to a fault. A little vain about its predictions, which is why they are scored against what really happens.
- **Weakness:** Its payer-rule library is still thin, and some of its code-pair tables are synthetic stand-ins.
- **Villain:** *The Edit Trap*: a payer's hidden rule that rejects a perfectly good claim.
- **Officer partner:** The Billing Officer.
- **Grimoire:** reads `claim`, `claim_details`, `payer_rule`, `contract_rate`; writes `agent_finding` (predicted probability, reason, allowed amount), `agent_forecast`.

**A6. The Courier** *(Claim Submission and Response)*
- **Power:** Carries the claim over the Relay Tower, and meets what comes back.
- **Signature move:** When a rejection or acknowledgement (999, 277CA) returns, it reads it in seconds and hands the fix to the right officer.
- **Trait:** Fast, practical, speaks in short sentences. Hates a package that comes back unopened.
- **Weakness:** The sending side is not complete: it still needs a release signal and its own claim writer.
- **Villain:** *The Silent Bounce*, a claim that is rejected at the gate and nobody notices for a week.
- **Officer partner:** The Billing Officer.
- **Grimoire:** reads `claim`, `claim_status_history`; writes `claim_status_history`, `agent_task`.

### After submission

**A7. The Hunter** *(AR Next-Best-Action)*
- **Power:** Smells the claims that have gone quiet.
- **Signature move:** Each week sweeps every submitted claim, compares its age to how long that payer usually takes, and ranks the overdue ones by dollars and filing risk.
- **Trait:** Patient predator. Never chases the same trail twice in the same day.
- **Weakness:** Real status inquiries (276/277) are not wired yet; it infers silence from age.
- **Villain:** *The Quiet Claim*, which sits in a payer's queue until the filing deadline passes.
- **Officer partner:** The Billing Officer.
- **Grimoire:** reads `claim`, `claim_status_history`, `ar`; writes `agent_task`, `agent_finding`.

**A8. The Advocate** *(Denial Resolution and Appeal)*
- **Power:** Gives every denial a category, an owner and a deadline, and drafts the argument.
- **Signature move:** Reads the sealed letter (835), finds what the denial really says, and builds the appeal packet with the evidence an officer needs.
- **Trait:** Fierce on the page, courteous in person. Believes every denial deserves a hearing.
- **Weakness:** Cannot yet gather evidence from the EHR on its own, or track the final outcome without help.
- **Villain:** *The Denial Dragon*.
- **Officer partner:** The Denials Officer, whose name goes on every appeal.
- **Grimoire:** reads `denial`, `transactions`, `adjustment_reason`, `remark_code`, `document`; writes `appeal`, `agent_task`, `agent_approval`.

**A9. The Coach** *(Denial Prevention Learning)*
- **Power:** Notices when the same denial keeps coming back and teaches the others to stop it.
- **Signature move:** Clusters denials by payer, procedure and reason over 120 days, proposes a new rule, and, after a named approval, hands it to the Mirror.
- **Trait:** Teacherly. Loves a lesson that is tested before it is taught.
- **Weakness:** Its thresholds are placeholders and it works one rule family so far.
- **Villain:** *The Repeating Wraith*, the same denial, again and again.
- **Officer partner:** The Compliance Officer, who must approve every new rule by name.
- **Grimoire:** reads `denial`, `claim_details`; writes `payer_rule`, `agent_value`.

### Payment

**A10. The Auditor** *(Contract and Underpayment)*
- **Power:** Knows what the contract says each payment should have been.
- **Signature move:** Compares every payment to the contract rate, names the cause, spots payer-wide patterns, drafts the dispute.
- **Trait:** Meticulous, dry, quietly delighted by a rounding error.
- **Weakness:** Needs the real signed contracts; today many rates are inferred and marked as such.
- **Villain:** *The Short-Pay Goblin*, who pays a little less every time and hopes nobody checks.
- **Officer partner:** The Billing Officer, with the Practice Manager for payer disputes.
- **Grimoire:** reads `payment`, `claim_details`, `contract_rate`, `fee_list`; writes `agent_finding`, `agent_value`.

**A11. The Bookkeeper** *(Payment Posting and Reconciliation)*
- **Power:** Matches the letter of payment to what the clinic's books actually recorded.
- **Signature move:** Finds a claim that was paid but not posted, or posted for less than paid, and measures days to post.
- **Trait:** Neat. Counts everything twice. Does not trust anyone's "I think it's posted."
- **Weakness:** Does not see the bank any more (the bank deposit feed was removed by design), so it reconciles *payment to posting*, not payment to account.
- **Villain:** *The Cash Ghost*: money received, recorded nowhere.
- **Officer partner:** The Finance Officer.
- **Grimoire:** reads `payment`, `transactions`, `claim`; writes `agent_finding`, `agent_task`.

### Patient and people

**A12. The Concierge** *(Patient Financial Engagement)*
- **Power:** Explains a patient's balance in plain words, so staff can speak to it with confidence.
- **Signature move:** Sorts open balances by kind and age and writes a short, kind explanation for the staff member.
- **Trait:** Warm and patient. Treats a bill as a conversation.
- **Weakness:** Staff-facing only. No outreach, no payment processing and no write-off until legal review of texting and collection rules is done.
- **Villain:** *The Forgotten Balance*.
- **Officer partner:** The Patient Accounts Officer.
- **Grimoire:** reads `ar`, `patient_statement`, `payment_plan`, `patient_contact_preference`; writes `agent_task`.

**A13. The Credentialing Sentinel** *(Credentialing and Enrollment)*
- **Power:** Watches the seals that let each provider be paid by each House.
- **Signature move:** Counts the dollars at risk when an enrollment is about to lapse or a screening finds a problem, and raises it early.
- **Trait:** Grave, patient, remembers dates.
- **Weakness:** No portal and no live exclusion-list lookup yet.
- **Villain:** *The Lapsed Seal*.
- **Officer partner:** The Credentialing Officer.
- **Grimoire:** reads `enrollment`, `provider`, `payer`, `claim`; writes `agent_finding`.

### Across the realm

**A14. The Captain** *(RCM Control Tower)*
- **Power:** Sees every agent's finding in one hall and decides what the officers should look at first.
- **Signature move:** The morning council: one inbox, a cash forecast whose accuracy is measured, four standing signals, and a daily review of what is stuck.
- **Trait:** Calm. Allergic to noise. Never raises a card without a dollar amount.
- **Weakness:** No screen of its own yet, and its forecast model is simple.
- **Villain:** *The Fog*: everyone busy, nobody knowing what matters.
- **Officer partner:** The Practice Manager (the Commander).
- **Grimoire:** reads every `agent_*` table; writes `agent_forecast`, `agent_task`.

**A15. The Detective / Scout** *(Revenue Assurance Investigator)*
- **Power:** Notices slow bleeding that no single alarm catches.
- **Signature move:** Compares what a payer actually pays to what the contract expects, recent weeks against a baseline, then explains each slice and names which upstream agent had flagged the claim before billing.
- **Trait:** Curious. Never satisfied with "it just dipped."
- **Weakness:** Detects and explains, but cannot fix; it depends on the others to act.
- **Villain:** *The Slow Bleed*, a thousand small leaks that add up to a flood.
- **Officer partner:** The Practice Manager and the Finance Officer.
- **Grimoire:** reads `payment`, `claim_details`, `contract_rate`, `agent_finding`; writes `agent_finding`, `agent_value`.

---

## Part 3. The officers

| Officer | Holds the key to | Works most with |
|---|---|---|
| **Commander** (Practice Manager) | Priorities, payer disputes, the escalation ladder | Captain, Detective / Scout |
| **Front Desk Officer** | Booking, insurance cards, calling patients | Gatekeeper |
| **Authorization Officer** | Filing permits with the Great Houses | Permit Clerk |
| **The Provider** (clinician) | Notes, signatures, medical judgement | Note Chaser |
| **Coding Officer** | Every code, final word | Code Whisperer |
| **Billing Officer** | Releasing, fixing and following up claims | Mirror, Courier, Hunter, Auditor |
| **Denials Officer** | Putting a name on an appeal | Advocate |
| **Finance Officer** | Posting, refunds, write-offs | Bookkeeper |
| **Patient Accounts Officer** | Speaking to patients about balances | Concierge |
| **Credentialing Officer** | Enrollment and revalidation | Credentialing Sentinel |
| **Compliance Warden** | Approving rules, guarding the Oaths | Coach, and everyone |

---

## Part 4. The tale: *One traveler, one road*

*The traveler is a synthetic patient, known to the Guild only by a hash. The officers are given first names for the telling.*

### Chapter 1. The lapsed policy

At dawn the booking bell rings at the Front Desk. **Imani**, the Front Desk Officer, scribbles a new appointment into the clinic's book.

Three seconds later the **Gatekeeper** has seen it. It asks the Relay Tower one question for each policy the traveler holds. The answer returns before Imani finishes her tea: *no active coverage on the day of service.*

The Gatekeeper writes the finding in the Ledger of Deeds and leaves a task on Imani's desk: *Coverage ended last month. Ask the traveler for a new card.* Imani makes the call. The new policy turns out to belong to a different House. The Gatekeeper asks again, 3 days before the visit and 1 day before, to be sure.

Beside it, the **Permit Clerk** reads the planned procedure and sighs. This House wants a permit. It prepares the request and passes it to **Tomas**, the Authorization Officer, who files it with seven days to spare.

*The Lapsed Policy and the Missing Permit are defeated before the traveler has even arrived.*

### Chapter 2. The unsigned scroll

The visit goes well. By evening, the **Note Chaser** notices the scroll is unsigned and the charge has not been entered. It leaves a polite nudge for **Dr. Okafor**. The next morning, the same nudge, firmer. By the third day it quietly climbs the ladder, and the Commander finds a card in the inbox.

Dr. Okafor signs. The charge appears. The **Code Whisperer** reads what was documented and murmurs: *this visit looks undercoded by a level; difference at contract rate, forty-some dollars.* **Lin**, the Coding Officer, reads the note, agrees with half of it, and changes one code. The Whisperer logs which half it got right.

*Level Drift is held at bay, and the Whisperer never touched a code.*

### Chapter 3. The mirror and the bounce

Before the claim leaves the clinic, **Sven**, the Billing Officer, holds it up to the **Mirror**. The Mirror shows a 31 percent chance of denial and names a reason: this House has been rejecting that procedure when paired with a certain modifier. Sven fixes the pair and releases the claim.

The **Courier** carries it over the Relay Tower. An hour later a rejection returns: a member number with a transposed digit. The Courier reads it in seconds and puts the fix on Sven's desk before lunch. It is resent the same day.

*The Edit Trap and the Silent Bounce are both beaten; the claim is on the road, clean.*

### Chapter 4. The long wait

Thirty-five days pass. In another claim's file, the **Hunter** has smelled something: a submitted claim with no answer, older than this House usually takes. It ranks the claim above fifty others by dollars and by how close it is to the filing deadline. Sven calls the House, and the claim, once found, moves.

*The Quiet Claim is dragged into the light.*

### Chapter 5. The verdict

The sealed letter arrives. One line is paid. One line is denied, with a code and a remark. The **Advocate** reads the letter, calls the denial a "missing information" kind, gives it an owner and a deadline, and drafts the appeal with the evidence it can find. **Priya**, the Denials Officer, reads it, strikes one sentence, and signs her name. Only then does the appeal leave.

Meanwhile the **Auditor** has laid the payment beside the contract. The paid line is short of what the contract promises, and the same House has been short before. It writes the dispute package for the Billing Officer and the Commander to take to the payer.

And the **Bookkeeper** notes that the payment landed on Tuesday but was posted for less than paid on Thursday. The difference is waiting in unapplied cash. **Carlos**, the Finance Officer, finds the missing line and posts it.

*The Denial Dragon is fought fairly, the Short-Pay Goblin is named, and the Cash Ghost is given a home.*

### Chapter 6. The balance

What the House did not pay becomes the traveler's balance. The **Concierge** drafts a plain explanation for **Hana**, the Patient Accounts Officer: what the House paid, what it did not, what the traveler owes, and why. Hana reads it and speaks to the traveler, in her own voice. The Concierge does not send a thing.

*The Forgotten Balance is remembered, kindly.*

### Chapter 7. The slow bleed

Weeks later, the **Detective** notices that one House's payments have drifted six percent below the contract across the last month. It traces the slice to a procedure, and finds that the **Mirror** had warned about it on some claims, and the **Auditor** on others. It tells the Commander.

The **Coach** has seen the same pattern: the same denial, the same House, the same reason. It writes a proposal for a new rule. **Warden Bell**, the Compliance Officer, reads the evidence and approves it *by name*. The rule joins the Mirror's glass, and the Coach schedules a test, so everyone will know whether the lesson worked.

Elsewhere, the **Credentialing Sentinel** has been counting. Dr. Okafor's seal with one House lapses in 40 days, and the Sentinel has priced the claims at risk. **Ravi**, the Credentialing Officer, renews it before anyone is hurt.

*The Slow Bleed is staunched; the Repeating Wraith and the Lapsed Seal are bound.*

### Chapter 8. The morning council

At eight the next morning the **Captain** calls the council. One inbox, ranked by dollars. The cash forecast, with its measured error. Four signals, one of them amber. Three stuck items escalated. The Commander reads them over coffee, assigns two, and dismisses one.

"And the Guild?" asks the Commander.

The Captain opens the Ledger of Deeds. "Every one of us stayed in the Shadow Grounds. We wrote what we *would* have done. The officers did the doing."

The Commander smiles. "Good. Keep it that way, until the Ledger says otherwise."

---

## Part 5. What the story is hiding

If you read it as a product spec, the story is saying:

- **Fifteen narrow agents beat one clever one.** Each guards one bridge and is easy to test, trust and promote.
- **The officer is a feature, not a limit.** Every action that moves money has a named human.
- **The Ledger of Deeds is the real product.** It is what makes an agent auditable, replayable and promotable.
- **Shadow first.** Rank (autonomy) is earned by evidence, per power, per client.
- **The Guild talks.** The Detective cites the Mirror and the Auditor; the Coach teaches the Mirror; the Captain reads them all. The `agent_*` tables are how.
