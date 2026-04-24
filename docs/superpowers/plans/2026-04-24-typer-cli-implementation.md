# Typer CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert Resume Tailorator CLI from argparse to Typer with interactive prompts, global options, and rich formatted help text.

**Architecture:** Create a new `cli/` module that encapsulates all CLI logic while keeping core workflow logic in `main.py` and `workflows/`. Use Typer's decorator-based command structure with callback for global options. Interactive prompts fallback for missing required inputs.

**Tech Stack:** Typer (CLI framework), Rich (formatting), current Python 3.13+

---

## File Structure

```
resume_tailorator/
├── cli/                           # NEW: CLI module
│   ├── __init__.py                # Package init
│   ├── main.py                    # Typer app + global options callback
│   ├── commands/
│   │   ├── __init__.py
│   │   ├── tailor.py              # Main workflow command
│   │   ├── docs.py                # Documentation command
│   │   └── debug.py               # Debug info command
│   └── utils.py                   # Validation, prompts, helpers
├── main.py                        # MODIFIED: Import from cli.main
├── pyproject.toml                 # MODIFIED: Add typer[all] dependency
└── tests/
    └── cli/                       # NEW: CLI tests
        ├── test_app.py
        ├── test_commands.py
        └── test_utils.py
```

---

## Phase 1: Setup & Dependencies

### Task 1: Add Typer Dependency

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Open pyproject.toml and locate dependencies section**

- [ ] **Step 2: Add typer[all] to dependencies**

Replace the dependencies section:
```toml
dependencies = [
    "aiofiles>=25.1.0",
    "html2text>=2025.4.15",
    "markdown>=3.10",
    "markdown-pdf>=1.10",
    "markitdown[docx,pdf]>=0.1.0",
    "playwright>=1.56.0",
    "pydantic-ai>=1.24.0",
    "python-docx>=1.1.0",
    "typer[all]>=0.12.0",
]
```

- [ ] **Step 3: Verify syntax is valid**

Run: `python -m py_compile pyproject.toml` or just check for syntax errors visually

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "build(deps): add typer[all] for CLI framework"
```

---

### Task 2: Create CLI Package Structure

**Files:**
- Create: `cli/__init__.py`
- Create: `cli/commands/__init__.py`

- [ ] **Step 1: Create cli directory**

```bash
mkdir -p /Users/emadmokhtar/Projects/resume_tailorator/cli/commands
```

- [ ] **Step 2: Create cli/__init__.py (empty package marker)**

```python
"""Resume Tailorator CLI module."""
```

- [ ] **Step 3: Create cli/commands/__init__.py (empty package marker)**

```python
"""CLI commands for Resume Tailorator."""
```

- [ ] **Step 4: Verify structure**

```bash
ls -la cli/
ls -la cli/commands/
```

Expected output shows both `__init__.py` files created

- [ ] **Step 5: Commit**

```bash
git add cli/__init__.py cli/commands/__init__.py
git commit -m "build(cli): create cli package structure"
```

---

## Phase 2: Core CLI Infrastructure

### Task 3: Create CLI Utilities Module

**Files:**
- Create: `cli/utils.py`
- Test: `tests/cli/test_utils.py` (write alongside)

- [ ] **Step 1: Create test file first (TDD)**

Create `tests/cli/test_utils.py`:
```python
import pytest
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from cli.utils import validate_resume_path, validate_job_url, validate_output_formats


class TestValidateResumePath:
    def test_valid_existing_file(self, tmp_path):
        """Test validation passes for existing file."""
        test_file = tmp_path / "resume.md"
        test_file.write_text("# Resume\nContent here")
        result = validate_resume_path(str(test_file))
        assert result is None  # No exception raised

    def test_file_not_found(self, tmp_path):
        """Test validation fails for non-existent file."""
        with pytest.raises(ValueError, match="File not found"):
            validate_resume_path(str(tmp_path / "nonexistent.md"))

    def test_empty_file(self, tmp_path):
        """Test validation fails for empty file."""
        test_file = tmp_path / "empty.md"
        test_file.write_text("")
        with pytest.raises(ValueError, match="empty"):
            validate_resume_path(str(test_file))


class TestValidateJobUrl:
    def test_valid_https_url(self):
        """Test validation passes for valid HTTPS URL."""
        result = validate_job_url("https://example.com/job")
        assert result is None  # No exception raised

    def test_valid_http_url(self):
        """Test validation passes for valid HTTP URL."""
        result = validate_job_url("http://example.com/job")
        assert result is None  # No exception raised

    def test_invalid_url_no_protocol(self):
        """Test validation fails for URL without protocol."""
        with pytest.raises(ValueError, match="must start with http"):
            validate_job_url("example.com/job")

    def test_invalid_url_wrong_protocol(self):
        """Test validation fails for URL with wrong protocol."""
        with pytest.raises(ValueError, match="must start with http"):
            validate_job_url("ftp://example.com/job")


class TestValidateOutputFormats:
    def test_valid_single_format(self):
        """Test validation passes for valid single format."""
        result = validate_output_formats(["md"])
        assert result is None

    def test_valid_multiple_formats(self):
        """Test validation passes for valid multiple formats."""
        result = validate_output_formats(["md", "pdf", "docx"])
        assert result is None

    def test_invalid_format(self):
        """Test validation fails for invalid format."""
        with pytest.raises(ValueError, match="must be one of"):
            validate_output_formats(["txt"])

    def test_case_insensitive(self):
        """Test validation accepts case-insensitive formats."""
        result = validate_output_formats(["MD", "PDF", "DOCX"])
        assert result is None

    def test_empty_list(self):
        """Test validation fails for empty list."""
        with pytest.raises(ValueError, match="at least one"):
            validate_output_formats([])
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/emadmokhtar/Projects/resume_tailorator
python -m pytest tests/cli/test_utils.py -v
```

Expected: All tests fail with "ModuleNotFoundError: No module named 'cli.utils'"

- [ ] **Step 3: Create cli/utils.py with implementations**

```python
"""CLI utility functions for validation and prompts."""

from pathlib import Path
from typing import Optional


def validate_resume_path(path: str) -> None:
    """Validate that resume file exists and is not empty.
    
    Args:
        path: Path to resume file.
        
    Raises:
        ValueError: If file doesn't exist or is empty.
    """
    resume_path = Path(path)
    if not resume_path.exists():
        raise ValueError(f"File not found at '{path}'")
    
    content = resume_path.read_text(encoding="utf-8").strip()
    if not content:
        raise ValueError(f"Resume file at '{path}' is empty")


def validate_job_url(url: str) -> None:
    """Validate that job URL has proper format.
    
    Args:
        url: The URL to validate.
        
    Raises:
        ValueError: If URL format is invalid.
    """
    if not url.startswith(("http://", "https://")):
        raise ValueError(
            f"Job URL must start with http:// or https://. Got: {url}"
        )


def validate_output_formats(formats: list[str]) -> None:
    """Validate that output formats are valid.
    
    Args:
        formats: List of output format strings.
        
    Raises:
        ValueError: If any format is invalid or list is empty.
    """
    if not formats:
        raise ValueError("At least one output format must be specified")
    
    valid_formats = {"md", "pdf", "docx"}
    for fmt in formats:
        if fmt.lower() not in valid_formats:
            raise ValueError(
                f"Output format '{fmt}' is invalid. "
                f"Must be one of: {', '.join(sorted(valid_formats))}"
            )


def prompt_for_resume_path(default: str = "files/resume.md") -> str:
    """Prompt user for resume path with validation.
    
    Args:
        default: Default path to show in prompt.
        
    Returns:
        Validated resume path.
    """
    import typer
    
    while True:
        try:
            path = typer.prompt(f"Resume Path", default=default)
            validate_resume_path(path)
            return path
        except ValueError as e:
            typer.echo(f"❌ Error: {e}", err=True)


def prompt_for_job_url() -> str:
    """Prompt user for job URL with validation.
    
    Returns:
        Validated job URL.
    """
    import typer
    
    while True:
        try:
            url = typer.prompt("Job URL")
            validate_job_url(url)
            return url
        except ValueError as e:
            typer.echo(f"❌ Error: {e}", err=True)


def prompt_for_output_formats(default: str = "md") -> list[str]:
    """Prompt user for output formats with validation.
    
    Args:
        default: Default formats as space-separated string (e.g., "md" or "md pdf").
        
    Returns:
        List of validated output formats.
    """
    import typer
    
    while True:
        try:
            formats_str = typer.prompt("Output Format", default=default)
            formats = [fmt.strip() for fmt in formats_str.split()]
            validate_output_formats(formats)
            return formats
        except ValueError as e:
            typer.echo(f"❌ Error: {e}", err=True)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/emadmokhtar/Projects/resume_tailorator
python -m pytest tests/cli/test_utils.py -v
```

Expected: All tests pass

- [ ] **Step 5: Commit**

```bash
git add cli/utils.py tests/cli/test_utils.py
git commit -m "feat(cli): add validation and prompt utilities"
```

---

### Task 4: Create Main CLI App and Global Options

**Files:**
- Create: `cli/main.py`

- [ ] **Step 1: Create cli/main.py with Typer app**

```python
"""Main CLI application for Resume Tailorator."""

import typer
from typing import Optional
from utils.logging_config import configure_root_logger, get_logger

app = typer.Typer(
    name="resume-tailorator",
    help="Tailor your resume to match specific job postings using AI analysis.",
    rich_markup_mode="rich",
    no_args_is_help=False,  # Allow running without args for interactive mode
)

logger = get_logger(__name__)


@app.callback()
def global_options(
    debug: bool = typer.Option(
        False,
        "--debug/--no-debug",
        help="Enable DEBUG logging level (shows detailed information)"
    ),
    config: Optional[str] = typer.Option(
        None,
        "--config",
        help="Path to configuration file (reserved for future use)"
    ),
    ctx: typer.Context = typer.Context(None),
):
    """Global options callback - runs before any command.
    
    Configures logging based on --debug flag and stores config path.
    """
    # Configure root logger based on debug flag
    if debug:
        configure_root_logger(level="DEBUG")
        logger.debug("Debug logging enabled")
    else:
        configure_root_logger(level="INFO")
    
    # Store config in context for subcommands to access
    if ctx.obj is None:
        ctx.obj = {}
    ctx.obj["config_path"] = config
    ctx.obj["debug"] = debug


if __name__ == "__main__":
    app()
```

- [ ] **Step 2: Test that app starts and shows help**

```bash
cd /Users/emadmokhtar/Projects/resume_tailorator
python -m cli.main --help
```

Expected: Shows usage with "resume-tailorator" and mentions "Options" section

- [ ] **Step 3: Test that global options work**

```bash
python -m cli.main --debug --help
```

Expected: Help displayed (--debug consumed but command not yet defined)

- [ ] **Step 4: Commit**

```bash
git add cli/main.py
git commit -m "feat(cli): create main app with global options callback"
```

---

## Phase 3: Implement Commands

### Task 5: Create Tailor Command (Main Workflow)

**Files:**
- Create: `cli/commands/tailor.py`
- Test: `tests/cli/test_commands.py` (create alongside)

- [ ] **Step 1: Create test file first**

Create `tests/cli/test_commands.py`:
```python
import pytest
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from cli.commands.tailor import tailor
from unittest.mock import patch, MagicMock


class TestTailorCommand:
    def test_tailor_with_all_options_provided(self, tmp_path):
        """Test tailor command with all options explicitly provided."""
        # Create a test resume file
        resume_file = tmp_path / "resume.md"
        resume_file.write_text("# My Resume\nContent")
        
        # Mock the core workflow to avoid running it
        with patch("cli.commands.tailor.execute_workflow") as mock_workflow:
            mock_workflow.return_value = None
            
            # Call tailor with all options
            tailor(
                resume_path=str(resume_file),
                job_url="https://example.com/job",
                output=["md", "pdf"]
            )
            
            # Verify workflow was called with correct args
            mock_workflow.assert_called_once()
            call_args = mock_workflow.call_args
            assert str(resume_file) in str(call_args)

    def test_tailor_invalid_resume_path_raises(self, tmp_path):
        """Test tailor raises error for invalid resume path."""
        with pytest.raises(SystemExit):  # typer.echo + sys.exit on error
            tailor(
                resume_path="/nonexistent/resume.md",
                job_url="https://example.com/job",
                output=["md"]
            )

    def test_tailor_invalid_job_url_raises(self, tmp_path):
        """Test tailor raises error for invalid job URL."""
        resume_file = tmp_path / "resume.md"
        resume_file.write_text("# My Resume")
        
        with pytest.raises(SystemExit):
            tailor(
                resume_path=str(resume_file),
                job_url="not-a-url",
                output=["md"]
            )
```

- [ ] **Step 2: Create cli/commands/tailor.py**

```python
"""Tailor command - main workflow."""

from typing import Optional, List
import typer
from pathlib import Path

from cli.utils import (
    validate_resume_path,
    validate_job_url,
    validate_output_formats,
    prompt_for_resume_path,
    prompt_for_job_url,
    prompt_for_output_formats,
)
from utils.logging_config import get_logger

logger = get_logger(__name__)


def execute_workflow(resume_path: str, job_url: str, output_formats: List[str]) -> None:
    """Execute the core resume tailoring workflow.
    
    Args:
        resume_path: Path to resume file.
        job_url: URL of job posting to scrape.
        output_formats: List of output formats (md, pdf, docx).
    """
    # TODO: Import and call actual workflow from workflows/
    # This is a placeholder for integration with existing workflow
    typer.echo(f"✅ Inputs validated successfully")
    typer.echo(f"🚀 Starting Resume Tailorator workflow...")
    typer.echo(f"📄 Resume: {resume_path}")
    typer.echo(f"🔗 Job URL: {job_url}")
    typer.echo(f"📁 Output formats: {', '.join(output_formats)}")


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
    ),
):
    """Tailor your resume to match a specific job posting.
    
    This command will:
    1. Read your resume from the provided path
    2. Scrape and analyze the job posting from the URL
    3. Generate a tailored version matching the job requirements
    4. Save output in requested format(s)
    
    Examples:
        resume-tailorator tailor --resume-path resume.md \\
            --job-url https://example.com/job --output pdf --output docx
    """
    # Prompt for missing required options
    if not resume_path:
        resume_path = prompt_for_resume_path()
    
    if not job_url:
        job_url = prompt_for_job_url()
    
    # Validate all inputs
    try:
        validate_resume_path(resume_path)
        validate_job_url(job_url)
        validate_output_formats(output)
    except ValueError as e:
        typer.echo(f"❌ Error: {e}", err=True)
        raise typer.Exit(1)
    
    logger.info(f"Inputs validated: resume={resume_path}, url={job_url}")
    
    # Execute workflow
    execute_workflow(resume_path, job_url, output)
```

- [ ] **Step 3: Run tests to verify they pass**

```bash
cd /Users/emadmokhtar/Projects/resume_tailorator
python -m pytest tests/cli/test_commands.py::TestTailorCommand -v
```

Expected: Tests pass

- [ ] **Step 4: Commit**

```bash
git add cli/commands/tailor.py tests/cli/test_commands.py
git commit -m "feat(cli): implement tailor command with validation and prompts"
```

---

### Task 6: Create Docs Command

**Files:**
- Create: `cli/commands/docs.py`

- [ ] **Step 1: Create cli/commands/docs.py**

```python
"""Docs command - show usage documentation."""

import typer

from utils.logging_config import get_logger

logger = get_logger(__name__)


def docs():
    """Show usage documentation and examples.
    
    Displays comprehensive help for Resume Tailorator including:
    - Command examples
    - Environment setup tips
    - Troubleshooting guide
    """
    content = """
╭─ Resume Tailorator - Usage Guide ─────────────────────────────────────╮
│                                                                          │
│ QUICK START                                                             │
│ ──────────────────────────────────────────────────────────────────────│
│                                                                         │
│   $ resume-tailorator                                                  │
│   → Interactive mode (prompts for resume path and job URL)            │
│                                                                         │
│   $ resume-tailorator tailor --resume-path resume.md \\               │
│       --job-url https://example.com/job --output pdf                  │
│   → Explicit mode (all options provided)                             │
│                                                                         │
│ GLOBAL OPTIONS                                                         │
│ ──────────────────────────────────────────────────────────────────────│
│                                                                         │
│   --debug              Enable DEBUG logging (shows detailed info)     │
│   --config PATH        Path to config file (future use)              │
│                                                                         │
│ MAIN COMMAND: tailor                                                  │
│ ──────────────────────────────────────────────────────────────────────│
│                                                                         │
│   --resume-path PATH   Path to resume (Markdown)                     │
│   --job-url URL        Job posting URL to scrape                     │
│   --output FORMAT      Output format(s): md, pdf, docx (repeatable)  │
│                                                                         │
│ EXAMPLES                                                              │
│ ──────────────────────────────────────────────────────────────────────│
│                                                                         │
│   Interactive with defaults:                                         │
│   $ resume-tailorator                                                │
│                                                                         │
│   With resume path, prompt for job URL:                             │
│   $ resume-tailorator --resume-path my-resume.md                   │
│                                                                         │
│   Explicit with multiple output formats:                            │
│   $ resume-tailorator --debug \\                                    │
│       --resume-path resume.md \\                                    │
│       --job-url https://example.com/job \\                          │
│       --output md --output pdf --output docx                        │
│                                                                         │
│ SUB-COMMANDS                                                          │
│ ──────────────────────────────────────────────────────────────────────│
│                                                                         │
│   docs                Show this documentation                         │
│   debug               Show debug info and verify setup               │
│                                                                         │
╰──────────────────────────────────────────────────────────────────────╯
    """
    typer.echo(content)
    logger.info("Documentation displayed")
```

- [ ] **Step 2: Test that docs command works**

```bash
cd /Users/emadmokhtar/Projects/resume_tailorator
python -m cli.main docs
```

Expected: Documentation displayed in terminal

- [ ] **Step 3: Commit**

```bash
git add cli/commands/docs.py
git commit -m "feat(cli): implement docs command"
```

---

### Task 7: Create Debug Command

**Files:**
- Create: `cli/commands/debug.py`

- [ ] **Step 1: Create cli/commands/debug.py**

```python
"""Debug command - show debug info and verify setup."""

import typer
import sys
import importlib
from pathlib import Path

from utils.logging_config import get_logger

logger = get_logger(__name__)


def debug():
    """Show debug info and verify setup.
    
    Displays:
    - Python version and environment info
    - Package versions
    - Logging configuration
    - Module imports verification
    - File access verification
    """
    typer.echo("\n" + "=" * 70)
    typer.echo("Resume Tailorator - Debug Information")
    typer.echo("=" * 70)
    
    # Python info
    typer.echo("\n📌 Python Environment:")
    typer.echo(f"   Python version: {sys.version.split()[0]}")
    typer.echo(f"   Platform: {sys.platform}")
    typer.echo(f"   Executable: {sys.executable}")
    
    # Package versions
    typer.echo("\n📦 Key Dependencies:")
    packages = ["typer", "pydantic_ai", "playwright", "markdown"]
    for pkg in packages:
        try:
            mod = importlib.import_module(pkg)
            version = getattr(mod, "__version__", "unknown")
            typer.echo(f"   {pkg}: {version} ✅")
        except ImportError:
            typer.echo(f"   {pkg}: NOT INSTALLED ❌")
    
    # Logging info
    typer.echo("\n🔍 Logging Configuration:")
    import logging
    root_logger = logging.getLogger()
    typer.echo(f"   Root logger level: {logging.getLevelName(root_logger.level)}")
    typer.echo(f"   Handlers: {len(root_logger.handlers)}")
    for i, handler in enumerate(root_logger.handlers):
        typer.echo(f"      {i+1}. {handler.__class__.__name__}")
    
    # Test imports
    typer.echo("\n✨ Module Imports:")
    modules = [
        "cli",
        "cli.main",
        "cli.commands",
        "utils.logging_config",
        "workflows",
    ]
    for mod_name in modules:
        try:
            importlib.import_module(mod_name)
            typer.echo(f"   {mod_name}: ✅")
        except ImportError as e:
            typer.echo(f"   {mod_name}: ❌ {e}")
    
    # File access
    typer.echo("\n📁 File Access:")
    project_root = Path(__file__).parent.parent.parent
    files_to_check = [
        ("Resume example", project_root / "files" / "resume.md"),
        ("Job posting example", project_root / "files" / "job_posting.md"),
    ]
    for name, path in files_to_check:
        if path.exists():
            typer.echo(f"   {name}: ✅ ({path})")
        else:
            typer.echo(f"   {name}: ⚠️  NOT FOUND ({path})")
    
    typer.echo("\n" + "=" * 70)
    typer.echo("✅ Debug info complete\n")
    logger.info("Debug command executed")
```

- [ ] **Step 2: Test that debug command works**

```bash
cd /Users/emadmokhtar/Projects/resume_tailorator
python -m cli.main debug
```

Expected: Debug information displayed

- [ ] **Step 3: Commit**

```bash
git add cli/commands/debug.py
git commit -m "feat(cli): implement debug command"
```

---

## Phase 4: Register Commands and Update Entry Point

### Task 8: Register Commands with App

**Files:**
- Modify: `cli/main.py`

- [ ] **Step 1: Add command imports to cli/main.py**

Add after the existing imports at the top:
```python
from cli.commands import tailor, docs, debug
```

- [ ] **Step 2: Add default command setup to cli/main.py**

Add this after the `global_options` callback function:
```python
# Register sub-commands
app.command(name="docs")(docs.docs)
app.command(name="debug")(debug.debug)

# Make tailor the default command by setting invoke_without_command
# The main app calls tailor if no command is specified
@app.command(name="tailor")
def default_tailor(
    resume_path: Optional[str] = typer.Option(None, "--resume-path"),
    job_url: Optional[str] = typer.Option(None, "--job-url"),
    output: List[str] = typer.Option(["md"], "--output"),
):
    """Tailor your resume to match a specific job posting."""
    tailor.tailor(resume_path=resume_path, job_url=job_url, output=output)
```

Actually, let me fix this approach. Typer commands need proper structure. Replace the entire cli/main.py:

```python
"""Main CLI application for Resume Tailorator."""

from typing import Optional, List
import typer

from cli.commands import tailor as tailor_cmd
from cli.commands import docs as docs_cmd
from cli.commands import debug as debug_cmd
from utils.logging_config import configure_root_logger, get_logger

app = typer.Typer(
    name="resume-tailorator",
    help="Tailor your resume to match specific job postings using AI analysis.",
    rich_markup_mode="rich",
)

logger = get_logger(__name__)


@app.callback(invoke_without_command=True)
def global_options(
    ctx: typer.Context,
    debug: bool = typer.Option(
        False,
        "--debug/--no-debug",
        help="Enable DEBUG logging level (shows detailed information)"
    ),
    config: Optional[str] = typer.Option(
        None,
        "--config",
        help="Path to configuration file (reserved for future use)"
    ),
):
    """Global options callback - runs before any command.
    
    Configures logging based on --debug flag and stores config path.
    """
    # Configure root logger based on debug flag
    if debug:
        configure_root_logger(level="DEBUG")
        logger.debug("Debug logging enabled")
    else:
        configure_root_logger(level="INFO")
    
    # Store config in context for subcommands to access
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config
    ctx.obj["debug"] = debug
    
    # If no command specified, run tailor in interactive mode
    if ctx.invoked_subcommand is None:
        ctx.invoke(default_tailor)


@app.command(name="tailor")
def default_tailor(
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
    ),
):
    """Tailor your resume to match a specific job posting.
    
    This command will:
    1. Read your resume from the provided path
    2. Scrape and analyze the job posting from the URL
    3. Generate a tailored version matching the job requirements
    4. Save output in requested format(s)
    
    Examples:
        resume-tailorator tailor --resume-path resume.md \\
            --job-url https://example.com/job --output pdf --output docx
    """
    tailor_cmd.tailor(resume_path=resume_path, job_url=job_url, output=output)


@app.command(name="docs")
def show_docs():
    """Show usage documentation and examples."""
    docs_cmd.docs()


@app.command(name="debug")
def show_debug():
    """Show debug info and verify setup."""
    debug_cmd.debug()


if __name__ == "__main__":
    app()
```

- [ ] **Step 3: Test that all commands are registered**

```bash
cd /Users/emadmokhtar/Projects/resume_tailorator
python -m cli.main --help
```

Expected: Output shows tailor, docs, debug commands

- [ ] **Step 4: Test individual commands**

```bash
python -m cli.main tailor --help
python -m cli.main docs --help
python -m cli.main debug --help
```

Expected: Each command shows its help

- [ ] **Step 5: Commit**

```bash
git add cli/main.py cli/commands/tailor.py
git commit -m "feat(cli): register commands and implement tailor as default"
```

---

### Task 9: Update main.py Entry Point

**Files:**
- Modify: `main.py`

- [ ] **Step 1: Replace main.py content to use CLI**

Replace entire `main.py`:
```python
"""Resume Tailorator - Entry point using Typer CLI."""

from cli.main import app

if __name__ == "__main__":
    app()
```

- [ ] **Step 2: Test that main.py still works as entry point**

```bash
cd /Users/emadmokhtar/Projects/resume_tailorator
python main.py --help
```

Expected: Typer help displayed

- [ ] **Step 3: Test interactive mode**

```bash
python main.py --help
python main.py debug
```

Expected: Help and debug info displayed

- [ ] **Step 4: Commit**

```bash
git add main.py
git commit -m "feat(cli): update main.py to use CLI as entry point"
```

---

### Task 10: Update Makefile

**Files:**
- Modify: `Makefile`

- [ ] **Step 1: Update run target in Makefile**

Replace the `run` target in Makefile:
```makefile
run: install ## Run the resume tailorator agentic workflow
	@echo "🚀 Running Resume Tailorator..."
	@uv run python main.py
```

- [ ] **Step 2: Add cli-help target to Makefile**

Add new target after `run`:
```makefile
cli-help: install/dev ## Show CLI help
	@uv run python main.py --help

cli-docs: install/dev ## Show CLI documentation
	@uv run python main.py docs

cli-debug: install/dev ## Show debug information
	@uv run python main.py debug
```

- [ ] **Step 3: Test Makefile targets**

```bash
cd /Users/emadmokhtar/Projects/resume_tailorator
make cli-help
make cli-debug
make cli-docs
```

Expected: Each target executes successfully

- [ ] **Step 4: Commit**

```bash
git add Makefile
git commit -m "build(makefile): add CLI targets and update run target"
```

---

## Phase 5: Integration Testing

### Task 11: Test Full CLI Flow

**Files:**
- Test: `tests/cli/test_integration.py` (create new)

- [ ] **Step 1: Create integration test file**

Create `tests/cli/test_integration.py`:
```python
"""Integration tests for the full CLI."""

import pytest
import os
import sys
from pathlib import Path
from unittest.mock import patch
from io import StringIO

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from typer.testing import CliRunner
from cli.main import app


runner = CliRunner()


class TestCLIIntegration:
    def test_help_displays_correctly(self):
        """Test that main help displays with proper formatting."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "resume-tailorator" in result.stdout
        assert "tailor" in result.stdout
        assert "docs" in result.stdout
        assert "debug" in result.stdout

    def test_tailor_help_displays(self):
        """Test that tailor command help displays correctly."""
        result = runner.invoke(app, ["tailor", "--help"])
        assert result.exit_code == 0
        assert "--resume-path" in result.stdout
        assert "--job-url" in result.stdout
        assert "--output" in result.stdout

    def test_docs_command_works(self):
        """Test that docs command displays documentation."""
        result = runner.invoke(app, ["docs"])
        assert result.exit_code == 0
        assert "Resume Tailorator" in result.stdout
        assert "QUICK START" in result.stdout

    def test_debug_command_works(self):
        """Test that debug command displays debug info."""
        result = runner.invoke(app, ["debug"])
        assert result.exit_code == 0
        assert "Python" in result.stdout
        assert "Dependencies" in result.stdout

    def test_debug_global_option_works(self):
        """Test that --debug global option is accepted."""
        result = runner.invoke(app, ["--debug", "debug"])
        assert result.exit_code == 0

    def test_global_help_shows_global_options(self):
        """Test that global options are shown in main help."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "--debug" in result.stdout
        assert "--config" in result.stdout

    def test_tailor_with_invalid_resume_path(self, tmp_path):
        """Test that tailor fails gracefully with invalid resume path."""
        result = runner.invoke(
            app,
            [
                "tailor",
                "--resume-path", "/nonexistent/path.md",
                "--job-url", "https://example.com/job",
            ]
        )
        assert result.exit_code != 0
        assert "not found" in result.stdout.lower() or "error" in result.stdout.lower()

    def test_tailor_with_invalid_job_url(self, tmp_path):
        """Test that tailor fails gracefully with invalid job URL."""
        resume_file = tmp_path / "resume.md"
        resume_file.write_text("# Resume")
        
        result = runner.invoke(
            app,
            [
                "tailor",
                "--resume-path", str(resume_file),
                "--job-url", "not-a-url",
            ]
        )
        assert result.exit_code != 0
        assert "must start with" in result.stdout.lower() or "error" in result.stdout.lower()
```

- [ ] **Step 2: Run integration tests**

```bash
cd /Users/emadmokhtar/Projects/resume_tailorator
python -m pytest tests/cli/test_integration.py -v
```

Expected: All tests pass

- [ ] **Step 3: Commit**

```bash
git add tests/cli/test_integration.py
git commit -m "test(cli): add comprehensive integration tests"
```

---

### Task 12: Run All Existing Tests to Verify No Regression

**Files:**
- No new files

- [ ] **Step 1: Install dev dependencies with CLI changes**

```bash
cd /Users/emadmokhtar/Projects/resume_tailorator
uv sync
```

Expected: All dependencies installed including typer[all]

- [ ] **Step 2: Run all tests**

```bash
cd /Users/emadmokhtar/Projects/resume_tailorator
python -m pytest tests/ -v
```

Expected: All tests pass (including new CLI tests and existing tests)

- [ ] **Step 3: Run specific test categories to verify**

```bash
# Run CLI tests only
python -m pytest tests/cli/ -v

# Run existing workflow tests
python -m pytest tests/workflows/ -v
```

Expected: Both categories pass

- [ ] **Step 4: Note results**

If any tests fail that aren't expected, document them for investigation.

---

## Phase 6: Documentation

### Task 13: Update README with CLI Usage

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Locate Usage section in README**

Find the existing usage/quick start section in README.md

- [ ] **Step 2: Update with CLI examples**

Add or replace with:
```markdown
## Usage

### Quick Start (Interactive)

```bash
resume-tailorator
```

This runs in interactive mode and prompts you for:
- Resume path (with default `files/resume.md`)
- Job posting URL
- Output format(s)

### Explicit Mode (All Options)

```bash
resume-tailorator --resume-path resume.md \
    --job-url https://example.com/job \
    --output pdf --output docx
```

### Debug Mode

Enable detailed logging with `--debug`:

```bash
resume-tailorator --debug --resume-path resume.md --job-url https://...
```

### Show Help

```bash
resume-tailorator --help
resume-tailorator tailor --help
resume-tailorator docs
resume-tailorator debug
```

### Available Commands

| Command | Purpose |
|---------|---------|
| `tailor` (default) | Tailor resume to a job posting |
| `docs` | Show usage documentation and examples |
| `debug` | Show debug info and verify setup |

### Environment

- Python 3.13+
- Typer CLI framework
- Pydantic AI for LLM operations

```

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: update README with CLI usage examples"
```

---

### Task 14: Create CLI.md Documentation

**Files:**
- Create: `docs/CLI.md`

- [ ] **Step 1: Create docs/CLI.md with comprehensive documentation**

```markdown
# Resume Tailorator CLI Reference

Complete reference for using the Resume Tailorator command-line interface.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Commands](#commands)
3. [Global Options](#global-options)
4. [Examples](#examples)
5. [Troubleshooting](#troubleshooting)

## Quick Start

### Interactive Mode

```bash
$ resume-tailorator
Resume Path [files/resume.md]: resume.md
Job URL: https://example.com/job
Output Format [md]: pdf

✅ Inputs validated successfully
🚀 Starting Resume Tailorator workflow...
```

### Explicit Mode

```bash
resume-tailorator --resume-path resume.md \
    --job-url https://example.com/job \
    --output pdf --output docx
```

## Commands

### tailor (default)

Tailor your resume to match a specific job posting.

**Syntax:**
```
resume-tailorator tailor [OPTIONS]
resume-tailorator [OPTIONS]  # If no command specified, runs tailor
```

**Options:**

| Option | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| `--resume-path PATH` | Text | No | None | Path to resume file (Markdown). Interactive prompt if omitted. |
| `--job-url URL` | Text | No | None | URL of job posting to scrape. Interactive prompt if omitted. |
| `--output FORMAT` | Choice | No | md | Output format(s): md, pdf, docx. Repeatable. |

**Example:**
```bash
resume-tailorator tailor --resume-path resume.md \
    --job-url https://example.com/job --output pdf
```

### docs

Show usage documentation and examples.

**Syntax:**
```
resume-tailorator docs
```

**Example:**
```bash
resume-tailorator docs
```

### debug

Show debug info and verify setup.

**Syntax:**
```
resume-tailorator debug
```

**Example:**
```bash
resume-tailorator debug
```

## Global Options

Global options are available to all commands:

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--debug` / `--no-debug` | Boolean | --no-debug | Enable DEBUG logging level (shows detailed information) |
| `--config PATH` | Text | None | Path to configuration file (reserved for future use) |
| `--help` | Flag | N/A | Show help message and exit |

**Example:**
```bash
resume-tailorator --debug tailor --resume-path resume.md --job-url https://...
```

## Examples

### Interactive with Defaults

```bash
$ resume-tailorator
Resume Path [files/resume.md]: 
Job URL: https://example.com/job
Output Format [md]: 
```

### Specify Resume, Prompt for Job URL

```bash
$ resume-tailorator --resume-path my-resume.md
Job URL: https://example.com/job
Output Format [md]: 
```

### Multiple Output Formats

```bash
resume-tailorator --resume-path resume.md \
    --job-url https://example.com/job \
    --output md --output pdf --output docx
```

### Debug Mode with Logging

```bash
resume-tailorator --debug --resume-path resume.md \
    --job-url https://example.com/job
```

### Show All Available Commands

```bash
resume-tailorator --help
```

### Show Command-Specific Help

```bash
resume-tailorator tailor --help
resume-tailorator debug --help
```

## Troubleshooting

### File not found

**Error:** `File not found at 'resume.md'`

**Solution:** Check the file path is correct. Use absolute path or relative path from current directory.

```bash
# Absolute path
resume-tailorator --resume-path /home/user/resume.md

# Relative path
resume-tailorator --resume-path ./files/resume.md
```

### Invalid URL

**Error:** `URL must start with http:// or https://`

**Solution:** Ensure the job posting URL starts with http:// or https://

```bash
# Correct
resume-tailorator --job-url https://example.com/job

# Incorrect
resume-tailorator --job-url example.com/job
```

### Invalid output format

**Error:** `Output format must be one of: md, pdf, docx`

**Solution:** Use only supported output formats (case-insensitive)

```bash
# Correct
resume-tailorator --output md --output pdf

# Incorrect
resume-tailorator --output txt
```

### Debugging Issues

Use `--debug` flag to enable detailed logging:

```bash
resume-tailorator --debug tailor --resume-path resume.md --job-url https://...
```

Check setup and dependencies:

```bash
resume-tailorator debug
```

## Making an Alias

For convenience, create a shell alias:

```bash
# Add to ~/.bashrc or ~/.zshrc
alias rtailor="resume-tailorator"

# Then use:
rtailor --help
```

```

- [ ] **Step 2: Commit**

```bash
git add docs/CLI.md
git commit -m "docs: add comprehensive CLI reference documentation"
```

---

## Phase 7: Final Verification

### Task 15: End-to-End Manual Testing

**Files:**
- No new files (manual testing)

- [ ] **Step 1: Test interactive flow**

```bash
cd /Users/emadmokhtar/Projects/resume_tailorator
python main.py docs
```

Expected: Documentation displayed

- [ ] **Step 2: Test debug command**

```bash
python main.py debug
```

Expected: Debug info displayed

- [ ] **Step 3: Test help formatting**

```bash
python main.py --help
python main.py tailor --help
```

Expected: Rich formatted help with clear options

- [ ] **Step 4: Test with valid files (if available)**

If `files/resume.md` exists:
```bash
python main.py --resume-path files/resume.md --help
```

Expected: Help displays without error

- [ ] **Step 5: Test global debug option**

```bash
python main.py --debug docs
python main.py --debug debug
```

Expected: Commands execute with debug logging

- [ ] **Step 6: Note any issues**

Document any issues found and create bug tickets if needed

---

### Task 16: Final Git Status and Summary

**Files:**
- No new files

- [ ] **Step 1: Check git status**

```bash
cd /Users/emadmokhtar/Projects/resume_tailorator
git status
```

Expected: All files committed, clean working directory

- [ ] **Step 2: Review git log**

```bash
git log --oneline -15
```

Expected: Shows all CLI implementation commits

- [ ] **Step 3: Create final summary**

Review what was completed:
- ✅ Typer dependency added
- ✅ CLI module structure created
- ✅ Utility functions for validation and prompts
- ✅ Main app with global options
- ✅ Tailor command (main workflow)
- ✅ Docs command
- ✅ Debug command
- ✅ Commands registered with app
- ✅ Entry point updated
- ✅ Makefile updated
- ✅ Integration tests created
- ✅ All tests passing
- ✅ Documentation updated

- [ ] **Step 4: Final commit if needed**

```bash
git log --oneline --all -1
```

Expected: Clean state with all implementation commits

---

## Success Criteria Checklist

✅ **CLI Help Text**
- `resume-tailorator --help` shows rich formatted help
- Commands listed clearly (tailor, docs, debug)
- Global options documented (--debug, --config)

✅ **Interactive Mode**
- `resume-tailorator` with no args prompts for resume path
- `resume-tailorator` prompts for job URL if not provided
- Prompts for output format with default

✅ **Explicit Mode**
- `resume-tailorator --resume-path file.md --job-url https://... --output pdf` works
- Multiple output formats supported: `--output md --output pdf --output docx`

✅ **Global Options**
- `--debug` flag enables DEBUG logging
- `--debug` works with all commands

✅ **Sub-commands**
- `resume-tailorator docs` shows documentation
- `resume-tailorator debug` shows debug info
- Each command has working `--help`

✅ **Tests**
- All CLI tests pass
- All existing tests pass (no regression)
- Integration tests verify full flow

✅ **Documentation**
- README updated with CLI examples
- CLI.md created with comprehensive reference
- Help text is clear and helpful

---

## Implementation Summary

This plan converts Resume Tailorator from argparse to Typer in **16 concrete tasks** organized into 7 phases:

1. **Setup & Dependencies** (Task 1-2): Add typer[all] and create package structure
2. **Core Infrastructure** (Task 3-4): Utilities and main app with global options
3. **Commands** (Task 5-7): Implement tailor, docs, and debug commands
4. **Integration** (Task 8-10): Register commands, update entry point, update Makefile
5. **Testing** (Task 11-12): Integration tests and regression verification
6. **Documentation** (Task 13-14): Update README and create CLI reference
7. **Verification** (Task 15-16): End-to-end testing and final review

Each task is self-contained, testable, and produces working software that can be committed independently. Follow the TDD approach (test first, implement, verify) and commit frequently.

