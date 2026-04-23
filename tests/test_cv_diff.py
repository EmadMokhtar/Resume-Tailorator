"""Unit tests for compute_cv_diff and compute_gap_analysis.

These are pure-Python tests — no LLM calls.
"""
import pytest

from models.agents.output import (
    CV,
    CVDiff,
    GapAnalysis,
    JobAnalysis,
    WorkExperience,
)
from utils.cv_diff import compute_cv_diff, compute_gap_analysis


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def original_cv() -> CV:
    return CV(
        full_name="Alice Dev",
        contact_info="alice@example.com",
        summary="Backend engineer with 5 years experience.",
        skills=["Python", "Django", "PostgreSQL", "Redis", "Docker"],
        experience=[
            WorkExperience(
                company="Acme Corp",
                role="Software Engineer",
                dates="2020-2024",
                highlights=[
                    "Built REST APIs serving 10k requests/day.",
                    "Maintained PostgreSQL databases.",
                ],
            )
        ],
        education=["BSc Computer Science, MIT, 2019"],
        certifications=[],
        publications=[],
        projects=[],
    )


@pytest.fixture
def tailored_cv(original_cv: CV) -> CV:
    """A tailored version: summary changed, skills reordered, one bullet rephrased."""
    return CV(
        full_name=original_cv.full_name,
        contact_info=original_cv.contact_info,
        summary="Backend engineer focused on scalable APIs and cloud-native development.",
        skills=["Python", "Docker", "Django", "PostgreSQL", "Redis"],  # Docker moved up
        experience=[
            WorkExperience(
                company="Acme Corp",
                role="Software Engineer",
                dates="2020-2024",
                highlights=[
                    "Designed and shipped REST APIs handling 10k requests/day.",  # rephrased
                    "Maintained PostgreSQL databases.",  # unchanged
                ],
            )
        ],
        education=original_cv.education,
        certifications=original_cv.certifications,
        publications=original_cv.publications,
        projects=original_cv.projects,
    )


@pytest.fixture
def job_analysis() -> JobAnalysis:
    return JobAnalysis(
        job_title="Senior Backend Engineer",
        company_name="Acme Corp",
        summary="Looking for a senior backend engineer.",
        hard_skills=["Python", "Docker", "Kubernetes", "Terraform"],
        soft_skills=["teamwork", "communication"],
        key_responsibilities=["Build APIs", "Manage infra"],
        keywords_to_target=["Python", "Docker", "Kubernetes", "REST API", "CI/CD"],
    )


# ---------------------------------------------------------------------------
# compute_cv_diff tests
# ---------------------------------------------------------------------------

def test_cv_diff_detects_summary_change(original_cv: CV, tailored_cv: CV):
    diff = compute_cv_diff(original_cv, tailored_cv)
    assert diff.summary_changed is True


def test_cv_diff_no_summary_change_when_identical(original_cv: CV):
    diff = compute_cv_diff(original_cv, original_cv)
    assert diff.summary_changed is False


def test_cv_diff_detects_skills_reordered(original_cv: CV, tailored_cv: CV):
    diff = compute_cv_diff(original_cv, tailored_cv)
    # Docker moved from index 4 to index 1 — should appear in reordered
    assert "Docker" in diff.skills_reordered


def test_cv_diff_detects_skills_deprioritized(original_cv: CV, tailored_cv: CV):
    diff = compute_cv_diff(original_cv, tailored_cv)
    # Redis moved from index 3 to index 4 — should appear in deprioritized
    assert "Redis" in diff.skills_deprioritized


def test_cv_diff_detects_rephrased_bullets(original_cv: CV, tailored_cv: CV):
    diff = compute_cv_diff(original_cv, tailored_cv)
    assert len(diff.experience_changes) == 1
    change = diff.experience_changes[0]
    assert change.company == "Acme Corp"
    assert len(change.bullets_rephrased) == 1
    assert "→" in change.bullets_rephrased[0]


def test_cv_diff_counts_unchanged_bullets(original_cv: CV, tailored_cv: CV):
    diff = compute_cv_diff(original_cv, tailored_cv)
    change = diff.experience_changes[0]
    assert change.bullets_unchanged == 1


def test_cv_diff_sections_modified_includes_summary(original_cv: CV, tailored_cv: CV):
    diff = compute_cv_diff(original_cv, tailored_cv)
    assert "summary" in diff.sections_modified


def test_cv_diff_identical_cv_produces_empty_diff(original_cv: CV):
    diff = compute_cv_diff(original_cv, original_cv)
    assert diff.summary_changed is False
    assert diff.skills_reordered == []
    assert diff.skills_deprioritized == []
    assert diff.experience_changes == []
    assert diff.sections_modified == []


# ---------------------------------------------------------------------------
# compute_gap_analysis tests
# ---------------------------------------------------------------------------

def test_gap_analysis_missing_hard_skills(
    original_cv: CV, tailored_cv: CV, job_analysis: JobAnalysis
):
    gap = compute_gap_analysis(original_cv, tailored_cv, job_analysis)
    # Kubernetes and Terraform are not in original_cv.skills
    assert "Kubernetes" in gap.missing_hard_skills
    assert "Terraform" in gap.missing_hard_skills


def test_gap_analysis_no_false_positive_for_existing_skill(
    original_cv: CV, tailored_cv: CV, job_analysis: JobAnalysis
):
    gap = compute_gap_analysis(original_cv, tailored_cv, job_analysis)
    # Python and Docker ARE in original_cv.skills — should NOT appear as missing
    assert "Python" not in gap.missing_hard_skills
    assert "Docker" not in gap.missing_hard_skills


def test_gap_analysis_covered_keywords(
    original_cv: CV, tailored_cv: CV, job_analysis: JobAnalysis
):
    gap = compute_gap_analysis(original_cv, tailored_cv, job_analysis)
    # "Python", "Docker", "REST API" appear in tailored CV text
    assert "Python" in gap.covered_keywords
    assert "Docker" in gap.covered_keywords


def test_gap_analysis_missing_keywords(
    original_cv: CV, tailored_cv: CV, job_analysis: JobAnalysis
):
    gap = compute_gap_analysis(original_cv, tailored_cv, job_analysis)
    # "Kubernetes" and "CI/CD" do NOT appear in tailored CV text
    assert "Kubernetes" in gap.missing_keywords


def test_gap_analysis_coverage_percent_is_between_0_and_100(
    original_cv: CV, tailored_cv: CV, job_analysis: JobAnalysis
):
    gap = compute_gap_analysis(original_cv, tailored_cv, job_analysis)
    assert 0.0 <= gap.keyword_coverage_percent <= 100.0


def test_gap_analysis_when_tailored_cv_is_none_keyword_coverage_is_zero(
    original_cv: CV, job_analysis: JobAnalysis
):
    """When writer fails (new_cv is None), coverage defaults to 0%."""
    gap = compute_gap_analysis(original_cv, None, job_analysis)
    assert gap.keyword_coverage_percent == 0.0
    assert gap.covered_keywords == []
