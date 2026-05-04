"""Tests for CLI with Typer - tailor command."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import os

import pytest
import typer

from resume_tailorator import main as main_module
from resume_tailorator.models.agents.output import CV, WorkExperience, ScrapedJobPosting
from resume_tailorator.models.workflow import ResumeTailorResult

pytestmark = pytest.mark.anyio


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
            "feedback_summary": "Looks good.",
        },
        passed=passed,
    )


def _make_scraped_job(markdown: str = "# Job Posting\nPython engineer") -> ScrapedJobPosting:
    return ScrapedJobPosting(
        markdown=markdown,
        url="https://example.com/job/123",
        source_text="Raw job posting text",
        extraction_strategy="test",
    )


async def test_taylor_command_success(tmp_path, monkeypatch, subtests) -> None:
    """tailor command with valid inputs should succeed and show output."""
    resume_file = tmp_path / "resume.md"
    resume_file.write_text("# Jane Doe\nPython developer.")

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    monkeypatch.chdir(tmp_path)

    cv = _make_cv()
    workflow_result = _make_result(cv=cv, passed=True)

    mock_workflow = MagicMock()
    mock_workflow.run = AsyncMock(return_value=workflow_result)
    mock_generate_resume = MagicMock()

    scraped_job = _make_scraped_job()

    patches = [
        patch("resume_tailorator.main.job_scraper_agent.run", AsyncMock(return_value=MagicMock(output=scraped_job))),
        patch("resume_tailorator.main.ResumeTailorWorkflow", return_value=mock_workflow),
        patch("resume_tailorator.main.generate_resume", mock_generate_resume),
    ]

    with patches[0], patches[1], patches[2]:
        exit_code = await main_module.tailor(
            job_url="https://example.com/job/123",
            resume_path=str(resume_file),
            output_dir=str(output_dir),
            model=None,
        )

    with subtests.test("exit code is 0"):
        assert exit_code == 0

    with subtests.test("workflow.run called"):
        mock_workflow.run.assert_called_once()

    with subtests.test("generate_resume called"):
        mock_generate_resume.assert_called_once()


async def test_taylor_command_invalid_url_format(tmp_path, monkeypatch, capsys) -> None:
    """tailor command with invalid URL format should return 1."""
    resume_file = tmp_path / "resume.md"
    resume_file.write_text("# Jane Doe\nPython developer.")

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    monkeypatch.chdir(tmp_path)

    exit_code = await main_module.tailor(
        job_url="not-a-valid-url",
        resume_path=str(resume_file),
        output_dir=str(output_dir),
        model=None,
    )

    assert exit_code == 1
    output = capsys.readouterr().out
    assert "http://" in output or "https://" in output


async def test_taylor_command_resume_not_found(tmp_path, monkeypatch, capsys) -> None:
    """tailor command with non-existent resume should return 1."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    monkeypatch.chdir(tmp_path)

    exit_code = await main_module.tailor(
        job_url="https://example.com/job/123",
        resume_path="/no/such/file.md",
        output_dir=str(output_dir),
        model=None,
    )

    assert exit_code == 1
    output = capsys.readouterr().out
    assert "not found" in output.lower() or "❌" in output


async def test_taylor_command_scraping_failure(tmp_path, monkeypatch, capsys) -> None:
    """tailor command when scraping fails should return 1."""
    resume_file = tmp_path / "resume.md"
    resume_file.write_text("# Jane Doe\nPython developer.")

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    monkeypatch.chdir(tmp_path)

    mock_scraper = AsyncMock(side_effect=Exception("Network error"))

    with patch("resume_tailorator.main.job_scraper_agent.run", mock_scraper):
        exit_code = await main_module.tailor(
            job_url="https://example.com/job/123",
            resume_path=str(resume_file),
            output_dir=str(output_dir),
            model=None,
        )

    assert exit_code == 1
    output = capsys.readouterr().out
    assert "scrape" in output.lower() or "failed" in output.lower()


async def test_taylor_command_failed_audit_exits_zero(tmp_path, monkeypatch, capsys) -> None:
    """tailor command with failed audit should exit 0 (report still generated)."""
    resume_file = tmp_path / "resume.md"
    resume_file.write_text("# Jane Doe\nPython developer.")

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    monkeypatch.chdir(tmp_path)

    cv = _make_cv()
    workflow_result = _make_result(cv=cv, passed=False)

    mock_workflow = MagicMock()
    mock_workflow.run = AsyncMock(return_value=workflow_result)

    scraped_job = _make_scraped_job()

    with patch("resume_tailorator.main.job_scraper_agent.run", AsyncMock(return_value=MagicMock(output=scraped_job))):
        with patch("resume_tailorator.main.ResumeTailorWorkflow", return_value=mock_workflow):
            exit_code = await main_module.tailor(
                job_url="https://example.com/job/123",
                resume_path=str(resume_file),
                output_dir=str(output_dir),
                model=None,
            )

    assert exit_code == 0
    mock_workflow.run.assert_called_once()


async def test_taylor_command_empty_job_content(tmp_path, monkeypatch, capsys) -> None:
    """tailor command when scraped job is empty should return 1."""
    resume_file = tmp_path / "resume.md"
    resume_file.write_text("# Jane Doe\nPython developer.")

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    monkeypatch.chdir(tmp_path)

    scraped_job = _make_scraped_job(markdown="")

    with patch("resume_tailorator.main.job_scraper_agent.run", AsyncMock(return_value=MagicMock(output=scraped_job))):
        exit_code = await main_module.tailor(
            job_url="https://example.com/job/123",
            resume_path=str(resume_file),
            output_dir=str(output_dir),
            model=None,
        )

    assert exit_code == 1
    output = capsys.readouterr().out
    assert "empty" in output.lower()


async def test_taylor_command_docx_conversion(tmp_path, monkeypatch) -> None:
    """tailor command should convert DOCX resume to markdown."""
    from docx import Document

    resume_file = tmp_path / "resume.docx"
    doc = Document()
    doc.add_heading("Jane Doe", 0)
    doc.add_paragraph("Python developer")
    doc.save(str(resume_file))

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    monkeypatch.chdir(tmp_path)

    cv = _make_cv()
    workflow_result = _make_result(cv=cv, passed=True)

    mock_workflow = MagicMock()
    mock_workflow.run = AsyncMock(return_value=workflow_result)
    mock_generate_resume = MagicMock()

    scraped_job = _make_scraped_job()

    with patch("resume_tailorator.main.job_scraper_agent.run", AsyncMock(return_value=MagicMock(output=scraped_job))):
        with patch("resume_tailorator.main.ResumeTailorWorkflow", return_value=mock_workflow):
            with patch("resume_tailorator.main.generate_resume", mock_generate_resume):
                exit_code = await main_module.tailor(
                    job_url="https://example.com/job/123",
                    resume_path=str(resume_file),
                    output_dir=str(output_dir),
                    model=None,
                )

    assert exit_code == 0
    mock_workflow.run.assert_called_once()
    converted_file = output_dir / "resume_converted.md"
    assert converted_file.exists()