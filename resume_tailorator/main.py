"""CLI entry point for Resume Tailorator using Typer."""

import logging
import os

import typer
from rich.console import Console

from resume_tailorator.models.agents.output import FinalReport, ScrapedJobPosting
from resume_tailorator.utils.markdown_writer import generate_report_markdown, generate_resume
from resume_tailorator.utils.resume_converter import (
    InputConverterRegistry,
    ResumeFileNotFoundError,
    UnsupportedFormatError,
    ConversionFailedError,
)
from resume_tailorator.workflows import ResumeTailorWorkflow
from resume_tailorator.workflows.agents import job_scraper_agent

logger = logging.getLogger(__name__)
console = Console()
app = typer.Typer()


def _get_company_slug(company_name: str) -> str:
    return company_name.replace(" ", "_").lower()


def _validate_job_url(url: str) -> bool:
    if not url.startswith(("http://", "https://")):
        raise ValueError(f"Job URL must start with http:// or https://. Got: {url}")
    return True


def _print_report_to_console(report: FinalReport) -> None:
    width = 60
    console.print("\n" + "=" * width)
    console.print(f"📊 SELF-REVIEW REPORT — {report.company_name} · {report.job_title}")
    console.print("=" * width)
    console.print(f"🎯 Match Score: {report.match_score}/100 · {report.overall_recommendation}")
    console.print(f"📅 Generated: {report.generated_at}")
    console.print(f"{'✅' if report.passed else '❌'} Audit: {'Passed' if report.passed else 'Failed'}")

    console.print("\nWHAT CHANGED")
    diff = report.what_changed
    if not diff.sections_modified:
        console.print("  (no significant changes detected)")
    else:
        if diff.summary_changed:
            console.print("  ✏️  Summary rewritten")
        if diff.skills_reordered:
            console.print(f"  🔼 Skills reordered to top: {', '.join(diff.skills_reordered)}")
        if diff.skills_deprioritized:
            console.print(f"  🔽 Skills deprioritized: {', '.join(diff.skills_deprioritized)}")
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
) -> tuple[int, str | None, str | None]:
    workflow = ResumeTailorWorkflow()
    result = await workflow.run(
        resume_content,
        job_content=job_posting_markdown,
        model=model,
    )

    company_slug = _get_company_slug(result.company_name)
    resume_path = None
    report_path = None

    if result.passed:
        console.print("\n✅ Audit Passed. Saving CV...")
        generate_resume(result, output_dir=output_dir)
        resume_path = os.path.join(output_dir, f"tailored_resume_{company_slug}.md")
    else:
        console.print("\n❌ Audit Failed. Please review the feedback and try again.")
        feedback = result.audit_report.get("feedback_summary", "No feedback available")
        console.print(f"Feedback: {feedback}")

    if result.final_report is not None:
        _print_report_to_console(result.final_report)

        report_md = generate_report_markdown(result.final_report)
        report_path = os.path.join(output_dir, f"report_{company_slug}.md")

        try:
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(report_md)
            console.print(f"\n📄 Report saved to: {report_path}")
        except IOError as e:
            console.print(f"⚠️ Error writing report file: {e}")
    else:
        console.print("\n⚠️ Self-review report could not be generated.")

    return 0, resume_path, report_path


@app.command()
async def tailor(
    job_url: str = typer.Argument(..., help="URL of job posting to scrape"),
    resume_path: str = typer.Argument(..., help="Path to resume (Markdown, DOCX, PDF)"),
    output_dir: str = typer.Option("./output", help="Directory for output files"),
    model: str | None = typer.Option(None, help="AI model to use (e.g., openai:gpt-4o-mini)"),
) -> int:
    """Run the full resume tailoring workflow."""
    if not job_url.startswith(("http://", "https://")):
        console.print(f"[red]❌ Error: Job URL must start with http:// or https://. Got: {job_url}[/red]")
        return 1

    resume_path = os.path.expanduser(resume_path)
    if not os.path.exists(resume_path):
        console.print(f"[red]❌ Resume file not found at {resume_path}[/red]")
        return 1

    os.makedirs(output_dir, exist_ok=True)

    resume_content = ""
    resume_ext = os.path.splitext(resume_path)[1].lower()

    if resume_ext in (".docx", ".pdf"):
        try:
            registry = InputConverterRegistry()
            resume_content = registry.get(resume_ext).convert(resume_path)
            console.print(f"✅ Resume converted from {resume_ext} file")
            converted_resume_path = os.path.join(output_dir, "resume_converted.md")
            with open(converted_resume_path, "w", encoding="utf-8") as f:
                f.write(resume_content)
            console.print(f"📄 Converted resume saved to: {converted_resume_path}")
        except (UnsupportedFormatError, ConversionFailedError) as e:
            console.print(f"[red]❌ Failed to convert resume: {e}[/red]")
            return 1
        except ResumeFileNotFoundError as e:
            console.print(f"[red]❌ Resume file not found: {e}[/red]")
            return 1
    else:
        try:
            with open(resume_path, encoding="utf-8") as f:
                resume_content = f.read()
        except (IOError, OSError) as e:
            console.print(f"[red]❌ Error reading resume file: {e}[/red]")
            return 1

    console.print(f"✅ Resume loaded from {resume_path}")

    if not resume_content.strip():
        console.print("[red]❌ Resume content is empty[/red]")
        return 1

    logger.info("scraping_job_posting", extra={"url": job_url})
    try:
        scrape_result = await job_scraper_agent.run(
            f"Extract and convert to Markdown this job posting: {job_url}",
        )
        if isinstance(scrape_result.output, ScrapedJobPosting):
            job_posting_markdown = scrape_result.output.markdown
            if not job_posting_markdown.strip():
                logger.error("job_posting_scraped_but_empty", extra={"url": job_url})
                console.print("[red]❌ Job posting scraped but content is empty[/red]")
                return 1
            logger.info(
                "job_posting_scraped_successfully",
                extra={"url": job_url, "content_length": len(job_posting_markdown)},
            )
            console.print(f"✅ Job posting scraped successfully from {job_url}")
        else:
            console.print(f"[yellow]⚠️ Unexpected scraper output type: {type(scrape_result.output)}[/yellow]")
            return 1
    except Exception as e:
        logger.error(
            "job_posting_scraping_failed", extra={"url": job_url, "error": str(e)}
        )
        console.print(f"[red]❌ Failed to scrape job posting from URL: {e}[/red]")
        console.print("[yellow]💡 Tip: Ensure the URL is publicly accessible and contains a valid job posting.[/yellow]")
        return 1

    exit_code, resume_path_out, report_path_out = await _run_workflow(
        resume_content,
        job_posting_markdown,
        output_dir,
        model,
    )

    if exit_code == 0 and resume_path_out and report_path_out:
        console.print("\n✅ Job completed")
        console.print(f"📄 Tailored CV: {resume_path_out}")
        console.print(f"📊 Report: {report_path_out}")

    return exit_code


@app.command()
async def re_tailor(
    job_id: str = typer.Argument(..., help="UUID of prior job"),
    recommendations: str = typer.Argument(..., help="Comments/recommendations from prior audit"),
    resume_path: str | None = typer.Option(None, help="Path to resume (uses stored path if omitted)"),
    output_dir: str = typer.Option("./output", help="Directory for output files"),
    model: str | None = typer.Option(None, help="AI model to use"),
) -> int:
    """Re-run tailoring with recommendations from a prior audit."""
    os.makedirs(output_dir, exist_ok=True)

    from resume_tailorator.memory.repository import ResumeMemoryRepository
    from resume_tailorator.memory.parser import ResumeParserAdapter
    from resume_tailorator.memory.service import ResumeMemoryService

    repo = ResumeMemoryRepository()
    parser = ResumeParserAdapter()
    service = ResumeMemoryService(repository=repo, parser=parser)

    tailored_record = repo.get_tailored_resume_by_id(job_id)
    if tailored_record is None:
        console.print(f"[red]❌ Job not found: {job_id}[/red]")
        return 1

    console.print(f"📋 Found prior job: {tailored_record.company_name} / {tailored_record.job_title}")

    if resume_path:
        resume_path = os.path.expanduser(resume_path)
        if not os.path.exists(resume_path):
            console.print(f"[red]❌ Resume file not found at {resume_path}[/red]")
            return 1
    else:
        console.print("📄 Using original resume from prior job")
        resume_path = None

    resolved = service.resolve_original_resume(path=resume_path)
    resume_content = resolved.cv.model_dump_json()

    job_posting_markdown = tailored_record.job_posting_markdown
    if not job_posting_markdown:
        console.print("[red]❌ No job posting content stored for this job[/red]")
        return 1

    console.print(f"📝 Applying recommendations: {recommendations[:50]}...")

    workflow = ResumeTailorWorkflow()
    result = await workflow.run(
        resume_content,
        job_content=job_posting_markdown,
        model=model,
        recommendations=recommendations,
    )

    company_slug = _get_company_slug(result.company_name)
    updated_cv_path = None
    updated_report_path = None

    if result.passed:
        console.print("\n✅ Audit Passed. Saving updated CV...")
        generate_resume(result, output_dir=output_dir)
        updated_cv_path = os.path.join(output_dir, f"tailored_resume_{company_slug}.md")
    else:
        console.print("\n❌ Audit Failed.")
        feedback = result.audit_report.get("feedback_summary", "No feedback available")
        console.print(f"Feedback: {feedback}")

    if result.final_report is not None:
        _print_report_to_console(result.final_report)

        report_md = generate_report_markdown(result.final_report)
        updated_report_path = os.path.join(output_dir, f"report_{company_slug}.md")

        try:
            with open(updated_report_path, "w", encoding="utf-8") as f:
                f.write(report_md)
            console.print(f"\n📄 Updated report saved to: {updated_report_path}")
        except IOError as e:
            console.print(f"⚠️ Error writing report file: {e}")
    else:
        console.print("\n⚠️ Self-review report could not be generated.")

    if updated_cv_path and updated_report_path:
        console.print(f"\n✅ Re-tailoring completed: {result.company_name} / {result.job_title}")
        console.print(f"📄 Updated CV: {updated_cv_path}")
        console.print(f"📊 Updated Report: {updated_report_path}")

    return 0


def run():
    app()


if __name__ == "__main__":
    run()