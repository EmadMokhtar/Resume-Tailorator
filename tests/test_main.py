"""Tests for _tailor_impl memory service integration and error handling.

Coverage:
- Successful workflow run → result persisted via memory service
- Failed audit → record still persisted (for re-tailoring), resume file NOT generated
- Save failure → graceful handling (warning, not crash)
- Cache hit: pre-parsed CV reused when available
- Cache miss / error → falls back to AI parsing
- Invalid URL rejected early
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer import Exit as TyperExit

from tests.factories import make_cv, make_result, make_scraped_job

pytestmark = pytest.mark.anyio


# ---------------------------------------------------------------------------
# Mock setup
# ---------------------------------------------------------------------------


def _setup_mocks(
    *,
    cv=None,
    passed: bool = True,
    resolve_side_effect=None,
    save_side_effect=None,
    scraper_side_effect=None,
):
    """Patch all external collaborators needed by _tailor_impl()."""
    cv = cv or make_cv()
    workflow_result = make_result(cv=cv, passed=passed)
    scraped_job = make_scraped_job()

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
# Tests
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

    patches, mocks = _setup_mocks()

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


@pytest.mark.anyio
async def test_tailor_impl_failed_audit_persists_record(tmp_path, monkeypatch) -> None:
    """Save record even when audit fails (for re-tailoring), but skip resume file."""
    resume_file = tmp_path / "resume.md"
    resume_file.write_text("# Jane Doe\nPython developer.")

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    monkeypatch.chdir(tmp_path)

    patches, mocks = _setup_mocks(passed=False)

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
    mocks["service"].save_tailored_resume.assert_called_once()
    mocks["generate_resume"].assert_not_called()


@pytest.mark.anyio
async def test_tailor_impl_save_failure_handled_gracefully(
    tmp_path, monkeypatch
) -> None:
    """Warn and continue when save_tailored_resume fails."""
    resume_file = tmp_path / "resume.md"
    resume_file.write_text("# Jane Doe\nPython developer.")

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    monkeypatch.chdir(tmp_path)

    patches, mocks = _setup_mocks(save_side_effect=Exception("disk full"))

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
    mocks["generate_resume"].assert_called_once()
    mocks["service"].save_tailored_resume.assert_called_once()


@pytest.mark.anyio
async def test_tailor_impl_cache_hit_reuses_pre_parsed_cv(
    tmp_path, monkeypatch
) -> None:
    """When memory service returns a cached CV, pass it to the workflow."""
    resume_file = tmp_path / "resume.md"
    resume_file.write_text("# Jane Doe\nPython developer.")

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    monkeypatch.chdir(tmp_path)

    cv = make_cv(full_name="Cached Jane")
    patches, mocks = _setup_mocks(cv=cv)

    from resume_tailorator.main import _tailor_impl

    with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
        await _tailor_impl(
            job_url="https://example.com/job/123",
            resume_path=str(resume_file),
            output_dir=str(output_dir),
            model=None,
        )

    call_kwargs = mocks["workflow"].run.call_args.kwargs
    assert call_kwargs.get("pre_parsed_cv") == cv


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

    patches, mocks = _setup_mocks(resolve_side_effect=Exception("DB connection lost"))

    from resume_tailorator.main import _tailor_impl

    with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
        await _tailor_impl(
            job_url="https://example.com/job/123",
            resume_path=str(resume_file),
            output_dir=str(output_dir),
            model=None,
        )

    mocks["workflow"].run.assert_called_once()
    call_kwargs = mocks["workflow"].run.call_args.kwargs
    assert call_kwargs.get("pre_parsed_cv") is None


@pytest.mark.anyio
async def test_tailor_impl_invalid_url_exits(tmp_path, monkeypatch) -> None:
    """Reject non-http(s) URLs with TyperExit."""
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


@pytest.mark.anyio
async def test_tailor_impl_empty_resume_content_exits(tmp_path, monkeypatch) -> None:
    """Reject empty resume content with TyperExit."""
    resume_file = tmp_path / "resume.md"
    resume_file.write_text("")

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    monkeypatch.chdir(tmp_path)

    from resume_tailorator.main import _tailor_impl

    with pytest.raises(TyperExit):
        await _tailor_impl(
            job_url="https://example.com/job/123",
            resume_path=str(resume_file),
            output_dir=str(output_dir),
            model=None,
        )
