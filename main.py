import argparse
import asyncio
import logging
import os

from models.agents.output import FinalReport, ScrapedJobPosting
from utils.markdown_writer import generate_report_markdown, generate_resume
from utils.resume_converter import (
    InputConverterRegistry,
    ResumeFileNotFoundError,
    UnsupportedFormatError,
    ConversionFailedError,
)
from workflows import ResumeTailorWorkflow
from workflows.agents import job_scraper_agent

logger = logging.getLogger(__name__)


def _get_company_slug(company_name: str) -> str:
    """Extract a URL-safe slug from a company name.

    Args:
        company_name: The company name to convert.

    Returns:
        A lowercase slug with spaces replaced by underscores.
    """
    return company_name.replace(" ", "_").lower()


def _print_report_to_console(report: FinalReport) -> None:
    """Print a compact self-review report summary to stdout."""
    width = 60
    print("\n" + "=" * width)
    print(f"📊 SELF-REVIEW REPORT — {report.company_name} · {report.job_title}")
    print("=" * width)
    print(f"🎯 Match Score: {report.match_score}/100 · {report.overall_recommendation}")
    print(f"📅 Generated: {report.generated_at}")
    print(
        f"{'✅' if report.passed else '❌'} Audit: {'Passed' if report.passed else 'Failed'}"
    )

    print("\nWHAT CHANGED")
    diff = report.what_changed
    if not diff.sections_modified:
        print("  (no significant changes detected)")
    else:
        if diff.summary_changed:
            print("  ✏️  Summary rewritten")
        if diff.skills_reordered:
            print(f"  🔼 Skills reordered to top: {', '.join(diff.skills_reordered)}")
        if diff.skills_deprioritized:
            print(f"  🔽 Skills deprioritized: {', '.join(diff.skills_deprioritized)}")
        for exp_change in diff.experience_changes:
            print(
                f"  📝 {exp_change.role} @ {exp_change.company}: "
                f"{len(exp_change.bullets_rephrased)} bullet(s) rephrased"
            )

    gap = report.gaps
    total_kw = len(gap.covered_keywords) + len(gap.missing_keywords)
    print(
        f"\nKEYWORD COVERAGE: {len(gap.covered_keywords)}/{total_kw} ({gap.keyword_coverage_percent:.1f}%)"
    )
    if gap.covered_keywords:
        print(f"  ✅ Covered: {', '.join(gap.covered_keywords)}")
    if gap.missing_keywords:
        print(f"  ❌ Missing: {', '.join(gap.missing_keywords)}")

    print("\nSKILL GAPS (not in your CV)")
    if gap.missing_hard_skills:
        print(f"  Hard: {', '.join(gap.missing_hard_skills)}")
    else:
        print("  Hard: (none)")
    if gap.missing_soft_skills:
        print(f"  Soft: {', '.join(gap.missing_soft_skills)}")
    else:
        print("  Soft: (none)")

    print("\nSUGGESTIONS TO STRENGTHEN")
    for suggestion in report.suggestions_to_strengthen:
        print(f"  → {suggestion}")

    print(f"\nRECOMMENDATION: {report.overall_recommendation}")
    # Indent the rationale to 2 spaces
    for line in report.recommendation_rationale.splitlines():
        print(f"  {line}")

    print("=" * width)


def _validate_job_url(url: str) -> bool:
    """Validate that a job URL has proper format."""
    if not url.startswith(("http://", "https://")):
        raise ValueError(f"Job URL must start with http:// or https://. Got: {url}")
    return True


async def main(job_url: str | None = None, resume_path: str | None = None, output_dir: str = "./output", model: str | None = None) -> None:
    """Execute the resume tailoring workflow.

    Args:
        job_url: Optional URL to scrape job posting from.
        resume_path: Optional path to the original resume (Markdown or DOCX).
        output_dir: Directory to save output files.
        model: AI model to use (e.g., openai:gpt-4o-mini).
    """
    os.makedirs(output_dir, exist_ok=True)

    # --- Load resume content ---
    resume_content: str = ""
    if resume_path:
        resume_path = os.path.expanduser(resume_path)
        resume_ext = os.path.splitext(resume_path)[1].lower()

        if not os.path.exists(resume_path):
            print(f"❌ Resume file not found at {resume_path}")
            return

        if resume_ext in (".docx", ".pdf"):
            try:
                registry = InputConverterRegistry()
                resume_content = registry.get(resume_ext).convert(resume_path)
                print(f"✅ Resume converted from {resume_ext} file")
                converted_resume_path = os.path.join(output_dir, "resume_converted.md")
                with open(converted_resume_path, "w", encoding="utf-8") as f:
                    f.write(resume_content)
                print(f"📄 Converted resume saved to: {converted_resume_path}")
            except (UnsupportedFormatError, ConversionFailedError) as e:
                print(f"❌ Failed to convert resume: {e}")
                return
            except ResumeFileNotFoundError as e:
                print(f"❌ Resume file not found: {e}")
                return
        else:
            try:
                with open(resume_path, encoding="utf-8") as f:
                    resume_content = f.read()
            except (IOError, OSError) as e:
                print(f"❌ Error reading resume file: {e}")
                return

        print(f"✅ Resume loaded from {resume_path}")

    if not resume_content.strip():
        print("❌ Resume content is empty")
        return

    # --- Scrape job posting ---
    job_posting_markdown: str = ""
    if job_url:
        try:
            _validate_job_url(job_url)
        except ValueError as e:
            print(f"❌ Error: {e}")
            return

        logger.info("scraping_job_posting", extra={"url": job_url})
        try:
            scrape_result = await job_scraper_agent.run(
                f"Extract and convert to Markdown this job posting: {job_url}",
            )
            if isinstance(scrape_result.output, ScrapedJobPosting):
                job_posting_markdown = scrape_result.output.markdown
                if not job_posting_markdown.strip():
                    logger.error("job_posting_scraped_but_empty", extra={"url": job_url})
                    print("❌ Job posting scraped but content is empty")
                    return
                logger.info(
                    "job_posting_scraped_successfully",
                    extra={"url": job_url, "content_length": len(job_posting_markdown)},
                )
                print(f"✅ Job posting scraped successfully from {job_url}")
            else:
                print(f"⚠️ Unexpected scraper output type: {type(scrape_result.output)}")
                return
        except Exception as e:
            logger.error(
                "job_posting_scraping_failed", extra={"url": job_url, "error": str(e)}
            )
            print(f"❌ Failed to scrape job posting from URL: {e}")
            print("💡 Tip: Ensure the URL is publicly accessible and contains a valid job posting.")
            return
    else:
        print("❌ No job URL provided")
        return

    # --- Run the workflow ---
    workflow = ResumeTailorWorkflow()
    result = await workflow.run(
        resume_content,
        job_content=job_posting_markdown,
        model=model,
    )

    # Save tailored CV if audit passed
    if result.passed:
        print("\n✅ Audit Passed. Saving CV...")
        generate_resume(result, output_dir=output_dir)
    else:
        print("\n❌ Audit Failed. Please review the feedback and try again.")
        feedback = result.audit_report.get("feedback_summary", "No feedback available")
        print(f"Feedback: {feedback}")

    # Print and save the self-review report (always)
    if result.final_report is not None:
        _print_report_to_console(result.final_report)

        report_md = generate_report_markdown(result.final_report)
        company_slug = _get_company_slug(result.company_name)
        report_path = os.path.join(output_dir, f"report_{company_slug}.md")

        try:
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(report_md)
            print(f"\n📄 Report saved to: {report_path}")
        except IOError as e:
            print(f"⚠️ Error writing report file: {e}")
    else:
        print("\n⚠️ Self-review report could not be generated.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Resume Tailorator - Tailor your resume for any job"
    )
    parser.add_argument(
        "--job-url",
        default=None,
        metavar="URL",
        help="URL of the job posting to scrape.",
    )
    parser.add_argument(
        "--resume-path",
        default=None,
        metavar="PATH",
        help="Path to your original resume (Markdown or DOCX).",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        metavar="DIR",
        help="Directory to save the output report (default: ./output).",
    )
    parser.add_argument(
        "--model",
        default=None,
        metavar="MODEL",
        help="AI model to use (e.g., openai:gpt-4o-mini, anthropic:claude-sonnet-4).",
    )
    args = parser.parse_args()

    output_dir = args.output_dir or "./output"

    asyncio.run(main(job_url=args.job_url, resume_path=args.resume_path, output_dir=output_dir, model=args.model))
