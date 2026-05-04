"""Tests for QualityCheckResult model."""

import pytest
from models.agents.output import QualityCheckResult


def test_quality_check_result_valid_pass_score(subtests):
    result = QualityCheckResult(score=9, reasoning="Solid output", improvements=[])
    with subtests.test(msg="score"):
        assert result.score == 9
    with subtests.test(msg="improvements_empty"):
        assert result.improvements == []


def test_quality_check_result_valid_fail_score(subtests):
    result = QualityCheckResult(
        score=5,
        reasoning="Needs work",
        improvements=["Add more keywords", "Fix tone"],
    )
    with subtests.test(msg="score"):
        assert result.score == 5
    with subtests.test(msg="improvements"):
        assert len(result.improvements) == 2


def test_quality_check_result_rejects_score_above_10():
    with pytest.raises(Exception):
        QualityCheckResult(score=11, reasoning="Over limit", improvements=[])


def test_quality_check_result_rejects_score_below_0():
    with pytest.raises(Exception):
        QualityCheckResult(score=-1, reasoning="Below zero", improvements=[])


def test_quality_check_result_improvements_defaults_to_empty():
    result = QualityCheckResult(score=10, reasoning="Perfect")
    assert result.improvements == []
