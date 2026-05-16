"""Shared test factories for resume-tailorator tests."""

from resume_tailorator.models.agents.output import (
    CV,
    WorkExperience,
    ScrapedJobPosting,
    FinalReport,
    CVDiff,
    GapAnalysis,
)
from resume_tailorator.models.workflow import ResumeTailorResult


def make_cv(full_name: str = "Jane Doe") -> CV:
    return CV(
        full_name=full_name,
        contact_info="jane@example.com",
        summary="Platform engineer.",
        skills=["Python", "SQL"],
        experience=[
            WorkExperience(
                company="Acme",
                role="Engineer",
                dates="2022-2026",
                highlights=["Built services"],
            )
        ],
        education=["BSc CS"],
    )


def make_result(cv: CV | None = None, passed: bool = True) -> ResumeTailorResult:
    cv = cv or make_cv()
    return ResumeTailorResult(
        company_name="Acme Corp",
        job_title="Software Engineer",
        tailored_resume=cv.model_dump_json(),
        audit_report={
            "passed": passed,
            "hallucination_score": 0,
            "ai_cliche_score": 1,
            "issues": [],
            "feedback_summary": "Looks good." if passed else "Needs work.",
        },
        passed=passed,
        final_report=FinalReport(
            job_title="Software Engineer",
            company_name="Acme Corp",
            generated_at="2026-01-01T00:00:00Z",
            overall_recommendation="Strong Match" if passed else "Weak Match",
            match_score=85 if passed else 40,
            what_changed=CVDiff(sections_modified=["summary"]),
            gaps=GapAnalysis(covered_keywords=["Python"]),
            suggestions_to_strengthen=[],
            audit_summary="Passed" if passed else "Failed",
            recommendation_rationale="Good match",
            passed=passed,
        ),
    )


def make_scraped_job(
    markdown: str = "# Senior Engineer at Acme Corp\n\nPython role.",
    extraction_strategy: str = "test",
) -> ScrapedJobPosting:
    return ScrapedJobPosting(
        markdown=markdown,
        url="https://example.com/job/123",
        source_text="Raw text",
        extraction_strategy=extraction_strategy,
    )
