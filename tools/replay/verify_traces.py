"""Checks the decision traces against the database: re-runs each logged read on Postgres and compares the answer with what the agent saw.

Usage (server must be running and a replay finished):  python verify_traces.py [samples-per-decision-type]
"""
import sys
from collections import defaultdict

import requests

BASE = "http://127.0.0.1:8765"
N = int(sys.argv[1]) if len(sys.argv) > 1 else 6


def same(logged, cols, rows):
    if not rows:
        return False
    row = dict(zip(cols, rows[0]))
    if isinstance(logged, dict):
        for k, v in logged.items():
            if k not in row:
                continue
            a, b = v, row[k]
            if a is None and b is None:
                continue
            try:
                if abs(float(a) - float(b)) < 0.005:
                    continue
            except (TypeError, ValueError):
                pass
            if str(a) != str(b):
                return False
        return True
    return str(logged) == str(rows[0][0])


state = requests.get(f"{BASE}/api/state").json()
last = state["last"]
log = open(sorted(__import__("pathlib").Path(__file__).parent.joinpath("logs").glob("replay-*.jsonl"))[-1], encoding="utf-8").read().splitlines()
import json
traces = [json.loads(x) for x in log]
by = defaultdict(list)
for t in traces:
    by[t["decision_type"]].append(t)
print(f"{len(traces)} traces logged; types: { {k: len(v) for k, v in by.items()} }\n")
bad = 0
for dtype, lst in sorted(by.items()):
    step = max(1, len(lst) // N)
    ok = no = skipped = 0
    for t in lst[::step][:N]:
        for i, rd in enumerate(t["reads"]):
            if not rd.get("runnable", True):
                skipped += 1
                continue
            r = requests.post(f"{BASE}/api/trace/{t['id']}/run/{i}")
            if r.status_code != 200:
                no += 1
                print(f"  ERROR {dtype} #{t['id']} read {i}: {r.text[:200]}")
                continue
            j = r.json()
            if same(rd["result"], j["columns"], j["rows"]):
                ok += 1
            else:
                no += 1
                print(f"  DIFF  {dtype} #{t['id']} read {i} ({rd['table']}): logged={rd['result']} db={dict(zip(j['columns'], j['rows'][0])) if j['rows'] else 'no rows'}")
    bad += no
    print(f"{dtype:24s} reads re-run: {ok + no:3d}   same: {ok:3d}   different: {no}   (not runnable: {skipped})")
print("\nresult:", "every re-run read matches what the agent saw" if not bad else f"{bad} read(s) differ")
