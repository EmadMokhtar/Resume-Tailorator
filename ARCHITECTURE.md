# ARCHITECTURE.md — Resume Tailorator

## Project Overview

Resume Tailorator is a multi-agent AI system that analyzes job postings and tailors resumes to match specific job requirements. It ensures authenticity, avoids AI clichés, and optimizes for Applicant Tracking Systems (ATS). The system uses a sequential pipeline of specialized agents orchestrated by `pydantic-ai`, with built-in quality gates, an inner refinement loop, and SQLite-backed memory for caching and persistence.

---

## Architecture at a Glance

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  RESUME  │    │   JOB    │    │    CV    │    │ REVIEWER │    │ AUDITOR  │    │  REPORT  │
│  PARSER  │───▶│ ANALYST  │───▶│  WRITER  │───▶│  (x3)    │───▶│          │───▶│GENERATOR │
│          │    │          │    │          │    │          │    │          │    │          │
│ CV JSON  │    │ Job JSON │    │ Tailored │    │  Review  │    │  Audit   │    │  Final   │
│          │    │          │    │ CV JSON  │    │  Scores  │    │  Result  │    │  Report  │
└──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
     ▲                ▲               │                                  │
     │                │               │          ◀── RETRY LOOP ──       │
     │                │               ▼          (up to 3 attempts)      │
     │                │         ┌──────────┐                            │
     │                │         │  QUALITY  │◀─────── score < 9          │
     │                │         │   GATE    │         triggers retry     │
     │                │         └──────────┘                            │
     │                │                                                  │
  Content-         Raw Job                                               │
  Hash Cache       Posting                                               │
  (SQLite)         Markdown                                              │
```

The system runs a **6-stage sequential pipeline** in `ResumeTailorWorkflow`:

1. **PARSING_RESUME** — Parse resume → structured `CV`
2. **ANALYZING_JOB** — Extract structured `JobAnalysis`
3. **WRITING_CV** — Tailor CV to match job
4. **REVIEWING_CV** — Score quality, suggest improvements (refinement loop)
5. **AUDITING_CV** — Validate for hallucinations and AI clichés
6. **GENERATING_REPORT** — Compile self-review report

Stages 3-5 form the **Write → Review → Audit inner loop**: after the initial write, the reviewer assesses quality and the writer refines (up to 3 review iterations). The auditor then checks the final draft. If the audit fails, the entire Write → Review → Audit loop retries (up to 3 write attempts). The Report phase **always runs**, even on audit failure.

---

## Agent Pipeline (Execution Order)

### 0. Job Scraper (`job_scraper_agent`)

**Not part of the internal pipeline** — called by the CLI before launching the workflow.

- **Responsibility**: Fetch job posting from a URL and extract clean Markdown content.
- **Output**: `ScrapedJobPosting` (url, markdown, source_text, extraction_strategy)
- **Tools**:
  - `fetch_webpage(url, timeout)` — Playwright-based page fetch (headless Chromium)
  - `validate_extraction(raw_html, extracted_markdown)` — Checks for placeholder content, minimum length (>200 chars), returns quality score
- **Retries**: 3
- **Quality Gate**: No (uses `validate_extraction` tool instead)

### 1. Resume Parser (`resume_parser_agent`)

- **Responsibility**: Parse Markdown resume text into a structured `CV` object. Extract ALL skills from every section (summary, experience, projects, certifications, education, publications).
- **Output**: `CV` (full_name, contact_info, summary, skills, projects, experience, education, certifications, publications)
- **Key Rules**: Preserve ALL hyperlinks in `[text](url)` format. Never add or modify information. For senior resumes, expect 40+ skills.
- **Retries**: 5
- **Quality Gate**: Yes — validated by `_validate_resume_parser`

### 2. Job Analyst (`analyst_agent`)

- **Responsibility**: Analyze raw job posting text and extract structured job requirements. Identifies core requirements (not "nice-to-haves") and hidden ATS keywords.
- **Output**: `JobAnalysis` (job_title, company_name, summary, hard_skills, soft_skills, key_responsibilities, keywords_to_target)
- **Retries**: 5
- **Quality Gate**: Yes — validated by `_validate_analyst`

### 3. CV Writer (`writer_agent`)

- **Responsibility**: Rewrite the CV to target the Job Analysis using ONLY content from the original CV. Rephrase and reorganize but never invent skills or experiences. Groups relevant skills at the top.
- **Output**: `CV`
- **Key Rules**: Only use skills/experiences from original CV. Rephrase existing content to align with job keywords. Avoid AI clichés. Preserve ALL hyperlinks.
- **Retries**: 5
- **Quality Gate**: Yes — validated by `_validate_writer`
- **Also used**: For the refinement loop (review-based improvements)

### 4. Reviewer (`reviewer_agent`)

- **Responsibility**: Review the tailored CV against job requirements. Score quality and provide specific improvement suggestions.
- **Output**: `ReviewResult` (quality_score 0-10, needs_improvement bool, specific_suggestions, strengths)
- **Review Criteria**: Keyword optimization, impact & achievements, relevance, clarity & readability, ATS compatibility
- **Retries**: 5
- **Quality Gate**: No — reviewer output is used to drive refinement, not gated itself

### 5. Auditor (`auditor_agent`)

- **Responsibility**: Compare original vs. tailored CV. Validate: no hallucinations (no new skills/companies/roles), no AI clichés, all hyperlinks preserved, proper job targeting.
- **Output**: `AuditResult` (passed bool, hallucination_score 0-10, ai_cliche_score 0-10, issues list, feedback_summary)
- **Pass Criteria**: Hallucination score ≤ 2, AI cliché score ≤ 3, all hyperlinks preserved
- **Retries**: 5
- **Quality Gate**: Yes — validated by `_validate_auditor`

### 6. Report Generator (`report_agent`)

- **Responsibility**: Write the narrative section of the self-review report. Receives pre-computed CVDiff, GapAnalysis, AuditResult, ReviewResult, and JobAnalysis as structured JSON.
- **Output**: `FinalReport` (overall_recommendation, match_score, suggestions_to_strengthen, audit_summary, recommendation_rationale, passed)
- **Key Design**: CVDiff and GapAnalysis are computed in **pure Python** (cv_diff.py), not by the LLM. The report agent only produces narrative fields.
- **Retries**: 5
- **Quality Gate**: No

### Auxiliary Agents

| Agent                       | Output Type          | Quality Gate | Status                                                     |
| --------------------------- | -------------------- | :----------: | ---------------------------------------------------------- |
| `cover_letter_writer_agent` | `str`                |     Yes      | Defined but **not wired** into the main workflow.          |
| `quality_gate_agent`        | `QualityCheckResult` |     N/A      | Shared validator; scores any pipeline agent's output 0–10. |

---

## Data Models

All models are defined in `resume_tailorator/models/agents/output.py` using Pydantic v2.

### Core CV & Job Models

| Model            | Purpose                    | Key Fields                                                                                                                |
| ---------------- | -------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| `CV`             | Parsed resume structure    | `full_name`, `contact_info`, `summary`, `skills`, `experience`, `education`, `certifications`, `publications`, `projects` |
| `WorkExperience` | Single job entry           | `company`, `role`, `dates`, `highlights`                                                                                  |
| `JobAnalysis`    | Extracted job requirements | `job_title`, `company_name`, `summary`, `hard_skills`, `soft_skills`, `key_responsibilities`, `keywords_to_target`        |

### Audit & Review Models

| Model                | Purpose                           | Key Fields                                                                                     |
| -------------------- | --------------------------------- | ---------------------------------------------------------------------------------------------- |
| `AuditResult`        | Hallucination & cliché validation | `passed`, `hallucination_score` (0–10), `ai_cliche_score` (0–10), `issues`, `feedback_summary` |
| `AuditIssue`         | Single audit finding              | `severity` ("Critical" / "Minor"), `issue`, `suggestion`                                       |
| `ReviewResult`       | Quality review scoring            | `quality_score` (0–10), `needs_improvement`, `specific_suggestions`, `strengths`               |
| `QualityCheckResult` | Quality gate scoring              | `score` (0–10), `reasoning`, `improvements`                                                    |

### Diff & Report Models

| Model              | Purpose                               | Key Fields                                                                                                                                                                                                           |
| ------------------ | ------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `CVDiff`           | Structural diff original vs. tailored | `summary_changed`, `skills_reordered`, `skills_deprioritized`, `experience_changes`, `sections_modified`                                                                                                             |
| `ExperienceChange` | Per-role bullet changes               | `role`, `company`, `bullets_rephrased`, `bullets_unchanged`                                                                                                                                                          |
| `GapAnalysis`      | Skill/keyword gap metrics             | `missing_hard_skills`, `missing_soft_skills`, `covered_keywords`, `missing_keywords`, `keyword_coverage_percent`                                                                                                     |
| `FinalReport`      | Complete self-review output           | `job_title`, `company_name`, `overall_recommendation` (Strong/Partial/Weak Match), `match_score` (0–100), `what_changed`, `gaps`, `suggestions_to_strengthen`, `audit_summary`, `recommendation_rationale`, `passed` |

### Scraping Model

| Model               | Purpose                                                                      |
| ------------------- | ---------------------------------------------------------------------------- |
| `ScrapedJobPosting` | Scraped job content: `url`, `markdown`, `source_text`, `extraction_strategy` |

### Workflow Result

`ResumeTailorResult` (in `models/workflow.py`): `company_name`, `job_title`, `tailored_resume` (JSON string), `audit_report` (dict), `passed`, `final_report` (optional `FinalReport`)

---

## Data Flow

```
1. CLI (main.py)
   ├── Reads resume file → converts DOCX/PDF to Markdown via InputConverterRegistry
   ├── Scrapes job URL via job_scraper_agent → job_posting_markdown
   └── ResumeMemoryService.aresolve_original_resume (hash-based cache check)
       └── Pre-parsed CV if cache hit, None if miss

2. ResumeTailorWorkflow.run()
   ├── PARSING_RESUME: markdown → resume_parser_agent → CV JSON
   │   └── If pre_parsed_cv provided, skip AI parsing
   ├── ANALYZING_JOB: job markdown → analyst_agent → JobAnalysis JSON
   ├── WRITING_CV: CV + JobAnalysis → writer_agent → tailored CV JSON
   │   └── REVIEWING_CV: tailored CV → reviewer_agent → ReviewResult
   │       └── If needs_improvement: writer_agent refines (up to 3 iterations)
   ├── AUDITING_CV: original CV + tailored CV → auditor_agent → AuditResult
   │   └── If failed: retry WRITING → REVIEWING → AUDITING (up to 3 write attempts)
   └── GENERATING_REPORT:
       ├── compute_cv_diff(original, tailored) → CVDiff (pure Python, no LLM)
       ├── compute_gap_analysis(original, tailored, job) → GapAnalysis (pure Python)
       └── report_agent: diff + gaps + audit + review → narrative fields
           └── Workflow assembles FinalReport from narrative + computed data

3. CLI post-processing
   ├── If passed: generate_resume → .md + .pdf + .docx output files
   ├── generate_report_markdown → _report.md
   ├── Files saved to output/{company_name}-{job_title}/
   └── Memory: ResumeMemoryService.save_tailored_resume → SQLite
```

### Key Data Flow Design Decisions

- **CVDiff and GapAnalysis are computed in pure Python** (`cv_diff.py`), not by any LLM agent. This ensures deterministic diff and gap metrics.
- **The report_agent only produces narrative fields** (recommendation, match_score, suggestions, audit_summary, rationale). The workflow assembles the `FinalReport` by combining the narrative with the pre-computed `CVDiff` and `GapAnalysis`.
- **The Report phase always runs**, even when audit fails or the writer produces no output. This ensures the user always gets feedback.
- **Content-hash-based caching** in `ResumeMemoryService`: if the resume file content hash matches a previously parsed version AND the parser version matches, the cached `CV` is reused, skipping AI parsing entirely.

---

## Quality Gate System

### Architecture

- **Shared validator**: A single `quality_gate_agent` scores all gated agents' output, not per-agent custom validation code.
- **Decorator pattern**: Each quality-gated agent has an `@output_validator` async function that calls the quality gate.
- **Threshold**: Score ≥ 9 = pass. Score < 9 = raise `ModelRetry` with improvements.
- **Fallback**: `_QualityState` per-agent holds `last_output`. On `UnexpectedModelBehavior` (retries exhausted), the fallback is used.
- **Retry counts**: Quality gate itself has `retries=2`. Pipeline agents have `retries=5`. Job scraper has `retries=3`.

### Gated Agents

| Agent                       | Validator Function              | Fallback State |
| --------------------------- | ------------------------------- | -------------- |
| `resume_parser_agent`       | `_validate_resume_parser`       | `_parser_qs`   |
| `analyst_agent`             | `_validate_analyst`             | `_analyst_qs`  |
| `writer_agent`              | `_validate_writer`              | `_writer_qs`   |
| `auditor_agent`             | `_validate_auditor`             | `_auditor_qs`  |
| `cover_letter_writer_agent` | `_validate_cover_letter_writer` | `_cover_qs`    |

### Ungated Agents

- `reviewer_agent` — Output drives refinement loop; quality is implicitly validated by the auditor later.
- `report_agent` — Produces narrative; factual data is computed deterministically.
- `job_scraper_agent` — Uses `validate_extraction` tool instead of quality gate.

### Scoring Criteria by Role

| Role                | Criteria                                                                          |
| ------------------- | --------------------------------------------------------------------------------- |
| Resume Parser       | Completeness, no data loss, correctly structured fields                           |
| Job Analyst         | Keyword coverage, clear requirement identification, no omissions                  |
| CV Writer           | No hallucinations, ATS keywords naturally incorporated, human tone, no clichés    |
| Auditor             | Thorough hallucination check, specific cliché identification, actionable feedback |
| Cover Letter Writer | Authentic human voice, no AI clichés, specific to role, concise                   |

---

## Memory Layer

```
resume_tailorator/memory/
├── models.py          # Data classes: ResolvedOriginalResume, TailoredResumeRecord, etc.
├── repository.py      # Abstract interface: ResumeMemoryRepository
├── sqlite_repository.py  # SQLite implementation
├── parser.py          # PydanticAIResumeParser (adapter over resume_parser_agent)
└── service.py         # ResumeMemoryService — single entry point for CLI
```

### Key Behaviors

- **Database**: SQLite at `files/resume_memory.sqlite3`
- **Content-hash caching**: `ResumeMemoryService.resolve_original_resume()` hashes the resume file content. If the hash matches a previously parsed version AND the parser version matches, the stored `CV` JSON is deserialized directly — no AI call.
- **Two variants**: `resolve_original_resume` (sync) and `aresolve_original_resume` (async). The CLI uses the async variant since it runs under `asyncio`.
- **Source tracking**: Every resume source is stored with its absolute path and content hash. Multiple tailored resumes can link back to the same source.
- **Job fingerprint**: Each tailored resume is keyed by a truncated SHA-256 hash (first 32 hex chars) of `{job_url}:{job_title}` to avoid duplicates for the same job.

---

## Tools Layer

```
resume_tailorator/tools/
├── playwright.py         # read_job_content_file — agent tool for file-based job content
└── job_scraper_helpers.py # parse_html_with_markitdown, parse_html_with_html2text,
                           # detect_placeholder_content, clean_job_posting_markdown
```

### Job Scraper Architecture

- `fetch_webpage(url, timeout)`: Playwright (headless Chromium) → raw HTML
- `parse_html_with_markitdown(html)`: Primary parser via `markitdown` library
- `parse_html_with_html2text(html)`: Fallback parser via `html2text` library
- `detect_placeholder_content(text)`: Validates extracted content isn't error/placeholder (checks for `<script` tags, "click here", "error loading", "404", minimum 100 chars)
- `clean_job_posting_markdown(markdown)`: Normalizes whitespace, collapses blank lines

---

## Utils Layer

```
resume_tailorator/utils/
├── cv_diff.py              # Pure Python CVDiff + GapAnalysis (no LLM calls)
├── markdown_writer.py      # generate_resume (.md/.pdf/.docx), generate_report_markdown
├── resume_converter.py     # InputConverterRegistry: DOCX/PDF → Markdown via markitdown
├── resume_output_converter.py  # Output format conversion utilities
├── pdf_converter.py        # PDF creation helpers
└── validate_inputs.py      # Standalone input validation (not used by Typer CLI)
```

---

## CLI

Entry point: `resume_tailorator/main.py` — Typer app, console script `resume-tailor`

### Subcommands

#### `tailor` — Full workflow

```
uv run resume-tailor tailor JOB_URL RESUME_PATH [OPTIONS]
```

| Option                  | Type | Default                      | Description                                                       |
| ----------------------- | ---- | ---------------------------- | ----------------------------------------------------------------- |
| `--output-dir`          | PATH | `./output`                   | Output directory                                                  |
| `--model`               | TEXT | `None`                       | LLM provider:model override (e.g., `anthropic:claude-sonnet-4-5`) |
| `--verbose` / `-v`      | FLAG | `False`                      | Stream agent thinking in real-time                                |
| `--debug` / `-d`        | FLAG | `False`                      | Save converted resume, show content hashes                        |
| `--output-pattern`      | TEXT | `{company_name}-{job_title}` | Subdirectory name template                                        |
| `--resume-name-pattern` | TEXT | `{company_name}-{full_name}` | Resume file base name template                                    |

Template variables: `{company_name}`, `{job_title}`, `{full_name}`, `{timestamp}`

#### `re-tailor` — Re-run with audit feedback

```
uv run resume-tailor re-tailor JOB_ID RECOMMENDATIONS [OPTIONS]
```

All options from `tailor` plus:

| Option          | Type | Default | Description                               |
| --------------- | ---- | ------- | ----------------------------------------- |
| `--resume-path` | TEXT | `None`  | Resume path (uses stored path if omitted) |

**Edge case**: When the original resume file no longer exists on disk but a source record is stored, the CLI prints an error and instructs the user to re-provide `--resume-path`.

### Execution Flow

Both commands are synchronous wrappers (`def`) that call `asyncio.run()` on async implementation functions:

- `tailor` → `asyncio.run(_tailor_impl(...))`
- `re_tailor` → `asyncio.run(_re_tailor_impl(...))`

---

## Technology Stack

| Component         | Technology      | Version Constraint |
| ----------------- | --------------- | ------------------ |
| Language          | Python          | ≥ 3.13             |
| Package manager   | uv              | latest             |
| Agent framework   | pydantic-ai     | ≥ 1.24.0           |
| Data validation   | Pydantic v2     | (via pydantic-ai)  |
| CLI framework     | Typer           | ≥ 0.25.1           |
| Web scraping      | Playwright      | ≥ 1.56.0           |
| HTML→Markdown     | html2text       | ≥ 2025.4.15        |
| DOCX/PDF→Markdown | markitdown      | ≥ 0.1.0            |
| Markdown→PDF      | markdown-pdf    | ≥ 1.10             |
| DOCX generation   | python-docx     | ≥ 1.1.0            |
| Rich output       | rich            | ≥ 14.2.0           |
| Memory            | SQLite (stdlib) | —                  |
| Linting           | ruff            | ≥ 0.14.6 (dev)     |
| Testing           | pytest          | ≥ 8.0.0 (dev)      |
| Releases          | commitizen      | ≥ 4.15.1 (dev)     |
| Build backend     | hatchling       | —                  |

---

## Key Design Decisions

1. **Shared Quality Gate**: One `quality_gate_agent` validates all pipeline agents via role-specific scoring criteria, rather than per-agent custom validation code.

2. **Pure Python Diffs**: `CVDiff` and `GapAnalysis` are computed deterministically in `cv_diff.py` — no LLM involved. The report agent only produces narrative.

3. **Always-Run Report Phase**: The Report phase executes regardless of audit pass/fail, ensuring users always get actionable feedback.

4. **Content-Hash Caching**: `ResumeMemoryService` caches parsed CVs by content hash + parser version. If the resume hasn't changed, AI parsing is skipped entirely.

5. **Fallback State Pattern**: Each quality-gated agent stores its `last_output` in a module-level `_QualityState` instance. On quality gate exhaustion, the fallback is used rather than crashing.

6. **Inner Loop with Outer Retry**: The Write → Review refinement loop (up to 3 iterations) is nested inside the Write → Audit retry loop (up to 3 attempts). This allows both fine-tuning and broader corrections.

7. **Job Fingerprint Dedup**: Tailored resumes are keyed by a truncated SHA-256 fingerprint (first 32 hex chars of `{job_url}:{job_title}`), preventing duplicate entries for the same job applied multiple times.

8. **Pre-Parsed CV Bypass**: The workflow accepts an optional `pre_parsed_cv` parameter. When provided (from cache), the Resume Parser stage is skipped entirely, saving AI calls.

9. **Streaming via Verbose Mode**: `run_agent()` has a `verbose` flag that streams `TextPartDelta` and `ThinkingPartDelta` events to console via Rich.

10. **CLI runs under asyncio**: All async implementation functions use `asyncio.run()` from synchronous Typer command wrappers.
