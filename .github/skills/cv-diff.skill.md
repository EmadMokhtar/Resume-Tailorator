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
