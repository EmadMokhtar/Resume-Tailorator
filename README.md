#  📄 Resume Tailorator

![cover](./cover.png)

Resume Tailorator is a multi-agent AI system that analyzes job postings and tailors your resume to match specific job requirements. It ensures authenticity, avoids AI clichés, and optimizes for Applicant Tracking Systems (ATS).

## 🚀 Features

- **Multi-Agent Architecture**: 6 pipeline stages with dedicated agents for analysis, writing, and quality assurance.
- **Automated Job Scraping**: Fetches job posting content from any public URL using Playwright.
- **Resume Memory**: Stores your original resume plus job-specific tailored outputs in SQLite.
- **Authentic Tailoring**: Rephrases your experience to match the job without inventing skills.
- **Hallucination & Cliché Detection**: Built-in auditor to ensure quality and "human" tone.
- **Quality Gate Validators**: Each agent's output is scored 0–10 by a quality gate before the pipeline proceeds.
- **Comprehensive Reporting**: Generates self-review reports with gaps analysis, suggestions, and recommendations.
- **Self-Correcting Workflow**: Write → Review → Audit loop with retries and quality feedback (up to 3 write attempts).
- **Re-Tailoring**: Re-run tailoring on a saved job with recommendations from a prior audit (`re_tailor` command).

## 🛠️ Architecture

The system runs a sequential pipeline of 6 stages:

1.  **Resume Parser**: Parses your resume (Markdown, DOCX, or PDF) into structured data → Quality gate validates parsing
2.  **Job Analyst**: Extracts structured job requirements (title, company, skills, keywords) → Quality gate validates extraction
3.  **CV Writer**: Tailors the CV to match job requirements → Quality gate validates tailoring
4.  **Reviewer**: Scores CV quality and suggests improvements; triggers refinement loop
5.  **Auditor**: Validates for hallucinations and AI clichés → Quality gate validates audit quality
6.  **Report Generator**: Compiles a self-review report with CVDiff, gap analysis, and recommendations

**Quality Gate System**: Each agent has a built-in validator that checks output quality (scored 0–10). If quality is insufficient (score < 9), the agent retries with corrective feedback. On quality gate exhaustion, the system falls back to the last available output.

**Write → Review → Audit Loop**: After the initial write, the reviewer scores the draft and suggests refinements. Once review iterations are exhausted, the auditor checks for hallucinations. If the audit fails, the entire write → review → audit loop retries (up to 3 write attempts).

## 📋 Prerequisites

- **Python 3.13+**
- **[uv](https://github.com/astral-sh/uv)** (Fast Python package installer and resolver)
- **OpenAI API Key** (or compatible LLM provider configured in environment)

## 📦 Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/EmadMokhtar/resume_tailorator
    cd resume_tailorator
    ```

2.  **Install dependencies**:
    This project uses `uv` for dependency management.
    ```bash
    uv sync
    ```

3.  **Set up Environment Variables**:
    Export your OpenAI API key:
    ```bash
    export OPENAI_API_KEY=your_api_key_here
    ```

## 🏃 Usage

The CLI uses **positional arguments** (not interactive prompts). Two commands are available:

### `tailor` — Run the full workflow

```bash
uv run resume-tailor tailor <JOB_URL> <RESUME_PATH> [OPTIONS]
```

**Arguments:**
- `JOB_URL` — URL of the job posting (must start with `http://` or `https://`)
- `RESUME_PATH` — Path to your resume (`.md`, `.docx`, or `.pdf`)

**Options:**
- `--output-dir PATH` — Output directory (default: `./output`)
- `--model MODEL` — AI model override (default: `openai:gpt-5-mini`)

### Example

```bash
uv run resume-tailor tailor \
  https://www.linkedin.com/jobs/view/12345678 \
  /Users/me/resume.md \
  --model openai:gpt-4o-mini
```

### `re_tailor` — Re-run with feedback from a prior audit

```bash
uv run resume-tailor re_tailor <JOB_ID> <RECOMMENDATIONS> [OPTIONS]
```

**Arguments:**
- `JOB_ID` — UUID of the prior job (shown in output after a `tailor` run)
- `RECOMMENDATIONS` — Comments or recommendations from the prior audit report

**Options:**
- `--resume-path PATH` — Resume path (uses the stored path from the prior job if omitted)
- `--output-dir PATH` — Output directory (default: `./output`)
- `--model MODEL` — AI model override

### Example

```bash
uv run resume-tailor re_tailor \
  a1b2c3d4-... \
  "Add more emphasis on cloud infrastructure experience" \
  --model openai:gpt-4o-mini
```

### Alternative entry point

You can also invoke the CLI directly:

```bash
uv run python resume_tailorator/main.py tailor <JOB_URL> <RESUME_PATH>
```

### View Results

Upon successful completion, output files are saved in the `output/` directory (or the path specified via `--output-dir`):

*   `tailored_resume_<Company_Name>.md` — Tailored resume in Markdown format
*   `tailored_resume_<Company_Name>.pdf` — Tailored resume in PDF format
*   `tailored_resume_<Company_Name>.docx` — Tailored resume in DOCX format
*   `report_<company_name>.md` — Comprehensive self-review report

## 🧠 Resume Memory Behavior

- The first run requires providing a resume path so the CLI can store your original resume.
- Subsequent runs reuse the latest stored original resume from the SQLite database.
- Every job submission starts from the original resume, never from a previous tailored resume.
- Each successful tailoring run stores the tailored resume and audit result linked back to the original source resume.
- The local memory database lives at `files/resume_memory.sqlite3`.

## 📊 Self-Review Report

Each workflow run generates a **self-review report** that includes:

- **What Changed**: Summary changes, reordered/deprioritized skills, and per-experience bullet rewrites
- **Quality Metrics**: Hallucination score (0–10) and AI cliché score (0–10)
- **Gap Analysis**: Keyword coverage, missing hard/soft skills vs. the job posting
- **Suggestions to Strengthen**: Recommended improvements to better match the job
- **Audit Summary**: Feedback from the auditor on tone, authenticity, and compliance
- **Overall Recommendation**: "Strong Match", "Partial Match", or "Weak Match"
- **Match Score**: 0–100 score based on keyword coverage and gap severity

## ✅ Quality Gate System

The system includes built-in quality validation for every agent:

- **Validation Threshold**: Each agent's output must score 9/10 or higher to proceed
- **Automatic Retry**: If validation fails, the agent receives corrective feedback and retries (up to 2 retries)
- **Graceful Fallback**: On quality gate exhaustion, the system uses the last available output instead of failing fatally
- **Token Usage Tracking**: All validation runs are included in usage metrics for accurate cost tracking

## 🛠️ Make Commands

| Command            | Description                                          |
|--------------------|------------------------------------------------------|
| `make help`        | Show available commands and descriptions.            |
| `make install`     | Install production dependencies using `uv`.           |
| `make install/dev` | Install development dependencies using `uv`.          |
| `make test`        | Run the full test suite using `pytest`.               |
| `make install/uv`  | Ensure `uv` is installed (auto-run by other targets). |

> **Note:** The `make run` target is deprecated and uses outdated paths. Use `uv run resume-tailor tailor <JOB_URL> <RESUME_PATH>` instead.

## 📂 Project Structure

```
resume_tailorator/
├── resume_tailorator/       # Main Python package
│   ├── main.py              # CLI entry point (Typer: tailor + re_tailor)
│   ├── workflows/           # Workflow orchestration and agent definitions
│   ├── models/              # Pydantic data models (agents, workflow)
│   ├── memory/              # SQLite-backed memory (parser, repository, service)
│   ├── tools/               # Playwright scraping, HTML parsing helpers
│   └── utils/               # Markdown writer, resume conversion, CV diff
├── tests/                   # Test suite
├── output/                  # Default output directory for generated files
├── Makefile                 # Command shortcuts
├── pyproject.toml           # Project configuration and dependencies
└── README.md                # This file
```

## 🛡️ Safety & Quality

- **Anti-Hallucination**: The system is strictly instructed never to invent skills or experiences.
- **Cliché Filter**: Avoids terms like "spearheaded", "synergy", "leveraged", and "game-changer".
- **Multi-Layer Validation**: Quality gates score every agent output; auditor cross-checks final CV against the original.

## 🤝 Contributing

Contributions are welcome! Please ensure you follow the coding guidelines and add tests for new features.
