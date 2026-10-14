# Synthea data foundation (M12a)

Synthea (github.com/synthetichealth/synthea) makes synthetic patients, visits and diagnoses. It does not make claims
that get rejected, denied or underpaid. `krisnai/synthea/` bills Synthea's visits, runs a seeded payer simulator that
plants known problems, and writes the same files `krisnai ingest` already reads, so agents see this data exactly as
they would see a client's.

## Flow

```
krisnai synthea run   --population 300 --seed 7 --yes     Synthea in Docker (jar download + image pull)
krisnai synthea build --in out/synthea --out out/book --as-of 2026-06-30
krisnai ingest out/book --tenant 1 ; krisnai match --tenant 1
krisnai a8|a5|a6 seed ; krisnai a8|a5|a6 replay ... ; krisnai tower --tenant 1 --as-of 2026-06-30
```

`run` without `--yes` only prints the steps. Java is not installed on this PC, so Synthea runs in a container
(`eclipse-temurin:17-jre`); Docker Desktop must be running.

## What is built

| File | Job |
|---|---|
| `runner.py` | the Docker command, jar download |
| `reader.py` | Synthea CSVs (patients, encounters, claims, claims_transactions, payers) |
| `bundles.py` | one billable bundle per professional claim; counts what it skips |
| `crosswalk.py` | placeholder SNOMED to CPT / ICD-10 and CPT base fees |
| `simulate.py` | payer behaviour, planted problems, ground truth, file writing |
| `x12out.py` | 837P, 999, 277CA, 835 text |

Planted: denial, timely_filing, underpayment, rejection, unbilled_visit, plus claims still unpaid or stuck (10%).
`ground_truth.csv` lists each planted problem; `open_ar.csv` lists unpaid claims. Nothing is chosen because it is
unpaid: payment timing decides what is open at `--as-of`.

## Documentation feed (`--documentation`)

Adds `visits.csv` with every billed service (one visit per claim line), `notes.csv`, `charges.csv` and `doc_truth.csv`. Planted: missing note (5%), unsigned note
(6%), missing required element (6%), charge keyed 4+ days late (8%), and the unbilled visits get a signed note and no charge. Defects go only on visits at least 10
days old at `--as-of`. It has its own random stream, so the claims and payer behaviour are unchanged. Synthea itself has no note, signature or charge-entry data;
those fields are simulated.

## Payer rate cuts

`krisnai synthea build ... --rate-cut PAYER:CPT:YYYY-MM-DD:PCT` (repeatable) makes a payer pay PCT% under the contract on one CPT from a date. Each affected
line is an underpayment in `ground_truth.csv`. It is how A10's payer-wide pattern detection is tested; without the flag the output is unchanged.

## Limits (read before trusting a number)

- Synthea codes in SNOMED. The CPT / ICD-10 crosswalk is a small stand-in; unmapped codes fall back to an E/M code by
  visit class and a general-exam diagnosis, and are counted in the build report.
- Synthea claims are not used for prices: charges come from the crosswalk fee table (billed = base x 1.6), payers pay
  base x a per-payer multiplier. Payer behaviour is a stable function of the payer name, not a real contract.
- Inpatient, home and similar visit classes are not billed on a 837P and are skipped (counted).
- The simulator and the agents' rules were written by the same team: 100% recall on the planted set shows the
  pipeline is wired correctly, not that the rules would find problems in a real practice.
- The test suite uses a hand-made folder with Synthea's file and column names (`tests/fixtures/synthea_mini.py`).
  A real Synthea run is a manual step; the column names are from the Synthea CSV data dictionary and were not yet
  checked against a real run on this PC.

## First real Synthea run (2026-10-14, 300 patients, seed 7, Massachusetts)

The reader's column names matched Synthea's real CSVs on the first run. Two things the mini folder could not show:
- Synthea writes a whole lifetime of claims (back to 1929): the build keeps the last 18 months (`--lookback-days`).
- 73% of claims shared a patient and a day with another claim (one visit recorded as several encounters). Billed
  separately, A5 flagged 40% of claims as duplicates. They are now merged into one claim per patient, day and payer
  (1,789 merges). That was a bundler flaw, not an A5 flaw.

Result on the merged book (1,776 claims, 435 planted problems): all five Wave 1 agents ran in shadow, 0 executed;
the leakage diagnostic found 435 of 435. A5 flagged 65 claims (44 late filings, 21 NCCI pairs on merged visits).
The forecast backtest over 8 past dates had WAPE 6.7% with the actual value inside the range 6 times in 8.
Unmapped: 9,749 procedure codes and 1,309 diagnoses fall back to generic codes (crosswalk is a stand-in).
