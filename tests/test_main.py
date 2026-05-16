"""Tests for _tailor_impl memory service integration and error handling.

Coverage:
- Successful workflow run → result persisted via memory service
- Failed audit (passed=False) → result NOT saved
- Save failure → graceful handling (warning, not crash)
- Cache hit: pre-parsed CV reused when available
- Cache miss / error → falls back to AI parsing
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


def _make_cv(full_name: str = "Jane Doe") -> CV:
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


def _make_result(cv: CV | None = None, passed: bool = True) -> ResumeTailorResult:
    cv = cv or _make_cv()
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


def _make_scraped_job(
    markdown: str = "# Senior Engineer at Acme Corp\n\nPython role.",
) -> ScrapedJobPosting:
    return ScrapedJobPosting(
        markdown=markdown,
        url="https://example.com/job/123",
        source_text="Raw text",
        extraction_strategy="test",
    )


def _setup_mocks_for_tailor_impl(
    *,
    cv: CV | None = None,
    passed: bool = True,
    resolve_side_effect=None,
    save_side_effect=None,
    scraper_side_effect=None,
):
    """Patch all external collaborators needed by _tailor_impl().

    Returns a dict of mocks keyed by name.
    """
    cv = cv or _make_cv()
    workflow_result = _make_result(cv=cv, passed=passed)
    scraped_job = _make_scraped_job()

    mock_workflow = MagicMock()
    mock_workflow.run = AsyncMock(return_value=workflow_result)

    mock_generate_resume = MagicMock(return_value="/fake/output/resume.md")

    if scraper_side_effect is not None:
        mock_scraper_run = AsyncMock(side_effect=scraper_side_effect)
    else:
        mock_scraper_run = AsyncMock(return_value=MagicMock(output=scraped_job))

    mock_repo = MagicMock()
    mock_parser = MagicMock()
    mock_svc = MagicMock()

    resolved = MagicMock()
    resolved.source = MagicMock(id="src-123")
    resolved.cv = cv

    if resolve_side_effect is not None:
        mock_svc.aresolve_original_resume = AsyncMock(side_effect=resolve_side_effect)
    else:
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
        "parser": mock_parser,
        "service": mock_svc,
    }

    patches = [
        patch(
            "resume_tailorator.main.job_scraper_agent.run",
            mock_scraper_run,
        ),
        patch(
            "resume_tailorator.main.ResumeTailorWorkflow",
            return_value=mock_workflow,
        ),
        patch(
            "resume_tailorator.main.generate_resume",
            mock_generate_resume,
        ),
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
# Test 1: Successful run persists result
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_tailor_impl_persists_result_on_success(
    tmp_path, monkeypatch, subtests
) -> None:
    """_tailor_impl() with valid inputs should save to memory on success."""
    resume_file = tmp_path / "resume.md"
    resume_file.write_text("# Jane Doe\nPython developer.")

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    monkeypatch.chdir(tmp_path)

    patches, mocks = _setup_mocks_for_tailor_impl()

    from resume_tailorator.main import _tailor_impl

    with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
        exit_code = await _tailor_impl(
            job_url="https://example.com/job/123",
            resume_path=str(resume_file),
            output_dir=str(output_dir),
            model=None,
        )

    with subtests.test("exits zero"):
        assert exit_code == 0

    with subtests.test("workflow.run called"):
        mocks["workflow"].run.assert_called_once()

    with subtests.test("generate_resume called"):
        mocks["generate_resume"].assert_called_once()

    with subtests.test("save_tailored_resume called"):
        mocks["service"].save_tailored_resume.assert_called_once()


# ---------------------------------------------------------------------------
# Test 2: Failed audit skips save
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_tailor_impl_failed_audit_persists_record(tmp_path, monkeypatch) -> None:
    """_tailor_impl() should save record even when audit fails (for re-tailoring)."""
    resume_file = tmp_path / "resume.md"
    resume_file.write_text("# Jane Doe\nPython developer.")

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    monkeypatch.chdir(tmp_path)

    patches, mocks = _setup_mocks_for_tailor_impl(passed=False)

    from resume_tailorator.main import _tailor_impl

    with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
        exit_code = await _tailor_impl(
            job_url="https://example.com/job/123",
            resume_path=str(resume_file),
            output_dir=str(output_dir),
            model=None,
        )

    assert exit_code == 0
    mocks["workflow"].run.assert_called_once()
    # Record is persisted so it can be re-tailored later
    mocks["service"].save_tailored_resume.assert_called_once()
    # But resume file is NOT generated (audit didn't pass)
    mocks["generate_resume"].assert_not_called()


# ---------------------------------------------------------------------------
# Test 3: Save failure handled gracefully
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_tailor_impl_save_failure_handled_gracefully(
    tmp_path, monkeypatch
) -> None:
    """_tailor_impl() should warn and continue when save_tailored_resume fails."""
    resume_file = tmp_path / "resume.md"
    resume_file.write_text("# Jane Doe\nPython developer.")

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    monkeypatch.chdir(tmp_path)

    patches, mocks = _setup_mocks_for_tailor_impl(
        save_side_effect=Exception("disk full")
    )

    from resume_tailorator.main import _tailor_impl

    with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
        exit_code = await _tailor_impl(
            job_url="https://example.com/job/123",
            resume_path=str(resume_file),
            output_dir=str(output_dir),
            model=None,
        )

    # Should complete successfully even though save failed
    assert exit_code == 0
    mocks["workflow"].run.assert_called_once()
    mocks["generate_resume"].assert_called_once()
    mocks["service"].save_tailored_resume.assert_called_once()


# ---------------------------------------------------------------------------
# Test 4: Cache hit — pre-parsed CV reused
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_tailor_impl_cache_hit_reuses_pre_parsed_cv(
    tmp_path, monkeypatch
) -> None:
    """When memory service returns a cached CV, it should be passed to the workflow."""
    resume_file = tmp_path / "resume.md"
    resume_file.write_text("# Jane Doe\nPython developer.")

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    monkeypatch.chdir(tmp_path)

    cv = _make_cv(full_name="Cached Jane")
    patches, mocks = _setup_mocks_for_tailor_impl(cv=cv)

    from resume_tailorator.main import _tailor_impl

    with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
        await _tailor_impl(
            job_url="https://example.com/job/123",
            resume_path=str(resume_file),
            output_dir=str(output_dir),
            model=None,
        )

    # The workflow should be called with pre_parsed_cv set
    call_kwargs = mocks["workflow"].run.call_args.kwargs
    assert call_kwargs.get("pre_parsed_cv") == cv


# ---------------------------------------------------------------------------
# Test 5: Cache miss — falls back to AI parsing
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_tailor_impl_cache_miss_falls_back_to_ai_parsing(
    tmp_path, monkeypatch
) -> None:
    """When memory service raises, pre_parsed_cv should be None (fallback to AI)."""
    resume_file = tmp_path / "resume.md"
    resume_file.write_text("# Jane Doe\nPython developer.")

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    monkeypatch.chdir(tmp_path)

    patches, mocks = _setup_mocks_for_tailor_impl(
        resolve_side_effect=Exception("DB connection lost")
    )

    from resume_tailorator.main import _tailor_impl

    with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
        await _tailor_impl(
            job_url="https://example.com/job/123",
            resume_path=str(resume_file),
            output_dir=str(output_dir),
            model=None,
        )

    # Should still complete successfully (falling back to AI parsing)
    mocks["workflow"].run.assert_called_once()
    call_kwargs = mocks["workflow"].run.call_args.kwargs
    assert call_kwargs.get("pre_parsed_cv") is None


# ---------------------------------------------------------------------------
# Test 6: Invalid URL rejected early
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_tailor_impl_invalid_url_exits(tmp_path, monkeypatch) -> None:
    """_tailor_impl() should raise typer.Exit for non-http(s) URLs."""
    resume_file = tmp_path / "resume.md"
    resume_file.write_text("# Jane Doe\nPython developer.")

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    monkeypatch.chdir(tmp_path)

    from resume_tailorator.main import _tailor_impl

    with pytest.raises(TyperExit):
        await _tailor_impl(
            job_url="not-a-url",
            resume_path=str(resume_file),
            output_dir=str(output_dir),
            model=None,
        )
