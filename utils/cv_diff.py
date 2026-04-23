"""Pure-Python utilities for computing CV diffs and gap analysis.

No LLM calls. All comparisons are done on Pydantic model fields directly.
"""

from __future__ import annotations

from models.agents.output import CV, CVDiff, ExperienceChange, GapAnalysis, JobAnalysis


def compute_cv_diff(original: CV, tailored: CV) -> CVDiff:
    """Compute a factual diff between an original CV and a tailored CV.

    Args:
        original: The candidate's original CV.
        tailored: The CV produced by the writer agent.

    Returns:
        CVDiff populated with detected changes.
    """
    sections_modified: list[str] = []

    # --- Summary ---
    summary_changed = original.summary.strip() != tailored.summary.strip()
    if summary_changed:
        sections_modified.append("summary")

    # --- Skills reordering ---
    orig_positions = {skill.lower(): idx for idx, skill in enumerate(original.skills)}
    tail_positions = {skill.lower(): idx for idx, skill in enumerate(tailored.skills)}

    skills_reordered: list[str] = []
    skills_deprioritized: list[str] = []

    for skill in tailored.skills:
        key = skill.lower()
        if key in orig_positions:
            orig_idx = orig_positions[key]
            tail_idx = tail_positions[key]
            if tail_idx < orig_idx:
                skills_reordered.append(skill)
            elif tail_idx > orig_idx:
                skills_deprioritized.append(skill)

    if skills_reordered or skills_deprioritized:
        sections_modified.append("skills")

    # --- Experience bullet diffs ---
    experience_changes: list[ExperienceChange] = []

    # Build lookup for tailored experience by (company, role)
    tailored_exp_map = {
        (exp.company.strip(), exp.role.strip()): exp for exp in tailored.experience
    }

    for orig_exp in original.experience:
        key = (orig_exp.company.strip(), orig_exp.role.strip())
        tail_exp = tailored_exp_map.get(key)
        if tail_exp is None:
            continue

        bullets_rephrased: list[str] = []
        bullets_unchanged = 0

        for i, orig_bullet in enumerate(orig_exp.highlights):
            if i < len(tail_exp.highlights):
                tail_bullet = tail_exp.highlights[i]
                if orig_bullet.strip() != tail_bullet.strip():
                    bullets_rephrased.append(
                        f"{orig_bullet.strip()} → {tail_bullet.strip()}"
                    )
                else:
                    bullets_unchanged += 1
            else:
                # Bullet was removed
                bullets_rephrased.append(f"{orig_bullet.strip()} → (removed)")

        if bullets_rephrased:
            experience_changes.append(
                ExperienceChange(
                    company=orig_exp.company,
                    role=orig_exp.role,
                    bullets_rephrased=bullets_rephrased,
                    bullets_unchanged=bullets_unchanged,
                )
            )

    if experience_changes:
        sections_modified.append("experience")

    return CVDiff(
        summary_changed=summary_changed,
        skills_reordered=skills_reordered,
        skills_deprioritized=skills_deprioritized,
        experience_changes=experience_changes,
        sections_modified=sections_modified,
    )


def compute_gap_analysis(
    original: CV,
    tailored: CV | None,
    job: JobAnalysis,
) -> GapAnalysis:
    """Compute skill and keyword gaps between the original CV and job requirements.

    Args:
        original: The candidate's original CV (used for skill gap detection).
        tailored: The tailored CV (used for keyword coverage). Pass None if the
                  writer failed — keyword coverage will default to 0%.
        job: Structured job analysis with required skills and ATS keywords.

    Returns:
        GapAnalysis with missing skills and keyword coverage metrics.
    """
    # Normalise original skills to lowercase for comparison
    original_skills_lower = {s.lower() for s in original.skills}

    # --- Missing hard/soft skills (from original CV, not tailored) ---
    missing_hard = [
        skill for skill in job.hard_skills if skill.lower() not in original_skills_lower
    ]
    missing_soft = [
        skill for skill in job.soft_skills if skill.lower() not in original_skills_lower
    ]

    # --- Keyword coverage (from tailored CV text) ---
    if tailored is None:
        return GapAnalysis(
            missing_hard_skills=missing_hard,
            missing_soft_skills=missing_soft,
            covered_keywords=[],
            missing_keywords=list(job.keywords_to_target),
            keyword_coverage_percent=0.0,
        )

    # Serialise the entire tailored CV to a single lowercase text blob
    tailored_text = tailored.model_dump_json().lower()

    covered: list[str] = []
    missing: list[str] = []

    for keyword in job.keywords_to_target:
        if keyword.lower() in tailored_text:
            covered.append(keyword)
        else:
            missing.append(keyword)

    total = len(job.keywords_to_target)
    coverage_pct = (len(covered) / total * 100.0) if total > 0 else 0.0

    return GapAnalysis(
        missing_hard_skills=missing_hard,
        missing_soft_skills=missing_soft,
        covered_keywords=covered,
        missing_keywords=missing,
        keyword_coverage_percent=round(coverage_pct, 1),
    )
