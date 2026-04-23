# Design Spec: Per-Agent Quality Gate

**Date:** 2026-04-22
**Feature:** Per-Agent Self-Review Quality Gate
**Status:** Approved

---

## Overview

Every agent in the Resume Tailorator pipeline runs an internal self-review before passing output to the next step. A single universal `quality_gate_agent` scores the output on a 0–10 scale using agent-specific criteria. If the score is below 9 the agent retries with the improvement feedback injected as context. When retries are exhausted the workflow continues with the best available output and logs a warning. This catches low-quality agent outputs early, preventing garbage-in-garbage-out propagation across the pipeline.

---

## Architecture

```
Agent output
    │
    ▼
@agent.output_validator
    │
    ├── saves output to _<agent>_qs.last_output
    │
    ▼
quality_gate_agent.run(role + output, usage=ctx.usage)
    │
    ├── score ≥ 9  →  return output (pass)
    └── score < 9  →  raise ModelRetry(improvements)
                            │
                            ▼
                     agent retries (up to 5 attempts)
                            │
                     UnexpectedModelBehavior (retries exhausted)
                            │
                            ▼
                  workflows/__init__.py catches exception
                  uses _<agent>_qs.last_output + logs warning
```

**Cost roll-up:** each validator calls `quality_gate_agent.run(..., usage=ctx.usage)` — token counts roll up into the parent agent's `RunUsage` which is threaded through the workflow via `total_usage`.

---

## Data Models (`models/agents/output.py`)

### `QualityCheckResult`

```python
class QualityCheckResult(BaseModel):
    score: int = Field(..., ge=0, le=10, description="Quality score. ≥9 passes.")
    reasoning: str = Field(description="Why this score was given.")
    improvements: list[str] = Field(
        default_factory=list,
        description="Concrete improvements needed if score < 9.",
    )
```

### `_QualityState` (`workflows/agents.py`, module-level)

One instance per agent, holds the most-recent output for fallback recovery.

```python
class _QualityState(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    last_output: Any = None

_parser_qs  = _QualityState()
_analyst_qs = _QualityState()
_writer_qs  = _QualityState()
_auditor_qs = _QualityState()
_cover_qs   = _QualityState()
```

---

## `quality_gate_agent` (`workflows/agents.py`)

One universal agent. The validator passes the role name and serialised output in the prompt so the agent can apply role-specific criteria.

```python
quality_gate_agent = Agent(
    MODLE_NAME,
    system_prompt="""You are a strict Quality Gate Reviewer.
Score the output of another AI agent on a 0–10 scale.
Tailor criteria to the agent role passed in the prompt:
  - Resume Parser: completeness, no data loss, accurate structure
  - Job Analyst: keyword coverage, requirement identification
  - CV Writer: authenticity, keyword targeting, no hallucinations, natural tone
  - Auditor: thoroughness, specificity, actionable feedback
  - Cover Letter Writer: human tone, no AI clichés, authentic story
Score ≥9 = ready to proceed. Score <9 = must improve.
Be strict but fair.""",
    output_type=QualityCheckResult,
    retries=2,
)
```

---

## Output Validators (`workflows/agents.py`)

All 5 validators follow the same pattern. Role name and serialised output are passed in the prompt. The validator saves output before raising `ModelRetry` so the fallback always has the last attempt.

### Resume Parser

```python
@resume_parser_agent.output_validator
async def _validate_resume_parser(ctx: RunContext[None], output: CV) -> CV:
    _parser_qs.last_output = output
    result = await quality_gate_agent.run(
        f"Role: Resume Parser\nOutput:\n{output.model_dump_json(indent=2)}",
        usage=ctx.usage,
    )
    check = result.output
    if check.score < 9:
        raise ModelRetry(
            f"Score: {check.score}/10. Improvements:\n"
            + "\n".join(f"- {i}" for i in check.improvements)
        )
    return output
```

### Job Analyst

```python
@analyst_agent.output_validator
async def _validate_analyst(ctx: RunContext[None], output: JobAnalysis) -> JobAnalysis:
    _analyst_qs.last_output = output
    result = await quality_gate_agent.run(
        f"Role: Job Analyst\nOutput:\n{output.model_dump_json(indent=2)}",
        usage=ctx.usage,
    )
    check = result.output
    if check.score < 9:
        raise ModelRetry(
            f"Score: {check.score}/10. Improvements:\n"
            + "\n".join(f"- {i}" for i in check.improvements)
        )
    return output
```

### CV Writer

```python
@cv_writer_agent.output_validator
async def _validate_cv_writer(ctx: RunContext[None], output: CV) -> CV:
    _writer_qs.last_output = output
    result = await quality_gate_agent.run(
        f"Role: CV Writer\nOutput:\n{output.model_dump_json(indent=2)}",
        usage=ctx.usage,
    )
    check = result.output
    if check.score < 9:
        raise ModelRetry(
            f"Score: {check.score}/10. Improvements:\n"
            + "\n".join(f"- {i}" for i in check.improvements)
        )
    return output
```

### Auditor

```python
@auditor_agent.output_validator
async def _validate_auditor(ctx: RunContext[None], output: AuditResult) -> AuditResult:
    _auditor_qs.last_output = output
    result = await quality_gate_agent.run(
        f"Role: Auditor\nOutput:\n{output.model_dump_json(indent=2)}",
        usage=ctx.usage,
    )
    check = result.output
    if check.score < 9:
        raise ModelRetry(
            f"Score: {check.score}/10. Improvements:\n"
            + "\n".join(f"- {i}" for i in check.improvements)
        )
    return output
```

### Cover Letter Writer

The cover letter output is a plain `str`. It is passed directly in the prompt.

```python
@cover_letter_writer_agent.output_validator
async def _validate_cover_letter(ctx: RunContext[None], output: str) -> str:
    _cover_qs.last_output = output
    result = await quality_gate_agent.run(
        f"Role: Cover Letter Writer\nOutput:\n{output}",
        usage=ctx.usage,
    )
    check = result.output
    if check.score < 9:
        raise ModelRetry(
            f"Score: {check.score}/10. Improvements:\n"
            + "\n".join(f"- {i}" for i in check.improvements)
        )
    return output
```

---

## Error Handling (`workflows/__init__.py`)

All 5 agent calls are wrapped in `try/except UnexpectedModelBehavior`. When retries are exhausted, the workflow uses the last saved output and continues. This is only triggered if the quality gate cannot reach a passing score after 5 retries.

```python
from pydantic_ai.exceptions import UnexpectedModelBehavior

try:
    writer_result = await cv_writer_agent.run(prompt, usage=total_usage)
    new_cv = writer_result.output
except UnexpectedModelBehavior:
    new_cv = _writer_qs.last_output
    print("⚠️  CV Writer quality gate exhausted — using best available output")
```

The pattern repeats for each of the 5 agents, using the corresponding `_<agent>_qs` state object.

---

## Retry Configuration

All 5 pipeline agents increase from `retries=3` to `retries=5`. Combined with the pydantic-ai retry mechanism this gives 6 total attempts (1 initial + 5 retries) per agent, with the quality gate firing on each attempt.

`quality_gate_agent` keeps `retries=2` since its structured output (`QualityCheckResult`) is simple.

---

## Affected Files

| File | Change |
|---|---|
| `models/agents/output.py` | Add `QualityCheckResult` |
| `workflows/agents.py` | Add `_QualityState`, 5 state instances, `quality_gate_agent`, 5 `@agent.output_validator` decorators; bump `retries` from 3 → 5 on all agents |
| `workflows/__init__.py` | Wrap all 5 agent calls in `try/except UnexpectedModelBehavior`; import `_parser_qs`, `_analyst_qs`, `_writer_qs`, `_auditor_qs`, `_cover_qs` |

---

## Out of Scope

- Per-agent custom `quality_gate_agent` instances — one universal agent is sufficient
- Separate quality score storage in `ResumeTailorResult` — scores live in `QualityCheckResult` inside the retry loop, not persisted beyond the run
- Human-in-the-loop interruption on low scores — automatic retry only
