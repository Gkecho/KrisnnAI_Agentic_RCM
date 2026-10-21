# ADR-0003: Replies to the payer in the demo (corrected claims, appeals, disputes, records)

Status: **accepted for the demo**. Date: 2026-10-21.

## Context
The live encounter stream (`docs/plan_live_encounter_stream.md`) takes a visit transcript to a coded claim and a payer decision, and until now stopped there: after
the first 835 the agents only proposed tasks. The product picture is the whole journey, so after the payer's reply our bots reply to the reply (fix a rejected claim,
send a corrected claim, appeal, dispute an underpayment, send records) until the claim is settled or a person has to decide.
`CLAUDE.md` rule 3 says nothing is submitted to payers except through the partner clearinghouse adapter, and only for actions whose policy allows it. Rule 4 says codes,
refunds and write-offs are never automatic. Rules 2 and 3 are written for client systems.

## Decision
1. **Demo tenant only.** Replies exist only in the demo stream (`StreamConfig.replies`, off by default). Real clients stay read-only toward their systems and keep the
   rule-3 gate: nothing here is a path to a real payer, and no real-payer endpoint is configured anywhere in this code.
2. **Destination.** Every reply goes only to the mock clearinghouse (corrected 837 claims) or is handed to the payer simulator (appeal packet, dispute, records), which
   answers from a seeded stream. Nothing is real payer behaviour; the answers are labelled as simulation.
3. **Every action carries an approval.** Either a named simulated person, always labelled `person:simulated-<role> (demo)`, or the capped demo policy
   `policy:demo-replies-v1`. The policy covers only technical fixes (a corrected claim after a clearinghouse rejection) and sending records. Appeals, coverage
   corrections and disputes are approved by a simulated person. A **daily cap** on replies stands in for the unbuilt kill switch; an action over the cap waits for the
   next day, it is never dropped.
4. **What a corrected claim may change.** Data-entry and missing-information fields only (payer id, a blanked diagnosis restored from the coder's saved record, insurance
   details, an added note). It **never changes a CPT code, an ICD-10 code or a modifier**, and nothing creates a write-off or a refund. A denial that would need a code
   change, a duplicate, a timely-filing denial, an unknown reason code, an expired deadline, a missing deadline rule, or a claim still denied after the rounds allowed
   goes to **review for a person**. A write-off is only ever proposed as a review item, never done.
5. **Deadlines.** An appeal or a corrected claim is sent only if the Knowledge Book's deadline for that route (`krisnai.knowledge.deadlines.deadline`, evaluated on the
   simulation clock) is still open when it is sent. An expired route, or a rule the book cannot compute, escalates to a person and nothing is sent.
6. **Published rules.** Each denial is checked against the payer's published rules (coverage, prior authorization for that payer, service and date). When the payer
   contradicted its own published rule (or its own 271 answer), the reply says so and appeals on that ground.
7. **Records.** Each action writes an event (step `8 reply: ...`) with its approval label and the rule or evidence used, and a decision record line
   (`decision_records.jsonl`). Replies are idempotent (keyed by claim and round) and saved after every step.

## Consequences
- A remit, including a second remit from a reply, is what the payer simulator says it paid, not cash. Cash collected stays 0.00.
- Second-round remits use a distinct claim id `<claim>-R<n>` so they reconcile to a separate truth file (`truth_replies.csv`) without double counting the first remit.
- This shows the shape of the loop on synthetic data, not that unattended appeals are safe. Promotion of any action type is still a per-tenant config change backed by evidence.
