"""Every agent the runner advances, in dependency order, with how it is driven.

`cadence` is the number of days between a time-based agent's sweep dates. Sweep dates sit on a fixed calendar grid
(ordinal day divisible by the cadence), so a run on any day produces the same events a long backfill would: the grid
point is the same wherever the window starts. Agents without a cadence are driven by their own windows (checkpoints,
one event per day) or have no sweep at all (event driven, replayed over new events only).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True)
class Step:
    name: str  # a1 ... a15
    agent_id: str
    make_agent: Callable  # () -> Agent
    sweep: Callable | None = None  # (engine, tenant, start, end[, every_days]) -> result with .events
    cadence: int | None = None  # grid spacing in days for sweeps that take `every_days`
    seed: Callable | None = None  # (session) -> int rows added


def grid_start(start: date, cadence: int) -> date:
    """First date on or after `start` whose ordinal is a multiple of `cadence`."""
    return start + timedelta(days=(-start.toordinal()) % cadence)


def steps() -> list[Step]:
    from krisnnai.agents import a9_learning as a9m
    from krisnnai.agents.a1_clearance import A1ClearanceAgent
    from krisnnai.agents.a1_clearance import sweep as a1_sweep
    from krisnnai.agents.a2_authorization import A2AuthorizationAgent
    from krisnnai.agents.a2_authorization import seed_defaults as a2_seed
    from krisnnai.agents.a2_authorization import sweep as a2_sweep
    from krisnnai.agents.a3_documentation import A3DocumentationAgent
    from krisnnai.agents.a3_documentation import sweep as a3_sweep
    from krisnnai.agents.a4_coding import A4CodingAgent
    from krisnnai.agents.a5_prevention import A5PreventionAgent
    from krisnnai.agents.a5_prevention import seed_defaults as a5_seed
    from krisnnai.agents.a6_submission import A6SubmissionAgent
    from krisnnai.agents.a6_submission import seed_defaults as a6_seed
    from krisnnai.agents.a7_ar import A7ArAgent
    from krisnnai.agents.a7_ar import sweep as a7_sweep
    from krisnnai.agents.a8_denial import A8DenialAgent
    from krisnnai.agents.a8_denial import seed_defaults as a8_seed
    from krisnnai.agents.a10_underpay import A10UnderpaymentAgent
    from krisnnai.agents.a11_cash import A11CashAgent
    from krisnnai.agents.a11_cash import sweep as a11_sweep
    from krisnnai.agents.a12_patient import A12PatientAgent
    from krisnnai.agents.a12_patient import sweep as a12_sweep
    from krisnnai.agents.a13_credentialing import A13CredentialingAgent
    from krisnnai.agents.a13_credentialing import sweep as a13_sweep
    from krisnnai.agents.a14_tower import A14TowerAgent
    from krisnnai.agents.a14_tower import sweep as a14_sweep
    from krisnnai.agents.a15_investigator import A15InvestigatorAgent
    from krisnnai.agents.a15_investigator import sweep as a15_sweep

    return [
        Step("a8", "a8_denial", A8DenialAgent, seed=a8_seed),
        Step("a5", "a5_prevention", A5PreventionAgent, seed=a5_seed),
        Step("a6", "a6_submission", A6SubmissionAgent, seed=a6_seed),
        Step("a7", "a7_ar", A7ArAgent, a7_sweep, 7),
        Step("a10", "a10_underpay", A10UnderpaymentAgent),
        Step("a3", "a3_documentation", A3DocumentationAgent, a3_sweep, 7),
        Step("a1", "a1_clearance", A1ClearanceAgent, a1_sweep),
        Step("a9", "a9_learning", a9m.A9LearningAgent, a9m.sweep, 28),
        Step("a2", "a2_authorization", A2AuthorizationAgent, a2_sweep, seed=a2_seed),
        Step("a11", "a11_cash", A11CashAgent, a11_sweep, 7),
        Step("a13", "a13_credentialing", A13CredentialingAgent, a13_sweep, 7),
        Step("a12", "a12_patient", A12PatientAgent, a12_sweep, 7),
        Step("a4", "a4_coding", A4CodingAgent),
        Step("a15", "a15_investigator", A15InvestigatorAgent, a15_sweep, 28),
        Step("a14", "a14_tower", A14TowerAgent, a14_sweep),
    ]
