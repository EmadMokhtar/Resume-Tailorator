# Add this import at the top
import os
import json

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
