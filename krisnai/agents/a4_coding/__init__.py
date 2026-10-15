"""A4 Coding & charge integrity copilot (M20), shadow mode, suggestions only."""

from krisnai.agents.a4_coding.agent import ACTION_TYPES, AGENT_ID, CODING_REVIEW, EVENT_TYPE, A4CodingAgent
from krisnai.agents.a4_coding.rules import COULD_BE_HIGHER, UNSUPPORTED, Finding, check, supported_level
from krisnai.agents.a4_coding.summary import format_variance, variance

__all__ = [
    "ACTION_TYPES",
    "AGENT_ID",
    "A4CodingAgent",
    "CODING_REVIEW",
    "COULD_BE_HIGHER",
    "EVENT_TYPE",
    "Finding",
    "UNSUPPORTED",
    "check",
    "format_variance",
    "supported_level",
    "variance",
]
