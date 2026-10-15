# The mock practice demo

One command builds a mock practice, runs all fifteen agents in shadow mode, and writes a single HTML page you can open.

```
.venv\Scripts\python.exe -m krisnai.cli demo --out out/demo --synthea out/synthea --as-of 2026-10-14
start out\demo\report.html
```

## What it does
1. Builds a book from the real Synthea output in `out/synthea` (837, 835, 999, 277CA, 271 and the PM feeds), with defects planted by the simulator: random
   denials, underpayments, rejections, missing documentation, coverage and authorization problems, deposit and posting gaps, enrollment gaps, patient balance
   cases and coding differences, **plus two payer-wide problems in the last 8 weeks**: one payer pays 30% under contract on its most-billed CPT, another denies
   its second most-billed CPT with CARC 50 at 60%.
2. Creates `out/demo/demo.sqlite` with one tenant (`demo`).
3. Runs `ops backfill` over the whole history: load, match, reconciliation gate, then every agent in dependency order.
4. Writes `out/demo/report.html`: the work queue, one section per agent (what it decided, example cards with their reasons and next steps, what was planted),
   the A15-lite leakage baseline scored against the answer key, and the payer/CPT slices A15 found below baseline.

The folder is wiped and rebuilt on every run. The answer keys are kept in `out/demo/truth/`, not in the inbox.

## Reading the page
- **Shadow banner:** every agent only proposes. Nothing is submitted, sent, changed or paid.
- **Work queue:** the control tower's open items by priority. "since go-live" separates items raised in the last 28 days from the history.
- **Agent sections:** the "planted" table is the answer key for that agent; the "decisions" table is what it proposed. Compare them.
- **Limits box:** the data is synthetic and written by the same team as the rules. It shows the pipeline works, not that it is right on a real practice, and it
  says nothing about staff time saved.

## Show incremental loading
The demo database is a normal KrisnAI database. Drop a new file in a folder and run a daily load against it:

```
set DEMO_SALT=demo-salt
.venv\Scripts\python.exe -m krisnai.cli --db-url sqlite:///out/demo/demo.sqlite ops daily --inbox C:\path\new_files --as-of 2026-10-15 --tenant 1
```

Files are loaded in dependency order, moved to `archive/<date>/` (or `rejected/<date>/` with a reason file), the gate checks the totals, and only the new
events are decided.

## If something is missing
- No `out/synthea`: `krisnai synthea run --yes` (needs Docker; downloads the Synthea jar and runs it) or point `--synthea` at any Synthea output folder.
- The run stops with "gated": the load did not reconcile; the report is not written. `ops status` and the `ops_run` row say why.
