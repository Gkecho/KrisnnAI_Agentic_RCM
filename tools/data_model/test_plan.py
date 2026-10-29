"""Validate one agent's table-design module against the real model.  Usage: python test_plan.py plan/plan_X.py"""
import os, re, sys

d = os.path.dirname(os.path.abspath(__file__))
os.environ["KRISNNAI_SKIP_PLAN"] = (re.search(r"plan_([A-Z])", sys.argv[1]) or [None, ""])[1]  # leave the module under test out of the model
src = open(os.path.join(d, "gen_final.py"), encoding="utf-8").read()
ns = {"__file__": os.path.join(d, "gen_final.py")}
exec(re.split(r"^# =+ WORKBOOK$", src, flags=re.M)[0], ns)
T = ns["T"]
before = {n: len(v["cols"]) for n, v in T.items()}
tbd_before = [r[0] for r in ns["TBD"]]

path = sys.argv[1]
exec(compile(open(path, encoding="utf-8").read(), path, "exec"), ns)

errs = []
new = [n for n in T if n not in before]
for n, c in before.items():
    if len(T[n]["cols"]) != c:
        errs.append(f"existing table {n} was modified (columns {c} -> {len(T[n]['cols'])}); not allowed")
PRI = {ns["M_"], ns["I_"], ns["O_"]}
for n in new:
    t = T[n]
    cols = t["cols"]
    names = [c[0] for c in cols]
    if t["priority"] not in PRI:
        errs.append(f"{n}: bad table priority")
    for k in ("what", "purpose", "metrics", "fallback"):
        if not t.get(k):
            errs.append(f"{n}: empty {k}")
    if names[0] != f"{n}_id":
        errs.append(f"{n}: first column must be {n}_id")
    for x in {x for x in names if names.count(x) > 1}:
        errs.append(f"{n}: duplicate column {x}")
    for must in ("tenant_id", "source", "known_at", "loaded_at"):
        if must not in names and t["pair"] != "reference":
            errs.append(f"{n}: missing {must}")
    for c in cols:
        if len(c) != 7:
            errs.append(f"{n}.{c[0]}: column tuple must have 7 items (use L(...))")
            continue
        if c[2] not in PRI:
            errs.append(f"{n}.{c[0]}: bad priority {c[2]}")
        if not c[5] or not c[6]:
            errs.append(f"{n}.{c[0]}: description and fallback are required")
        if c[3] and c[3] not in T:
            errs.append(f"{n}.{c[0]}: links to unknown table {c[3]}")
        if re.search(r"\b(fact|dim)_", c[0]) or c[0].startswith(("fact", "dim")):
            errs.append(f"{n}.{c[0]}: no fact/dim words in names")
    if re.search(r"\b(fact|dim)\b", n):
        errs.append(f"{n}: no fact/dim words in names")

REMAP = ns.get("REMAP", {})
OK = {"Exact", "Renamed", "Derived", "Partial", "Dropped", "Planned table", "Added"}
for k, (tb, col, res, note) in REMAP.items():
    if res not in OK:
        errs.append(f"REMAP {k}: result {res} not in {sorted(OK)}")
    if res in ("Exact", "Renamed", "Partial", "Added") and (tb not in T or col not in [c[0] for c in T[tb]["cols"]]):
        errs.append(f"REMAP {k}: target {tb}.{col} does not exist")
for n in ns.get("TBD_DONE", []):
    if n not in tbd_before:
        errs.append(f"TBD_DONE: {n} is not on the TBD list")

print(f"new tables: {new}")
print(f"columns: {sum(len(T[n]['cols']) for n in new)} | remap entries: {len(REMAP)} | TBD_DONE: {ns.get('TBD_DONE', [])}")
if errs:
    print("ERRORS:")
    for e in errs:
        print("  -", e)
    sys.exit(1)
print("OK: module is valid")
