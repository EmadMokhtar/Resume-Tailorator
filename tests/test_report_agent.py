"""Integration tests for report_agent using TestModel (no real LLM calls)."""

import pytest
from pydantic_ai import models
from pydantic_ai.models.test import TestModel
from pytest_subtests import SubTests

from models.agents.output import FinalReport

models.ALLOW_MODEL_REQUESTS = False

pytestmark = pytest.mark.anyio


async def test_report_agent_returns_final_report() -> None:
    """report_agent should return a FinalReport when given valid JSON context."""
    from workflows.agents import report_agent  # noqa: PLC0415 — avoids import-time LLM init

    custom = {
        "job_title": "Senior Backend Engineer",
        "company_name": "Acme Corp",
        "generated_at": "2024-01-01T00:00:00Z",
        "overall_recommendation": "Partial Match",
        "match_score": 65,
        "what_changed": {},
        "gaps": {},
        "suggestions_to_strengthen": ["Get Kubernetes certification"],
        "audit_summary": "Hallucination score 1/10. AI cliché score 2/10.",
        "recommendation_rationale": "Strong backend skills but missing infra experience.",
        "passed": False,
    }

    with report_agent.override(model=TestModel(custom_output_args=custom)):
        result = await report_agent.run(
            "CV Diff: {} Gap Analysis: {} Audit: {} Review: {} Job: {}"
        )

    assert isinstance(result.output, FinalReport)


async def test_report_agent_output_has_required_fields(subtests: SubTests) -> None:
    """FinalReport output must contain all expected fields."""
    from workflows.agents import report_agent  # noqa: PLC0415 — avoids import-time LLM init

    custom = {
        "job_title": "Senior Backend Engineer",
        "company_name": "Acme Corp",
        "generated_at": "2024-01-01T00:00:00Z",
        "overall_recommendation": "Strong Match",
        "match_score": 88,
        "what_changed": {},
        "gaps": {},
        "suggestions_to_strengthen": ["Add Terraform side project"],
        "audit_summary": "Excellent quality. No hallucinations.",
        "recommendation_rationale": "Covers 90% of job keywords.",
        "passed": True,
    }

    with report_agent.override(model=TestModel(custom_output_args=custom)):
        result = await report_agent.run("CV Diff: {} Gap Analysis: {}")

    output = result.output

    with subtests.test("overall_recommendation"):
        assert output.overall_recommendation in (
            "Strong Match",
            "Partial Match",
            "Weak Match",
        )

    with subtests.test("match_score_range"):
        assert 0 <= output.match_score <= 100

    with subtests.test("suggestions_list"):
        assert isinstance(output.suggestions_to_strengthen, list)

    with subtests.test("audit_summary_non_empty"):
        assert len(output.audit_summary) > 0

    with subtests.test("rationale_non_empty"):
        assert len(output.recommendation_rationale) > 0
