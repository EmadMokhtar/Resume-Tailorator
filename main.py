import asyncio
import os

from models.agents.output import FinalReport
from utils.markdown_writer import generate_report_markdown, generate_resume
from workflows import ResumeTailorWorkflow


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


async def main():
    # --- Inputs ---
    files_path = os.path.join(os.getcwd(), "files")
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
    except Exception as e:
        print(f"⚠️ Error reading resume file: {e}")

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
        print(f"Feedback: {result.audit_report.get('feedback_summary', '')}")

    # Print and save the self-review report (always)
    if result.final_report is not None:
        _print_report_to_console(result.final_report)

        report_md = generate_report_markdown(result.final_report)
        company_slug = result.company_name.replace(" ", "_").lower()
        report_path = os.path.join(files_path, f"report_{company_slug}.md")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_md)
        print(f"\n📄 Report saved to: {report_path}")
    else:
        print("\n⚠️ Self-review report could not be generated.")


if __name__ == "__main__":
    asyncio.run(main())
