# Typer CLI Design Specification

**Date:** 2026-04-24  
**Status:** Ready for Implementation  
**Scope:** Convert Resume Tailorator CLI from argparse to Typer with improved help text and interactive prompts

---

## Executive Summary

Resume Tailorator currently uses basic `argparse` for CLI argument handling. This specification outlines a modernization to **Typer**, a modern Python CLI framework that provides:

- **Rich formatted help text** with colors, boxes, and organized sections
- **Interactive prompts** for missing required options
- **Modular command structure** for future expansion
- **Global options** for cross-cutting concerns like debug logging
- **Better user experience** with clearer error messages and defaults

The new CLI will maintain backward compatibility with existing workflows while providing a significantly improved user experience.

---

## 1. Architecture & File Structure

### Current State
```
resume_tailorator/
├── main.py                         # Entry point (runs workflow)
├── utils/
│   ├── validate_inputs.py          # CLI argument parsing (argparse)
│   ├── logging_config.py           # Logging configuration
│   └── ...
└── workflows/
    └── agents.py                   # Core workflow logic
```

### Desired State
```
resume_tailorator/
├── cli/                            # NEW: All CLI logic
│   ├── __init__.py                 # CLI package init
│   ├── main.py                     # Typer app instance + global options
│   ├── commands/
│   │   ├── __init__.py
│   │   ├── tailor.py              # Main workflow command (default)
│   │   ├── docs.py                # Documentation sub-command
│   │   └── debug.py               # Debug info sub-command
│   └── utils.py                   # CLI helpers (prompts, validation, formatting)
├── main.py                         # MODIFIED: Import from CLI, keep core logic
├── utils/
│   ├── validate_inputs.py          # DEPRECATED: Logic moved to cli/
│   ├── logging_config.py           # UNCHANGED: Logging configuration
│   └── ...
└── workflows/
    └── agents.py                   # UNCHANGED: Core workflow logic
```

### Design Rationale

**Separation of concerns:**
- `cli/` module: handles user interaction, argument parsing, help formatting
- `main.py`: orchestrates CLI and core workflow
- `workflows/`: contains pure business logic (unchanged)
- `utils/logging_config.py`: cross-cutting concern, used by both CLI and core

**Benefits:**
- CLI logic isolated and testable
- Easy to extend with new commands
- Core workflow logic remains pure and reusable
- Clear dependency direction: CLI → Core Logic

---

## 2. Command Structure

### 2.1 Global Options

Global options are available to all commands and processed first:

```bash
resume-tailorator [GLOBAL_OPTIONS] [COMMAND] [COMMAND_OPTIONS]
```

**Global Options:**

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--debug` / `--no-debug` | Boolean | `--no-debug` | Enable DEBUG logging level (shows detailed info from all modules) |
| `--config` | Path | None | Path to configuration file (reserved for future use) |
| `--help` | Flag | N/A | Show help and exit |
| `--version` | Flag | N/A | Show version and exit (optional) |

**Implementation:**
- Global options handled via Typer callback decorator
- Callback runs before any command, sets up logging/config
- Available to all sub-commands via context or shared state

---

### 2.2 Commands

#### **Main Command: `tailor` (Default)**

**Purpose:** Tailor resume to a specific job posting

**Usage:**
```bash
resume-tailorator tailor [OPTIONS]
resume-tailorator [OPTIONS]  # Default if no command specified
```

**Options:**

| Option | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| `--resume-path` | Path | No | None | Path to resume file (Markdown). Interactive prompt if omitted. |
| `--job-url` | URL | No | None | URL of job posting to scrape. Interactive prompt if omitted. |
| `--output` | Choice (repeatable) | No | `md` | Output format(s): `md`, `pdf`, `docx`. Can be used multiple times. |

**Examples:**
```bash
# Interactive mode (no options provided)
$ resume-tailorator
Resume Path [files/resume.md]: 
Job URL: 
Output Format [md]: pdf docx

# Explicit options
$ resume-tailorator tailor --resume-path resume.md --job-url https://... --output pdf

# With global options
$ resume-tailorator --debug tailor --output pdf --output docx

# Shorthand (default command)
$ resume-tailorator --resume-path resume.md --job-url https://...
```

**Flow:**
1. Parse all options
2. Check which options are missing
3. For each missing required option, prompt interactively
4. Validate all inputs (file exists, URL format, output formats)
5. Set log level based on `--debug` flag
6. Execute core workflow
7. Display results with output format summary

---

#### **Sub-command: `docs`**

**Purpose:** Show usage documentation and examples

**Usage:**
```bash
resume-tailorator docs [OPTIONS]
```

**Options:**
None (inherits global options only)

**Behavior:**
- Display formatted documentation in terminal
- Show example commands
- Show environment setup tips
- Show troubleshooting guide

---

#### **Sub-command: `debug`**

**Purpose:** Show debug information and verify setup

**Usage:**
```bash
resume-tailorator debug [OPTIONS]
```

**Options:**
None (inherits global options only)

**Behavior:**
- Display Python version and environment info
- Display Typer version, dependencies versions
- Show logging configuration
- Test importing all critical modules
- Verify file access (files/ directory, resume.md if exists)
- Display current log level and `--debug` effect

---

### 2.3 Help Text Examples

**Main help:**
```
 Usage: resume-tailorator [OPTIONS] COMMAND [ARGS]...

 Tailor your resume to match specific job postings using AI analysis.

 ╭─ Global Options ──────────────────────────────────────────────────╮
 │ --debug               Enable DEBUG logging (detailed output)         │
 │ --no-debug            Disable debug logging [default]               │
 │ --config TEXT         Path to config file [optional, future use]    │
 │ --help                Show this message and exit.                   │
 │ --version             Show version and exit.                        │
 ╰───────────────────────────────────────────────────────────────────╯

 ╭─ Commands ────────────────────────────────────────────────────────╮
 │ tailor              Tailor resume to a job posting [default]        │
 │ docs                Show usage documentation and examples           │
 │ debug               Show debug info and verify setup                │
 ╰───────────────────────────────────────────────────────────────────╯

 Use 'resume-tailorator COMMAND --help' for more info on a command.
```

**Tailor command help:**
```
 Usage: resume-tailorator tailor [OPTIONS]

 Tailor your resume to match a specific job posting.

 This command will:
 1. Read your resume from the provided path
 2. Scrape and analyze the job posting from the URL
 3. Generate a tailored version matching the job requirements
 4. Save output in requested format(s)

 ╭─ Options ─────────────────────────────────────────────────────────╮
 │ --resume-path TEXT                Path to resume (Markdown)        │
 │                                   Will prompt if omitted.           │
 │ --job-url TEXT                    URL of job posting to scrape      │
 │                                   Will prompt if omitted.           │
 │ --output [md|pdf|docx]            Output format(s) [default: md]   │
 │                                   Repeatable: --output pdf --output docx │
 │ --help                            Show this message and exit.       │
 ╰───────────────────────────────────────────────────────────────────╯

 Examples:
   # Interactive mode (will prompt for missing options)
   $ resume-tailorator tailor

   # Explicit options
   $ resume-tailorator tailor --resume-path resume.md \\
       --job-url https://example.com/job --output pdf --output docx

   # With debug logging
   $ resume-tailorator --debug tailor --output pdf
```

---

## 3. Interactive Flow & User Experience

### 3.1 Interactive Prompt Flow

**Scenario 1: User runs with no options**
```bash
$ resume-tailorator

Resume Path [files/resume.md]: 
Job URL: https://example.com/job
Output Format [md]: pdf docx

✅ Inputs validated successfully
🚀 Starting Resume Tailorator workflow...
```

**Scenario 2: User provides resume-path, prompts for job-url**
```bash
$ resume-tailorator --resume-path my-resume.md

Job URL: https://example.com/job
Output Format [md]: 

✅ Inputs validated successfully
🚀 Starting Resume Tailorator workflow...
```

**Scenario 3: Invalid input during prompt**
```bash
$ resume-tailorator

Resume Path [files/resume.md]: /nonexistent/path.md
❌ Error: File not found at '/nonexistent/path.md'
Resume Path [files/resume.md]: resume.md

Job URL: not-a-url
❌ Error: URL must start with http:// or https://
Job URL: https://example.com/job

Output Format [md]: invalid
❌ Error: Output format must be one of: md, pdf, docx
Output Format [md]: pdf

✅ Inputs validated successfully
🚀 Starting Resume Tailorator workflow...
```

### 3.2 Validation Rules

| Input | Rule | Error Message |
|-------|------|---------------|
| `--resume-path` | File must exist | "File not found at {path}" |
| `--job-url` | Must start with http:// or https:// | "URL must start with http:// or https://" |
| `--output` | Each value must be md, pdf, or docx (case-insensitive) | "Output format must be one of: md, pdf, docx" |

---

## 4. Implementation Details

### 4.1 Typer Structure

**File: `cli/main.py`**
```python
import typer
from typing import Optional, List
from cli.commands import tailor, docs, debug

app = typer.Typer(
    name="resume-tailorator",
    help="Tailor your resume to match specific job postings using AI analysis.",
    rich_markup_mode="rich"  # Enable rich formatting in help
)

@app.callback()
def global_options(
    debug: bool = typer.Option(False, "--debug/--no-debug", help="Enable debug logging"),
    config: Optional[str] = typer.Option(None, "--config", help="Path to config file")
):
    """Global options callback - runs before any command."""
    # Set up logging based on --debug flag
    # Load config if provided
    pass

# Add commands
app.command()(tailor.tailor)
app.command()(docs.docs)
app.command()(debug.debug)

if __name__ == "__main__":
    app()
```

**File: `cli/commands/tailor.py`**
```python
import typer
from typing import Optional, List

def tailor(
    resume_path: Optional[str] = typer.Option(
        None,
        "--resume-path",
        help="Path to your resume (Markdown). Will prompt if omitted."
    ),
    job_url: Optional[str] = typer.Option(
        None,
        "--job-url",
        help="URL of job posting to scrape and analyze."
    ),
    output: List[str] = typer.Option(
        ["md"],
        "--output",
        help="Output format(s): md, pdf, docx. Repeatable."
    )
):
    """
    Tailor your resume to match a specific job posting.
    
    This command will:
    1. Read your resume from the provided path
    2. Scrape and analyze the job posting from the URL
    3. Generate a tailored version matching the job requirements
    4. Save output in requested format(s)
    
    Examples:
        resume-tailorator tailor --resume-path resume.md \\
            --job-url https://example.com/job --output pdf --output docx
    """
    # Implementation
    pass
```

### 4.2 Dependencies

Add to `pyproject.toml`:
```toml
dependencies = [
    ...existing deps...,
    "typer[all]>=0.12.0",  # Includes rich for formatting
]
```

`typer[all]` includes:
- `typer` (CLI framework)
- `rich` (formatting and progress bars)
- `shellingham` (shell detection for completion)

### 4.3 Entry Point

Update or create `pyproject.toml` scripts section:
```toml
[project.scripts]
resume-tailorator = "cli.main:app"
```

This allows:
```bash
$ resume-tailorator --help
$ resume-tailorator tailor --help
```

### 4.4 Core Logic Layer

**File: `main.py` (Modified)**

Keep existing core logic intact. Modify only the entry point:

```python
# OLD APPROACH (current)
if __name__ == "__main__":
    # Parse args, run workflow

# NEW APPROACH (with CLI)
from cli.main import app

if __name__ == "__main__":
    app()  # Typer handles everything
```

The core workflow logic stays the same, CLI layer is thin and focused on:
- Parsing arguments
- Interactive prompts
- Input validation
- Logging setup
- Presenting results

---

## 5. Error Handling & Edge Cases

### 5.1 Validation Errors

**File not found:**
```
Resume Path: /nonexistent.md
❌ Error: Resume file not found at '/nonexistent.md'
Resume Path [files/resume.md]: 
```

**Invalid URL:**
```
Job URL: just-text
❌ Error: Job URL must start with http:// or https://
Job URL: 
```

**Invalid output format:**
```
Output Format: txt
❌ Error: Output format must be one of: md, pdf, docx
Output Format [md]: 
```

### 5.2 Core Workflow Errors

Errors from the core workflow (workflow failure, OpenAI timeout, etc.) are caught and displayed with helpful context:
```
❌ Workflow failed: {error_message}
💡 Tip: Run with --debug for more details
```

---

## 6. Testing Strategy

### 6.1 CLI Tests

Test cases for each command:
- ✅ All options provided
- ✅ Missing options, interactive prompts succeed
- ✅ Invalid option values, validation fails
- ✅ `--debug` flag enables DEBUG logging
- ✅ `--help` shows proper formatting
- ✅ Sub-commands (docs, debug) execute without error

### 6.2 Integration Tests

- ✅ Full flow: no options → prompt → validate → execute
- ✅ Multiple output formats: `--output pdf --output docx`
- ✅ Global options propagate to sub-commands
- ✅ Help text is readable and complete

---

## 7. Migration Plan

### Phase 1: Create CLI Module
- Create `cli/` directory structure
- Implement Typer app and commands
- Copy validation logic from `validate_inputs.py`

### Phase 2: Update Entry Point
- Update `main.py` to use `cli.main:app`
- Update `Makefile` to call new entry point

### Phase 3: Testing & Verification
- Run all existing tests
- Test new CLI manually
- Test help text formatting

### Phase 4: Deprecation
- Keep `utils/validate_inputs.py` for backward compatibility
- Mark as deprecated in docstring
- Can remove in future release

---

## 8. Success Criteria

✅ **Users can run CLI with excellent help text**
```bash
$ resume-tailorator --help
$ resume-tailorator tailor --help
```

✅ **Interactive prompts work for missing required options**
```bash
$ resume-tailorator  # Prompts for resume-path and job-url
```

✅ **Options can be specified explicitly**
```bash
$ resume-tailorator --resume-path resume.md --job-url https://... --output pdf
```

✅ **Global `--debug` flag enables detailed logging**
```bash
$ resume-tailorator --debug tailor
```

✅ **Sub-commands work and show help**
```bash
$ resume-tailorator docs
$ resume-tailorator debug --help
```

✅ **Existing tests pass**
- No regression in core workflow functionality
- New CLI tests added

✅ **Help text is clear, formatted, and helpful**
- Uses rich formatting (colors, boxes)
- Includes examples
- Shows all options clearly

---

## 9. Future Extensions

This design allows for easy future additions:
- `resume-tailorator config set` — Configure defaults
- `resume-tailorator templates` — Show available output templates
- `resume-tailorator history` — Show past tailoring jobs
- `resume-tailorator watch` — Continuous mode for job hunting
- Shell completion: `resume-tailorator --install-completion`

---

## 10. References

- **Typer Documentation:** https://typer.tiangolo.com/
- **Rich Documentation:** https://rich.readthedocs.io/
- **Current CLI Code:** `utils/validate_inputs.py`
- **Entry Point:** `main.py`

