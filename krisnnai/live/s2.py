# ruff: noqa: E501
"""S2 of the live encounter stream: code a batch of synthetic transcripts and score the coder against the answer key.

No OpenEMR needed. The coder sees only the transcript text and the signed flag; the answer key (`Visit.expected`) is read
here, after the fact, to score it. Records go to `coding_records.jsonl`, the score to `summary.json`.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import date
from pathlib import Path

from krisnnai.live.coder import Coder, Policy
from krisnnai.live.transcripts import generate


def run_s2(out: Path, count: int = 50, seed: int = 7, policy_on: bool = True, start: date = date(2026, 10, 24)) -> dict:
    visits = generate(seed, count, start)
    coder = Coder(Policy(enabled=policy_on, seed=seed))
    recs = [(v, coder.code(v.visit_id, v.text, v.signed, v.day)) for v in visits]
    clean = [(v, r) for v, r in recs if v.expected.route == "auto"]
    problems = [(v, r) for v, r in recs if v.expected.route == "coder"]
    auto_ok = sum(1 for v, r in clean if r.route == "auto" and r.cpt == v.expected.cpt and r.dx[0][0] == v.expected.dx)
    sampled = sum(1 for _, r in clean if r.reason == "qa_sample")
    routed_right = sum(1 for v, r in problems if r.route == "coder" and r.reason == v.expected.reason)
    summary = {
        "visits": len(recs), "policy_on": policy_on, "clean": len(clean), "problematic": len(problems),
        "auto_accepted": sum(1 for _, r in recs if r.route == "auto"),
        "auto_accepted_correct": auto_ok, "clean_sampled_to_coder": sampled,
        "clean_held_back_other": len(clean) - auto_ok - sampled,
        "problematic_routed_with_right_reason": routed_right,
        "problematic_auto_accepted": sum(1 for _, r in problems if r.route == "auto"),
        "routes": dict(Counter(f"{r.route}:{r.reason}" if r.reason else r.route for _, r in recs)),
    }  # fmt: skip
    out.mkdir(parents=True, exist_ok=True)
    (out / "coding_records.jsonl").write_text(
        "".join(json.dumps({**r.to_dict(), "expected": v.expected.__dict__}) + "\n" for v, r in recs), encoding="utf-8")
    (out / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    return summary
