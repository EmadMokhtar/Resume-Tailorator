# Resume Parsing Determinism Design

## Goal

Fix non-deterministic resume parsing where the same `.docx` resume yields wildly different results across runs (e.g., 8 skills vs 58 skills). The AI parsing agent is inherently non-deterministic, so we cache the first successful parse and reuse it on subsequent runs.

## Approach

Three-part fix: (1) content-addressed cache for parsed CVs, (2) `--debug` flag for visibility into conversion quality, and (3) richer parser agent system prompt for better first-time extraction.

## Part 1 — Parsed CV Cache

### Flow

```
1. Convert DOCX/PDF to markdown (existing, deterministic via markitdown)
2. Compute SHA-256 hash of the markdown content
3. Query SQLite via ResumeMemoryService: SELECT parsed_cv WHERE content_hash = ?
   -> HIT:  pass pre_parsed_cv to workflow, skip AI parsing entirely
   -> MISS: workflow parses normally, then save parsed CV keyed by hash
4. Workflow proceeds (Step 0 skipped on cache hit)
5. Save result to memory (existing behavior, unchanged)
```

### Workflow API Change

`ResumeTailorWorkflow.run()` gains a new optional parameter:

```python
async def run(
    self,
    resume_text: str,
    *,
    job_content_file_path: str | None = None,
    job_content: str | None = None,
    model: str | None = None,
    pre_parsed_cv: CV | None = None,  # NEW
    debug: bool = False,               # NEW
) -> ResumeTailorResult:
```

When `pre_parsed_cv` is provided, Step 0 ("PARSING_RESUME") is skipped and `original_cv` is set to the provided value. The console prints "Using cached parsed resume" instead of the parser agent output.

### Memory Service Additions

Two new methods on `ResumeMemoryService`:

```python
def lookup_parsed_cv(self, content_hash: str) -> CV | None:
    """Return cached parsed CV for this hash, or None on miss."""

def save_parsed_cv(self, content_hash: str, cv: CV) -> None:
    """Store parsed CV keyed by content hash."""
```

The `resume_sources` table already has a `content_hash` column. The parsed CV JSON is stored in an existing column or a new `parsed_cv_json TEXT` column on `resume_sources`.

### Hash Computation

In `_tailor_impl`, after markdown conversion:

```python
import hashlib
content_hash = hashlib.sha256(resume_content.encode()).hexdigest()
```

### Error Handling

Cache is best-effort only. DB failures, hash collisions, or deserialization errors fall back to normal AI parsing with a logged warning. The cache must never become a failure path.

## Part 2 — `--debug` Flag

Add `--debug` / `-d` boolean flag to `tailor` and `re-tailor` commands. Default: `False`.

Threaded through: CLI → `_tailor_impl` → `_run_workflow` → `workflow.run()`.

When enabled:
- Save the converted resume markdown to `output_dir/job_dir/resume_debug.md` (alongside the tailored output, not overwritten by other runs)
- Print content hash (SHA-256) and cache hit/miss status to console
- Print first 500 chars of the markdown sent to the parser agent (so user can verify conversion quality)
- Also applies during `re-tailor` — saves the re-loaded resume markdown for debugging

This replaces the current always-on save to `output_dir/resume_converted.md`, which gets overwritten on each run. With `--debug`, the dump lands in the job-specific directory and persists across runs.

## Part 3 — Parser Agent Prompt Improvements

The `resume_parser_agent` system prompt in `workflows/agents.py` is updated to:

1. Explicitly instruct extraction of skills from *all* sections (summary, experience bullets, projects, certifications, not just a dedicated skills section)
2. Add guidance that a senior professional resume should yield 40+ skills when thoroughly parsed
3. Emphasize preserving all technical terms, frameworks, tools, and methodologies as individual skills

No structural changes to the agent — just richer instructions in the `system_prompt` string.

## Files Touched

| File | Change |
|------|--------|
| `resume_tailorator/main.py` | CLI: add `--debug` flag to `tailor` and `re-tailor`; `_tailor_impl`: hash computation, cache lookup/save, debug output |
| `resume_tailorator/workflows/__init__.py` | `ResumeTailorWorkflow.run()`: add `pre_parsed_cv` and `debug` params, skip Step 0 when cached |
| `resume_tailorator/workflows/agents.py` | `resume_parser_agent`: richer system prompt |
| `resume_tailorator/memory/service.py` | Add `lookup_parsed_cv` and `save_parsed_cv` methods |
| `resume_tailorator/memory/repository.py` | Add DB query/upsert for parsed CV by content hash |
| `resume_tailorator/memory/sqlite_repository.py` | SQL implementation of the above |
| `tests/` | Unit + integration tests for new paths |

## Testing

- **Unit tests**: `lookup_parsed_cv` returns CV on hit, None on miss; `save_parsed_cv` persists and is retrievable
- **Integration test**: Workflow with `pre_parsed_cv` skips parsing and uses provided CV
- **Regression**: All existing tests must pass unchanged (cache is opt-in, current behavior preserved with `pre_parsed_cv=None`)
