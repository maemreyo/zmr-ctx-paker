"""
Phase-Aware Context Selection for agent workflows.

Agents work in cycles: Discovery → Planning → Implementation → Verification.
Each phase benefits from a different ranking strategy:

  discovery  — directory trees + high-level signatures; low token density
  edit       — verbatim code + related type definitions; high token density
  test       — test files + mock deps + assertion patterns

Usage
-----
    from ws_ctx_engine.ranking.phase_ranker import AgentPhase, apply_phase_weights

    ranked = retrieval_engine.retrieve(query=q, top_k=100)
    ranked = apply_phase_weights(ranked, AgentPhase.EDIT)
"""

from __future__ import annotations

import dataclasses
from enum import Enum
from typing import Dict, List, Optional, Tuple


class AgentPhase(Enum):
    DISCOVERY = "discovery"
    EDIT = "edit"
    TEST = "test"


@dataclasses.dataclass
class PhaseWeightConfig:
    """Weight overrides applied by each agent phase."""
    semantic_weight: float = 0.5
    symbol_weight: float = 0.3
    signature_only: bool = False     # Force compression for every file
    include_tree: bool = False       # Always include directory tree
    max_token_density: float = 1.0   # Fraction of token budget used for code
    test_file_boost: float = 1.0     # Score multiplier for test files
    mock_file_boost: float = 1.0     # Score multiplier for mock/stub files


PHASE_WEIGHT_OVERRIDES: Dict[AgentPhase, PhaseWeightConfig] = {
    AgentPhase.DISCOVERY: PhaseWeightConfig(
        semantic_weight=0.2,
        symbol_weight=0.1,
        signature_only=True,
        include_tree=True,
        max_token_density=0.3,
        test_file_boost=1.0,
        mock_file_boost=1.0,
    ),
    AgentPhase.EDIT: PhaseWeightConfig(
        semantic_weight=0.5,
        symbol_weight=0.4,
        signature_only=False,
        include_tree=False,
        max_token_density=1.0,
        test_file_boost=1.0,
        mock_file_boost=1.0,
    ),
    AgentPhase.TEST: PhaseWeightConfig(
        semantic_weight=0.3,
        symbol_weight=0.3,
        signature_only=False,
        include_tree=False,
        max_token_density=0.8,
        test_file_boost=2.0,
        mock_file_boost=1.5,
    ),
}

# File patterns that identify test files
_TEST_PATTERNS = (
    "test_", "_test.", ".spec.", "/test/", "/tests/",
    "/spec/", "_spec.", "mock_", "_mock.",
)


def _is_test_file(path: str) -> bool:
    return any(pat in path for pat in _TEST_PATTERNS)


def _is_mock_file(path: str) -> bool:
    return "mock" in path.lower() or "stub" in path.lower()


def apply_phase_weights(
    ranked_files: List[Tuple[str, float]],
    phase: AgentPhase,
) -> List[Tuple[str, float]]:
    """
    Re-weight a ranked file list according to the agent's current phase.

    Args:
        ranked_files: List of (file_path, score) sorted descending.
        phase: Current agent phase.

    Returns:
        Re-sorted list with phase-specific score adjustments.
    """
    cfg = PHASE_WEIGHT_OVERRIDES[phase]
    adjusted: List[Tuple[str, float]] = []

    for path, score in ranked_files:
        new_score = score
        if cfg.test_file_boost != 1.0 and _is_test_file(path):
            new_score *= cfg.test_file_boost
        if cfg.mock_file_boost != 1.0 and _is_mock_file(path):
            new_score *= cfg.mock_file_boost
        adjusted.append((path, new_score))

    adjusted.sort(key=lambda x: x[1], reverse=True)
    return adjusted


def get_phase_config(phase: AgentPhase) -> PhaseWeightConfig:
    """Return the PhaseWeightConfig for *phase*."""
    return PHASE_WEIGHT_OVERRIDES[phase]


def parse_phase(value: Optional[str]) -> Optional[AgentPhase]:
    """Parse CLI --mode string into AgentPhase, or None if absent/invalid."""
    if not value:
        return None
    try:
        return AgentPhase(value.lower())
    except ValueError:
        return None
