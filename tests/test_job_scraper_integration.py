"""Integration tests for job scraper within _tailor_impl().

Coverage:
- Scraper errors handled gracefully (timeout, network failure)
- Empty scraper content detected and rejected
- Job posting content flows correctly to workflow
- Unexpected scraper output type rejected
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
    scraper_output: MagicMock | None = None,
    scraper_error: BaseException | None = None,
    passed: bool = True,
    save_side_effect=None,
):
    """Set up mocks for _tailor_impl() dependencies.

    Exactly one of scraper_output or scraper_error may be set.
    """
    if scraper_output is not None and scraper_error is not None:
        raise ValueError("scraper_output and scraper_error are mutually exclusive")

    cv = make_cv()
    workflow_result = make_result(passed=passed)

    mock_workflow = MagicMock()
    mock_workflow.run = AsyncMock(return_value=workflow_result)

    mock_generate_resume = MagicMock(return_value="/fake/output/resume.md")

    if scraper_error is not None:
        mock_scraper_run = AsyncMock(side_effect=scraper_error)
    elif scraper_output is not None:
        mock_scraper_run = AsyncMock(return_value=scraper_output)
    else:
        mock_scraper_run = AsyncMock(return_value=MagicMock(output=make_scraped_job()))

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
            return_value=MagicMock(),
        ),
        patch(
            "resume_tailorator.main.PydanticAIResumeParser",
            return_value=MagicMock(),
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
async def test_scraper_empty_output_rejected(tmp_path, monkeypatch) -> None:
    """Exit with error when scraper returns whitespace-only markdown."""
    resume_file = tmp_path / "resume.md"
    resume_file.write_text("# Jane Doe\nPython developer.")

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    monkeypatch.chdir(tmp_path)

    empty_job = make_scraped_job(markdown="   \n")
    scraper_output = MagicMock(output=empty_job)

    patches, mocks = _setup_mocks(scraper_output=scraper_output)

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


@pytest.mark.anyio
async def test_scraper_timeout_handled(tmp_path, monkeypatch) -> None:
    """Exit with error on scraper timeout."""
    resume_file = tmp_path / "resume.md"
    resume_file.write_text("# Jane Doe\nPython developer.")

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    monkeypatch.chdir(tmp_path)

    patches, mocks = _setup_mocks(
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


@pytest.mark.anyio
async def test_scraper_network_error_handled(tmp_path, monkeypatch) -> None:
    """Exit with error on network failure."""
    resume_file = tmp_path / "resume.md"
    resume_file.write_text("# Jane Doe\nPython developer.")

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    monkeypatch.chdir(tmp_path)

    patches, mocks = _setup_mocks(
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


@pytest.mark.anyio
async def test_scraper_content_flows_to_workflow(tmp_path, monkeypatch) -> None:
    """Scraped job content is correctly forwarded to the workflow."""
    resume_file = tmp_path / "resume.md"
    resume_file.write_text("# Jane Doe\nPython developer.")

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    monkeypatch.chdir(tmp_path)

    expected_keyword = "Kubernetes-Experience-Required-12345"
    scraped = make_scraped_job(
        markdown=f"# Platform Engineer\n\nMust have: {expected_keyword}."
    )
    scraper_output = MagicMock(output=scraped)

    patches, mocks = _setup_mocks(scraper_output=scraper_output)

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
    assert expected_keyword in call_kwargs.get("job_content", "")


@pytest.mark.anyio
async def test_scraper_unexpected_output_type_handled(tmp_path, monkeypatch) -> None:
    """Exit when scraper returns non-ScrapedJobPosting output."""
    resume_file = tmp_path / "resume.md"
    resume_file.write_text("# Jane Doe\nPython developer.")

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    monkeypatch.chdir(tmp_path)

    # Simulate scraper returning a raw string instead of ScrapedJobPosting
    bad_output = MagicMock()
    bad_output.output = "just a raw string, not a ScrapedJobPosting"

    patches, mocks = _setup_mocks(scraper_output=bad_output)

    from resume_tailorator.main import _tailor_impl

    with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
        with pytest.raises(TyperExit):
            await _tailor_impl(
                job_url="https://example.com/job/broken",
                resume_path=str(resume_file),
                output_dir=str(output_dir),
                model=None,
            )

    mocks["workflow"].run.assert_not_called()
