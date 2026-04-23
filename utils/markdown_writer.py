# Add this import at the top
import os
import json

from models.agents.output import FinalReport
from models.workflow import ResumeTailorResult
from utils.pdf_converter import markdown_to_pdf


def generate_resume(result: ResumeTailorResult) -> None:
    """
    Convert Markdown content to PDF with professional styling.

    Args:
        result: ResumeTailorResult object containing tailored resume and company name
    """
    files_path = os.path.join(os.getcwd(), "files")
    base_filename = f"tailored_resume_{result.company_name}"
    md_output_path = os.path.join(files_path, f"{base_filename}.md")
    pdf_output_path = os.path.join(files_path, f"{base_filename}.pdf")

    # Parse the CV JSON back to CV object
    cv_data = json.loads(result.tailored_resume)

    # Build markdown content
    md_content = [f"# {cv_data.get('full_name', 'N/A')}\n"]

    if cv_data.get("contact_info"):
        md_content.append(f"{cv_data.get('contact_info')}\n")
    md_content.append("\n")

    md_content.append(f"## Professional Summary\n{cv_data.get('summary', '')}\n\n")

    md_content.append("## Skills\n")
    for skill in cv_data.get("skills", []):
        md_content.append(f"- {skill}\n")

    if cv_data.get("projects"):
        md_content.append("\n## Projects\n")
        for project in cv_data.get("projects", []):
            md_content.append(f"{project}\n\n")

    md_content.append("\n## Work Experience\n")
    for exp in cv_data.get("experience", []):
        md_content.append(
            f"### {exp.get('role', '')} at {exp.get('company', '')} ({exp.get('dates', '')})\n\n"
        )
        for hl in exp.get("highlights", []):
            md_content.append(f"- {hl}\n")
        md_content.append("\n")

    md_content.append("## Education\n")
    for edu in cv_data.get("education", []):
        md_content.append(f"- {edu}\n")

    if cv_data.get("certifications"):
        md_content.append("\n## Certifications\n")
        for cert in cv_data.get("certifications", []):
            md_content.append(f"- {cert}\n")

    if cv_data.get("publications"):
        md_content.append("\n## Publications\n")
        for pub in cv_data.get("publications", []):
            md_content.append(f"- {pub}\n")

    markdown_text = "".join(md_content)

    # Save Markdown
    with open(md_output_path, "w", encoding="utf-8") as f:
        f.write(markdown_text)

    # Save PDF
    markdown_to_pdf(markdown_text, pdf_output_path)

    print(
        f"✅ Tailored CV saved to:\n   - Markdown: {md_output_path}\n   - PDF: {pdf_output_path}"
    )


def generate_report_markdown(report: FinalReport) -> str:
    """Render a FinalReport as a Markdown string.

    Args:
        report: The completed FinalReport.

    Returns:
        A Markdown-formatted string ready to write to a file.
    """
    lines: list[str] = []

    lines.append(f"# Self-Review Report — {report.company_name} · {report.job_title}\n")
    lines.append(f"**Generated:** {report.generated_at}  ")
    lines.append(f"**Audit Passed:** {'✅ Yes' if report.passed else '❌ No'}\n")

    lines.append("---\n")

    # Match score and recommendation
    lines.append("## 🎯 Match Score & Recommendation\n")
    lines.append(f"**Score:** {report.match_score}/100  ")
    lines.append(f"**Verdict:** {report.overall_recommendation}\n")
    lines.append(f"\n{report.recommendation_rationale}\n")

    # What changed
    lines.append("---\n")
    lines.append("## ✏️ What Changed\n")
    diff = report.what_changed
    if not diff.sections_modified:
        lines.append("_No significant changes detected._\n")
    else:
        if diff.summary_changed:
            lines.append("- **Summary** was rewritten\n")
        if diff.skills_reordered:
            reordered = ", ".join(diff.skills_reordered)
            lines.append(f"- **Skills reordered to top:** {reordered}\n")
        if diff.skills_deprioritized:
            deprioritized = ", ".join(diff.skills_deprioritized)
            lines.append(f"- **Skills deprioritized:** {deprioritized}\n")
        for exp_change in diff.experience_changes:
            lines.append(
                f"- **{exp_change.role} at {exp_change.company}:** "
                f"{len(exp_change.bullets_rephrased)} bullet(s) rephrased, "
                f"{exp_change.bullets_unchanged} unchanged\n"
            )
            for bullet in exp_change.bullets_rephrased:
                lines.append(f"  - {bullet}\n")

    # Keyword coverage
    lines.append("---\n")
    lines.append("## 🔑 Keyword Coverage\n")
    gap = report.gaps
    total = len(gap.covered_keywords) + len(gap.missing_keywords)
    lines.append(
        f"**{len(gap.covered_keywords)}/{total} keywords covered "
        f"({gap.keyword_coverage_percent:.1f}%)**\n"
    )
    if gap.covered_keywords:
        covered_str = ", ".join(f"`{k}`" for k in gap.covered_keywords)
        lines.append(f"\n✅ **Covered:** {covered_str}\n")
    if gap.missing_keywords:
        missing_str = ", ".join(f"`{k}`" for k in gap.missing_keywords)
        lines.append(f"\n❌ **Missing:** {missing_str}\n")

    # Skill gaps
    lines.append("---\n")
    lines.append("## 🚧 Skill Gaps\n")
    if not gap.missing_hard_skills and not gap.missing_soft_skills:
        lines.append("_No skill gaps detected — your CV covers all required skills!_\n")
    else:
        if gap.missing_hard_skills:
            hard_str = ", ".join(gap.missing_hard_skills)
            lines.append(f"**Hard skills not in your CV:** {hard_str}\n")
        if gap.missing_soft_skills:
            soft_str = ", ".join(gap.missing_soft_skills)
            lines.append(f"**Soft skills not in your CV:** {soft_str}\n")

    # Suggestions
    lines.append("---\n")
    lines.append("## 💡 Suggestions to Strengthen Your Application\n")
    for suggestion in report.suggestions_to_strengthen:
        lines.append(f"- {suggestion}\n")

    # Audit summary
    lines.append("---\n")
    lines.append("## 🔍 Audit Summary\n")
    lines.append(f"{report.audit_summary}\n")

    return "\n".join(lines)
