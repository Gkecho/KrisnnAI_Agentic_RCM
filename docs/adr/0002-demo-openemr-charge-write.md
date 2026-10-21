# ADR-0002: Writing charges into the local demo OpenEMR, and policy-based coding approval in the demo

Status: **accepted for the demo** (Gk, 2026-10-21; amended same day). Date: 2026-10-21.

## Context
The live encounter stream (`docs/plan_live_encounter_stream.md`) needs OpenEMR to hold a coded charge so that OpenEMR's own generator can produce the 837P.
OpenEMR's REST API has no charge endpoint (spike, 2026-10-21), so a charge can only be entered by OpenEMR's own PHP code (`BillingUtilities::addBilling`) and
SQL setup inside our container. `CLAUDE.md` rule 2 says no code may write to a client PM/EHR database and limits write-back to tasks and notes.

## Decision
1. The exception covers **only the demo OpenEMR we run in Docker on this machine**, with synthetic data. It is not a client system.
2. The writer refuses any target that is not a local address (the same guard as `check_endpoint` for FHIR) and any container that is not ours.
3. **Exception-only coding (departure from `CLAUDE.md` rule 4, demo tenant only).** A code is auto-accepted only when *every* deterministic check passes: the documented
   elements support the level, no NCCI or MUE conflict, no authorization mismatch, nothing missing. The charge record then says "approved by policy <id>, rules <ids>", not a
   named person. Anything else goes to a coder with the reason it was routed (missing documentation, ambiguous procedure, unsupported level, a case the rules cannot settle).
   A random sample (default 10%) of auto-accepted codes still goes to a coder, so wrong auto-accepts can be found. Caps in config (daily maximum) stand in for the kill switch
   and blast-radius limits, which are **not built**. The setting is off by default; the demo tenant turns it on and the screen says so. Agents never write; only the demo
   orchestrator does, and only under this policy or after a named approval.
4. Every such write is recorded (who approved, which codes, when) and shown on screen as "demo OpenEMR write", distinct from agent proposals.
5. The writer is off by default and enabled per run by an explicit flag.

## Consequences
- Rule 4 stays as written for every real client: a person approves codes until a client signs a policy and evidence exists. The departure is a policy setting, not a code default.
- This does **not** change the rule for client systems. A real client's EMR stays read-only; write-back there still needs its own ADR, an adapter disabled by default,
  and policy evidence.
- It shows the shape of the loop, not that unattended automation is safe. Moving agents up the autonomy levels is still a per-action-type config change backed by evidence.
- The writer depends on OpenEMR 7.0.3 internals; pin that version.
