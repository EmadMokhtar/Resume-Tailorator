"""CLI entry point for Resume Tailorator using Typer."""

import asyncio
import hashlib
import logging
import os
import re
from datetime import date
from pathlib import Path

import typer
from pydantic import ValidationError
from rich.console import Console

from resume_tailorator.memory.parser import PydanticAIResumeParser
from resume_tailorator.memory.service import ResumeMemoryService
from resume_tailorator.memory.sqlite_repository import SQLiteResumeMemoryRepository
from resume_tailorator.models.agents.output import (
    AuditIssue,
    AuditResult,
    CV,
    FinalReport,
    ScrapedJobPosting,
)
from resume_tailorator.models.workflow import ResumeTailorResult
from resume_tailorator.utils.markdown_writer import (
    generate_report_markdown,
    generate_resume,
)
from resume_tailorator.utils.resume_converter import (
    ConversionFailedError,
    InputConverterRegistry,
    ResumeFileNotFoundError,
    UnsupportedFormatError,
)
from resume_tailorator.workflows import ResumeTailorWorkflow
from resume_tailorator.workflows.agents import job_scraper_agent, run_agent

logger = logging.getLogger(__name__)
console = Console()
app = typer.Typer()


def _get_company_slug(company_name: str) -> str:
    return company_name.replace(" ", "_").lower()


def _get_job_fingerprint(job_url: str, job_title: str) -> str:
    return hashlib.sha256(f"{job_url}:{job_title}".encode()).hexdigest()[:32]


def _slugify(text: str) -> str:
    """Convert text to a filesystem-safe slug."""
    text = text.lower().replace(" ", "_")
    text = re.sub(r"[^a-z0-9_]", "", text)
    return text


def _resolve_pattern(template: str, result: ResumeTailorResult, cv: CV) -> str:
    """Replace template variables with slugified values from result and CV."""
    timestamp = date.today().strftime("%Y%m%d")
    replacements = {
        "{company_name}": _slugify(result.company_name),
        "{job_title}": _slugify(result.job_title),
        "{full_name}": _slugify(cv.full_name),
        "{timestamp}": timestamp,
    }
    resolved = template
    for variable, value in replacements.items():
        resolved = resolved.replace(variable, value)
    return resolved


_INVALID_PATH_CHARS = re.compile(r"[\x00-\x1f\x7f<>:\"|?*]")


def _is_safe_path_component(name: str) -> bool:
    """Reject path components that could escape the intended directory."""
    if not name or name == "." or ".." in name:
        return False
    # Reject path separators (forward slash everywhere, backslash on Windows)
    if "/" in name or "\\" in name:
        return False
    # Reject control chars and other filesystem-dangerous characters
    if _INVALID_PATH_CHARS.search(name):
        return False
    # Reject absolute paths
    if name.startswith("/") or (len(name) > 1 and name[1] == ":"):
        return False
    return True


def _audit_result_from_dict(audit_dict: dict) -> AuditResult:
    issues = [
        AuditIssue(
            severity=i.get("severity", "Unknown"),
            issue=i.get("issue", ""),
            suggestion=i.get("suggestion", ""),
        )
        for i in audit_dict.get("issues", [])
    ]
    return AuditResult(
        passed=audit_dict.get("passed", False),
        hallucination_score=audit_dict.get("hallucination_score", 0) or 0,
        ai_cliche_score=audit_dict.get("ai_cliche_score", 0) or 0,
        issues=issues,
        feedback_summary=audit_dict.get("feedback_summary", ""),
    )


def _print_report_to_console(report: FinalReport) -> None:
    width = 60
    console.print("\n" + "=" * width)
    console.print(f"📊 SELF-REVIEW REPORT — {report.company_name} · {report.job_title}")
    console.print("=" * width)
    console.print(
        f"🎯 Match Score: {report.match_score}/100 · {report.overall_recommendation}"
    )
    console.print(f"📅 Generated: {report.generated_at}")
    console.print(
        f"{'✅' if report.passed else '❌'} Audit: {'Passed' if report.passed else 'Failed'}"
    )

    console.print("\nWHAT CHANGED")
    diff = report.what_changed
    if not diff.sections_modified:
        console.print("  (no significant changes detected)")
    else:
        if diff.summary_changed:
            console.print("  ✏️  Summary rewritten")
        if diff.skills_reordered:
            console.print(
                f"  🔼 Skills reordered to top: {', '.join(diff.skills_reordered)}"
            )
        if diff.skills_deprioritized:
            console.print(
                f"  🔽 Skills deprioritized: {', '.join(diff.skills_deprioritized)}"
            )
        for exp_change in diff.experience_changes:
            console.print(
                f"  📝 {exp_change.role} @ {exp_change.company}: "
                f"{len(exp_change.bullets_rephrased)} bullet(s) rephrased"
            )

    gap = report.gaps
    total_kw = len(gap.covered_keywords) + len(gap.missing_keywords)
    console.print(
        f"\nKEYWORD COVERAGE: {len(gap.covered_keywords)}/{total_kw} ({gap.keyword_coverage_percent:.1f}%)"
    )
    if gap.covered_keywords:
        console.print(f"  ✅ Covered: {', '.join(gap.covered_keywords)}")
    if gap.missing_keywords:
        console.print(f"  ❌ Missing: {', '.join(gap.missing_keywords)}")

    console.print("\nSKILL GAPS (not in your CV)")
    if gap.missing_hard_skills:
        console.print(f"  Hard: {', '.join(gap.missing_hard_skills)}")
    else:
        console.print("  Hard: (none)")
    if gap.missing_soft_skills:
        console.print(f"  Soft: {', '.join(gap.missing_soft_skills)}")
    else:
        console.print("  Soft: (none)")

    console.print("\nSUGGESTIONS TO STRENGTHEN")
    for suggestion in report.suggestions_to_strengthen:
        console.print(f"  → {suggestion}")

    console.print(f"\nRECOMMENDATION: {report.overall_recommendation}")
    for line in report.recommendation_rationale.splitlines():
        console.print(f"  {line}")

    console.print("=" * width)


async def _run_workflow(
    resume_content: str,
    job_posting_markdown: str,
    output_dir: str,
    model: str | None,
    recommendations: str = "",
    verbose: bool = False,
    output_pattern: str = "{company_name}-{job_title}",
    resume_name_pattern: str = "{company_name}-{full_name}",
    pre_parsed_cv: CV | None = None,
    debug: bool = False,
) -> tuple[int, str | None, str | None, ResumeTailorResult]:
    workflow = ResumeTailorWorkflow()

    job_content = job_posting_markdown
    if recommendations:
        job_content += f"\n\n---\n**Additional recommendations from prior audit:**\n{recommendations}\n"

    result = await workflow.run(
        resume_content,
        job_content=job_content,
        model=model,
        pre_parsed_cv=pre_parsed_cv,
        debug=debug,
        verbose=verbose,
    )

    resume_path = None
    report_path = None

    # Guard CV parsing: workflow may return empty or invalid tailored_resume
    full_name = ""
    if result.tailored_resume:
        try:
            cv = CV.model_validate_json(result.tailored_resume)
            full_name = cv.full_name
        except (ValidationError, ValueError):
            full_name = ""

    # Build a minimal CV-like object for pattern resolution if parsing failed
    cv_fallback = CV(
        full_name=full_name or "unknown",
        summary="",
        skills=[],
        experience=[],
        education=[],
    )

    # Resolve directory and file name patterns
    job_dir_name = _resolve_pattern(output_pattern, result, cv_fallback)
    if not _is_safe_path_component(job_dir_name):
        console.print(
            f"[red]❌ Invalid output pattern resolves to unsafe path: {job_dir_name}[/red]"
        )
        raise typer.Exit(code=1)
    job_dir = os.path.join(output_dir, job_dir_name)
    os.makedirs(job_dir, exist_ok=True)

    if debug:
        debug_path = os.path.join(job_dir, "resume_debug.md")
        with open(debug_path, "w", encoding="utf-8") as f:
            f.write(resume_content)
        console.print(f"🔍 [Debug] Converted resume saved to: {debug_path}")
        console.print(
            f"🔍 [Debug] First 500 chars of resume sent to parser:\n"
            f"{resume_content[:500]}"
        )

    resume_base_name = _resolve_pattern(resume_name_pattern, result, cv_fallback)
    if not _is_safe_path_component(resume_base_name):
        console.print(
            f"[red]❌ Invalid resume name pattern resolves to unsafe path: {resume_base_name}[/red]"
        )
        raise typer.Exit(code=1)

    if result.passed:
        console.print("\n✅ Audit Passed. Saving CV...")
        resume_path = generate_resume(result, job_dir, resume_base_name)
    else:
        console.print("\n❌ Audit Failed. Please review the feedback and try again.")
        feedback = result.audit_report.get("feedback_summary", "No feedback available")
        console.print(f"Feedback: {feedback}")

    if result.final_report is not None:
        _print_report_to_console(result.final_report)

        report_md = generate_report_markdown(result.final_report)
        report_path = os.path.join(job_dir, f"{resume_base_name}_report.md")

        try:
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(report_md)
            console.print(f"\n📄 Report saved to: {report_path}")
        except IOError as e:
            console.print(f"⚠️ Error writing report file: {e}")
    else:
        console.print("\n⚠️ Self-review report could not be generated.")

    return 0, resume_path, report_path, result


async def _tailor_impl(
    job_url: str,
    resume_path: str,
    output_dir: str,
    model: str | None,
    verbose: bool = False,
    output_pattern: str = "{company_name}-{job_title}",
    resume_name_pattern: str = "{company_name}-{full_name}",
    debug: bool = False,
) -> int:
    """Async implementation of tailor command."""
    if not job_url.startswith(("http://", "https://")):
        console.print(
            f"[red]❌ Error: Job URL must start with http:// or https://. Got: {job_url}[/red]"
        )
        raise typer.Exit(code=1)

    resume_path_expanded = os.path.expanduser(resume_path)
    if not os.path.exists(resume_path_expanded):
        console.print(f"[red]❌ Resume file not found at {resume_path_expanded}[/red]")
        raise typer.Exit(code=1)

    os.makedirs(output_dir, exist_ok=True)

    resume_content = ""
    resume_ext = os.path.splitext(resume_path_expanded)[1].lower()
    converted_resume_path: str | None = None

    if resume_ext in (".docx", ".pdf"):
        try:
            registry = InputConverterRegistry()
            resume_content = registry.get(resume_ext).convert(resume_path_expanded)
            console.print(f"✅ Resume converted from {resume_ext} file")
            converted_resume_path = os.path.join(output_dir, "resume_converted.md")
            with open(converted_resume_path, "w", encoding="utf-8") as f:
                f.write(resume_content)
            console.print(f"📄 Converted resume saved to: {converted_resume_path}")
        except (UnsupportedFormatError, ConversionFailedError) as e:
            console.print(f"[red]❌ Failed to convert resume: {e}[/red]")
            raise typer.Exit(code=1)
        except ResumeFileNotFoundError as e:
            console.print(f"[red]❌ Resume file not found: {e}[/red]")
            raise typer.Exit(code=1)
    else:
        try:
            with open(resume_path_expanded, encoding="utf-8") as f:
                resume_content = f.read()
        except (IOError, OSError) as e:
            console.print(f"[red]❌ Error reading resume file: {e}[/red]")
            raise typer.Exit(code=1)

    console.print(f"✅ Resume loaded from {resume_path_expanded}")

    if not resume_content.strip():
        console.print("[red]❌ Resume content is empty[/red]")
        raise typer.Exit(code=1)

    # Compute content hash and check cache before running the workflow
    content_hash = hashlib.sha256(resume_content.encode()).hexdigest()
    pre_parsed_cv: CV | None = None
    try:
        repo = SQLiteResumeMemoryRepository()
        parser = PydanticAIResumeParser()
        service = ResumeMemoryService(repository=repo, parser=parser)
        resolved = await service.aresolve_original_resume(
            path=(converted_resume_path or resume_path_expanded)
        )
        pre_parsed_cv = resolved.cv
        if debug:
            console.print(f"🔍 [Debug] Content hash: {content_hash}")
            console.print(
                f"🔍 [Debug] Cache hit: using pre-parsed CV with "
                f"{len(pre_parsed_cv.skills)} skills"
            )
    except Exception:
        if debug:
            console.print(
                "[yellow]🔍 [Debug] Cache miss or error — will parse with AI[/yellow]"
            )
        pre_parsed_cv = None

    logger.info("scraping_job_posting", extra={"url": job_url})
    try:
        scrape_result = await run_agent(
            job_scraper_agent,
            f"Extract and convert to Markdown this job posting: {job_url}",
            verbose=verbose,
            agent_label="Scraper",
        )
        if isinstance(scrape_result.output, ScrapedJobPosting):
            job_posting_markdown = scrape_result.output.markdown
            if not job_posting_markdown.strip():
                logger.error("job_posting_scraped_but_empty", extra={"url": job_url})
                console.print("[red]❌ Job posting scraped but content is empty[/red]")
                raise typer.Exit(code=1)
            logger.info(
                "job_posting_scraped_successfully",
                extra={"url": job_url, "content_length": len(job_posting_markdown)},
            )
            console.print(f"✅ Job posting scraped successfully from {job_url}")
        else:
            console.print(
                f"[yellow]⚠️ Unexpected scraper output type: {type(scrape_result.output)}[/yellow]"
            )
            raise typer.Exit(code=1)
    except Exception as e:
        logger.error(
            "job_posting_scraping_failed", extra={"url": job_url, "error": str(e)}
        )
        console.print(f"[red]❌ Failed to scrape job posting from URL: {e}[/red]")
        console.print(
            "[yellow]💡 Tip: Ensure the URL is publicly accessible and contains a valid job posting.[/yellow]"
        )
        raise typer.Exit(code=1)

    exit_code, resume_path_out, report_path_out, result = await _run_workflow(
        resume_content,
        job_posting_markdown,
        output_dir,
        model,
        verbose=verbose,
        output_pattern=output_pattern,
        resume_name_pattern=resume_name_pattern,
        pre_parsed_cv=pre_parsed_cv,
        debug=debug,
    )

    if exit_code == 0:
        try:
            repo = SQLiteResumeMemoryRepository()
            parser = PydanticAIResumeParser()
            service = ResumeMemoryService(repository=repo, parser=parser)

            # Use converted markdown path for non-markdown resumes so
            # resolve_original_resume can read it as text.
            source_path = converted_resume_path or resume_path_expanded
            resolved = await service.aresolve_original_resume(path=source_path)
            job_fingerprint = _get_job_fingerprint(job_url, result.job_title)

            audit = _audit_result_from_dict(result.audit_report)

            if result.tailored_resume:
                tailored_cv = CV.model_validate_json(result.tailored_resume)
            else:
                tailored_cv = resolved.cv

            record = service.save_tailored_resume(
                source_id=resolved.source.id,
                job_fingerprint=job_fingerprint,
                company_name=result.company_name,
                job_title=result.job_title,
                tailored_cv=tailored_cv,
                audit_result=audit,
                job_posting_markdown=job_posting_markdown,
            )
            console.print(f"\n💾 Job ID: {record.id}")
            console.print("\n✅ Job completed")
            console.print(f"📄 Tailored CV: {resume_path_out}")
            console.print(f"📊 Report: {report_path_out}")
        except Exception as e:
            logger.warning("Failed to persist tailored resume", exc_info=True)
            console.print(f"[yellow]⚠️ Failed to save job to memory: {e}[/yellow]")
            if resume_path_out and report_path_out:
                console.print("\n✅ Job completed")
                console.print(f"📄 Tailored CV: {resume_path_out}")
                console.print(f"📊 Report: {report_path_out}")

    return exit_code


@app.command()
def tailor(
    job_url: str = typer.Argument(..., help="URL of job posting to scrape"),
    resume_path: str = typer.Argument(..., help="Path to resume (Markdown, DOCX, PDF)"),
    output_dir: str = typer.Option("./output", help="Directory for output files"),
    model: str | None = typer.Option(
        None, help="AI model to use (e.g., openai:gpt-4o-mini)"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Stream agent thinking and prompts in real-time"
    ),
    output_pattern: str = typer.Option(
        "{company_name}-{job_title}",
        help="Template for the job-specific subdirectory name",
    ),
    resume_name_pattern: str = typer.Option(
        "{company_name}-{full_name}",
        help="Template for the resume file base name (without extension)",
    ),
    debug: bool = typer.Option(
        False, "--debug", "-d", help="Enable debug output and save converted resume"
    ),
) -> int:
    """Run the full resume tailoring workflow."""
    return asyncio.run(
        _tailor_impl(
            job_url,
            resume_path,
            output_dir,
            model,
            verbose=verbose,
            output_pattern=output_pattern,
            resume_name_pattern=resume_name_pattern,
            debug=debug,
        )
    )


async def _re_tailor_impl(
    job_id: str,
    recommendations: str,
    resume_path: str | None,
    output_dir: str,
    model: str | None,
    verbose: bool = False,
    output_pattern: str = "{company_name}-{job_title}",
    resume_name_pattern: str = "{company_name}-{full_name}",
    debug: bool = False,
) -> int:
    """Async implementation of re-tailor command."""
    os.makedirs(output_dir, exist_ok=True)

    repo = SQLiteResumeMemoryRepository()
    parser = PydanticAIResumeParser()
    service = ResumeMemoryService(repository=repo, parser=parser)

    tailored_record = repo.get_tailored_resume_by_id(job_id)
    if tailored_record is None:
        console.print(f"[red]❌ Job not found: {job_id}[/red]")
        raise typer.Exit(code=1)

    console.print(
        f"📋 Found prior job: {tailored_record.company_name} / {tailored_record.job_title}"
    )

    # Resolve resume path and read original text content.
    _resume_source_path: str | None = None
    if resume_path:
        _resume_source_path = os.path.expanduser(resume_path)
        if not os.path.exists(_resume_source_path):
            console.print(
                f"[red]❌ Resume file not found at {_resume_source_path}[/red]"
            )
            raise typer.Exit(code=1)
        resolved = await service.aresolve_original_resume(path=_resume_source_path)
    else:
        source = repo.get_source_by_id(tailored_record.source_id)
        if source is not None and Path(source.path).exists():
            console.print("📄 Using original resume from prior job")
            _resume_source_path = source.path
            resolved = await service.aresolve_original_resume(path=_resume_source_path)
        elif source is not None:
            # Original source is known but the file no longer exists on disk.
            console.print(
                f"[red]❌ Original resume not found at recorded path: {source.path}[/red]"
            )
            console.print(
                "[yellow]💡 Tip: Re-run with --resume-path to provide the resume file.[/yellow]"
            )
            raise typer.Exit(code=1)
        else:
            console.print(
                "[red]❌ No original resume source recorded for this job[/red]"
            )
            console.print(
                "[yellow]💡 Tip: Re-run with --resume-path to provide the resume file.[/yellow]"
            )
            raise typer.Exit(code=1)

    # Read actual file content as text — never round-trip through parsed CV JSON.
    ext = (
        os.path.splitext(_resume_source_path)[1].lower() if _resume_source_path else ""
    )
    if ext in (".docx", ".pdf"):
        try:
            registry = InputConverterRegistry()
            resume_content = registry.get(ext).convert(_resume_source_path)
        except Exception as e:
            console.print(f"[red]❌ Failed to convert resume: {e}[/red]")
            raise typer.Exit(code=1)
    else:
        try:
            with open(_resume_source_path, encoding="utf-8") as f:
                resume_content = f.read()
        except Exception as e:
            console.print(f"[red]❌ Error reading resume file: {e}[/red]")
            raise typer.Exit(code=1)

    # Use the pre-parsed CV from the resolved original resume
    pre_parsed_cv = resolved.cv if resolved else None
    if debug:
        content_hash = hashlib.sha256(resume_content.encode()).hexdigest()
        console.print(f"🔍 [Debug] Content hash: {content_hash}")
        if pre_parsed_cv:
            console.print(
                f"🔍 [Debug] Using pre-parsed CV with "
                f"{len(pre_parsed_cv.skills)} skills"
            )

    job_posting_markdown = tailored_record.job_posting_markdown
    if not job_posting_markdown:
        console.print("[red]❌ No job posting content stored for this job[/red]")
        raise typer.Exit(code=1)

    console.print(f"📝 Applying recommendations: {recommendations[:50]}...")

    exit_code, resume_path_out, report_path_out, result = await _run_workflow(
        resume_content,
        job_posting_markdown,
        output_dir,
        model,
        recommendations=recommendations,
        verbose=verbose,
        output_pattern=output_pattern,
        resume_name_pattern=resume_name_pattern,
        pre_parsed_cv=pre_parsed_cv,
        debug=debug,
    )

    if exit_code == 0:
        try:
            audit = _audit_result_from_dict(result.audit_report)

            if result.tailored_resume:
                tailored_cv = CV.model_validate_json(result.tailored_resume)
            else:
                tailored_cv = resolved.cv

            repo.save_tailored_resume(
                source_id=tailored_record.source_id,
                job_fingerprint=tailored_record.job_fingerprint,
                company_name=result.company_name,
                job_title=result.job_title,
                tailored_cv_json=tailored_cv.model_dump_json(),
                audit_report_json=audit.model_dump_json(),
                job_posting_markdown=job_posting_markdown,
            )

            if resume_path_out and report_path_out:
                console.print(
                    f"\n✅ Re-tailoring completed: {result.company_name} / {result.job_title}"
                )
                console.print(f"📄 Updated CV: {resume_path_out}")
                console.print(f"📊 Updated Report: {report_path_out}")
        except Exception as e:
            logger.warning("Failed to update tailored resume record", exc_info=True)
            console.print(f"[yellow]⚠️ Failed to update job record: {e}[/yellow]")

    return exit_code


@app.command()
def re_tailor(
    job_id: str = typer.Argument(..., help="UUID of prior job"),
    recommendations: str = typer.Argument(
        ..., help="Comments/recommendations from prior audit"
    ),
    resume_path: str | None = typer.Option(
        None, help="Path to resume (uses stored path if omitted)"
    ),
    output_dir: str = typer.Option("./output", help="Directory for output files"),
    model: str | None = typer.Option(None, help="AI model to use"),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Stream agent thinking and prompts in real-time"
    ),
    output_pattern: str = typer.Option(
        "{company_name}-{job_title}",
        help="Template for the job-specific subdirectory name",
    ),
    resume_name_pattern: str = typer.Option(
        "{company_name}-{full_name}",
        help="Template for the resume file base name (without extension)",
    ),
    debug: bool = typer.Option(
        False, "--debug", "-d", help="Enable debug output and save converted resume"
    ),
) -> int:
    """Re-run tailoring with recommendations from a prior audit."""
    return asyncio.run(
        _re_tailor_impl(
            job_id,
            recommendations,
            resume_path,
            output_dir,
            model,
            verbose=verbose,
            output_pattern=output_pattern,
            resume_name_pattern=resume_name_pattern,
            debug=debug,
        )
    )


def run():
    app()


if __name__ == "__main__":
    run()
