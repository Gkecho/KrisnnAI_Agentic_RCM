# Stage 1 integrations: clearinghouse, FHIR, portal bots

All of this runs against **local mock or sandbox services**. Nothing here talks to a real payer, clearinghouse or EMR, and the clients refuse any non-local
URL unless `KRISNAI_ALLOW_REAL_ENDPOINTS=1` is set. Credentials come from environment variables only.

```
.venv\Scripts\python.exe -m krisnai.cli stage1 --out out/stage1 --synthea out/synthea --as-of 2026-06-30 [--with-fhir]
start out\stage1\stage1_report.html
```

## 1. Clearinghouse (`krisnai/integrations/clearinghouse/`)
| piece | what it does |
|---|---|
| `x12_out.py` | builds **270** (eligibility), **276** (claim status) and the **replacement 837** (CLM05-3 = 7 with REF*F8); reads the **277** status answer |
| `mock_server.py` | FastAPI service: `POST /v1/eligibility` (270 to 271), `/v1/claim-status` (276 to 277), `/v1/claims` (837 to 999 + 277CA). Bearer token. Answers come from the book's answer keys and its 835 / 277CA files |
| `client.py` | `ClearinghouseClient`: the same four calls over HTTPS to any base URL; local-only by default |
| `bots.py` | **eligibility bot** (A1's flagged appointments), **status bot** (A7's open claims), **resubmission bot** (A6's returned claims). Responses are written as X12 files the daily loader reads; every call is logged with member ids masked |
| `claim_store.py` | what a bot may read: the practice's own extract (837s, 835s, 277CAs, appointments). The database holds only hashes, so a bot needs the extract to know a member id |

**What it proves:** the whole loop is wired. A1 flags an appointment, the bot sends a 270, a 271 comes back and is loaded, and at the next checkpoint the gap is
gone (the control run without the bot still has it). **What it does not prove:** that a real clearinghouse or payer answers this way. The mock accepts any
replacement of a claim it returned, so it shows the transport and the loop, not whether a correction is right.

### Stedi (built, not yet run against the live sandbox)
`stedi.py` implements the same three calls over Stedi's **raw X12** healthcare endpoints (`eligibility/v3/raw-x12`, `claimstatus/v2/raw-x12`,
`professionalclaims/v3/raw-x12-submission`, base `https://healthcare.us.stedi.com/2024-04-01`), so the repo's own 270/276/837 builders and 271/277/277CA
parsers are used unchanged. Request and response shapes come from Stedi's published reference (checked 2026-10-16) and are tested with recorded-shape
responses; **no call has been made to Stedi from this repo**. Safety: the key comes from `STEDI_API_KEY` only; non-local URLs need
`KRISNAI_ALLOW_REAL_ENDPOINTS=1`; claim submission needs `KRISNAI_ALLOW_STEDI_SUBMIT=1` and an explicit test-key confirmation (a production key would send a
real claim); a response in production mode stops the client unless `KRISNAI_ALLOW_STEDI_PRODUCTION=1`.

To run the live check yourself (set the key in your own shell, never in chat):
```
set STEDI_API_KEY=<your TEST-mode key>
set KRISNAI_ALLOW_REAL_ENDPOINTS=1
.venv\Scripts\python.exe -m krisnai.cli stedi
.venv\Scripts\python.exe -m pytest tests/test_stedi.py -k live
```
Known gaps: Stedi's test mode only answers its documented mock subscribers exactly (the Aetna mock is a dependent case; our 270 sends the subscriber
loop only, so the first live call may return an AAA error to adjust), the auth header style (bare key vs `Key <key>`) should be confirmed on the first call
(`KRISNAI_STEDI_AUTH_STYLE=key` switches it), and a new-style JSON eligibility API exists that this does not use.

## 2. FHIR (`krisnai/integrations/fhir/`)
| piece | what it does |
|---|---|
| `docker-compose.fhir.yml` | **microsoft/fhir-server** (R4) on SQL Server 2022, security off, `127.0.0.1:8080` only. The SQL password is generated per run under `out/fhir/` |
| `client.py` | search with paging and `_lastUpdated`, transaction bundles, capability check; local-only guard |
| `mapper.py` | Patient, Practitioner, Organization, Appointment, Encounter, DocumentReference to and from `appointments.csv`, `visits.csv`, `notes.csv` |
| `sync.py` | `seed` (feeds to server) and `pull` (server to feeds) |

```
krisnai fhir up                                   # first start pulls about 2 GB of images
krisnai fhir seed --feeds out/demo/archive/2026-10-14
krisnai fhir pull --out out/fhir_pull [--since 2026-06-01]
krisnai fhir down
```

**Measured:** 1,777 appointments, 2,243 encounters and 2,134 notes went into the Microsoft FHIR server and came back with zero differing rows.
Notes (from this build): the server needs placeholder `FhirServer__Security__Authentication__Authority` / `Audience` values even with security off, a
DocumentReference needs `content`, and `/metadata` only answers once those are set. A real EMR's FHIR API will differ in profiles, scopes (SMART on FHIR
authorization) and which resources it exposes; the mapper reads only the resources and fields above.

## 3. Portal bots (`krisnai/integrations/portal/`)
| piece | what it does |
|---|---|
| `mock_portal.py` | login, claim search, claim detail (status, pend reason, amount), records-request page; `layout=2` renames elements to model a redesign |
| `driver.py` | `HttpDriver` (httpx + id lookup, no browser) and the `ScreenChanged` error |
| `bots.py` | `claim_status_bot`: log in, find the claim, read status, reason and amount, read an open records request, save each page as evidence |

Behaviour built in and tested: credentials from environment variables, never logged or saved; every page checked for the elements the bot expects, and the
first mismatch **stops the whole run** with nothing else requested; a rate limit stops the run; a wrong password stops at sign in. A browser driver
(Playwright) is not installed; the HTTP driver covers server-rendered portals. Real portals add MFA, CAPTCHA and JavaScript, where the bot must stop and hand
to a person; none of that is exercised here.

## Failure behaviour (what the bots do when things go wrong)
Proven by `tests/test_ch_faults.py` (31 tests) and `tests/test_portal_hard.py` (12 tests), all against local mocks with deterministic fault injection
(`clearinghouse/faults.py`, `FaultyClient`).

**Clearinghouse bots** (eligibility, status, resubmission)
| what goes wrong | what the bot does |
|---|---|
| timeout, connection error, 5xx on a read-only call | retried up to `retries` (default 2, optional backoff); batch continues |
| 400-class refusal | no retry; that subject is `error`, the batch continues |
| 401/403 | stops the batch at once; the rest are `not_attempted` |
| garbage or truncated reply | `bad_response`; the reply is **not** written to the inbox |
| reply for another patient / claim (checked by the echoed reference) | `bad_response`; not kept, so no agent reads another subject's answer |
| 3 failures in a row (`breaker_limit`) | circuit opens; the rest are `not_attempted` |
| resubmission: timeout / 5xx / lost reply | `unknown_sent`: never retried or resent; the status bot or a person resolves it |
| resubmission: connection error | retried (the request never left) |
| resubmission: any repeat run | skipped via `sent_ledger.jsonl` (written *before* the send); one replacement per (claim, payer claim number) |

The log carries outcome and a short reason only: no full member id, token, or reply body.

**Portal bot** stops and records `needs_human` (with `handoff` = mfa, captcha, js_required, account_locked, maintenance, session_expired) and requests
nothing further. It never tries to solve a challenge, never retries a locked account, posts no password when it sees a CAPTCHA on the sign-in page, and
re-logs in at most once per page and five times per run.

**Not proven:** real clearinghouse error shapes (Stedi's 4xx/5xx bodies), real portal MFA/CAPTCHA flows, a JavaScript browser (Playwright is not
installed here, so script-drawn pages are detected and handed off, not read), duplicate delivery from a real queue, and anything past the bots (the
engine-level kill switch, maker-checker and write-back failure tests are still open, see `docs/ROADMAP.md`).

## What is still not done
Real authentication flows and payer/portal behaviour, vendor-specific clearinghouse formats (Stedi, Optum), a browser driver, FHIR write-back to an EMR (the
repo rules limit write-back to tasks and notes behind a disabled adapter), and any measurement of staff time saved (needs the Stage 3 baseline and control
group).
