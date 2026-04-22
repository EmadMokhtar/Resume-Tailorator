"""Workflow contract tests: structured original CV input, no resume_parser_agent calls."""

import pytest

from models.agents.output import AuditResult, JobAnalysis, ReviewResult
from workflows import ResumeTailorWorkflow


class DummyRunResult:
    def __init__(self, output):
        self.output = output


@pytest.mark.asyncio
async def test_workflow_uses_provided_original_cv_without_reparsing(
    monkeypatch, sample_cv, subtests
) -> None:
    async def fail_parser(*args, **kwargs):
        raise AssertionError("resume_parser_agent should not be called")

    async def run_analyst(*args, **kwargs):
        return DummyRunResult(
            JobAnalysis(
                job_title="Platform Engineer",
                company_name="Acme",
                summary="Platform role",
                hard_skills=["Python"],
                soft_skills=["Communication"],
                key_responsibilities=["Build systems"],
                keywords_to_target=["Python", "Platform"],
            )
        )

    async def run_writer(*args, **kwargs):
        return DummyRunResult(sample_cv)

    async def run_reviewer(*args, **kwargs):
        return DummyRunResult(
            ReviewResult(
                quality_score=9,
                needs_improvement=False,
                specific_suggestions=[],
                strengths=["Good targeting"],
            )
        )

    async def run_auditor(*args, **kwargs):
        return DummyRunResult(
            AuditResult(
                passed=True,
                hallucination_score=0,
                ai_cliche_score=0,
                issues=[],
                feedback_summary="Looks good",
            )
        )

    # Patch the canonical module location so the test does not require a
    # production import added solely to satisfy monkeypatching.
    monkeypatch.setattr("workflows.agents.resume_parser_agent.run", fail_parser)
    monkeypatch.setattr("workflows.analyst_agent.run", run_analyst)
    monkeypatch.setattr("workflows.writer_agent.run", run_writer)
    monkeypatch.setattr("workflows.reviewer_agent.run", run_reviewer)
    monkeypatch.setattr("workflows.auditor_agent.run", run_auditor)

    # If resume_parser_agent.run is called inside the workflow, fail_parser raises
    # AssertionError which will propagate and fail this test immediately.
    result = await ResumeTailorWorkflow().run(sample_cv, "files/job_posting.md")

    with subtests.test("job_title"):
        assert result.job_title == "Platform Engineer"

    with subtests.test("company_name"):
        assert result.company_name == "Acme"

    with subtests.test("passed"):
        assert result.passed is True


@pytest.mark.asyncio
async def test_analyst_failure_after_retries_raises_runtime_error(
    monkeypatch, sample_cv
) -> None:
    """Analyst failure after all retries must raise RuntimeError, not kill the process."""

    async def always_fail(*args, **kwargs):
        raise ValueError("simulated agent unavailable")

    monkeypatch.setattr("workflows.analyst_agent.run", always_fail)

    with pytest.raises(RuntimeError, match="job analysis"):
        await ResumeTailorWorkflow().run(sample_cv, "files/job_posting.md")
