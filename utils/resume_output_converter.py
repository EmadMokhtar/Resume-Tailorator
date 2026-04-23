"""Output resume conversion: Markdown string → .md / .pdf / .docx files."""

from __future__ import annotations

import json

from models.workflow import ResumeTailorResult
from utils.resume_converter import OutputConversionFailedError


# ---------------------------------------------------------------------------
# Markdown builder
# ---------------------------------------------------------------------------


def build_resume_markdown(result: ResumeTailorResult) -> str:
    """Build a Markdown string from a tailored resume result.

    Args:
        result: ResumeTailorResult with tailored_resume as a JSON-encoded CV dict.

    Returns:
        Formatted Markdown string.
    """
    try:
        cv = json.loads(result.tailored_resume)
    except json.JSONDecodeError as exc:
        raise OutputConversionFailedError(
            f"Invalid JSON in tailored_resume: {exc}"
        ) from exc
    parts: list[str] = [f"# {cv.get('full_name', 'N/A')}\n"]

    if cv.get("contact_info"):
        parts.append(f"{cv['contact_info']}\n")
    parts.append("\n")

    parts.append(f"## Professional Summary\n{cv.get('summary', '')}\n\n")

    parts.append("## Skills\n")
    for skill in cv.get("skills", []):
        parts.append(f"- {skill}\n")

    parts.append("\n## Work Experience\n")
    for exp in cv.get("experience", []):
        parts.append(
            f"### {exp.get('role', '')} at {exp.get('company', '')} "
            f"({exp.get('dates', '')})\n\n"
        )
        for highlight in exp.get("highlights", []):
            parts.append(f"- {highlight}\n")
        parts.append("\n")

    parts.append("## Education\n")
    for edu in cv.get("education", []):
        parts.append(f"- {edu}\n")

    if cv.get("certifications"):
        parts.append("\n## Certifications\n")
        for cert in cv.get("certifications", []):
            parts.append(f"- {cert}\n")

    if cv.get("publications"):
        parts.append("\n## Publications\n")
        for pub in cv.get("publications", []):
            parts.append(f"- {pub}\n")

    if cv.get("projects"):
        parts.append("\n## Projects\n")
        for project in cv.get("projects", []):
            parts.append(f"{project}\n\n")

    return "".join(parts)
