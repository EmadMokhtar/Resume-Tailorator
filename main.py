import argparse
import asyncio
import logging
import os

from models.agents.output import FinalReport, ScrapedJobPosting
from utils.markdown_writer import generate_report_markdown, generate_resume
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


async def main(job_url: str | None = None) -> None:
    """Execute the resume tailoring workflow.

    This function performs the following steps:
    1. Reads the original resume from files/resume.md
    2. Loads or scrapes the job posting (from URL if provided, or from files/job_posting.md)
    3. Runs the ResumeTailorWorkflow to tailor the resume
    4. If audit passes: saves the tailored CV
    5. Always: prints and saves the self-review report

    The report is saved to files/report_{company_slug}.md regardless of audit result.
    If any file is missing or an error occurs, a warning is printed and execution continues.

    Args:
        job_url: Optional URL to scrape job posting from. If not provided, uses local file.
    """
    # --- Inputs ---
    files_path = os.path.join(os.getcwd(), "files")
    os.makedirs(files_path, exist_ok=True)
    job_content_file_path = os.path.join(files_path, "job_posting.md")
    resume_file_path = os.path.join(files_path, "resume.md")
    original_cv_text: str = ""

    try:
        with open(resume_file_path, encoding="utf-8") as f:
            original_cv_text = f.read()
    except FileNotFoundError:
        print(
            f"⚠️ Resume file not found at {resume_file_path}. Continuing with empty resume."
        )
    except (IOError, OSError) as e:
        print(f"⚠️ Error reading resume file: {e}")

    # Load or scrape job posting
    job_posting_markdown: str = ""

    if job_url:
        # Scrape job posting from URL (takes priority)
        logger.info("scraping_job_posting", extra={"url": job_url})
        try:
            scrape_result = await job_scraper_agent.run(
                f"Extract and convert to Markdown this job posting: {job_url}",
            )
            if isinstance(scrape_result.output, ScrapedJobPosting):
                job_posting_markdown = scrape_result.output.markdown
                if not job_posting_markdown.strip():
                    logger.error(
                        "job_posting_scraped_but_empty", extra={"url": job_url}
                    )
                    print("❌ Job posting scraped but content is empty")
                    return
                logger.info(
                    "job_posting_scraped_successfully",
                    extra={"url": job_url, "content_length": len(job_posting_markdown)},
                )
                print(f"✅ Job posting scraped successfully from {job_url}")
                # Write scraped content to file for workflow
                try:
                    with open(job_content_file_path, "w", encoding="utf-8") as f:
                        f.write(job_posting_markdown)
                except (IOError, OSError) as e:
                    print(f"❌ Error writing scraped job posting to file: {e}")
                    return
            else:
                print(f"⚠️ Unexpected scraper output type: {type(scrape_result.output)}")
                return
        except Exception as e:
            logger.error(
                "job_posting_scraping_failed", extra={"url": job_url, "error": str(e)}
            )
            print(f"❌ Failed to scrape job posting from URL: {e}")
            print(
                "💡 Tip: Ensure the URL is publicly accessible and contains a valid job posting."
            )
            return
    else:
        # Load job posting from markdown file
        if not os.path.exists(job_content_file_path):
            print(
                f"⚠️ Job posting file not found at {job_content_file_path}. "
                "Please provide --job-url or ensure the file exists."
            )
            return

        try:
            with open(job_content_file_path, encoding="utf-8") as f:
                job_posting_markdown = f.read()
        except (IOError, OSError) as e:
            print(f"❌ Error reading job posting file: {e}")
            return

        if not job_posting_markdown.strip():
            print(f"❌ Job posting file is empty: {job_content_file_path}")
            return

    # Run the workflow
    workflow = ResumeTailorWorkflow()
    result = await workflow.run(
        original_cv_text, job_content_file_path=job_content_file_path
    )

    # Save tailored CV if audit passed
    if result.passed:
        print("\n✅ Audit Passed. Saving CV...")
        generate_resume(result)
    else:
        print("\n❌ Audit Failed. Please review the feedback and try again.")
        feedback = result.audit_report.get("feedback_summary", "No feedback available")
        print(f"Feedback: {feedback}")

    # Print and save the self-review report (always)
    if result.final_report is not None:
        _print_report_to_console(result.final_report)

        report_md = generate_report_markdown(result.final_report)
        company_slug = _get_company_slug(result.company_name)
        report_path = os.path.join(files_path, f"report_{company_slug}.md")

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
        default=os.environ.get("JOB_URL"),
        help="URL of job posting to scrape",
    )
    args = parser.parse_args()

    asyncio.run(main(job_url=args.job_url))
