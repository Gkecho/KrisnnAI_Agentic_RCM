"""End-to-end check of the live system through its own HTTP API: plays the people (manager, biller, denial specialist, AR specialist, billing lead) for a few minutes
of real time at high speed, then reads the outcome back from Postgres.   Usage: python scenario_test.py [seconds] [rate]   (server must be running)"""
import sys
import time
from collections import Counter

import requests

B = "http://127.0.0.1:8766"
secs = float(sys.argv[1]) if len(sys.argv) > 1 else 120
rate = float(sys.argv[2]) if len(sys.argv) > 2 else 14400
requests.post(f"{B}/api/rate", json={"rate": rate})
requests.post(f"{B}/api/start")
done, t0 = Counter(), time.time()
PLAY = {"manager": {"approve_rule": "approve_rule"}, "biller": {"claim_hold_review": "fix_and_release", "fix_rejection": "correct_and_resubmit", "unsigned_note": "chase_provider"},
        "denial_specialist": {"denial_work": "send_appeal"}, "ar_specialist": {"claim_follow_up": "resubmit"}, "billing_lead": {"dispute_package": "send_dispute"}}
while time.time() - t0 < secs:
    for role, plan in PLAY.items():
        for t in requests.get(f"{B}/api/inbox", params={"role": role}).json()["tasks"]:
            action = next((a for k, a in plan.items() if k == t["task_type"] or a == t["task_type"]), None)
            if t["task_type"] == "rule_review":
                action = "approve_rule"
            if action and action in t["actions"]:
                r = requests.post(f"{B}/api/task/{t['agent_task_id']}/act", json={"action": action})
                done[(role, t["task_type"], "ok" if r.ok else "failed")] += 1
    time.sleep(3)
requests.post(f"{B}/api/pause")
m = requests.get(f"{B}/api/metrics").json()
st = requests.get(f"{B}/api/state").json()
print("simulated time reached:", st["sim"])
print("people actions:", dict(done))
print("metrics:", {k: m[k] for k in ("claims", "value", "decisions", "mirror", "tasks", "world")})
