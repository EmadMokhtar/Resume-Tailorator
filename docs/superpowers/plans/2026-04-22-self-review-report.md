# Self-Review Report Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Report Phase to the Resume Tailorator pipeline that always runs after the audit, computes factual diffs/gaps in pure Python, generates narrative via `report_agent`, and prints a console summary and saves `files/report_<company>.md`.

**Architecture:** Pure Python utilities (`compute_cv_diff`, `compute_gap_analysis`) compare original vs tailored `CV` Pydantic objects and produce `CVDiff`/`GapAnalysis`. `report_agent` receives that pre-computed data as JSON context and returns only narrative fields (`ReportNarrative`). The workflow merges `CVDiff + GapAnalysis + ReportNarrative` into a `FinalReport` at a single exit point — eliminating the multiple early returns in the current pipeline so the Report Phase always runs.

**Tech Stack:** pydantic-ai v1.24+ (`Agent`, `RunUsage`, `TestModel`), pydantic v2, pytest + anyio

---

## Pre-work: Add test dependencies

- [ ] **Step 1: Add pytest and anyio dev dependencies**

```bash
uv add --dev pytest pytest-anyio anyio
```

Expected: `pyproject.toml` updated, lockfile updated.

- [ ] **Step 2: Verify pytest runs (empty suite)**

```bash
uv run pytest tests/ -v
```

Expected: `no tests ran` or `0 passed`.

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "build(deps): add pytest and anyio for testing"
```

---

## Task 1: New Pydantic Models

**Files:**
- Modify: `models/agents/output.py`
- Modify: `models/workflow.py`

- [ ] **Step 1: Add five new models to `models/agents/output.py`**

Append after the existing `ReviewResult` class at line 78:

```python
# --- Models for the Self-Review Report ---

class ExperienceChange(BaseModel):
    """Records changes made to a single work experience entry."""

    company: str
    role: str
    bullets_rephrased: list[str] = Field(
        default_factory=list,
        description="Strings in format 'original bullet → new bullet'",
    )
    bullets_unchanged: int = Field(default=0)


class CVDiff(BaseModel):
    """Factual diff between original and tailored CV."""

    summary_changed: bool = False
    skills_reordered: list[str] = Field(
        default_factory=list,
        description="Skills moved to earlier positions for relevance.",
    )
    skills_deprioritized: list[str] = Field(
        default_factory=list,
        description="Skills moved to later positions.",
    )
    experience_changes: list[ExperienceChange] = Field(default_factory=list)
    sections_modified: list[str] = Field(
        default_factory=list,
        description="Names of CV sections that changed, e.g. ['summary', 'skills']",
    )


class GapAnalysis(BaseModel):
    """Gap analysis between the original CV and the job requirements."""

    missing_hard_skills: list[str] = Field(
        default_factory=list,
        description="Hard skills required by the job but absent from the original CV.",
    )
    missing_soft_skills: list[str] = Field(
        default_factory=list,
        description="Soft skills required by the job but absent from the original CV.",
    )
    covered_keywords: list[str] = Field(
        default_factory=list,
        description="ATS keywords from the job that appear in the tailored CV.",
    )
    missing_keywords: list[str] = Field(
        default_factory=list,
        description="ATS keywords from the job still absent from the tailored CV.",
    )
    keyword_coverage_percent: float = Field(
        default=0.0,
        description="Percentage of job keywords covered in the tailored CV.",
    )


class ReportNarrative(BaseModel):
    """LLM-generated narrative fields for the final report."""

    overall_recommendation: str = Field(
        description="One of: 'Strong Match', 'Partial Match', 'Weak Match'",
    )
    match_score: int = Field(
        ge=0, le=100, description="0-100 match score based on keyword coverage and gap severity."
    )
    suggestions_to_strengthen: list[str] = Field(
        description="Concrete, actionable upskilling or application advice.",
    )
    audit_summary: str = Field(
        description="Plain-English summary of audit quality scores.",
    )
    recommendation_rationale: str = Field(
        description="Honest plain-English explanation of the overall recommendation.",
    )


class FinalReport(BaseModel):
    """Complete self-review report produced at the end of the pipeline."""

    job_title: str
    company_name: str
    generated_at: str = Field(description="ISO 8601 timestamp.")
    overall_recommendation: str
    match_score: int = Field(ge=0, le=100)
    what_changed: CVDiff
    gaps: GapAnalysis
    suggestions_to_strengthen: list[str]
    audit_summary: str
    recommendation_rationale: str
    passed: bool
```

- [ ] **Step 2: Add `final_report` to `models/workflow.py`**

Replace the entire file content:

```python
from pydantic import BaseModel

from models.agents.output import FinalReport


class ResumeTailorResult(BaseModel):
    company_name: str
    tailored_resume: str
    audit_report: dict
    passed: bool
    final_report: FinalReport | None = None
```

- [ ] **Step 3: Verify the models import cleanly**

```bash
uv run python -c "from models.agents.output import FinalReport, CVDiff, GapAnalysis, ReportNarrative, ExperienceChange; from models.workflow import ResumeTailorResult; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add models/agents/output.py models/workflow.py
git commit -m "feat(model): add CVDiff, GapAnalysis, ReportNarrative, FinalReport models"
```

---

## Task 2: Write Failing Tests for CV Diff Utilities

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/test_cv_diff.py`

- [ ] **Step 1: Create `tests/__init__.py`**

```bash
touch tests/__init__.py
```

- [ ] **Step 2: Create `tests/test_cv_diff.py` with failing tests**

```python
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
```

- [ ] **Step 3: Run tests to confirm they fail (utils/cv_diff.py doesn't exist yet)**

```bash
uv run pytest tests/test_cv_diff.py -v
```

Expected: `ModuleNotFoundError: No module named 'utils.cv_diff'`

- [ ] **Step 4: Commit the failing tests**

```bash
git add tests/__init__.py tests/test_cv_diff.py
git commit -m "test(cv-diff): add failing unit tests for compute_cv_diff and compute_gap_analysis"
```

---

## Task 3: Implement `utils/cv_diff.py`

**Files:**
- Create: `utils/cv_diff.py`

- [ ] **Step 1: Create `utils/cv_diff.py`**

```python
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
        (exp.company.strip(), exp.role.strip()): exp
        for exp in tailored.experience
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
                    bullets_rephrased.append(f"{orig_bullet.strip()} → {tail_bullet.strip()}")
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
        skill for skill in job.hard_skills
        if skill.lower() not in original_skills_lower
    ]
    missing_soft = [
        skill for skill in job.soft_skills
        if skill.lower() not in original_skills_lower
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
```

- [ ] **Step 2: Run the tests — all should pass**

```bash
uv run pytest tests/test_cv_diff.py -v
```

Expected output:
```
tests/test_cv_diff.py::test_cv_diff_detects_summary_change PASSED
tests/test_cv_diff.py::test_cv_diff_no_summary_change_when_identical PASSED
tests/test_cv_diff.py::test_cv_diff_detects_skills_reordered PASSED
tests/test_cv_diff.py::test_cv_diff_detects_skills_deprioritized PASSED
tests/test_cv_diff.py::test_cv_diff_detects_rephrased_bullets PASSED
tests/test_cv_diff.py::test_cv_diff_counts_unchanged_bullets PASSED
tests/test_cv_diff.py::test_cv_diff_sections_modified_includes_summary PASSED
tests/test_cv_diff.py::test_cv_diff_identical_cv_produces_empty_diff PASSED
tests/test_gap_analysis_missing_hard_skills PASSED
...
```

All 14 tests should pass.

- [ ] **Step 3: Commit**

```bash
git add utils/cv_diff.py
git commit -m "feat(utils): implement compute_cv_diff and compute_gap_analysis"
```

---

## Task 4: Write Failing Tests for `report_agent`

**Files:**
- Create: `tests/test_report_agent.py`

- [ ] **Step 1: Add `pydantic-ai` TestModel guard to prevent real LLM calls**

The tests will use `pydantic_ai.models.TestModel`. The `ALLOW_MODEL_REQUESTS = False` guard is set inside the test file.

- [ ] **Step 2: Create `tests/test_report_agent.py`**

```python
"""Integration tests for report_agent using TestModel (no real LLM calls)."""
import pytest
from pydantic_ai import models
from pydantic_ai.models.test import TestModel

from models.agents.output import ReportNarrative

models.ALLOW_MODEL_REQUESTS = False

pytestmark = pytest.mark.anyio


async def test_report_agent_returns_report_narrative():
    """report_agent should return a ReportNarrative when given valid JSON context."""
    from workflows.agents import report_agent  # noqa: PLC0415 — avoids import-time LLM init

    custom = {
        "overall_recommendation": "Partial Match",
        "match_score": 65,
        "suggestions_to_strengthen": ["Get Kubernetes certification"],
        "audit_summary": "Hallucination score 1/10. AI cliché score 2/10.",
        "recommendation_rationale": "Strong backend skills but missing infra experience.",
    }

    with report_agent.override(model=TestModel(custom_output_data=custom)):
        result = await report_agent.run(
            "CV Diff: {} Gap Analysis: {} Audit: {} Review: {} Job: {}"
        )

    assert isinstance(result.output, ReportNarrative)


async def test_report_agent_output_has_required_fields():
    """ReportNarrative output must contain all expected fields."""
    from workflows.agents import report_agent

    custom = {
        "overall_recommendation": "Strong Match",
        "match_score": 88,
        "suggestions_to_strengthen": ["Add Terraform side project"],
        "audit_summary": "Excellent quality. No hallucinations.",
        "recommendation_rationale": "Covers 90% of job keywords.",
    }

    with report_agent.override(model=TestModel(custom_output_data=custom)):
        result = await report_agent.run("CV Diff: {} Gap Analysis: {}")

    output = result.output

    with pytest.subtest("overall_recommendation"):
        assert output.overall_recommendation in ("Strong Match", "Partial Match", "Weak Match")

    with pytest.subtest("match_score_range"):
        assert 0 <= output.match_score <= 100

    with pytest.subtest("suggestions_list"):
        assert isinstance(output.suggestions_to_strengthen, list)

    with pytest.subtest("audit_summary_non_empty"):
        assert len(output.audit_summary) > 0

    with pytest.subtest("rationale_non_empty"):
        assert len(output.recommendation_rationale) > 0
```

- [ ] **Step 3: Run tests — confirm they fail because `report_agent` doesn't exist yet**

```bash
uv run pytest tests/test_report_agent.py -v
```

Expected: `ImportError: cannot import name 'report_agent' from 'workflows.agents'`

- [ ] **Step 4: Commit the failing tests**

```bash
git add tests/test_report_agent.py
git commit -m "test(report-agent): add failing integration tests for report_agent"
```

---

## Task 5: Implement `report_agent`

**Files:**
- Modify: `workflows/agents.py`

- [ ] **Step 1: Add `ReportNarrative` to the import at the top of `workflows/agents.py`**

Replace:
```python
from models.agents.output import JobAnalysis, CV, AuditResult, ReviewResult
```

With:
```python
from models.agents.output import JobAnalysis, CV, AuditResult, ReviewResult, ReportNarrative
```

- [ ] **Step 2: Append `report_agent` to the bottom of `workflows/agents.py`**

```python
# --- Agent 5: The Report Writer ---
# Responsibility: Write the narrative section of the self-review report.
# Receives pre-computed CVDiff, GapAnalysis, AuditResult, ReviewResult, and
# JobAnalysis as structured JSON. Produces only narrative fields (factual diff
# and gap data are injected by the workflow, not generated by the LLM).
report_agent = Agent(
    MODLE_NAME,
    system_prompt="""
    You are a Career Advisor writing a clear, honest self-review report.

    You receive pre-computed structured data about:
    - What changed between the original and tailored CV (CVDiff JSON)
    - Skill and keyword gaps vs. job requirements (GapAnalysis JSON)
    - Audit quality scores: hallucination and AI-cliché (AuditResult JSON)
    - Quality review scores (ReviewResult JSON)
    - Job requirements (JobAnalysis JSON)

    Your job is to produce ONLY the following narrative fields:
    1. overall_recommendation: exactly one of "Strong Match", "Partial Match", or "Weak Match"
       - "Strong Match": keyword_coverage_percent >= 80 AND missing_hard_skills <= 1
       - "Partial Match": keyword_coverage_percent >= 50 OR missing_hard_skills <= 3
       - "Weak Match": everything else
    2. match_score (0-100): base it primarily on keyword_coverage_percent,
       subtract 5 points per missing hard skill, subtract 2 per missing soft skill.
    3. suggestions_to_strengthen: 2-4 concrete, actionable items the candidate can do
       to close the gaps (certifications, side projects, courses, etc.)
    4. audit_summary: one paragraph in plain English summarising the hallucination
       score and AI-cliché score from the AuditResult.
    5. recommendation_rationale: one honest paragraph explaining your overall_recommendation.
       Be direct. Do not sugarcoat weak matches.

    CRITICAL RULES:
    - Never use AI clichés: "orchestrated", "spearheaded", "leveraged", "synergy",
      "tapestry", "dynamic", "innovative", "cutting-edge", "game-changer".
    - Do not repeat the raw JSON back. Synthesise it into human-readable text.
    - Be concise: audit_summary and recommendation_rationale should each be 2-4 sentences.
    """,
    output_type=ReportNarrative,
    retries=3,
)
```

- [ ] **Step 3: Run the failing report_agent tests — they should now pass**

```bash
uv run pytest tests/test_report_agent.py -v
```

Expected:
```
tests/test_report_agent.py::test_report_agent_returns_report_narrative PASSED
tests/test_report_agent.py::test_report_agent_output_has_required_fields PASSED
```

- [ ] **Step 4: Commit**

```bash
git add workflows/agents.py
git commit -m "feat(agent): add report_agent with ReportNarrative output type"
```

---

## Task 6: Implement `generate_report_markdown`

**Files:**
- Modify: `utils/markdown_writer.py`

- [ ] **Step 1: Append `generate_report_markdown` to `utils/markdown_writer.py`**

Add at the bottom of the file, after the existing `generate_resume` function:

```python
from models.agents.output import FinalReport


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
```

- [ ] **Step 2: Verify the import works (FinalReport must be defined in output.py)**

```bash
uv run python -c "from utils.markdown_writer import generate_report_markdown; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add utils/markdown_writer.py
git commit -m "feat(utils): add generate_report_markdown to markdown_writer"
```

---

## Task 7: Refactor `workflows/__init__.py` — Add Report Phase

**Files:**
- Modify: `workflows/__init__.py`

This is the most invasive change. The current code has 5 early `return` statements scattered inside loops. The refactor:
1. Replaces the early return in the `write_attempt` loop (audit passed case, line ~309) with `break`.
2. Removes the inner early return for `new_cv is None` and `audit is None` (replace with `continue`/`break` + flags).
3. Adds a Report Phase after the loop using `try/except` so a report failure never crashes the pipeline.
4. Threads `RunUsage` through all agent calls.
5. Consolidates to a **single** `return` at the bottom.

> Note: The two early `sys.exit()` calls (parser/analyst failures) stay — those are fatal and nothing can run without them. Only the returns within the `write_attempt` loop are consolidated.

- [ ] **Step 1: Replace the entire `workflows/__init__.py`**

```python
import sys
from datetime import datetime, timezone

from pydantic_ai import AgentRunResult
from pydantic_ai.usage import RunUsage

from models.agents.output import CV, CVDiff, FinalReport, JobAnalysis
from models.workflow import ResumeTailorResult
from utils.cv_diff import compute_cv_diff, compute_gap_analysis
from workflows.agents import (
    analyst_agent,
    auditor_agent,
    report_agent,
    resume_parser_agent,
    reviewer_agent,
    writer_agent,
)


class ResumeTailorWorkflow:
    MAX_RETRIES = 3
    max_review_iterations = 3
    max_write_attempts = 3

    def __init__(self):
        pass

    async def run(
        self, resume_text: str, job_content_file_path: str
    ) -> ResumeTailorResult:
        print("🚀 STARTING MULTI-AGENT PIPELINE\n")

        total_usage = RunUsage()

        # --- STEP 0: PARSE ORIGINAL RESUME ---
        print("🤖 Agent 0 (Parser): Parsing original resume...")
        original_cv_result: AgentRunResult[CV] | None = None
        for attempt in range(self.MAX_RETRIES):
            try:
                original_cv_result = await resume_parser_agent.run(
                    f"Parse this resume into structured format:\n\n{resume_text}",
                    usage=total_usage,
                )

                if original_cv_result.output is None:
                    raise ValueError("Resume parsing returned None")

                if (
                    original_cv_result.output.full_name
                    and original_cv_result.output.experience
                ):
                    break

                print(
                    f"⚠️ Attempt {attempt + 1}/{self.MAX_RETRIES}: Incomplete resume parse, retrying..."
                )

            except Exception as e:
                print(f"⚠️ Attempt {attempt + 1}/{self.MAX_RETRIES} failed: {e}")
                if attempt == self.MAX_RETRIES - 1:
                    sys.exit("❌ Failed to parse original resume after retries.")

        if original_cv_result is None or original_cv_result.output is None:
            sys.exit("❌ Failed to parse original resume after retries.")

        original_cv = original_cv_result.output
        print(f"   ✅ Resume Parsed: {original_cv.full_name}")
        print(
            f"   📋 Found {len(original_cv.skills)} skills, {len(original_cv.experience)} work experiences\n"
        )

        original_cv_json = original_cv.model_dump_json()

        # --- STEP 1: ANALYZE JOB (Agent 1) ---
        print("🤖 Agent 1 (Analyst): Reading job post...")
        job_analysis_result: AgentRunResult[JobAnalysis] | None = None
        for attempt in range(self.MAX_RETRIES):
            try:
                job_analysis_result = await analyst_agent.run(
                    f"Analyze the job content located at this file path {job_content_file_path} and extract structured job data.",
                    usage=total_usage,
                )

                print(f"   [Debug] Job Data: {job_analysis_result.output}")

                if job_analysis_result.output is None:
                    raise ValueError("Job analysis data is None")

                if (
                    job_analysis_result.output.job_title
                    and job_analysis_result.output.company_name
                ):
                    break

                print(
                    f"⚠️ Attempt {attempt + 1}/{self.MAX_RETRIES}: Incomplete job data, retrying..."
                )

            except Exception as e:
                print(f"⚠️ Attempt {attempt + 1}/{self.MAX_RETRIES} failed: {e}")
                if attempt == self.MAX_RETRIES - 1:
                    sys.exit("❌ Failed to get complete job analysis after retries.")

        if job_analysis_result is None or job_analysis_result.output is None:
            sys.exit("❌ Failed to get complete job analysis after retries.")

        print(
            f"   ✅ Job Analyzed: {job_analysis_result.output.job_title} at {job_analysis_result.output.company_name}"
        )
        print(
            f"   🎯 Keywords found: {job_analysis_result.output.keywords_to_target}\n"
        )

        job_data_json = job_analysis_result.output.model_dump_json()

        # --- STEP 2: WRITE + REVIEW + AUDIT LOOP ---
        new_cv: CV | None = None
        audit = None
        review = None
        audit_passed = False

        for write_attempt in range(self.max_write_attempts):
            print(
                f"🤖 Agent 2 (Writer): Tailoring CV (Attempt {write_attempt + 1}/{self.max_write_attempts})..."
            )
            if write_attempt == 0:
                print(f"   [Debug] Original CV has {len(original_cv.skills)} skills")
                writer_prompt = f"""
Here is the Job Analysis:
{job_data_json}

Here is the Original CV (structured):
{original_cv_json}

Rewrite the CV to match the Job Analysis. Use ONLY the information from the Original CV.
Rephrase and reorganize to highlight relevant experience, but do NOT add new skills or experiences.
"""
            else:
                print("   🔄 Retrying with audit feedback...")
                issues_text = "\n".join(
                    [
                        f"- [{getattr(i, 'severity', 'Unknown')}] {getattr(i, 'issue', str(i))} -> {getattr(i, 'suggestion', '')}"
                        for i in getattr(audit, "issues", [])
                    ]
                )
                writer_prompt = f"""
The previous CV draft failed the audit. Here is the feedback:

Audit Feedback: {getattr(audit, "feedback_summary", "")}

Issues to fix:
{issues_text}

Here is the Job Analysis:
{job_data_json}

Here is the Original CV (structured):
{original_cv_json}

CRITICAL RULES:
1. ONLY use skills and experience from the Original CV - DO NOT add new skills
2. Fix all the issues mentioned in the audit feedback
3. Ensure all job requirements are addressed using ONLY existing skills from the original CV
4. Avoid AI clichés and use natural language
5. You may rephrase existing content but cannot add new information

Rewrite the CV to match the Job Analysis while addressing all audit feedback.
"""

            writer_result = await writer_agent.run(writer_prompt, usage=total_usage)

            new_cv = writer_result.output or None
            if new_cv is None:
                if write_attempt == self.max_write_attempts - 1:
                    break  # exhausted retries — report phase still runs below
                continue

            print(f"   ✅ CV Drafted. Summary: {new_cv.summary[:100]}...\n")

            # --- STEP 2.5: QUALITY REVIEW (Agent 2.5) ---
            for review_iteration in range(self.max_review_iterations):
                print(
                    f"🤖 Agent 2.5 (Reviewer): Checking CV quality (Iteration {review_iteration + 1}/{self.max_review_iterations})..."
                )

                review_prompt = f"""
Review this CV against job requirements:

CV: {new_cv.model_dump_json() if hasattr(new_cv, "model_dump_json") else str(new_cv)}
Job Analysis: {job_data_json}

Assess quality and suggest improvements if needed.
"""

                try:
                    review_result = await reviewer_agent.run(review_prompt, usage=total_usage)
                    review = review_result.output

                    if review is None:
                        print("   ⚠️ Review returned None, skipping quality check\n")
                        break

                    print(f"   📊 Quality Score: {review.quality_score}/10")

                    if review.strengths:
                        print(f"   ✨ Strengths: {', '.join(review.strengths[:2])}")

                    if (
                        review.needs_improvement
                        and review_iteration < self.max_review_iterations - 1
                    ):
                        print("   🔄 Quality improvements needed, refining...\n")

                        suggestions_text = "\n".join(
                            f"- {s}" for s in review.specific_suggestions
                        )

                        improvement_prompt = f"""
Improve this CV based on reviewer feedback:

Current CV: {new_cv.model_dump_json() if hasattr(new_cv, "model_dump_json") else str(new_cv)}
Original CV: {original_cv_json}
Job Analysis: {job_data_json}

Specific improvements to address:
{suggestions_text}

CRITICAL RULES:
1. ONLY use information from the Original CV - DO NOT add new skills or experiences
2. Apply the suggestions to improve quality and relevance
3. Maintain accuracy and honesty
4. Use natural language, avoid AI clichés
5. Keep all dates and facts accurate

Focus on better highlighting relevant experience and incorporating job keywords naturally.
"""

                        refined_result = await writer_agent.run(improvement_prompt, usage=total_usage)
                        if refined_result.output:
                            new_cv = refined_result.output
                            print("   ✅ CV refined based on feedback\n")
                        else:
                            print("   ⚠️ Refinement returned None, keeping current CV\n")
                            break
                    else:
                        if review.needs_improvement:
                            print("   ℹ️ Max review iterations reached\n")
                        else:
                            print("   ✅ Quality check passed!\n")
                        break

                except Exception as e:
                    print(f"   ⚠️ Review failed: {e}, continuing with current CV\n")
                    break

            # --- STEP 3: AUDIT (Agent 3) ---
            new_cv_json = (
                new_cv.model_dump_json()
                if hasattr(new_cv, "model_dump_json")
                else str(new_cv)
            )

            print("🤖 Agent 3 (Auditor): Validating for hallucinations and AI-speak...")
            audit_prompt = f"""
ORIGINAL CV (structured):
{original_cv_json}

NEW GENERATED CV (structured):
{new_cv_json}

JOB REQUIREMENTS:
{job_data_json}

Compare the two structured CVs carefully. Ensure that:
1. No new skills appear in the new CV that weren't in the original
2. No new companies or roles were invented
3. All experiences in the new CV can be traced back to the original
4. The language is professional and not AI-generated sounding
5. The new CV properly targets the job requirements using only original information
"""
            audit_result = await auditor_agent.run(audit_prompt, usage=total_usage)

            audit = audit_result.output
            if audit is None:
                print(f"   ⚠️ Audit result is None on attempt {write_attempt + 1}")
                if write_attempt < self.max_write_attempts - 1:
                    print("   🔄 Will retry...\n")
                    continue
                else:
                    print("   ❌ Max attempts reached\n")
                    break

            audit_passed = getattr(audit, "passed", False)
            if audit_passed:
                print(f"   ✅ Audit passed on attempt {write_attempt + 1}!\n")
                break  # exit loop — report phase runs below
            else:
                print(f"   ⚠️ Audit failed on attempt {write_attempt + 1}")
                if write_attempt < self.max_write_attempts - 1:
                    print("   🔄 Will retry with feedback...\n")
                else:
                    print("   ❌ Max attempts reached\n")

        # Print audit report regardless of pass/fail
        print("\n" + "=" * 30)
        print("📋 FINAL AUDIT REPORT")
        print("=" * 30)

        if audit is None:
            print("⚠️ Warning: No audit result available")
        else:
            passed_display = getattr(audit, "passed", None)
            hallucination_score = getattr(audit, "hallucination_score", None)
            ai_cliche_score = getattr(audit, "ai_cliche_score", None)
            feedback_summary = getattr(audit, "feedback_summary", "")

            print(f"Passed: {passed_display}")
            print(f"Hallucination Score (0 is best): {hallucination_score}")
            print(f"AI Cliche Score (0 is best): {ai_cliche_score}")
            print(f"Feedback: {feedback_summary}")

            issues = getattr(audit, "issues", []) or []
            if issues:
                print("\n⚠️ Issues Found:")
                for i in issues:
                    sev = getattr(i, "severity", "Unknown")
                    issue_text = getattr(i, "issue", str(i))
                    suggestion = getattr(i, "suggestion", "")
                    print(f" - [{sev}] {issue_text} -> {suggestion}")

        # === REPORT PHASE — always runs ===
        final_report: FinalReport | None = None
        try:
            print("\n🤖 Agent 5 (Report Writer): Generating self-review report...")

            cv_diff = (
                compute_cv_diff(original_cv, new_cv)
                if new_cv is not None
                else CVDiff()
            )
            gap_analysis = compute_gap_analysis(
                original_cv,
                new_cv,
                job_analysis_result.output,
            )

            review_json = review.model_dump_json() if review is not None else "N/A"
            audit_json = audit.model_dump_json() if audit is not None else "N/A"

            report_prompt = f"""
CV Diff: {cv_diff.model_dump_json()}
Gap Analysis: {gap_analysis.model_dump_json()}
Audit Result: {audit_json}
Review Result: {review_json}
Job Analysis: {job_data_json}
"""

            report_result = await report_agent.run(report_prompt, usage=total_usage)
            narrative = report_result.output

            final_report = FinalReport(
                job_title=job_analysis_result.output.job_title,
                company_name=job_analysis_result.output.company_name,
                generated_at=datetime.now(timezone.utc).isoformat(),
                overall_recommendation=narrative.overall_recommendation,
                match_score=narrative.match_score,
                what_changed=cv_diff,
                gaps=gap_analysis,
                suggestions_to_strengthen=narrative.suggestions_to_strengthen,
                audit_summary=narrative.audit_summary,
                recommendation_rationale=narrative.recommendation_rationale,
                passed=audit_passed,
            )
            print("   ✅ Report generated.\n")

        except Exception as e:
            print(f"   ⚠️ Report generation failed: {e}\n")

        # Build audit_report dict for backward compatibility
        audit_report_dict: dict = {
            "passed": audit_passed,
            "hallucination_score": getattr(audit, "hallucination_score", None) if audit else None,
            "ai_cliche_score": getattr(audit, "ai_cliche_score", None) if audit else None,
            "feedback_summary": getattr(audit, "feedback_summary", "") if audit else "",
            "issues": [
                {
                    "severity": getattr(i, "severity", "Unknown"),
                    "issue": getattr(i, "issue", str(i)),
                    "suggestion": getattr(i, "suggestion", ""),
                }
                for i in (getattr(audit, "issues", []) or [])
            ],
        }

        return ResumeTailorResult(
            company_name=job_analysis_result.output.company_name,
            tailored_resume=(
                new_cv.model_dump_json()
                if new_cv and hasattr(new_cv, "model_dump_json")
                else str(new_cv) if new_cv else ""
            ),
            audit_report=audit_report_dict,
            passed=audit_passed,
            final_report=final_report,
        )
```

- [ ] **Step 2: Verify the module imports cleanly**

```bash
uv run python -c "from workflows import ResumeTailorWorkflow; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Run all tests to make sure nothing broke**

```bash
uv run pytest tests/ -v
```

Expected: All previously passing tests still pass.

- [ ] **Step 4: Commit**

```bash
git add workflows/__init__.py
git commit -m "feat(workflow): add Report Phase and thread RunUsage through pipeline"
```

---

## Task 8: Update `main.py` — Console Print and Markdown File Save

**Files:**
- Modify: `main.py`

- [ ] **Step 1: Replace `main.py` with the updated version**

```python
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
    print(f"{'✅' if report.passed else '❌'} Audit: {'Passed' if report.passed else 'Failed'}")

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
    print(f"\nKEYWORD COVERAGE: {len(gap.covered_keywords)}/{total_kw} ({gap.keyword_coverage_percent:.1f}%)")
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
```

- [ ] **Step 2: Verify main.py imports cleanly**

```bash
uv run python -c "import main; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Run the full test suite one final time**

```bash
uv run pytest tests/ -v
```

Expected: All tests pass (14 cv_diff tests + 2 report_agent tests = 16 total).

- [ ] **Step 4: Commit**

```bash
git add main.py
git commit -m "feat(main): print self-review report to console and save report Markdown file"
```

---

## Task 9: Create Skill Documentation

**Files:**
- Create: `.github/skills/cv-diff.skill.md`

- [ ] **Step 1: Create `.github/skills/cv-diff.skill.md`**

```markdown
# Skill: CV Diff Utilities

> `utils/cv_diff.py`

## Overview
Pure-Python utilities for computing factual diffs between CV Pydantic objects and
performing gap analysis against job requirements. No LLM calls — all comparisons are
done by comparing structured model fields directly. Used by the Report Phase of the
Resume Tailorator pipeline.

## Capabilities
- Detect summary rewrites between original and tailored CVs
- Identify skills that moved up (reordered) or down (deprioritized) in the skills list
- Diff experience bullet points per-role, tracking rephrased vs unchanged bullets
- Identify hard/soft skills required by the job but absent from the original CV
- Compute keyword coverage percentage for ATS keyword matching

## Key Symbols
| Symbol | Type | Description |
|--------|------|-------------|
| `compute_cv_diff` | function | Computes a `CVDiff` from two `CV` objects |
| `compute_gap_analysis` | function | Computes a `GapAnalysis` from original CV, tailored CV, and job analysis |

## Inputs & Outputs
| Symbol | Input | Output |
|--------|-------|--------|
| `compute_cv_diff` | `original: CV`, `tailored: CV` | `CVDiff` |
| `compute_gap_analysis` | `original: CV`, `tailored: CV \| None`, `job: JobAnalysis` | `GapAnalysis` |

## Usage Example
```python
from utils.cv_diff import compute_cv_diff, compute_gap_analysis

diff = compute_cv_diff(original_cv, tailored_cv)
gap = compute_gap_analysis(original_cv, tailored_cv, job_analysis)

print(f"Summary changed: {diff.summary_changed}")
print(f"Keyword coverage: {gap.keyword_coverage_percent:.1f}%")
```

## Internal Dependencies
- `models.agents.output` — `CV`, `CVDiff`, `ExperienceChange`, `GapAnalysis`, `JobAnalysis`

## External Dependencies
- None (pure Python standard library)

## Notes
- `compute_gap_analysis` accepts `tailored=None` (when the writer agent failed) and
  defaults keyword coverage to 0% in that case — it never raises.
- Skill matching is case-insensitive.
- Bullet diff is by position index — if bullets are reordered rather than rephrased,
  they will appear as rephrased. This is acceptable for the report's purpose.

## Changelog
| Date | Change |
|------|--------|
| 2026-04-22 | Initial skill created |
```

- [ ] **Step 2: Commit**

```bash
git add .github/skills/cv-diff.skill.md
git commit -m "docs(skills): add cv-diff skill documentation"
```

---

## Self-Review

### 1. Spec Coverage

| Spec requirement | Task |
|---|---|
| New models: `ExperienceChange`, `CVDiff`, `GapAnalysis`, `ReportNarrative`, `FinalReport` | Task 1 |
| `ResumeTailorResult.final_report` field | Task 1 |
| `compute_cv_diff` utility | Task 3 |
| `compute_gap_analysis` utility | Task 3 |
| `report_agent` with `ReportNarrative` output | Task 5 |
| `generate_report_markdown` | Task 6 |
| Workflow Report Phase (always runs) | Task 7 |
| `RunUsage` threaded through all agents | Task 7 |
| Console summary | Task 8 |
| `files/report_<company>.md` | Task 8 |
| Error handling: report failure doesn't crash pipeline | Task 7 (try/except) |
| Error handling: `new_cv is None` → `CVDiff()` defaults | Task 7 |
| Error handling: `tailored=None` → `keyword_coverage_percent=0` | Task 3 |
| Tests: pure Python cv_diff unit tests | Task 2 + 3 |
| Tests: report_agent integration with TestModel | Task 4 + 5 |
| Skill documentation | Task 9 |

No gaps found. ✅

### 2. Placeholder Scan

No TBDs, TODOs, or vague instructions. All steps contain complete code. ✅

### 3. Type Consistency

- `CVDiff` defined in Task 1, used in Tasks 3, 7, 8 — consistent.
- `GapAnalysis` defined in Task 1, used in Tasks 3, 7, 8 — consistent.
- `ReportNarrative` defined in Task 1, used in Tasks 4, 5 — consistent.
- `FinalReport` defined in Task 1, used in Tasks 6, 7, 8 — consistent.
- `compute_cv_diff(original: CV, tailored: CV)` defined in Task 3, called in Task 7 — consistent.
- `compute_gap_analysis(original, tailored | None, job)` defined in Task 3, called in Task 7 — consistent.
- `generate_report_markdown(report: FinalReport)` defined in Task 6, called in Task 8 — consistent.
- `report_agent.override(model=TestModel(...))` in Task 4 works because `report_agent` is defined in Task 5 — import is deferred inside the test function to avoid import-time failure. ✅
