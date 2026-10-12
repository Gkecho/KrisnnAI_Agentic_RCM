"""The decision-inbox card: one fixed shape every agent uses for "here is something a person should look at".

A screen can render any agent's proposal from these keys alone, so agents do not invent their own layouts.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

CARD_KEYS = ("title", "why", "priority", "expected_value", "deadline", "owner", "next_steps", "evidence")


def build_card(
    title: str,
    why: list[str],
    priority: Decimal,
    expected_value: Decimal,
    deadline: date,
    owner: str,
    next_steps: list[str],
    evidence: list[dict],
) -> dict:
    """Plain strings and lists only, so a card survives being stored as JSON and read back unchanged."""
    return {
        "title": title,
        "why": list(why),
        "priority": str(priority),
        "expected_value": str(expected_value),
        "deadline": deadline.isoformat(),
        "owner": owner,
        "next_steps": list(next_steps),
        "evidence": list(evidence),
    }
