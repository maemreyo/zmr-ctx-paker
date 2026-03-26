"""
Integration tests for phase-aware context selection.

Verifies that apply_phase_weights() produces meaningfully different rankings
for each agent phase — not just that the code runs, but that the behavior is
correct from an agent-workflow perspective:

  - discovery: test files are not boosted; scores stay low
  - edit:      no multipliers applied; scores pass through unchanged
  - test:      test files rank above same-score source files
"""

from __future__ import annotations

import pytest

from ws_ctx_engine.ranking.phase_ranker import (
    AgentPhase,
    apply_phase_weights,
    get_phase_config,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mixed_ranked_files() -> list[tuple[str, float]]:
    """A realistic ranked list with source, test, and mock files."""
    return [
        ("src/auth/handler.py", 0.90),
        ("src/auth/models.py", 0.80),
        ("tests/unit/test_auth.py", 0.75),
        ("src/utils/helpers.py", 0.70),
        ("tests/integration/test_api.py", 0.65),
        ("src/api/routes.py", 0.60),
        ("mocks/mock_auth.py", 0.55),
        ("src/db/session.py", 0.50),
    ]


@pytest.fixture()
def equal_score_files() -> list[tuple[str, float]]:
    """Source and test files with identical base scores to isolate boost effect."""
    return [
        ("src/payment.py", 0.70),
        ("tests/unit/test_payment.py", 0.70),
        ("src/user.py", 0.60),
        ("tests/unit/test_user.py", 0.60),
    ]


# ---------------------------------------------------------------------------
# Phase: EDIT
# ---------------------------------------------------------------------------


class TestEditPhase:
    def test_edit_passes_scores_unchanged(self, mixed_ranked_files: list) -> None:
        """EDIT phase applies no multipliers — scores must be identical."""
        result = apply_phase_weights(mixed_ranked_files, AgentPhase.EDIT)

        original_map = dict(mixed_ranked_files)
        for path, score in result:
            assert score == pytest.approx(original_map[path]), (
                f"{path}: expected {original_map[path]}, got {score}"
            )

    def test_edit_preserves_relative_order(self, mixed_ranked_files: list) -> None:
        """With no multipliers, sort order should match the original."""
        result = apply_phase_weights(mixed_ranked_files, AgentPhase.EDIT)
        result_paths = [p for p, _ in result]
        original_paths = [p for p, _ in sorted(mixed_ranked_files, key=lambda x: x[1], reverse=True)]
        assert result_paths == original_paths

    def test_edit_config_has_full_token_density(self) -> None:
        cfg = get_phase_config(AgentPhase.EDIT)
        assert cfg.max_token_density == pytest.approx(1.0)
        assert cfg.signature_only is False


# ---------------------------------------------------------------------------
# Phase: TEST
# ---------------------------------------------------------------------------


class TestTestPhase:
    def test_test_files_rank_higher_than_equal_source_files(
        self, equal_score_files: list
    ) -> None:
        """Test files should outrank source files with identical base scores.

        Uses `equal_score_files` where test and source files have the *same*
        base score, so any position advantage for test files is entirely due to
        the boost — not a pre-existing score difference (M-4 fix).
        """
        cfg = get_phase_config(AgentPhase.TEST)
        assert cfg.test_file_boost > 1.0, "TEST phase must have test_file_boost > 1"

        result = apply_phase_weights(equal_score_files, AgentPhase.TEST)
        result_map = dict(result)
        original_map = dict(equal_score_files)

        test_paths = [p for p in original_map if "test_" in p or "_test." in p]
        source_paths = [p for p in original_map if "test_" not in p and "_test." not in p]

        # Every test file with the same base score as a source file must have a
        # strictly higher boosted score.
        for t_path in test_paths:
            base = original_map[t_path]
            # Find source files that had the same or higher base score
            same_score_sources = [s for s in source_paths if original_map[s] == base]
            for s_path in same_score_sources:
                assert result_map[t_path] > result_map[s_path], (
                    f"Test file {t_path} (boosted={result_map[t_path]:.4f}) should "
                    f"outrank source file {s_path} (boosted={result_map[s_path]:.4f}) "
                    f"after applying test_file_boost={cfg.test_file_boost}"
                )

    def test_mock_files_get_boost(self, mixed_ranked_files: list) -> None:
        """Files with 'mock' in path should be boosted in TEST phase."""
        cfg = get_phase_config(AgentPhase.TEST)
        assert cfg.mock_file_boost > 1.0

        result = apply_phase_weights(mixed_ranked_files, AgentPhase.TEST)
        result_map = dict(result)

        mock_path = "mocks/mock_auth.py"
        original_score = dict(mixed_ranked_files)[mock_path]
        boosted_score = result_map[mock_path]

        # mock_auth.py matches both _is_test_file() (via "mock_" pattern) and
        # _is_mock_file(), so both boosts are applied cumulatively.
        # We only verify that the mock boost was applied (score strictly higher).
        min_expected = original_score * cfg.mock_file_boost
        assert boosted_score > original_score
        assert boosted_score >= min_expected - 1e-9

    def test_test_files_score_multiplied_correctly(self, mixed_ranked_files: list) -> None:
        """Test file scores must equal base_score × test_file_boost."""
        cfg = get_phase_config(AgentPhase.TEST)
        result_map = dict(apply_phase_weights(mixed_ranked_files, AgentPhase.TEST))
        original_map = dict(mixed_ranked_files)

        test_paths = [p for p in original_map if "test_" in p or "_test." in p]
        assert test_paths, "Fixture must contain test files"

        for path in test_paths:
            expected = original_map[path] * cfg.test_file_boost
            assert result_map[path] == pytest.approx(expected), (
                f"{path}: expected {expected}, got {result_map[path]}"
            )

    def test_source_files_not_boosted_in_test_phase(self, mixed_ranked_files: list) -> None:
        """Non-test, non-mock source files must have unchanged scores in TEST phase."""
        result_map = dict(apply_phase_weights(mixed_ranked_files, AgentPhase.TEST))
        original_map = dict(mixed_ranked_files)

        source_paths = [
            p for p in original_map
            if "test" not in p.lower() and "mock" not in p.lower() and "spec" not in p.lower()
        ]
        for path in source_paths:
            assert result_map[path] == pytest.approx(original_map[path]), (
                f"Source file {path} should not be boosted in TEST phase"
            )


# ---------------------------------------------------------------------------
# Phase: DISCOVERY
# ---------------------------------------------------------------------------


class TestDiscoveryPhase:
    def test_discovery_applies_no_score_boosts(self, mixed_ranked_files: list) -> None:
        """DISCOVERY has test_file_boost=1.0 and mock_file_boost=1.0 — no score changes."""
        cfg = get_phase_config(AgentPhase.DISCOVERY)
        assert cfg.test_file_boost == pytest.approx(1.0)
        assert cfg.mock_file_boost == pytest.approx(1.0)

        result_map = dict(apply_phase_weights(mixed_ranked_files, AgentPhase.DISCOVERY))
        original_map = dict(mixed_ranked_files)

        for path, original_score in original_map.items():
            assert result_map[path] == pytest.approx(original_score), (
                f"{path}: DISCOVERY should not change scores"
            )

    def test_discovery_config_limits_token_density(self) -> None:
        cfg = get_phase_config(AgentPhase.DISCOVERY)
        assert cfg.max_token_density < 1.0
        assert cfg.signature_only is True
        assert cfg.include_tree is True

    def test_discovery_token_density_less_than_edit(self) -> None:
        """Discovery should consume less of the token budget than edit."""
        discovery_cfg = get_phase_config(AgentPhase.DISCOVERY)
        edit_cfg = get_phase_config(AgentPhase.EDIT)
        assert discovery_cfg.max_token_density < edit_cfg.max_token_density


# ---------------------------------------------------------------------------
# Phase config consistency
# ---------------------------------------------------------------------------


class TestPhaseConfigConsistency:
    def test_all_phases_have_configs(self) -> None:
        for phase in AgentPhase:
            cfg = get_phase_config(phase)
            assert cfg is not None

    def test_boost_values_are_positive(self) -> None:
        for phase in AgentPhase:
            cfg = get_phase_config(phase)
            assert cfg.test_file_boost > 0
            assert cfg.mock_file_boost > 0
            assert cfg.max_token_density > 0

    def test_result_is_sorted_descending(self, mixed_ranked_files: list) -> None:
        """apply_phase_weights must always return a descending-sorted list."""
        for phase in AgentPhase:
            result = apply_phase_weights(mixed_ranked_files, phase)
            scores = [s for _, s in result]
            assert scores == sorted(scores, reverse=True), (
                f"Phase {phase.value}: result not sorted descending"
            )

    def test_no_files_dropped(self, mixed_ranked_files: list) -> None:
        """apply_phase_weights must not drop any files."""
        for phase in AgentPhase:
            result = apply_phase_weights(mixed_ranked_files, phase)
            assert len(result) == len(mixed_ranked_files)
