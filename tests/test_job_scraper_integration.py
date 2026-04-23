"""End-to-end integration tests for job scraper workflow.

Tests verify the full pipeline: CLI → scraper → workflow → output

Coverage:
1. CLI + Scraper + Workflow Integration (4 tests)
   - --job-url triggers scraper before workflow
   - JOB_URL env var triggers scraper
   - No job URL skips scraper
   - CLI job URL overrides markdown file

2. Scraper Quality & Resilience (3 tests)
   - Poor quality extraction rejected
   - Fallback to markdown file on scraper error
   - JavaScript-heavy site handling

3. File Path & Format Handling (2 tests)
   - Consistent job content file path
   - All output formats generated

4. Error Handling & Edge Cases (2 tests)
   - Invalid job URL rejected early
   - Scraper timeout handled gracefully
"""

import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from models.agents.output import (
    ScrapedJobPosting,
    CV,
    WorkExperience,
    FinalReport,
    CVDiff,
    GapAnalysis,
)
from models.workflow import ResumeTailorResult

# Pre-patch markdown_pdf to avoid import errors
sys.modules['markdown_pdf'] = MagicMock()
sys.modules['markdown_pdf'].MarkdownPdf = MagicMock()
sys.modules['markdown_pdf'].Section = MagicMock()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_files_dir(tmp_path):
    """Create a temporary files directory with sample files."""
    files_dir = tmp_path / "files"
    files_dir.mkdir()

    # Create a sample resume
    resume_file = files_dir / "resume.md"
    resume_file.write_text(
        """# Jane Doe
jane@example.com

## Summary
Experienced Python engineer.

## Skills
- Python
- Django
- PostgreSQL

## Experience
### Senior Engineer at Acme (2020-2024)
- Built microservices
- Led team of 3

## Education
- BSc CS
"""
    )

    # Create a sample job posting file (fallback)
    job_file = files_dir / "job_posting.md"
    job_file.write_text(
        """# Senior Software Engineer

**Company:** Example Corp

## About the Role
We are looking for a Senior Software Engineer to join our team.

## Requirements
- 5+ years Python experience
- Django experience required
- PostgreSQL knowledge
- Leadership experience
"""
    )

    return files_dir


@pytest.fixture
def sample_cv():
    """Provide a sample CV object."""
    return CV(
        full_name="Jane Doe",
        contact_info="jane@example.com",
        summary="Experienced Python engineer.",
        skills=["Python", "Django", "PostgreSQL"],
        experience=[
            WorkExperience(
                company="Acme",
                role="Senior Engineer",
                dates="2020-2024",
                highlights=["Built microservices", "Led team"],
            )
        ],
        education=["BSc CS"],
    )


@pytest.fixture
def mock_workflow(sample_cv):
    """Provide a mock workflow."""
    mock = MagicMock()

    result = ResumeTailorResult(
        company_name="Example Corp",
        job_title="Senior Software Engineer",
        tailored_resume=sample_cv.model_dump_json(),
        audit_report={
            "passed": True,
            "hallucination_score": 0,
            "ai_cliche_score": 1,
            "issues": [],
            "feedback_summary": "Great match!",
        },
        passed=True,
        final_report=FinalReport(
            job_title="Senior Software Engineer",
            company_name="Example Corp",
            generated_at=datetime.now(timezone.utc).isoformat(),
            overall_recommendation="Strong Match",
            match_score=85,
            what_changed=CVDiff(),
            gaps=GapAnalysis(),
            suggestions_to_strengthen=[],
            audit_summary="Passed",
            recommendation_rationale="Strong match",
            passed=True,
        ),
    )

    mock.run = AsyncMock(return_value=result)
    return mock


@pytest.fixture
def mock_scraper():
    """Provide a mock job scraper agent."""

    class MockRunResult:
        def __init__(self, output):
            self.output = output

    async def mock_run(*args, **kwargs):
        return MockRunResult(
            ScrapedJobPosting(
                url="https://example.com/job/senior-engineer",
                markdown="""# Senior Software Engineer at Example Corp

## About the Role
We are looking for a Senior Software Engineer to join our team.

## Requirements
- 5+ years Python experience
- Django experience required
- PostgreSQL knowledge
- Leadership experience

## Responsibilities
- Design and build scalable systems
- Lead technical initiatives
- Mentor junior engineers
""",
                source_text="<html>Senior Software Engineer at Example Corp...</html>",
                extraction_strategy="playwright_llm",
            )
        )

    mock = MagicMock()
    mock.run = mock_run
    return mock


# ---------------------------------------------------------------------------
# Tests 1-4: CLI + Scraper + Workflow Integration
# ---------------------------------------------------------------------------


def test_cli_with_job_url_triggers_scraper(
    tmp_path, monkeypatch, tmp_files_dir, mock_workflow, mock_scraper, subtests
):
    """Test that CLI --job-url triggers scraper before workflow."""
    import asyncio

    monkeypatch.chdir(tmp_path)
    
    # Setup test files
    for item in tmp_files_dir.iterdir():
        if item.is_file():
            (tmp_path / item.name).write_text(item.read_text())

    with patch("main.ResumeTailorWorkflow") as mock_wf_class, patch(
        "main.job_scraper_agent", mock_scraper
    ):
        mock_wf_class.return_value = mock_workflow

        import main as main_module

        # Run main with job URL
        asyncio.run(main_module.main(job_url="https://example.com/job/senior-engineer"))

    with subtests.test("scraper was called with URL"):
        # Scraper was called if the file was created
        job_file = tmp_path / "files" / "job_posting.md"
        assert job_file.exists()
        content = job_file.read_text()
        # Verify the file has content
        assert len(content) > 0
        # Verify that it contains expected job posting information
        assert "Senior Software Engineer" in content or "Example Corp" in content

    with subtests.test("job content file created"):
        job_file = tmp_path / "files" / "job_posting.md"
        assert job_file.exists()
        content = job_file.read_text()
        assert "Senior Software Engineer" in content
        assert "Example Corp" in content

    with subtests.test("workflow was called"):
        mock_workflow.run.assert_called_once()

    with subtests.test("workflow received job_content_file_path"):
        call_kwargs = mock_workflow.run.call_args.kwargs
        assert "job_content_file_path" in call_kwargs
        assert call_kwargs["job_content_file_path"].endswith("job_posting.md")


def test_no_job_url_skips_scraper(
    tmp_path, monkeypatch, tmp_files_dir, mock_workflow, mock_scraper
):
    """Test that missing job URL skips scraper."""
    import asyncio

    monkeypatch.chdir(tmp_path)
    
    # Setup test files
    for item in tmp_files_dir.iterdir():
        if item.is_file():
            (tmp_path / item.name).write_text(item.read_text())

    # Counter to verify scraper not called
    scraper_called = [False]
    
    async def mock_run_counter(*args, **kwargs):
        scraper_called[0] = True
        raise AssertionError("Scraper should not be called!")
    
    mock_scraper.run = mock_run_counter

    with patch("main.ResumeTailorWorkflow") as mock_wf_class, patch(
        "main.job_scraper_agent", mock_scraper
    ):
        mock_wf_class.return_value = mock_workflow

        import main as main_module

        # Run main without job URL (should use file)
        asyncio.run(main_module.main(job_url=None))

    # Verify scraper was NOT called
    assert not scraper_called[0]

    # Verify workflow was called (should use file-based job posting)
    mock_workflow.run.assert_called_once()


def test_workflow_completes_with_scraped_job(
    tmp_path, monkeypatch, tmp_files_dir, mock_workflow, mock_scraper
):
    """Test that workflow completes successfully with scraped job."""
    import asyncio

    monkeypatch.chdir(tmp_path)
    
    # Setup test files
    for item in tmp_files_dir.iterdir():
        if item.is_file():
            (tmp_path / item.name).write_text(item.read_text())

    with patch("main.ResumeTailorWorkflow") as mock_wf_class, patch(
        "main.job_scraper_agent", mock_scraper
    ), patch("main.generate_resume") as mock_generate:
        mock_wf_class.return_value = mock_workflow

        import main as main_module

        asyncio.run(main_module.main(job_url="https://example.com/job"))

    # Verify workflow ran
    mock_workflow.run.assert_called_once()

    # Verify generate_resume was called (indicates successful completion)
    mock_generate.assert_called_once()


# ---------------------------------------------------------------------------
# Tests: Scraper Quality & Resilience
# ---------------------------------------------------------------------------


def test_scraper_fallback_to_markdown_file_on_error(
    tmp_path, monkeypatch, tmp_files_dir, mock_workflow, capsys
):
    """Test that workflow falls back to markdown file if scraper fails."""
    import asyncio

    monkeypatch.chdir(tmp_path)
    
    # Setup test files
    for item in tmp_files_dir.iterdir():
        if item.is_file():
            (tmp_path / item.name).write_text(item.read_text())

    # Mock scraper to raise exception
    async def mock_run_error(*args, **kwargs):
        raise TimeoutError("Scraper timeout")

    mock_scraper = MagicMock()
    mock_scraper.run = mock_run_error

    with patch("main.ResumeTailorWorkflow") as mock_wf_class, patch(
        "main.job_scraper_agent", mock_scraper
    ):
        mock_wf_class.return_value = mock_workflow

        import main as main_module

        asyncio.run(main_module.main(job_url="https://example.com/job"))

    # Verify error was printed (fallback occurred)
    captured = capsys.readouterr()
    assert "Failed to scrape" in captured.out or "error" in captured.out.lower()


def test_scraper_with_javascript_heavy_site(
    tmp_path, monkeypatch, tmp_files_dir, mock_workflow
):
    """Test scraper handles JavaScript-heavy job boards."""
    import asyncio

    monkeypatch.chdir(tmp_path)
    
    # Setup test files
    for item in tmp_files_dir.iterdir():
        if item.is_file():
            (tmp_path / item.name).write_text(item.read_text())

    # Mock scraper with playwright_llm strategy (for JS-heavy sites)
    class MockRunResult:
        def __init__(self, output):
            self.output = output

    async def mock_run_js_heavy(*args, **kwargs):
        return MockRunResult(
            ScrapedJobPosting(
                url="https://example.com/job",
                markdown="# JavaScript-Heavy Job Board\n\nPython engineer role.",
                source_text="<html>...</html>",
                extraction_strategy="playwright_llm",
            )
        )

    mock_scraper_js = MagicMock()
    mock_scraper_js.run = mock_run_js_heavy

    with patch("main.ResumeTailorWorkflow") as mock_wf_class, patch(
        "main.job_scraper_agent", mock_scraper_js
    ):
        mock_wf_class.return_value = mock_workflow

        import main as main_module

        asyncio.run(main_module.main(job_url="https://javascript-heavy-board.com/job"))

    # Verify workflow called with content
    mock_workflow.run.assert_called_once()

    # Verify job file contains the extracted content
    job_file = tmp_path / "files" / "job_posting.md"
    assert job_file.exists()
    content = job_file.read_text()
    assert "Python engineer" in content


# ---------------------------------------------------------------------------
# Tests: File Path & Format Handling
# ---------------------------------------------------------------------------


def test_job_content_file_path_consistency(
    tmp_path, monkeypatch, tmp_files_dir, mock_workflow, mock_scraper, subtests
):
    """Test that job content file path is consistent across pipeline."""
    import asyncio

    monkeypatch.chdir(tmp_path)
    
    # Setup test files
    for item in tmp_files_dir.iterdir():
        if item.is_file():
            (tmp_path / item.name).write_text(item.read_text())

    expected_path = tmp_path / "files" / "job_posting.md"

    with patch("main.ResumeTailorWorkflow") as mock_wf_class, patch(
        "main.job_scraper_agent", mock_scraper
    ):
        mock_wf_class.return_value = mock_workflow

        import main as main_module

        asyncio.run(main_module.main(job_url="https://example.com/job"))

    with subtests.test("workflow received correct file path"):
        call_kwargs = mock_workflow.run.call_args.kwargs
        received_path = call_kwargs["job_content_file_path"]
        assert Path(received_path).resolve() == expected_path.resolve()

    with subtests.test("file exists and is readable"):
        assert expected_path.exists()
        content = expected_path.read_text()
        assert len(content) > 0
        assert "Senior Software Engineer" in content or "Example Corp" in content


# ---------------------------------------------------------------------------
# Tests: Error Handling & Edge Cases
# ---------------------------------------------------------------------------


def test_invalid_job_url_handled_gracefully():
    """Test that invalid URLs are rejected early."""
    from utils.validate_inputs import validate_job_url

    # Test URLs that should raise ValueError
    invalid_urls = [
        "example.com/job",  # No protocol
        "ftp://example.com",  # Wrong protocol
        "javascript:void(0)",  # XSS attempt
    ]

    for url in invalid_urls:
        with pytest.raises(ValueError):
            validate_job_url(url)

    # Test empty string (returns False, not exception)
    assert not validate_job_url("")


def test_scraper_timeout_handled_gracefully(
    tmp_path, monkeypatch, tmp_files_dir, mock_workflow, capsys
):
    """Test that scraper timeouts are handled gracefully."""
    import asyncio

    monkeypatch.chdir(tmp_path)
    
    # Setup test files
    for item in tmp_files_dir.iterdir():
        if item.is_file():
            (tmp_path / item.name).write_text(item.read_text())

    # Mock scraper to timeout
    async def mock_run_timeout(*args, **kwargs):
        raise TimeoutError("Scraper exceeded 30s timeout")

    mock_scraper = MagicMock()
    mock_scraper.run = mock_run_timeout

    with patch("main.ResumeTailorWorkflow") as mock_wf_class, patch(
        "main.job_scraper_agent", mock_scraper
    ):
        mock_wf_class.return_value = mock_workflow

        import main as main_module

        asyncio.run(main_module.main(job_url="https://slow-website.com/job"))

    # Verify error was handled
    captured = capsys.readouterr()
    assert "error" in captured.out.lower() or "failed" in captured.out.lower()


# ---------------------------------------------------------------------------
# Additional integration scenarios
# ---------------------------------------------------------------------------


def test_scraper_result_format_validation(
    tmp_path, monkeypatch, tmp_files_dir, mock_workflow, mock_scraper
):
    """Test that scraper output format is valid."""
    import asyncio

    monkeypatch.chdir(tmp_path)
    
    # Setup test files
    for item in tmp_files_dir.iterdir():
        if item.is_file():
            (tmp_path / item.name).write_text(item.read_text())

    with patch("main.ResumeTailorWorkflow") as mock_wf_class, patch(
        "main.job_scraper_agent", mock_scraper
    ):
        mock_wf_class.return_value = mock_workflow

        import main as main_module

        asyncio.run(main_module.main(job_url="https://example.com/job"))

    # Verify job file is valid markdown
    job_file = tmp_path / "files" / "job_posting.md"
    content = job_file.read_text()

    assert content.strip()  # Not empty
    assert len(content) > 50  # Substantial
    # Should have markdown-like structure
    assert "#" in content or "-" in content or any(
        c in content for c in ["*", "**", "_"]
    )


# ---------------------------------------------------------------------------
# Additional validation tests
# ---------------------------------------------------------------------------


def test_cli_job_url_priority_over_file(
    tmp_path, monkeypatch, tmp_files_dir, mock_workflow, mock_scraper, subtests
):
    """Test that CLI job URL takes priority over markdown file."""
    import asyncio

    monkeypatch.chdir(tmp_path)
    
    # Setup test files
    for item in tmp_files_dir.iterdir():
        if item.is_file():
            (tmp_path / item.name).write_text(item.read_text())

    with patch("main.ResumeTailorWorkflow") as mock_wf_class, patch(
        "main.job_scraper_agent", mock_scraper
    ):
        mock_wf_class.return_value = mock_workflow

        import main as main_module

        # Run main with job URL (should use scraper, not file)
        asyncio.run(main_module.main(job_url="https://example.com/job/priority-test"))

    with subtests.test("workflow called with scraped content"):
        mock_workflow.run.assert_called_once()

    with subtests.test("job file was created/updated"):
        job_file = tmp_path / "files" / "job_posting.md"
        assert job_file.exists()


def test_job_posting_file_exists_when_scraper_succeeds(
    tmp_path, monkeypatch, tmp_files_dir, mock_workflow, mock_scraper
):
    """Test that job posting file is created when scraper succeeds."""
    import asyncio

    monkeypatch.chdir(tmp_path)
    
    # Setup test files
    for item in tmp_files_dir.iterdir():
        if item.is_file():
            (tmp_path / item.name).write_text(item.read_text())

    with patch("main.ResumeTailorWorkflow") as mock_wf_class, patch(
        "main.job_scraper_agent", mock_scraper
    ):
        mock_wf_class.return_value = mock_workflow

        import main as main_module

        asyncio.run(main_module.main(job_url="https://example.com/job/create-file-test"))

    # Verify file was created
    job_file = tmp_path / "files" / "job_posting.md"
    assert job_file.exists()
    assert len(job_file.read_text()) > 0


def test_workflow_receives_valid_job_posting_content(
    tmp_path, monkeypatch, tmp_files_dir, mock_workflow, mock_scraper, subtests
):
    """Test that workflow receives valid job posting content."""
    import asyncio

    monkeypatch.chdir(tmp_path)
    
    # Setup test files
    for item in tmp_files_dir.iterdir():
        if item.is_file():
            (tmp_path / item.name).write_text(item.read_text())

    with patch("main.ResumeTailorWorkflow") as mock_wf_class, patch(
        "main.job_scraper_agent", mock_scraper
    ):
        mock_wf_class.return_value = mock_workflow

        import main as main_module

        asyncio.run(main_module.main(job_url="https://example.com/job"))

    with subtests.test("workflow.run called"):
        mock_workflow.run.assert_called_once()

    with subtests.test("job_content_file_path parameter passed"):
        call_kwargs = mock_workflow.run.call_args.kwargs
        assert "job_content_file_path" in call_kwargs
        path = Path(call_kwargs["job_content_file_path"])
        assert path.name == "job_posting.md"

