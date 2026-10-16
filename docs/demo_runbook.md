# Demo runbook: what to show, in what order, and what not to claim

Goal: show a boss what KrisnAI can do today, honestly. Everything below runs on synthetic data in shadow mode. The product preview
(`krisnai-site/product.html`) is the picture of the finished product; this runbook is the proof that the engine behind it works. Screens refer to
`docs/ui_mapping.md`.

## One-sentence story
"Give it a practice's claims and remits. It finds the money that is leaking, says why, and queues the work for a person, with nothing sent anywhere. Here it
is on a mock practice with problems we planted, so we can check whether it found them."

## Before the meeting (15 minutes, once)
1. Free memory: close what you do not need. The full test suite and several containers together ran the PC out of memory earlier. For the demo you need only
   Docker with OpenEMR (and the Microsoft FHIR server if you show it). Stop Supabase and the Postgres containers.
2. `krisnai demo` output exists in `out/demo` (`report.html`, `demo.sqlite`, `truth/`). To rebuild: see `docs/demo.md` (takes a while; do it the day before).
3. Open these tabs: `out/demo/report.html`, `out/stage1/stage1_report.html`, the product preview (`product.html`), a terminal in the repo.
4. Stedi test key in the environment of the terminal only (`STEDI_API_KEY`), never on screen. Rotate the key you pasted in chat earlier.
5. Rehearse the three live commands once. If a live step fails, say so and move to the saved report. Do not improvise.

## The 12-minute path
| Min | Show | What it proves | Say |
|---|---|---|---|
| 0-1 | Preview **My work** and **Agent activity** | The product shape | "This is where it is going. The next screens are the engine behind it." |
| 1-4 | `out/demo/report.html`: the shadow banner, then the work queue | A mock practice: files loaded, reconciliation gate passed, 15 agents ran, a ranked queue. Quote the counts shown on the page (the full run loaded 6,962 files and built 62,638 events as of 2026-10-14; `ui_data.json` is regenerated from it) | "Every item says why, what to do next, and the dollars. Nothing was sent." |
| 4-6 | Report: the **planted** table vs the **decisions** table for A8 (denials) and A10 (underpayments) | Answer key vs findings. The simulator planted one payer denying a CPT at 60% (CARC 50) and one payer paying 30% under contract | "We hid the answers in a separate folder, then compared." Show `truth/` is separate |
| 6-7 | Report: A15 leakage baseline and slices | Payer-wide patterns found beyond single claims | Read the slice with the largest dollars, then say the data is synthetic |
| 7-9 | `krisnai stedi` (live) | A real call to a clearinghouse sandbox: 270 out, 271 parsed (copay $40, coinsurance 20%, deductible remaining $1,000) | "Real protocol, a test patient. Claim status, claims and remits are not available in their test mode, so those run on our mock." |
| 9-10 | `out/stage1/stage1_report.html` | Bots against mock clearinghouse and portal; portal hands MFA, CAPTCHA and screen changes to a person | "It stops safely when a portal changes." Show a handed-off case |
| 10-11 | FHIR: `krisnai openemr status`, then the pulled feeds | Appointments, visits and notes written to OpenEMR 7.0.3 and read back identical (50 patients, 665 appointments, 843 encounters, 790 notes) | "Same path a real EMR would use. OpenEMR is a stand-in, not a vendor EMR." |
| 11-12 | Preview **Agent controls** and **Approval queue** | The honest gap | "Kill switch, maker-checker and policy history are the next build. Until then it only proposes." |

## What you can say
- 15 agents run in shadow mode over claim, remit, ack, status and PM data, and each decision is recorded with its rules, inputs and dollars.
- Reconciliation gate: a load is rejected if totals do not match.
- Re-running a day does not duplicate anything.
- No patient names in logs or outputs; patients are salted references.

## What you must not say
- Not "it recovered $X". Nothing was recovered. These are detected and proposed amounts on synthetic data written by the same team as the rules.
- Not "tested on real payers". Only Stedi eligibility, in sandbox, touched an outside service.
- Not "works with Epic or athenahealth". OpenEMR is open source, and the integration pattern is the same, not the vendor profiles.
- Not "agents at levels L1 to L4". Every agent is L0 / shadow. The levels in the preview are the target.
- Not "time saved". Nothing here measures staff time.

## Likely questions
| Question | Honest answer |
|---|---|
| Does it work on our data? | The next step is a read-only load of one practice's extract, replayed through History replay with the 10% holdout; the holdout is not built yet |
| Can it submit claims? | Only through the partner clearinghouse, only when policy allows it; today the policy is off for everything |
| What about HIPAA? | No real PHI anywhere in this repo. A BAA and hosting decision come before a real client |
| What does it need from us? | An 835/837 extract, PM tables, and one read-only EMR route (HL7, FHIR, or a nightly extract) |
| How accurate is it? | Measured on synthetic answer keys only. Accuracy on real data is the point of the replay and shadow period |

## Gaps this demo exposes (fix before a customer pilot)
1. Engine guardrails (kill switch, blast radius, maker-checker, versioned policy). Feeds Agent controls, Approval queue, Trust & QA.
2. Value ledger holdout (10%), so "confirmed" is measurable.
3. Per-claim timeline query and the approval API.
4. A6 and A7 can raise two cards for one claim (for example SYNC000357); suppress A7 when an open A6 rejection exists.
5. Preview screens still use illustrative data. A static `ui_data.js` hand-off exists (`docs/ui.md`); wiring one preview screen to it is the quickest way to show real output inside the product picture.
