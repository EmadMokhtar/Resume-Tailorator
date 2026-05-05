"""Workflow contract tests: structured original CV input, no resume_parser_agent calls."""

import pytest

from resume_tailorator.models.agents.output import AuditResult, JobAnalysis, ReviewResult
from resume_tailorator.workflows import ResumeTailorWorkflow


class DummyRunResult:
    def __init__(self, output):
        self.output = output


@pytest.mark.asyncio
async def test_workflow_uses_provided_original_cv_without_reparsing(
    monkeypatch, sample_cv, subtests
) -> None:
    """When provided with a structured CV, the workflow runs end-to-end without errors."""

    async def run_parser(*args, **kwargs):
        return DummyRunResult(sample_cv)

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

    monkeypatch.setattr("resume_tailorator.workflows.agents.resume_parser_agent.run", run_parser)
    monkeypatch.setattr("resume_tailorator.workflows.agents.analyst_agent.run", run_analyst)
    monkeypatch.setattr("resume_tailorator.workflows.agents.writer_agent.run", run_writer)
    monkeypatch.setattr("resume_tailorator.workflows.agents.reviewer_agent.run", run_reviewer)
    monkeypatch.setattr("resume_tailorator.workflows.agents.auditor_agent.run", run_auditor)

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

    async def run_parser(*args, **kwargs):
        return DummyRunResult(sample_cv)

    async def always_fail(*args, **kwargs):
        raise ValueError("simulated agent unavailable")

    monkeypatch.setattr("resume_tailorator.workflows.agents.resume_parser_agent.run", run_parser)
    monkeypatch.setattr("resume_tailorator.workflows.agents.analyst_agent.run", always_fail)


    with pytest.raises(RuntimeError, match="job analysis"):
        await ResumeTailorWorkflow().run(sample_cv, "files/job_posting.md")
