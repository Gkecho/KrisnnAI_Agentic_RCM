# UI: how the site and the agents connect

The planned UI follows the existing site (`krisnnaiagents.vercel.app`, folder `krisnai-site`): static HTML pages, a `data.js` per view, and a small Vercel
login middleware. The agents already produce everything such a UI needs; the missing piece is the hand-off.

## Now: a data file the pages load
`krisnai demo` (and later any run) writes `out/demo/ui_data.json` and `out/demo/ui_data.js` (`window.KRISNAI_LIVE = {...}`), the same pattern as the site's
`data.js` files. A page needs one `<script src="ui_data.js">` and plain DOM code; no server, no build step.

| key | holds |
|---|---|
| `meta` | `as_of`, `shadow: true`, run status and gate, the planted payer-wide problems |
| `queue` | open work items, highest priority first (agent, owner, title, value, deadline, overdue, why, next steps, evidence) |
| `agents` | one entry per A1 to A15: counts, actions with dollars, what was planted, up to three example cards |
| `baseline` | A15-lite leak totals (detected, not recovered) by type |
| `slices` | payer and payer+CPT slices below baseline with dollars and largest cause |

Money is a two-decimal string; dates are ISO strings; there is no raw patient data (patients are salted hashes and claims are referenced by id).

## Suggested screens (mapped to the site's modules)
1. **Work queue** (`queue`): the control tower inbox; filter by agent and owner; open a row to see why and next steps.
2. **Agent view** (`agents`): the site's workflow module for that agent, with live counts and example cards beside the static description.
3. **Leakage baseline and slices** (`baseline`, `slices`): the revenue assurance page.
4. **Run status** (`meta`): what was loaded, the gate, shadow banner.

## Later: a live API
The pages read a file today. For live data the same JSON shape can be served by a small read-only endpoint (`/api/queue`, `/api/agents`, ...) in front of the
database. FastAPI cannot load on the development PC (Windows Smart App Control blocks `pydantic-core`), so the first server is a standard-library
`http.server` wrapper or a function on another machine. Approving, rejecting or editing an item (A9 rule approval, task completion) needs the approval API
and maker-checker controls that are not built yet; the UI is read-only until they are.

## Not decided here
Authentication beyond the site's existing login, per-client tenancy in the URL, and where the database is hosted. Real data must not be placed in a public
Vercel deployment: the site is a presentation layer and the JSON for a real client belongs behind that client's own access control.
