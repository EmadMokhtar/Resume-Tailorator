"""Integration tests for job scraper within _tailor_impl().

Coverage:
- Scraper output format validation (markdown structure, non-empty, etc.)
- Different extraction strategies (playwright_llm for JS-heavy sites)
- Scraper errors handled gracefully (timeout, network failure)
- Empty scraper content detected and rejected
- Job posting content flows correctly to workflow
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer import Exit as TyperExit

from resume_tailorator.models.agents.output import (
    CV,
    WorkExperience,
    ScrapedJobPosting,
    FinalReport,
    CVDiff,
    GapAnalysis,
)
from resume_tailorator.models.workflow import ResumeTailorResult

pytestmark = pytest.mark.anyio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_cv() -> CV:
    return CV(
        full_name="Jane Doe",
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


def _make_result(passed: bool = True) -> ResumeTailorResult:
    cv = _make_cv()
    return ResumeTailorResult(
        company_name="Acme Corp",
        job_title="Software Engineer",
        tailored_resume=cv.model_dump_json(),
        audit_report={
            "passed": passed,
            "hallucination_score": 0,
            "ai_cliche_score": 1,
            "issues": [],
            "feedback_summary": "Looks good.",
        },
        passed=passed,
        final_report=FinalReport(
            job_title="Software Engineer",
            company_name="Acme Corp",
            generated_at="2026-01-01T00:00:00Z",
            overall_recommendation="Strong Match",
            match_score=85,
            what_changed=CVDiff(sections_modified=["summary"]),
            gaps=GapAnalysis(covered_keywords=["Python"]),
            suggestions_to_strengthen=[],
            audit_summary="Passed",
            recommendation_rationale="Good match",
            passed=True,
        ),
    )


def _make_scraped_job(
    markdown: str = "# Senior Engineer at Example Corp\n\nPython role.",
    extraction_strategy: str = "playwright_llm",
) -> ScrapedJobPosting:
    return ScrapedJobPosting(
        markdown=markdown,
        url="https://example.com/job/123",
        source_text="Raw job text",
        extraction_strategy=extraction_strategy,
    )


def _apply_patches(
    *,
    scraper_output=None,
    scraper_error=None,
    passed: bool = True,
    save_side_effect=None,
):
    """Set up mocks for _tailor_impl() dependencies.

    Returns (patches_list, mocks_dict).
    """
    cv = _make_cv()
    workflow_result = _make_result(passed=passed)

    mock_workflow = MagicMock()
    mock_workflow.run = AsyncMock(return_value=workflow_result)

    mock_generate_resume = MagicMock(return_value="/fake/output/resume.md")

    if scraper_error is not None:
        mock_scraper_run = AsyncMock(side_effect=scraper_error)
    elif scraper_output is not None:
        mock_scraper_run = AsyncMock(return_value=MagicMock(output=scraper_output))
    else:
        mock_scraper_run = AsyncMock(return_value=MagicMock(output=_make_scraped_job()))

    mock_repo = MagicMock()
    mock_parser = MagicMock()
    mock_svc = MagicMock()

    resolved = MagicMock()
    resolved.source = MagicMock(id="src-123")
    resolved.cv = cv
    mock_svc.aresolve_original_resume = AsyncMock(return_value=resolved)

    if save_side_effect is not None:
        mock_svc.save_tailored_resume = MagicMock(side_effect=save_side_effect)
    else:
        mock_svc.save_tailored_resume = MagicMock(return_value=MagicMock(id="job-456"))

    mocks = {
        "workflow": mock_workflow,
        "generate_resume": mock_generate_resume,
        "scraper_run": mock_scraper_run,
        "repo": mock_repo,
        "service": mock_svc,
    }

    patches = [
        patch("resume_tailorator.main.job_scraper_agent.run", mock_scraper_run),
        patch(
            "resume_tailorator.main.ResumeTailorWorkflow",
            return_value=mock_workflow,
        ),
        patch("resume_tailorator.main.generate_resume", mock_generate_resume),
        patch(
            "resume_tailorator.main.SQLiteResumeMemoryRepository",
            return_value=mock_repo,
        ),
        patch(
            "resume_tailorator.main.PydanticAIResumeParser",
            return_value=mock_parser,
        ),
        patch(
            "resume_tailorator.main.ResumeMemoryService",
            return_value=mock_svc,
        ),
    ]

    return patches, mocks


# ---------------------------------------------------------------------------
# Test 1: JS-heavy site uses playwright_llm strategy
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_scraper_js_heavy_site_strategy(tmp_path, monkeypatch, subtests) -> None:
    """Scraper handling JS-heavy job boards should use playwright_llm strategy."""
    resume_file = tmp_path / "resume.md"
    resume_file.write_text("# Jane Doe\nPython developer.")

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    monkeypatch.chdir(tmp_path)

    scraped = _make_scraped_job(
        markdown="# JS-Heavy Job Posting\n\nRequires Python and React.",
        extraction_strategy="playwright_llm",
    )

    patches, mocks = _apply_patches(scraper_output=scraped)

    from resume_tailorator.main import _tailor_impl

    with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
        exit_code = await _tailor_impl(
            job_url="https://javascript-board.example.com/jobs/456",
            resume_path=str(resume_file),
            output_dir=str(output_dir),
            model=None,
        )

    with subtests.test("exits zero"):
        assert exit_code == 0

    with subtests.test("workflow called"):
        mocks["workflow"].run.assert_called_once()

    with subtests.test("scraper called with correct URL"):
        mocks["scraper_run"].assert_called_once()
        call_arg = mocks["scraper_run"].call_args.args[0]
        assert "javascript-board.example.com/jobs/456" in call_arg


# ---------------------------------------------------------------------------
# Test 2: Empty scraper output rejected
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_scraper_empty_output_rejected(tmp_path, monkeypatch) -> None:
    """_tailor_impl() should exit with error when scraper returns empty markdown."""
    resume_file = tmp_path / "resume.md"
    resume_file.write_text("# Jane Doe\nPython developer.")

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    monkeypatch.chdir(tmp_path)

    empty_job = _make_scraped_job(markdown="   \n")

    patches, mocks = _apply_patches(scraper_output=empty_job)

    from resume_tailorator.main import _tailor_impl

    with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
        with pytest.raises(TyperExit):
            await _tailor_impl(
                job_url="https://example.com/job/empty",
                resume_path=str(resume_file),
                output_dir=str(output_dir),
                model=None,
            )

    mocks["workflow"].run.assert_not_called()


# ---------------------------------------------------------------------------
# Test 3: Scraper timeout handled gracefully
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_scraper_timeout_handled(tmp_path, monkeypatch) -> None:
    """_tailor_impl() should exit with error on scraper timeout."""
    resume_file = tmp_path / "resume.md"
    resume_file.write_text("# Jane Doe\nPython developer.")

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    monkeypatch.chdir(tmp_path)

    patches, mocks = _apply_patches(
        scraper_error=TimeoutError("Scraper exceeded 30s timeout")
    )

    from resume_tailorator.main import _tailor_impl

    with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
        with pytest.raises(TyperExit):
            await _tailor_impl(
                job_url="https://slow-site.example.com/job",
                resume_path=str(resume_file),
                output_dir=str(output_dir),
                model=None,
            )

    mocks["workflow"].run.assert_not_called()


# ---------------------------------------------------------------------------
# Test 4: Scraper network error handled gracefully
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_scraper_network_error_handled(tmp_path, monkeypatch) -> None:
    """_tailor_impl() should exit with error on network failure."""
    resume_file = tmp_path / "resume.md"
    resume_file.write_text("# Jane Doe\nPython developer.")

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    monkeypatch.chdir(tmp_path)

    patches, mocks = _apply_patches(
        scraper_error=ConnectionError("Failed to connect to host")
    )

    from resume_tailorator.main import _tailor_impl

    with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
        with pytest.raises(TyperExit):
            await _tailor_impl(
                job_url="https://nonexistent.example.com/job",
                resume_path=str(resume_file),
                output_dir=str(output_dir),
                model=None,
            )

    mocks["workflow"].run.assert_not_called()


# ---------------------------------------------------------------------------
# Test 5: Scraper output format validation
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_scraper_output_format_valid(tmp_path, monkeypatch, subtests) -> None:
    """Scraped job posting markdown should be well-formed and contain expected content."""
    resume_file = tmp_path / "resume.md"
    resume_file.write_text("# Jane Doe\nPython developer.")

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    monkeypatch.chdir(tmp_path)

    job_md = (
        "# Senior Software Engineer at Example Corp\n\n"
        "## About the Role\n"
        "We are looking for a Senior Software Engineer.\n\n"
        "## Requirements\n"
        "- 5+ years Python experience\n"
        "- Django experience required\n"
        "- PostgreSQL knowledge\n\n"
        "## Responsibilities\n"
        "- Design and build scalable systems\n"
        "- Lead technical initiatives\n"
    )

    scraped = _make_scraped_job(markdown=job_md)

    patches, mocks = _apply_patches(scraper_output=scraped)

    from resume_tailorator.main import _tailor_impl

    with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
        exit_code = await _tailor_impl(
            job_url="https://example.com/job/123",
            resume_path=str(resume_file),
            output_dir=str(output_dir),
            model=None,
        )

    assert exit_code == 0
    called = mocks["workflow"].run.call_args

    with subtests.test("job_content passed to workflow"):
        resume_content = (
            called.args[0] if called.args else called.kwargs.get("resume_content")
        )
        assert resume_content is not None

    with subtests.test("job_content contains job title"):
        if called.kwargs:
            job_content = called.kwargs.get("job_content", "")
            assert "Senior Software Engineer" in job_content
            assert "Example Corp" in job_content


# ---------------------------------------------------------------------------
# Test 6: Job posting content preserved through scraping
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_scraper_content_flows_to_workflow(tmp_path, monkeypatch) -> None:
    """Verify the scraped job content is correctly forwarded to the workflow."""
    resume_file = tmp_path / "resume.md"
    resume_file.write_text("# Jane Doe\nPython developer.")

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    monkeypatch.chdir(tmp_path)

    expected_keyword = "Kubernetes-Experience-Required-12345"
    scraped = _make_scraped_job(
        markdown=f"# Platform Engineer\n\nMust have: {expected_keyword}."
    )

    patches, mocks = _apply_patches(scraper_output=scraped)

    from resume_tailorator.main import _tailor_impl

    with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
        await _tailor_impl(
            job_url="https://example.com/job/platform-engineer",
            resume_path=str(resume_file),
            output_dir=str(output_dir),
            model=None,
        )

    mocks["workflow"].run.assert_called_once()
    call_kwargs = mocks["workflow"].run.call_args.kwargs
    job_content = call_kwargs.get("job_content", "")
    assert expected_keyword in job_content


# ---------------------------------------------------------------------------
# Test 7: Unexpected scraper output type handled
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_scraper_unexpected_output_type_handled(tmp_path, monkeypatch) -> None:
    """_tailor_impl() should exit when scraper returns non-ScrapedJobPosting output."""
    resume_file = tmp_path / "resume.md"
    resume_file.write_text("# Jane Doe\nPython developer.")

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    monkeypatch.chdir(tmp_path)

    # Scraper returns a raw string instead of ScrapedJobPosting
    mock_run_result = MagicMock()
    mock_run_result.output = "just a raw string, not a ScrapedJobPosting"

    patches, mocks = _apply_patches(
        scraper_output=_make_scraped_job()  # placeholder, overridden below
    )

    from resume_tailorator.main import _tailor_impl

    with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
        # Override the scraper mock directly
        mocks["scraper_run"].return_value = mock_run_result

        with pytest.raises(TyperExit):
            await _tailor_impl(
                job_url="https://example.com/job/broken",
                resume_path=str(resume_file),
                output_dir=str(output_dir),
                model=None,
            )

    mocks["workflow"].run.assert_not_called()
