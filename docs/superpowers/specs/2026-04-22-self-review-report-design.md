# Design: Self-Review Report

**Date:** 2026-04-22  
**Status:** Approved  
**Topic:** Add a human-readable self-review report phase to the Resume Tailorator pipeline

---

## Problem

The pipeline currently produces a tailored CV and a raw audit dict, but gives the user no holistic picture of:
- What actually changed between their original CV and the tailored version
- How well their background matches the target job
- What concrete gaps exist and how to close them

The user must read raw JSON audit output to understand the result.

---

## Proposed Approach

Add a **Report Phase** at the end of the existing pipeline. It always runs — regardless of audit pass/fail — and produces a `FinalReport` written to console and saved as a Markdown file.

The phase has two parts:

1. **Analytical utilities** (pure Python, no LLM) — compute factual diffs and gap analysis by comparing structured Pydantic models directly.
2. **`report_agent`** (LLM, narrow scope) — receives the pre-computed data and writes the human-readable narrative, match score, and recommendation.

This follows the pydantic-ai programmatic handoff pattern: inspect intermediate output in Python, then delegate narrative synthesis to the LLM.

---

## Architecture

```
Resume Parser → Job Analyst → Writer → Reviewer → Auditor
                                                       ↓
                                             [Report Phase — always runs]
                                          ┌──────────────────────────────┐
                                          │ compute_cv_diff()             │ ← pure Python
                                          │ compute_gap_analysis()        │ ← pure Python
                                          │ report_agent.run(...)         │ ← LLM narrative
                                          └──────────────────────────────┘
                                                       ↓
                                            FinalReport (Pydantic model)
                                                       ↓
                                   ┌───────────────────────────────────────┐
                                   │ Console summary + files/report_<co>.md │
                                   └───────────────────────────────────────┘
```

Token usage is accumulated via `RunUsage` threaded through the full workflow, per pydantic-ai-workflows guidance.

---

## New Files

| File | Purpose |
|------|---------|
| `utils/cv_diff.py` | `compute_cv_diff(original, tailored)` and `compute_gap_analysis(original, job)` |
| `models/agents/output.py` | Add `ExperienceChange`, `CVDiff`, `GapAnalysis`, `FinalReport` |
| `workflows/agents.py` | Add `report_agent` |
| `utils/markdown_writer.py` | Add `generate_report_markdown(report)` function |

### Modified Files

| File | Change |
|------|--------|
| `workflows/__init__.py` | Add Report Phase at end of `run()`; thread `RunUsage` through all agents |
| `models/workflow.py` | Add `final_report: FinalReport \| None` to `ResumeTailorResult` |
| `main.py` | Print report to console; save report Markdown file |

---

## Data Models

Added to `models/agents/output.py`:

```python
class ExperienceChange(BaseModel):
    company: str
    role: str
    bullets_rephrased: list[str]   # "original bullet → new bullet" strings
    bullets_unchanged: int

class CVDiff(BaseModel):
    summary_changed: bool
    skills_reordered: list[str]       # skills moved to top for relevance
    skills_deprioritized: list[str]   # skills pushed down
    experience_changes: list[ExperienceChange]
    sections_modified: list[str]      # e.g. ["summary", "skills", "experience"]

class GapAnalysis(BaseModel):
    missing_hard_skills: list[str]    # required by job, absent from original CV
    missing_soft_skills: list[str]
    covered_keywords: list[str]       # ATS keywords in tailored CV
    missing_keywords: list[str]       # ATS keywords still absent
    keyword_coverage_percent: float   # e.g. 72.5

class FinalReport(BaseModel):
    job_title: str
    company_name: str
    generated_at: str                         # ISO 8601
    overall_recommendation: str               # "Strong Match" | "Partial Match" | "Weak Match"
    match_score: int                          # 0–100
    what_changed: CVDiff
    gaps: GapAnalysis
    suggestions_to_strengthen: list[str]      # concrete upskilling advice
    audit_summary: str                        # plain-English audit score narrative
    recommendation_rationale: str             # why this recommendation
    passed: bool
```

`ResumeTailorResult` gains:
```python
final_report: FinalReport | None = None
```

---

## Analytical Utilities (`utils/cv_diff.py`)

### `compute_cv_diff(original: CV, tailored: CV) -> CVDiff`

Pure Python comparison of two `CV` Pydantic objects:
- `summary_changed`: `original.summary != tailored.summary`
- `skills_reordered`: skills that moved to earlier positions in the list
- `skills_deprioritized`: skills that moved to later positions
- `experience_changes`: per-role diff of highlights bullets (by position comparison)
- `sections_modified`: collected list of changed section names

### `compute_gap_analysis(original: CV, tailored: CV, job: JobAnalysis) -> GapAnalysis`

Set operations on structured data:
- `missing_hard_skills`: `set(job.hard_skills) - set(original.skills)` (case-insensitive) — uses `original` to reflect the candidate's true background
- `missing_soft_skills`: `set(job.soft_skills) - set(original.skills)`
- `covered_keywords`: job keywords present anywhere in the serialised `tailored` CV text — uses `tailored` to reflect what actually made it into the output
- `missing_keywords`: job keywords absent from tailored CV text
- `keyword_coverage_percent`: `len(covered) / len(all_keywords) * 100`

---

## `report_agent`

```python
report_agent = Agent(
    MODLE_NAME,
    system_prompt="""
    You are a Career Advisor writing a clear, honest self-review report.
    You receive pre-computed structured data about:
    - What changed between the original and tailored CV
    - Skill and keyword gaps vs. the job requirements
    - Audit quality scores (hallucination, AI cliché, overall quality)

    Your job is to produce:
    1. overall_recommendation: "Strong Match", "Partial Match", or "Weak Match"
    2. match_score (0-100) based on keyword coverage % and gap severity
    3. suggestions_to_strengthen: concrete, actionable upskilling advice
    4. recommendation_rationale: honest plain-English explanation
    5. audit_summary: plain-English summary of quality scores

    Be direct and honest. Do not sugarcoat weak matches. Avoid AI clichés.
    """,
    output_type=FinalReport,
    retries=3,
)
```

**Prompt structure** passed to the agent:
```
CV Diff: <CVDiff JSON>
Gap Analysis: <GapAnalysis JSON>
Audit Result: <AuditResult JSON>
Review Result: <ReviewResult JSON>
Job Analysis: <JobAnalysis JSON>
```

---

## Workflow Integration

`ResumeTailorWorkflow.run()` additions:

```python
# Initialised once at top of run():
total_usage = RunUsage()

# All existing agent.run() calls gain usage=total_usage

# After audit (always, pass or fail):
cv_diff = compute_cv_diff(original_cv, new_cv)
gap_analysis = compute_gap_analysis(original_cv, new_cv, job_analysis_result.output)

report_result = await report_agent.run(
    f"""
    CV Diff: {cv_diff.model_dump_json()}
    Gap Analysis: {gap_analysis.model_dump_json()}
    Audit Result: {audit.model_dump_json()}
    Review Result: {review.model_dump_json() if review else 'N/A'}
    Job Analysis: {job_data_json}
    """,
    usage=total_usage,
)

final_report = report_result.output
```

`ResumeTailorResult` is updated to include `final_report`.

---

## Report Output

### Console (always printed)

```
============================================================
📊 SELF-REVIEW REPORT — Acme Corp · Senior Engineer
============================================================
🎯 Match Score: 74/100 · Partial Match
📅 Generated: 2026-04-22T21:30:00Z

WHAT CHANGED
  ✏️  Summary rewritten
  🔼 Skills reordered: Python, FastAPI, PostgreSQL → top
  📝 3 experience bullets rephrased across 2 roles

KEYWORD COVERAGE: 9/13 keywords (69%)
  ✅ Covered: Python, REST API, CI/CD, Docker, ...
  ❌ Missing: Kubernetes, Terraform, gRPC

SKILL GAPS (not in your CV)
  Hard: Kubernetes, Terraform
  Soft: (none)

SUGGESTIONS TO STRENGTHEN
  → Get CKA certification to close Kubernetes gap
  → Add a side project using Terraform

RECOMMENDATION: Partial Match
  Your backend experience aligns well, but the infra/DevOps
  requirements (K8s, Terraform) are absent from your CV.
  Apply with confidence, but flag that you're learning these.
============================================================
```

### Markdown file

Saved to `files/report_<company_name>.md` using `generate_report_markdown(report: FinalReport)` in `utils/markdown_writer.py`. Contains the same sections formatted with Markdown headings, tables, and bullet lists.

---

## Testing

| File | What it tests |
|------|--------------|
| `test_cv_diff.py` | Unit tests for `compute_cv_diff` and `compute_gap_analysis` with fixture `CV` and `JobAnalysis` objects — pure Python, no LLM |
| `test_report_integration.py` | End-to-end workflow test using `TestModel` (pydantic-ai) to override `report_agent`, verifying the Report Phase runs and populates `FinalReport` without real API calls |

---

## Error Handling

- If `new_cv` is `None` (writer failed), `compute_cv_diff` is skipped and `CVDiff` is populated with empty/default values. `compute_gap_analysis` still runs using `original_cv` and the job analysis (it does not require a tailored CV for the missing-skills portion; keyword coverage is skipped and defaults to 0%).
- If `report_agent` fails after retries, `final_report` is `None` on `ResumeTailorResult`; the pipeline still returns its normal result.
- Report generation failure is logged as a warning, never crashes the pipeline.
