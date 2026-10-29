# KrisnnAI RCM
Read `CLAUDE.md` (rules) and `docs/BUILD_PLAN.md` (milestones).

    python -m venv .venv && .venv/Scripts/pip install -e ".[dev]"
    .venv/Scripts/python -m pytest
    .venv/Scripts/python -m tests.fixtures.make_synthetic --out out/synthetic   # synthetic X12 + ground truth
