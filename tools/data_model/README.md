# Data model generator

Builds the KrisnnAI canonical data model deliverables in `docs/data_model/`:

- `KrisnnAI-Canonical-Data-Model.xlsx` (every table and column, with the sheets for IDs, sources, settings, allowed values, review changes)
- `KrisnnAI-Data-Dictionary.html` (self-contained, searchable, add table or field in the browser)
- `KrisnnAI-Agent-Field-Remap.xlsx` (every agent field mapped to its final table and column)
- `schema_sqlserver.sql` (tables, keys, foreign keys and column descriptions), `ER-diagrams.md` (Mermaid, one per stage) and `TABLE-CATALOG.md`

Run `python tools/data_model/build_all.py`. Needs `openpyxl`. Output paths can be overridden with
`KRISNNAI_OUT`, `KRISNNAI_REMAP_OUT` and `KRISNNAI_DICT_OUT`. If a workbook is open in Excel, write to another path and swap it in.

`python tools/data_model/db_up.py` starts a local SQL Server container (`docker-compose.db.yml`) and loads that schema into `krisnnai_canonical` for inspection; add `--reset` to rebuild it.
The password is generated into `.env.db` (git-ignored). See `docs/ARCHITECTURE.md` for how to browse it in VS Code.

## Where the model lives

| File | What it holds |
|---|---|
| `gen_core.py` | The eight journey tables (appointment, encounter, bill, claim and their details) and the helpers `common`, `audit`, `L`, `M_ I_ O_` |
| `gen_final.py` | Everything else: transactions, denials, AR, payment, agent output tables, reference tables, settings, allowed values, then the review changes, then the workbook |
| `plan/plan_A..D.py` | The 16 tables designed in the planned-table review, with `notes_A..D.md` explaining each |
| `build/` | Generated intermediate files (`model.json`, `plan_remap.json`); not committed |
| `input/KrisnnAI-Field-Mapping.xlsx` | The agent field list (1,830 rows) that the remap re-points |
| `remap.py`, `overrides*.py`, `decisions_map.py`, `build_remap.py` | How each agent field was placed, with the decision behind it |
| `test_plan.py` | Validates a table-design module: `python test_plan.py plan/plan_A.py` |
| `plan_brief.md` | The brief the design agents followed (rules for tables and columns) |
| `docs/data_model/agent-field-review-decisions.md` | The decision log |

## To change the model

Add or edit a table in `gen_final.py` (or a `plan/` module), run `build_all.py`, and commit the regenerated files in `docs/data_model/`.
Rules: first column `<table>_id`; client numbers in a restricted `<table>_number`; every column has a description and a fallback; no names, birth dates or addresses; the brand is spelled KrisnnAI.
