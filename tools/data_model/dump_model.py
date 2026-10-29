import os, json
d = os.path.dirname(os.path.abspath(__file__))
B = os.path.join(d, "build")
os.makedirs(B, exist_ok=True)
src = open(os.path.join(d, "gen_final.py"), encoding="utf-8").read()
ns = {"__file__": os.path.join(d, "gen_final.py")}
exec(src.split("# =============================================================================================== WORKBOOK")[0], ns)
T = ns["T"]
order = ["1 Appointment", "2 Encounter", "3 Bill and claim", ns["G4"], ns["GA"], "Reference", "Data operations"]
def key(n):
    x = T[n]; g = order.index(x["group"]) if x["group"] in order else 9
    return (g, 0 if x["pair"] in ("header", "ledger", "reference") else 1, list(T).index(n))
out = {"tables": [], "tbd": [dict(zip(["name","phase","what","tier","enables","plugs","until"], r)) for r in ns["TBD"]],
       "allowed": [list(a) for a in ns["ALLOWED"]]}
for n in sorted(T, key=key):
    x = T[n]
    out["tables"].append(dict(name=n, group=x["group"], kind=x["pair"], priority=x["priority"], status=x["status"], what=x["what"], purpose=x["purpose"], metrics=x["metrics"], fallback=x["fallback"],
        cols=[dict(name=c[0], type=c[1], priority=c[2], link=c[3], restricted=bool(c[4]), desc=c[5], fb=c[6], **({"rev": ns["NEWF"][(n, c[0])][0], "why": ns["NEWF"][(n, c[0])][1], "agents": ns["NEWF"][(n, c[0])][2]} if (n, c[0]) in ns["NEWF"] else {})) for c in x["cols"]]))
out["plan_tables"] = list(ns["PLAN_TABLES_ALL"])
json.dump(out, open(os.path.join(B, "model.json"), "w", encoding="utf-8"), ensure_ascii=False)
print(len(out["tables"]), sum(len(t["cols"]) for t in out["tables"]), os.path.getsize(os.path.join(B, "model.json")))
json.dump({k: [[list(a), list(b)] for a, b in v.items()] for k, v in ns["PLAN_REMAP"].items()}, open(os.path.join(B, "plan_remap.json"), "w", encoding="utf-8"), ensure_ascii=False)
print("plan remap:", {k: len(v) for k, v in ns["PLAN_REMAP"].items()}, "| plan tables:", len(ns["PLAN_TABLES_ALL"]))
