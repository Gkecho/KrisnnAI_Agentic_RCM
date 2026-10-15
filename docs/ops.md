# Operations: daily runs, backfill, the load gate (M22)

Shadow mode throughout: nothing here executes, sends or submits anything.

## The inbox
One folder the PM, EHR and clearinghouse files land in. `krisnai ops daily --inbox DIR --as-of DATE --tenant ID` loads what is there, in dependency order:
reference data (fee schedule, crosswalk, enrollments, screenings), then 837, then 999 / 277CA, then 835, then the PM feeds (visits, notes, charges,
appointments, 271, authorizations), then deposits, postings and patient feeds. Each file goes through the same idempotent loader as `krisnai ingest`
(file hash, control numbers), then moves to `archive/<run date>/`. A file that does not parse goes to `rejected/<run date>/` with a `.reason.txt` beside it.
Nothing is deleted. A second run on an empty inbox does nothing.

## The gate
After loading and matching, and before any agent runs: no failed files (unless `--allow-failed`), and the G0 reconciliation must pass as of the run date
(claim and remit totals, payment totals, remit-to-claim match rate, default 99%, tolerance 0.01). On failure the run stops, records `gate = failed` in `ops_run`
with the reasons, and no agent runs. Fix the data and run again.

## What a run does
For each date window, each agent in dependency order (A8, A5, A6, A7, A10, A3, A1, A9, A2, A11, A13, A12, A4, A15, A14): seed its tables, sweep, then replay
**only events that have no decision record yet** (`replay(only_new=True)`). Time-based agents sweep on a fixed calendar grid (7 days, 28 days for A9 and A15), so a
daily run and a long backfill raise the same events; A1 and A2 use their checkpoint windows; the tower gets one event per day for the last 7 days of a period.

`ops backfill --from --to --step-days 28 [--go-live DATE]` is the same run over a long range, in windows (a crash resumes by running it again). `--go-live` only
changes the report: cards raised on or after that date are counted as new, the rest as history.

`ops status` shows the watermark (the latest date every agent was advanced to by a run that finished ok) and the last run. Runs are rows in `ops_run`
(migration 0015).

## Master patient id
An optional `patient_crosswalk.csv` (`member_id`, `master_id`) is loaded like any feed. When a patient reference is created, a member id that is in the
crosswalk resolves to the master id's hash, so one person with several member ids is one patient. Limit: rows loaded before the crosswalk keep the member id
hash; history is append-only and is not relinked. A member id that maps to two different master ids rejects the file.

## Measured
One full backfill of the demo book (300 Synthea patients, about 1,800 claims, 60,000 events, 547 days of history, 28-day windows, all fifteen agents), SQLite on
the development PC, Python only:

| step | seconds |
|---|---|
| load (6,990 files) | 173 |
| match, gate | 1 |
| A3 documentation (17,000 events) | 247 |
| A12 patient (10,500) | 126 |
| A8, A11, A7, A1, A14, A15 | 50 to 84 each |
| the other agents | 15 to 38 each |
| **total** | **about 20 minutes** |

The first run took 65 minutes. Per-event cost was dominated by every agent rebuilding the full pricing snapshot for each distinct event day (40 events: 48 s
for A4, now 3 s) and by A12 reading whole tables for one claim (now 10 ms an event). The pricer is now built once per tenant and filtered by day.
Not yet done: a bulk insert path in the loader (load is 173 s for 7,000 files), and one Snapshot per A15 sweep date. SQL Server timings are not measured.
`krisnai ops bench --claims N` repeats the measurement on the plain synthetic set.

## Not here
Real SFTP or clearinghouse pickup (folder inbox only), a scheduler (call the CLI from Task Scheduler or cron), SQL Server tuning (SQLite was measured), relinking
history after a crosswalk arrives, and the engine safety gaps (kill switch, maker-checker, versioned policy, value ledger) that still gate any agent leaving
shadow.
