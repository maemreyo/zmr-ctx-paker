"""Unit tests for phase-aware ranking (ranking/phase_ranker.py)."""

import pytest

from ws_ctx_engine.ranking.phase_ranker import (
    AgentPhase,
    apply_phase_weights,
    get_phase_config,
    parse_phase,
)


class TestParsePhase:
    def test_valid_discovery(self):
        assert parse_phase("discovery") == AgentPhase.DISCOVERY

    def test_valid_edit(self):
        assert parse_phase("edit") == AgentPhase.EDIT

    def test_valid_test(self):
        assert parse_phase("test") == AgentPhase.TEST

    def test_case_insensitive(self):
        assert parse_phase("EDIT") == AgentPhase.EDIT
        assert parse_phase("Discovery") == AgentPhase.DISCOVERY

    def test_invalid_returns_none(self):
        assert parse_phase("unknown") is None

    def test_none_returns_none(self):
        assert parse_phase(None) is None

    def test_empty_string_returns_none(self):
        assert parse_phase("") is None


class TestApplyPhaseWeights:
    def test_test_phase_boosts_test_files(self):
        ranked = [
            ("src/main.py", 0.8),
            ("tests/test_auth.py", 0.5),
        ]
        result = apply_phase_weights(ranked, AgentPhase.TEST)
        # test_auth.py: 0.5 * 2.0 = 1.0 > src/main.py: 0.8
        result_dict = dict(result)
        assert result_dict["tests/test_auth.py"] > result_dict["src/main.py"]

    def test_test_phase_boosts_mock_files(self):
        ranked = [
            ("src/main.py", 1.0),
            ("src/mock_service.py", 0.3),
        ]
        result = apply_phase_weights(ranked, AgentPhase.TEST)
        result_dict = dict(result)
        # mock_service.py receives both test and mock boost
        assert result_dict["src/mock_service.py"] > 0.3

    def test_discovery_phase_no_boost_for_test_files(self):
        cfg = get_phase_config(AgentPhase.DISCOVERY)
        assert cfg.test_file_boost == 1.0

    def test_edit_phase_no_boost_for_test_files(self):
        cfg = get_phase_config(AgentPhase.EDIT)
        assert cfg.test_file_boost == 1.0

    def test_result_sorted_descending(self):
        ranked = [
            ("src/z.py", 0.9),
            ("src/a.py", 0.1),
            ("tests/test_x.py", 0.5),
        ]
        result = apply_phase_weights(ranked, AgentPhase.TEST)
        scores = [s for _, s in result]
        assert scores == sorted(scores, reverse=True)

    def test_empty_list(self):
        assert apply_phase_weights([], AgentPhase.EDIT) == []

    def test_non_test_files_unaffected_by_test_phase(self):
        ranked = [("src/core.py", 0.7)]
        result = apply_phase_weights(ranked, AgentPhase.TEST)
        assert result[0][1] == pytest.approx(0.7)
