"""Unit tests for AI rule boost ranking (ranking/ranker.py)."""

import pytest

from ws_ctx_engine.ranking.ranker import (
    AI_RULE_BOOST,
    AI_RULE_FILES,
    apply_ai_rule_boost,
    apply_ai_rule_boost_to_ranked,
)


class TestApplyAiRuleBoost:
    def test_canonical_rule_file_gets_boost(self):
        for rule_file in AI_RULE_FILES:
            score = apply_ai_rule_boost(rule_file, base_score=0.5)
            assert score == pytest.approx(0.5 + AI_RULE_BOOST)

    def test_nested_rule_file_matched_by_name(self):
        # CLAUDE.md inside a subdirectory still matches by filename
        score = apply_ai_rule_boost("some/nested/dir/CLAUDE.md", base_score=0.0)
        assert score == pytest.approx(AI_RULE_BOOST)

    def test_non_rule_file_unchanged(self):
        score = apply_ai_rule_boost("src/main.py", base_score=0.7)
        assert score == pytest.approx(0.7)

    def test_extra_files_get_boost(self):
        score = apply_ai_rule_boost("CUSTOM_RULES.md", base_score=0.0, extra_files=["CUSTOM_RULES.md"])
        assert score == pytest.approx(AI_RULE_BOOST)

    def test_custom_boost_value(self):
        score = apply_ai_rule_boost("CLAUDE.md", base_score=1.0, boost=5.0)
        assert score == pytest.approx(6.0)

    def test_partial_filename_does_not_match(self):
        # "AGENTS.md.bak" should NOT match "AGENTS.md"
        score = apply_ai_rule_boost("AGENTS.md.bak", base_score=0.5)
        assert score == pytest.approx(0.5)

    def test_path_with_rule_as_suffix_matches(self):
        # path ends with "/.cursorrules" — caught by the endswith branch (line 58)
        score = apply_ai_rule_boost("repo/.cursorrules", base_score=0.0)
        assert score == pytest.approx(AI_RULE_BOOST)


class TestApplyAiRuleBoostToRanked:
    def test_rule_file_sorted_to_top(self):
        ranked = [
            ("src/main.py", 0.9),
            ("CLAUDE.md", 0.1),
            ("src/utils.py", 0.5),
        ]
        result = apply_ai_rule_boost_to_ranked(ranked)
        assert result[0][0] == "CLAUDE.md"
        assert result[0][1] == pytest.approx(0.1 + AI_RULE_BOOST)

    def test_non_rule_files_order_preserved(self):
        ranked = [
            ("src/a.py", 0.9),
            ("src/b.py", 0.5),
        ]
        result = apply_ai_rule_boost_to_ranked(ranked)
        assert result[0][0] == "src/a.py"
        assert result[1][0] == "src/b.py"

    def test_empty_list_returns_empty(self):
        assert apply_ai_rule_boost_to_ranked([]) == []

    def test_multiple_rule_files_all_boosted(self):
        ranked = [
            ("src/main.py", 0.8),
            ("CLAUDE.md", 0.2),
            ("AGENTS.md", 0.3),
        ]
        result = apply_ai_rule_boost_to_ranked(ranked)
        paths = [r[0] for r in result]
        # Both rule files should be above src/main.py
        assert paths.index("CLAUDE.md") < paths.index("src/main.py")
        assert paths.index("AGENTS.md") < paths.index("src/main.py")
