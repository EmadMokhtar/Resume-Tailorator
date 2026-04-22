# Quality Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a per-agent quality gate to the Resume Tailorator pipeline that scores each agent's output 0–10 and retries with feedback until score ≥ 9, falling back to best available output if retries are exhausted.

**Architecture:** A single `quality_gate_agent` is called from an `@agent.output_validator` decorator on each of the 5 pipeline agents. Each validator saves its output to a module-level `_QualityState` Pydantic model before raising `ModelRetry`, so the workflow can recover the last attempt if retries are exhausted. Token usage rolls up via `usage=ctx.usage`.

**Tech Stack:** pydantic-ai (`Agent`, `RunContext`, `ModelRetry`, `UnexpectedModelBehavior`, `TestModel`), pydantic v2, pytest + pytest-anyio

> ⚠️ **Ordering note:** This plan modifies `workflows/agents.py`, `models/agents/output.py`, and `workflows/__init__.py`. The Self-Review Report plan also modifies these files. Run this plan **first**, then the Report Phase plan.

---

## Pre-work: Test dependencies

> Skip if already done from the Self-Review Report plan. Check: `uv run pytest --version`

- [ ] **Step 1: Add pytest and anyio dev dependencies**

```bash
uv add --dev pytest pytest-anyio anyio
```

Expected: `pyproject.toml` updated, lockfile updated.

- [ ] **Step 2: Verify pytest runs (empty suite is fine)**

```bash
uv run pytest tests/ -v 2>&1 | head -20
```

Expected: `no tests ran` or `0 passed`.

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "build(deps): add pytest and anyio for testing"
```

---

## Task 1: `QualityCheckResult` model

**Files:**
- Modify: `models/agents/output.py`
- Create: `tests/test_quality_gate_models.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_quality_gate_models.py`:

```python
"""Tests for QualityCheckResult model."""
import pytest
from models.agents.output import QualityCheckResult


def test_quality_check_result_valid_pass_score():
    result = QualityCheckResult(score=9, reasoning="Solid output", improvements=[])
    with pytest.subtest("score"):
        assert result.score == 9
    with pytest.subtest("improvements_empty"):
        assert result.improvements == []


def test_quality_check_result_valid_fail_score():
    result = QualityCheckResult(
        score=5,
        reasoning="Needs work",
        improvements=["Add more keywords", "Fix tone"],
    )
    with pytest.subtest("score"):
        assert result.score == 5
    with pytest.subtest("improvements"):
        assert len(result.improvements) == 2


def test_quality_check_result_rejects_score_above_10():
    with pytest.raises(Exception):
        QualityCheckResult(score=11, reasoning="Over limit", improvements=[])


def test_quality_check_result_rejects_score_below_0():
    with pytest.raises(Exception):
        QualityCheckResult(score=-1, reasoning="Below zero", improvements=[])


def test_quality_check_result_improvements_defaults_to_empty():
    result = QualityCheckResult(score=10, reasoning="Perfect")
    assert result.improvements == []
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_quality_gate_models.py -v
```

Expected: `ImportError` — `QualityCheckResult` not yet defined.

- [ ] **Step 3: Add `QualityCheckResult` to `models/agents/output.py`**

Append after the `ReviewResult` class (end of file):

```python
class QualityCheckResult(BaseModel):
    """Result from the quality gate agent scoring another agent's output."""

    score: int = Field(..., ge=0, le=10, description="Quality score 0-10. >=9 passes.")
    reasoning: str = Field(description="Explanation of why this score was given.")
    improvements: list[str] = Field(
        default_factory=list,
        description="Concrete improvements needed if score < 9.",
    )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/test_quality_gate_models.py -v
```

Expected: 5 tests, all `PASSED`.

- [ ] **Step 5: Commit**

```bash
git add models/agents/output.py tests/test_quality_gate_models.py
git commit -m "feat(model): add QualityCheckResult model"
```

---

## Task 2: `_QualityState`, `quality_gate_agent`, and retry bump

**Files:**
- Modify: `workflows/agents.py`

No tests in this task — infrastructure is tested indirectly in Tasks 3–7.

- [ ] **Step 1: Add imports to `workflows/agents.py`**

Change the import block at the top from:

```python
from pydantic_ai import Agent

from models.agents.output import JobAnalysis, CV, AuditResult, ReviewResult
from tools.playwright import read_job_content_file
```

To:

```python
from typing import Any

from pydantic import BaseModel, ConfigDict
from pydantic_ai import Agent, ModelRetry, RunContext

from models.agents.output import (
    AuditResult,
    CV,
    JobAnalysis,
    QualityCheckResult,
    ReviewResult,
)
from tools.playwright import read_job_content_file
```

- [ ] **Step 2: Add `_QualityState` class and 5 state instances**

Add immediately after the imports, before the `MODLE_NAME = ...` line:

```python
class _QualityState(BaseModel):
    """Holds the last output from one pipeline agent for fallback recovery."""

    model_config = ConfigDict(arbitrary_types_allowed=True)
    last_output: Any = None


_parser_qs = _QualityState()
_analyst_qs = _QualityState()
_writer_qs = _QualityState()
_auditor_qs = _QualityState()
_cover_qs = _QualityState()
```

- [ ] **Step 3: Add `quality_gate_agent` immediately after `MODLE_NAME`**

After the line `MODLE_NAME = "openai:gpt-5-mini"`, add:

```python
# --- Quality Gate Agent ---
# Universal reviewer: scores any pipeline agent's output 0-10 and requests improvements.
quality_gate_agent = Agent(
    MODLE_NAME,
    system_prompt="""You are a strict Quality Gate Reviewer for a resume tailoring pipeline.
Score the output of the agent whose role is specified in the prompt, on a scale of 0 to 10.
Scoring criteria by role:
  - Resume Parser: completeness, no data loss, correctly structured fields
  - Job Analyst: keyword coverage, clear requirement identification, no omissions
  - CV Writer: no hallucinations, ATS keywords incorporated naturally, human tone, no clichés
  - Auditor: thorough hallucination check, specific cliché identification, actionable feedback
  - Cover Letter Writer: authentic human voice, no AI clichés, specific to the role, concise
A score of 9 or 10 means ready to proceed.
A score below 9 means the output must be improved before the pipeline continues.
Always provide a reasoning and list specific improvements when score < 9.""",
    output_type=QualityCheckResult,
    retries=2,
)
```

- [ ] **Step 4: Bump `retries` from 3 → 5 on all pipeline agents**

In `workflows/agents.py`, find every `retries=3` and change to `retries=5`.
There should be 7 occurrences (one per agent: scraper, analyst, resume_parser, writer, auditor, cover_letter_writer, reviewer).

Verify with:

```bash
grep -n "retries=" workflows/agents.py
```

Expected: all lines now show `retries=5`, `quality_gate_agent` shows `retries=2`.

- [ ] **Step 5: Verify file parses without errors**

```bash
uv run python -c "from workflows.agents import quality_gate_agent, _parser_qs, _analyst_qs; print('OK')"
```

Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add workflows/agents.py
git commit -m "feat(agents): add quality gate agent, QualityState singletons, bump retries to 5"
```

---

## Task 3: Validator for `resume_parser_agent`

**Files:**
- Modify: `workflows/agents.py`
- Create: `tests/test_quality_gate.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_quality_gate.py`:

```python
"""Tests for per-agent quality gate validators."""
import pytest
from pydantic_ai import models
from pydantic_ai.exceptions import UnexpectedModelBehavior
from pydantic_ai.models.test import TestModel

models.ALLOW_MODEL_REQUESTS = False

# ---------------------------------------------------------------------------
# Shared test data
# ---------------------------------------------------------------------------

SAMPLE_CV = {
    "full_name": "Jane Smith",
    "contact_info": "jane@example.com",
    "summary": "Software engineer with 5 years experience.",
    "skills": ["Python", "FastAPI"],
    "projects": [],
    "experience": [
        {
            "company": "Acme Corp",
            "role": "Engineer",
            "dates": "2020-2023",
            "highlights": ["Built REST APIs"],
        }
    ],
    "education": ["BSc Computer Science"],
    "certifications": [],
    "publications": [],
}

QC_PASS = {"score": 9, "reasoning": "Good output.", "improvements": []}
QC_FAIL = {"score": 5, "reasoning": "Needs improvement.", "improvements": ["Fix tone"]}


@pytest.fixture(autouse=True)
def reset_quality_states():
    """Reset all _QualityState singletons before and after each test."""
    from workflows.agents import (
        _analyst_qs,
        _auditor_qs,
        _cover_qs,
        _parser_qs,
        _writer_qs,
    )

    for qs in (_parser_qs, _analyst_qs, _writer_qs, _auditor_qs, _cover_qs):
        qs.last_output = None
    yield
    for qs in (_parser_qs, _analyst_qs, _writer_qs, _auditor_qs, _cover_qs):
        qs.last_output = None


# ---------------------------------------------------------------------------
# Resume Parser
# ---------------------------------------------------------------------------


def test_resume_parser_validator_passes_when_score_9():
    from workflows.agents import quality_gate_agent, resume_parser_agent

    with quality_gate_agent.override(model=TestModel(custom_output_data=QC_PASS)):
        with resume_parser_agent.override(model=TestModel(custom_output_data=SAMPLE_CV)):
            result = resume_parser_agent.run_sync("Parse this resume.")

    assert result.output.full_name == "Jane Smith"


def test_resume_parser_validator_saves_last_output_when_score_low():
    from workflows.agents import _parser_qs, quality_gate_agent, resume_parser_agent

    with quality_gate_agent.override(model=TestModel(custom_output_data=QC_FAIL)):
        with resume_parser_agent.override(model=TestModel(custom_output_data=SAMPLE_CV)):
            with pytest.raises(UnexpectedModelBehavior):
                resume_parser_agent.run_sync("Parse this resume.")

    assert _parser_qs.last_output is not None
    assert _parser_qs.last_output.full_name == "Jane Smith"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_quality_gate.py::test_resume_parser_validator_passes_when_score_9 tests/test_quality_gate.py::test_resume_parser_validator_saves_last_output_when_score_low -v
```

Expected: FAIL — validator not yet defined.

- [ ] **Step 3: Add validator to `workflows/agents.py`**

Append to the very end of `workflows/agents.py`:

```python
# ---------------------------------------------------------------------------
# Quality Gate Validators
# ---------------------------------------------------------------------------


@resume_parser_agent.output_validator
async def _validate_resume_parser(ctx: RunContext[None], output: CV) -> CV:
    """Score the resume parser output. Raises ModelRetry if score < 9."""
    _parser_qs.last_output = output
    result = await quality_gate_agent.run(
        f"Role: Resume Parser\nOutput:\n{output.model_dump_json(indent=2)}",
        usage=ctx.usage,
    )
    check = result.output
    if check.score < 9:
        raise ModelRetry(
            f"Score: {check.score}/10. Improvements needed:\n"
            + "\n".join(f"- {i}" for i in check.improvements)
        )
    return output
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_quality_gate.py::test_resume_parser_validator_passes_when_score_9 tests/test_quality_gate.py::test_resume_parser_validator_saves_last_output_when_score_low -v
```

Expected: 2 tests `PASSED`.

- [ ] **Step 5: Commit**

```bash
git add workflows/agents.py tests/test_quality_gate.py
git commit -m "feat(agents): add quality gate validator for resume_parser_agent"
```

---

## Task 4: Validator for `analyst_agent`

**Files:**
- Modify: `workflows/agents.py`
- Modify: `tests/test_quality_gate.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_quality_gate.py`:

```python
# ---------------------------------------------------------------------------
# Job Analyst
# ---------------------------------------------------------------------------

SAMPLE_JOB = {
    "job_title": "Backend Engineer",
    "company_name": "TechCorp",
    "summary": "Build scalable backend systems.",
    "hard_skills": ["Python", "FastAPI"],
    "soft_skills": ["Communication"],
    "key_responsibilities": ["Build APIs", "Write tests"],
    "keywords_to_target": ["Python", "FastAPI", "REST"],
}


def test_analyst_validator_passes_when_score_9():
    from workflows.agents import analyst_agent, quality_gate_agent

    with quality_gate_agent.override(model=TestModel(custom_output_data=QC_PASS)):
        with analyst_agent.override(model=TestModel(custom_output_data=SAMPLE_JOB)):
            result = analyst_agent.run_sync("Analyse this job posting.")

    assert result.output.job_title == "Backend Engineer"


def test_analyst_validator_saves_last_output_when_score_low():
    from workflows.agents import _analyst_qs, analyst_agent, quality_gate_agent

    with quality_gate_agent.override(model=TestModel(custom_output_data=QC_FAIL)):
        with analyst_agent.override(model=TestModel(custom_output_data=SAMPLE_JOB)):
            with pytest.raises(UnexpectedModelBehavior):
                analyst_agent.run_sync("Analyse this job posting.")

    assert _analyst_qs.last_output is not None
    assert _analyst_qs.last_output.job_title == "Backend Engineer"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_quality_gate.py::test_analyst_validator_passes_when_score_9 tests/test_quality_gate.py::test_analyst_validator_saves_last_output_when_score_low -v
```

Expected: FAIL — validator not yet defined.

- [ ] **Step 3: Add validator to `workflows/agents.py`**

Append after `_validate_resume_parser`:

```python
@analyst_agent.output_validator
async def _validate_analyst(ctx: RunContext[None], output: JobAnalysis) -> JobAnalysis:
    """Score the job analyst output. Raises ModelRetry if score < 9."""
    _analyst_qs.last_output = output
    result = await quality_gate_agent.run(
        f"Role: Job Analyst\nOutput:\n{output.model_dump_json(indent=2)}",
        usage=ctx.usage,
    )
    check = result.output
    if check.score < 9:
        raise ModelRetry(
            f"Score: {check.score}/10. Improvements needed:\n"
            + "\n".join(f"- {i}" for i in check.improvements)
        )
    return output
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_quality_gate.py::test_analyst_validator_passes_when_score_9 tests/test_quality_gate.py::test_analyst_validator_saves_last_output_when_score_low -v
```

Expected: 2 tests `PASSED`.

- [ ] **Step 5: Commit**

```bash
git add workflows/agents.py tests/test_quality_gate.py
git commit -m "feat(agents): add quality gate validator for analyst_agent"
```

---

## Task 5: Validator for `writer_agent`

**Files:**
- Modify: `workflows/agents.py`
- Modify: `tests/test_quality_gate.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_quality_gate.py`:

```python
# ---------------------------------------------------------------------------
# CV Writer
# ---------------------------------------------------------------------------


def test_writer_validator_passes_when_score_9():
    from workflows.agents import quality_gate_agent, writer_agent

    with quality_gate_agent.override(model=TestModel(custom_output_data=QC_PASS)):
        with writer_agent.override(model=TestModel(custom_output_data=SAMPLE_CV)):
            result = writer_agent.run_sync("Tailor this resume.")

    assert result.output.full_name == "Jane Smith"


def test_writer_validator_saves_last_output_when_score_low():
    from workflows.agents import _writer_qs, quality_gate_agent, writer_agent

    with quality_gate_agent.override(model=TestModel(custom_output_data=QC_FAIL)):
        with writer_agent.override(model=TestModel(custom_output_data=SAMPLE_CV)):
            with pytest.raises(UnexpectedModelBehavior):
                writer_agent.run_sync("Tailor this resume.")

    assert _writer_qs.last_output is not None
    assert _writer_qs.last_output.full_name == "Jane Smith"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_quality_gate.py::test_writer_validator_passes_when_score_9 tests/test_quality_gate.py::test_writer_validator_saves_last_output_when_score_low -v
```

Expected: FAIL — validator not yet defined.

- [ ] **Step 3: Add validator to `workflows/agents.py`**

Append after `_validate_analyst`:

```python
@writer_agent.output_validator
async def _validate_writer(ctx: RunContext[None], output: CV) -> CV:
    """Score the CV writer output. Raises ModelRetry if score < 9."""
    _writer_qs.last_output = output
    result = await quality_gate_agent.run(
        f"Role: CV Writer\nOutput:\n{output.model_dump_json(indent=2)}",
        usage=ctx.usage,
    )
    check = result.output
    if check.score < 9:
        raise ModelRetry(
            f"Score: {check.score}/10. Improvements needed:\n"
            + "\n".join(f"- {i}" for i in check.improvements)
        )
    return output
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_quality_gate.py::test_writer_validator_passes_when_score_9 tests/test_quality_gate.py::test_writer_validator_saves_last_output_when_score_low -v
```

Expected: 2 tests `PASSED`.

- [ ] **Step 5: Commit**

```bash
git add workflows/agents.py tests/test_quality_gate.py
git commit -m "feat(agents): add quality gate validator for writer_agent"
```

---

## Task 6: Validator for `auditor_agent`

**Files:**
- Modify: `workflows/agents.py`
- Modify: `tests/test_quality_gate.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_quality_gate.py`:

```python
# ---------------------------------------------------------------------------
# Auditor
# ---------------------------------------------------------------------------

SAMPLE_AUDIT = {
    "passed": True,
    "hallucination_score": 0,
    "ai_cliche_score": 1,
    "issues": [],
    "feedback_summary": "No hallucinations detected. Tone is natural.",
}


def test_auditor_validator_passes_when_score_9():
    from workflows.agents import auditor_agent, quality_gate_agent

    with quality_gate_agent.override(model=TestModel(custom_output_data=QC_PASS)):
        with auditor_agent.override(model=TestModel(custom_output_data=SAMPLE_AUDIT)):
            result = auditor_agent.run_sync("Audit this CV.")

    assert result.output.passed is True


def test_auditor_validator_saves_last_output_when_score_low():
    from workflows.agents import _auditor_qs, auditor_agent, quality_gate_agent

    with quality_gate_agent.override(model=TestModel(custom_output_data=QC_FAIL)):
        with auditor_agent.override(model=TestModel(custom_output_data=SAMPLE_AUDIT)):
            with pytest.raises(UnexpectedModelBehavior):
                auditor_agent.run_sync("Audit this CV.")

    assert _auditor_qs.last_output is not None
    assert _auditor_qs.last_output.passed is True
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_quality_gate.py::test_auditor_validator_passes_when_score_9 tests/test_quality_gate.py::test_auditor_validator_saves_last_output_when_score_low -v
```

Expected: FAIL — validator not yet defined.

- [ ] **Step 3: Add validator to `workflows/agents.py`**

Append after `_validate_writer`:

```python
@auditor_agent.output_validator
async def _validate_auditor(ctx: RunContext[None], output: AuditResult) -> AuditResult:
    """Score the auditor output. Raises ModelRetry if score < 9."""
    _auditor_qs.last_output = output
    result = await quality_gate_agent.run(
        f"Role: Auditor\nOutput:\n{output.model_dump_json(indent=2)}",
        usage=ctx.usage,
    )
    check = result.output
    if check.score < 9:
        raise ModelRetry(
            f"Score: {check.score}/10. Improvements needed:\n"
            + "\n".join(f"- {i}" for i in check.improvements)
        )
    return output
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_quality_gate.py::test_auditor_validator_passes_when_score_9 tests/test_quality_gate.py::test_auditor_validator_saves_last_output_when_score_low -v
```

Expected: 2 tests `PASSED`.

- [ ] **Step 5: Commit**

```bash
git add workflows/agents.py tests/test_quality_gate.py
git commit -m "feat(agents): add quality gate validator for auditor_agent"
```

---

## Task 7: Validator for `cover_letter_writer_agent`

**Files:**
- Modify: `workflows/agents.py`
- Modify: `tests/test_quality_gate.py`

> Note: `cover_letter_writer_agent` is not yet called in `workflows/__init__.py`. The validator is added now so it is active when the agent is wired into the pipeline.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_quality_gate.py`:

```python
# ---------------------------------------------------------------------------
# Cover Letter Writer
# ---------------------------------------------------------------------------

SAMPLE_COVER_LETTER = (
    "Hi, I am applying for the Backend Engineer role at TechCorp. "
    "I have built REST APIs with FastAPI for three years and I think "
    "I would fit well with your team. Looking forward to chatting."
)


def test_cover_letter_validator_passes_when_score_9():
    from workflows.agents import cover_letter_writer_agent, quality_gate_agent

    with quality_gate_agent.override(model=TestModel(custom_output_data=QC_PASS)):
        with cover_letter_writer_agent.override(
            model=TestModel(custom_output_text=SAMPLE_COVER_LETTER)
        ):
            result = cover_letter_writer_agent.run_sync("Write a cover letter.")

    assert "TechCorp" in result.output


def test_cover_letter_validator_saves_last_output_when_score_low():
    from workflows.agents import _cover_qs, cover_letter_writer_agent, quality_gate_agent

    with quality_gate_agent.override(model=TestModel(custom_output_data=QC_FAIL)):
        with cover_letter_writer_agent.override(
            model=TestModel(custom_output_text=SAMPLE_COVER_LETTER)
        ):
            with pytest.raises(UnexpectedModelBehavior):
                cover_letter_writer_agent.run_sync("Write a cover letter.")

    assert _cover_qs.last_output is not None
    assert "TechCorp" in _cover_qs.last_output
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_quality_gate.py::test_cover_letter_validator_passes_when_score_9 tests/test_quality_gate.py::test_cover_letter_validator_saves_last_output_when_score_low -v
```

Expected: FAIL — validator not yet defined.

- [ ] **Step 3: Add validator to `workflows/agents.py`**

Append after `_validate_auditor`:

```python
@cover_letter_writer_agent.output_validator
async def _validate_cover_letter(ctx: RunContext[None], output: str) -> str:
    """Score the cover letter output. Raises ModelRetry if score < 9."""
    _cover_qs.last_output = output
    result = await quality_gate_agent.run(
        f"Role: Cover Letter Writer\nOutput:\n{output}",
        usage=ctx.usage,
    )
    check = result.output
    if check.score < 9:
        raise ModelRetry(
            f"Score: {check.score}/10. Improvements needed:\n"
            + "\n".join(f"- {i}" for i in check.improvements)
        )
    return output
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_quality_gate.py::test_cover_letter_validator_passes_when_score_9 tests/test_quality_gate.py::test_cover_letter_validator_saves_last_output_when_score_low -v
```

Expected: 2 tests `PASSED`.

- [ ] **Step 5: Run full test suite so far**

```bash
uv run pytest tests/ -v
```

Expected: 15 tests pass (5 model tests + 10 validator tests).

- [ ] **Step 6: Commit**

```bash
git add workflows/agents.py tests/test_quality_gate.py
git commit -m "feat(agents): add quality gate validator for cover_letter_writer_agent"
```

---

## Task 8: Fallback handling in `workflows/__init__.py`

**Files:**
- Modify: `workflows/__init__.py`
- Modify: `tests/test_quality_gate.py`

This task adds `try/except UnexpectedModelBehavior` around the 4 currently-active agent calls so exhausted quality gate retries don't crash the pipeline — they degrade gracefully to the last saved output.

- [ ] **Step 1: Write structural tests (import + state access)**

Append to `tests/test_quality_gate.py`:

```python
# ---------------------------------------------------------------------------
# Workflow fallback (structural tests)
# ---------------------------------------------------------------------------


def test_quality_state_objects_are_importable_from_agents():
    from workflows.agents import _analyst_qs, _auditor_qs, _parser_qs, _writer_qs

    for qs in (_parser_qs, _analyst_qs, _writer_qs, _auditor_qs):
        assert hasattr(qs, "last_output")
        assert qs.last_output is None


def test_quality_state_accepts_cv_assignment():
    from workflows.agents import _parser_qs

    from models.agents.output import CV, WorkExperience

    cv = CV(
        full_name="Test User",
        contact_info="test@example.com",
        summary="Summary text.",
        skills=["Python"],
        experience=[WorkExperience(company="X Corp", role="Engineer", dates="2020", highlights=[])],
        education=["BSc Computer Science"],
    )
    _parser_qs.last_output = cv
    assert _parser_qs.last_output.full_name == "Test User"
```

- [ ] **Step 2: Run structural tests to verify they pass (these test existing code)**

```bash
uv run pytest tests/test_quality_gate.py::test_quality_state_objects_are_importable_from_agents tests/test_quality_gate.py::test_quality_state_accepts_cv_assignment -v
```

Expected: 2 tests `PASSED`.

- [ ] **Step 3: Update imports in `workflows/__init__.py`**

Find the import block at the top of `workflows/__init__.py`. It currently imports from `workflows.agents`:

```python
from workflows.agents import (
    analyst_agent,
    writer_agent,
    auditor_agent,
    resume_parser_agent,
    reviewer_agent,
)
```

Add `UnexpectedModelBehavior` and the 4 `_qs` state objects:

```python
from pydantic_ai.exceptions import UnexpectedModelBehavior

from workflows.agents import (
    _analyst_qs,
    _auditor_qs,
    _parser_qs,
    _writer_qs,
    analyst_agent,
    auditor_agent,
    resume_parser_agent,
    reviewer_agent,
    writer_agent,
)
```

- [ ] **Step 4: Add fallback for `resume_parser_agent`**

In `workflows/__init__.py`, find the `resume_parser_agent.run()` call inside `for attempt in range(self.MAX_RETRIES)`. The current try/except looks like:

```python
            try:
                original_cv_result = await resume_parser_agent.run(
                    f"Parse this resume into structured format:\n\n{resume_text}"
                )
                ...
            except Exception as e:
                print(f"⚠️ Attempt {attempt + 1}/{self.MAX_RETRIES} failed: {e}")
                if attempt == self.MAX_RETRIES - 1:
                    sys.exit("❌ Failed to parse original resume after retries.")
```

Add `except UnexpectedModelBehavior` BEFORE `except Exception as e`:

```python
            try:
                original_cv_result = await resume_parser_agent.run(
                    f"Parse this resume into structured format:\n\n{resume_text}"
                )
                ...
            except UnexpectedModelBehavior:
                if _parser_qs.last_output is not None:
                    print("⚠️  Resume Parser quality gate exhausted — using best available output")
                    original_cv = _parser_qs.last_output
                    break
                sys.exit("❌ Resume Parser quality gate exhausted with no fallback available.")
            except Exception as e:
                print(f"⚠️ Attempt {attempt + 1}/{self.MAX_RETRIES} failed: {e}")
                if attempt == self.MAX_RETRIES - 1:
                    sys.exit("❌ Failed to parse original resume after retries.")
```

Then find the post-loop assignment and make it conditional (it must not overwrite `original_cv` when it was already set from the fallback):

Find:
```python
        if original_cv_result is None or original_cv_result.output is None:
            sys.exit("❌ Failed to parse original resume after retries.")

        original_cv = original_cv_result.output
```

Replace with:
```python
        if not hasattr(locals(), "original_cv") or original_cv is None:  # type: ignore[possibly-undefined]
            if original_cv_result is None or original_cv_result.output is None:
                sys.exit("❌ Failed to parse original resume after retries.")
            original_cv = original_cv_result.output
```

> Tip: the exact variable names and surrounding code may differ slightly from the above; adapt to match the actual file structure while preserving the intent.

- [ ] **Step 5: Add fallback for `analyst_agent`**

Apply the same pattern to the `analyst_agent.run()` call inside its `for attempt in range(self.MAX_RETRIES)` loop:

```python
            except UnexpectedModelBehavior:
                if _analyst_qs.last_output is not None:
                    print("⚠️  Job Analyst quality gate exhausted — using best available output")
                    job_analysis = _analyst_qs.last_output
                    break
                sys.exit("❌ Job Analyst quality gate exhausted with no fallback available.")
```

And guard the post-loop assignment:
```python
        if not hasattr(locals(), "job_analysis") or job_analysis is None:  # type: ignore[possibly-undefined]
            if job_analysis_result is None or job_analysis_result.output is None:
                sys.exit("❌ Failed to analyse job after retries.")
            job_analysis = job_analysis_result.output
```

- [ ] **Step 6: Add fallback for `writer_agent`**

The `writer_agent.run()` call (~line 162) has no existing try/except. Wrap it:

```python
        try:
            write_result = await writer_agent.run(writer_prompt)
        except UnexpectedModelBehavior:
            if _writer_qs.last_output is not None:
                print("⚠️  CV Writer quality gate exhausted — using best available output")
                new_cv = _writer_qs.last_output
            else:
                print("⚠️  CV Writer quality gate exhausted with no fallback — skipping tailoring")
                new_cv = None
```

Then replace the existing direct assignment `new_cv = write_result.output` with a guard:

```python
        if "new_cv" not in dir():  # only assign if not already set by fallback
            new_cv = write_result.output if write_result else None
```

> Note: the exact surrounding code structure may require adjusting this pattern. The key intent is: if `UnexpectedModelBehavior` was caught and `new_cv` was set from `_writer_qs.last_output`, do not overwrite it.

- [ ] **Step 7: Add fallback for `auditor_agent`**

Apply the same pattern to the `auditor_agent.run()` call (~line 281):

```python
        try:
            audit_result = await auditor_agent.run(audit_prompt)
        except UnexpectedModelBehavior:
            if _auditor_qs.last_output is not None:
                print("⚠️  Auditor quality gate exhausted — using best available output")
                audit_output = _auditor_qs.last_output
            else:
                print("⚠️  Auditor quality gate exhausted with no fallback — skipping audit")
                audit_output = None
```

- [ ] **Step 8: Verify import works**

```bash
uv run python -c "from workflows import ResumeTailorator; print('OK')"
```

Expected: `OK` (no import errors).

- [ ] **Step 9: Run full test suite**

```bash
uv run pytest tests/ -v
```

Expected: 17 tests pass (5 model + 10 validator + 2 structural).

- [ ] **Step 10: Commit**

```bash
git add workflows/__init__.py tests/test_quality_gate.py
git commit -m "feat(workflow): add UnexpectedModelBehavior fallback for all quality gate agents"
```

---

## Self-Review

**Spec coverage check against `docs/superpowers/specs/2026-04-22-quality-gate-design.md`:**

| Spec requirement | Covered by task |
|---|---|
| `QualityCheckResult` model with score 0–10, reasoning, improvements | Task 1 |
| `_QualityState(BaseModel)` with `arbitrary_types_allowed=True` | Task 2 |
| 5 module-level `_qs` singleton instances | Task 2 |
| `quality_gate_agent` with universal system prompt | Task 2 |
| `retries` bumped 3→5 on all pipeline agents | Task 2 |
| `quality_gate_agent` retries=2 | Task 2 |
| `@resume_parser_agent.output_validator` | Task 3 |
| `@analyst_agent.output_validator` | Task 4 |
| `@writer_agent.output_validator` | Task 5 |
| `@auditor_agent.output_validator` | Task 6 |
| `@cover_letter_writer_agent.output_validator` | Task 7 |
| Save `last_output` BEFORE raising `ModelRetry` | Tasks 3–7 |
| Raise `ModelRetry` with score + improvements text | Tasks 3–7 |
| `usage=ctx.usage` passed to `quality_gate_agent.run()` | Tasks 3–7 |
| `try/except UnexpectedModelBehavior` in `__init__.py` | Task 8 |
| Fallback: use `_qs.last_output` when retries exhausted | Task 8 |
| `print()` warning when fallback is used | Task 8 |
| `models.ALLOW_MODEL_REQUESTS = False` in tests | Tasks 3–7 |
| `reset_quality_states` fixture to isolate tests | Task 3 |
| Cover letter agent uses `custom_output_text` (str output) | Task 7 |

All spec requirements are covered. ✅

