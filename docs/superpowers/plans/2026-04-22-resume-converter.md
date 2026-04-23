# Resume Converter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add local input conversion (`.docx`/`.pdf` → Markdown) and user-controlled output format selection (`--output md|pdf|docx`) to Resume Tailorator.

**Architecture:** Two new util modules behind Protocol interfaces — `utils/resume_converter.py` handles input conversion (Protocol + per-format converters + `InputConverterRegistry` + auto-detection + all custom exceptions); `utils/resume_output_converter.py` handles output conversion (`build_resume_markdown` helper + Protocol + per-format converters + `OutputConverterRegistry`). `main.py` gains `--resume` and `--output` argparse flags and wires both sides together. Existing `markdown_writer.py` and `pdf_converter.py` are left unchanged; they become legacy/unused except `pdf_converter.markdown_to_pdf` which is imported by `PdfOutputConverter`.

**Tech Stack:** `markitdown[docx,pdf]` (input .docx/.pdf → Markdown), `python-docx` (Markdown → .docx output), `markdown-pdf` (already a dep — used for PDF output), `pytest` + `pytest-subtests` (testing).

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `utils/resume_converter.py` | **Create** | All custom exceptions + `ResumeConverterProtocol` + `DocxInputConverter` + `PdfInputConverter` + `InputConverterRegistry` + `auto_detect_resume()` |
| `utils/resume_output_converter.py` | **Create** | `build_resume_markdown()` + `OutputConverterProtocol` + `MarkdownOutputConverter` + `PdfOutputConverter` + `DocxOutputConverter` + `OutputConverterRegistry` |
| `tests/__init__.py` | **Create** | Empty — marks `tests/` as a package |
| `tests/conftest.py` | **Create** | Shared pytest fixtures: `sample_docx`, `sample_pdf`, `sample_markdown_path` |
| `tests/test_resume_converter.py` | **Create** | Tests for all input-side code |
| `tests/test_resume_output_converter.py` | **Create** | Tests for all output-side code |
| `pyproject.toml` | **Modify** | Add `markitdown[docx,pdf]`, `python-docx`; add `pytest`, `pytest-subtests` as dev deps; add `[tool.pytest.ini_options]` |
| `main.py` | **Modify** | `argparse` with `--resume`/`--output`, input resolution, output registry call |
| `Makefile` | **Modify** | Add `test` target |

---

## Task 1: Add Dependencies and Test Infrastructure

**Files:**
- Modify: `pyproject.toml`
- Modify: `Makefile`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1.1: Update `pyproject.toml`**

Replace the full file content with:

```toml
[project]
name = "resume-tailorator"
version = "0.1.0"
description = "Add your description here"
readme = "README.md"
requires-python = ">=3.13"
dependencies = [
    "aiofiles>=25.1.0",
    "html2text>=2025.4.15",
    "markdown>=3.10",
    "markdown-pdf>=1.10",
    "markitdown[docx,pdf]>=0.1.0",
    "playwright>=1.56.0",
    "pydantic-ai>=1.24.0",
    "python-docx>=1.1.0",
]

[dependency-groups]
dev = [
    "pytest>=8.0.0",
    "pytest-subtests>=0.13.0",
    "ruff>=0.14.6",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

- [ ] **Step 1.2: Add `test` target to `Makefile`**

Add after the `install/dev` target:

```makefile
test: install/dev  ## Run tests
	@echo "🧪 Running tests..."
	@uv run pytest -v
	@echo "✅ Tests done"
```

- [ ] **Step 1.3: Install dependencies**

```bash
uv sync --dev
```

Expected output ends with: `Resolved ... packages` and no errors.

- [ ] **Step 1.4: Create `tests/__init__.py`**

Create an empty file at `tests/__init__.py`.

- [ ] **Step 1.5: Create `tests/conftest.py`**

```python
import json

import pytest
from pathlib import Path


SAMPLE_MARKDOWN = """\
# Jane Smith

jane@example.com | linkedin.com/in/janesmith

## Professional Summary

Experienced Python engineer.

## Skills

- Python
- Django

## Work Experience

### Senior Engineer at Acme Corp (2020-2024)

- Built microservices

## Education

- BSc CS, State University, 2018
"""


@pytest.fixture
def sample_docx(tmp_path: Path) -> Path:
    from docx import Document

    doc = Document()
    doc.add_heading("Jane Smith", 0)
    doc.add_paragraph("jane@example.com | linkedin.com/in/janesmith")
    doc.add_heading("Professional Summary", 1)
    doc.add_paragraph("Experienced Python engineer.")
    doc.add_heading("Skills", 1)
    doc.add_paragraph("Python", style="List Bullet")
    path = tmp_path / "resume.docx"
    doc.save(str(path))
    return path


@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    from markdown_pdf import MarkdownPdf, Section

    pdf = MarkdownPdf()
    pdf.add_section(Section(SAMPLE_MARKDOWN))
    path = tmp_path / "resume.pdf"
    pdf.save(str(path))
    return path


@pytest.fixture
def sample_markdown_path(tmp_path: Path) -> Path:
    path = tmp_path / "resume.md"
    path.write_text(SAMPLE_MARKDOWN, encoding="utf-8")
    return path
```

- [ ] **Step 1.6: Verify pytest is discovered**

```bash
uv run pytest --collect-only
```

Expected output: `no tests ran` (or similar) with no import errors.

- [ ] **Step 1.7: Commit**

```bash
git add pyproject.toml Makefile tests/__init__.py tests/conftest.py uv.lock
git commit -m "chore: add pytest, markitdown, python-docx dependencies and test infrastructure

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Task 2: Custom Exception Hierarchy

**Files:**
- Create: `utils/resume_converter.py` (exceptions only — converters added in Task 3)
- Create: `tests/test_resume_converter.py` (exception tests only)

- [ ] **Step 2.1: Write failing tests for exception hierarchy**

Create `tests/test_resume_converter.py`:

```python
import pytest

from utils.resume_converter import (
    ConversionFailedError,
    EmptyConversionResultError,
    NoResumeFileFoundError,
    OutputConversionFailedError,
    ResumeConverterError,
    ResumeFileNotFoundError,
    UnsupportedFormatError,
    UnsupportedOutputFormatError,
)


class TestExceptionHierarchy:
    def test_all_subclasses_inherit_from_base(self, subtests):
        subclasses = [
            ResumeFileNotFoundError,
            UnsupportedFormatError,
            ConversionFailedError,
            EmptyConversionResultError,
            NoResumeFileFoundError,
            OutputConversionFailedError,
            UnsupportedOutputFormatError,
        ]
        for exc_class in subclasses:
            with subtests.test(msg=exc_class.__name__):
                assert issubclass(exc_class, ResumeConverterError)

    def test_base_is_exception_subclass(self):
        assert issubclass(ResumeConverterError, Exception)

    def test_exceptions_are_raisable_with_message(self, subtests):
        all_classes = [
            ResumeConverterError,
            ResumeFileNotFoundError,
            UnsupportedFormatError,
            ConversionFailedError,
            EmptyConversionResultError,
            NoResumeFileFoundError,
            OutputConversionFailedError,
            UnsupportedOutputFormatError,
        ]
        for exc_class in all_classes:
            with subtests.test(msg=exc_class.__name__):
                with pytest.raises(exc_class, match="test message"):
                    raise exc_class("test message")
```

- [ ] **Step 2.2: Run tests to verify they fail**

```bash
uv run pytest tests/test_resume_converter.py -v
```

Expected: `ModuleNotFoundError: No module named 'utils.resume_converter'`

- [ ] **Step 2.3: Create `utils/resume_converter.py` with exceptions only**

```python
"""Input resume conversion: .docx/.pdf → Markdown, plus shared custom exceptions."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class ResumeConverterError(Exception):
    """Base exception for all resume conversion errors."""


class ResumeFileNotFoundError(ResumeConverterError):
    """Raised when the input resume file does not exist."""


class UnsupportedFormatError(ResumeConverterError):
    """Raised when the file extension is not supported."""


class ConversionFailedError(ResumeConverterError):
    """Raised when markitdown fails to convert the file."""


class EmptyConversionResultError(ResumeConverterError):
    """Raised when conversion produces empty/whitespace output."""


class NoResumeFileFoundError(ResumeConverterError):
    """Raised when auto-detection finds no resume file in files/."""


class OutputConversionFailedError(ResumeConverterError):
    """Raised when writing an output file fails."""


class UnsupportedOutputFormatError(ResumeConverterError):
    """Raised when the requested output format is not supported."""
```

- [ ] **Step 2.4: Run tests to verify they pass**

```bash
uv run pytest tests/test_resume_converter.py::TestExceptionHierarchy -v
```

Expected: `3 passed`

- [ ] **Step 2.5: Commit**

```bash
git add utils/resume_converter.py tests/test_resume_converter.py
git commit -m "feat(converter): add custom exception hierarchy

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Task 3: Input Converters, Registry, and Auto-Detection

**Files:**
- Modify: `utils/resume_converter.py` (add Protocol, converters, registry, auto_detect_resume)
- Modify: `tests/test_resume_converter.py` (add converter + registry + auto-detect tests)

- [ ] **Step 3.1: Append input converter tests to `tests/test_resume_converter.py`**

Add the following classes at the end of the file (keep existing `TestExceptionHierarchy`):

```python
from utils.resume_converter import (
    DocxInputConverter,
    InputConverterRegistry,
    PdfInputConverter,
    ResumeConverterProtocol,
    auto_detect_resume,
)


class TestDocxInputConverter:
    def test_convert_returns_nonempty_string(self, sample_docx):
        converter = DocxInputConverter()
        result = converter.convert(sample_docx)
        assert isinstance(result, str)
        assert result.strip()

    def test_convert_contains_name_from_document(self, sample_docx):
        converter = DocxInputConverter()
        result = converter.convert(sample_docx)
        assert "Jane Smith" in result

    def test_convert_raises_conversion_failed_on_corrupt_file(self, tmp_path):
        bad_path = tmp_path / "bad.docx"
        bad_path.write_bytes(b"this is not a docx file at all")
        converter = DocxInputConverter()
        with pytest.raises(ConversionFailedError):
            converter.convert(bad_path)

    def test_convert_raises_empty_result_on_blank_document(self, tmp_path):
        from docx import Document

        path = tmp_path / "empty.docx"
        Document().save(str(path))
        converter = DocxInputConverter()
        with pytest.raises(EmptyConversionResultError):
            converter.convert(path)


class TestPdfInputConverter:
    def test_convert_returns_nonempty_string(self, sample_pdf):
        converter = PdfInputConverter()
        result = converter.convert(sample_pdf)
        assert isinstance(result, str)
        assert result.strip()

    def test_convert_raises_conversion_failed_on_corrupt_file(self, tmp_path):
        bad_path = tmp_path / "bad.pdf"
        bad_path.write_bytes(b"not a pdf")
        converter = PdfInputConverter()
        with pytest.raises(ConversionFailedError):
            converter.convert(bad_path)


class TestInputConverterRegistry:
    def test_get_returns_docx_converter(self):
        registry = InputConverterRegistry()
        assert isinstance(registry.get(".docx"), DocxInputConverter)

    def test_get_returns_pdf_converter(self):
        registry = InputConverterRegistry()
        assert isinstance(registry.get(".pdf"), PdfInputConverter)

    def test_get_is_case_insensitive(self, subtests):
        registry = InputConverterRegistry()
        with subtests.test("DOCX"):
            assert isinstance(registry.get(".DOCX"), DocxInputConverter)
        with subtests.test("PDF"):
            assert isinstance(registry.get(".PDF"), PdfInputConverter)

    def test_get_raises_unsupported_for_unknown_extension(self):
        registry = InputConverterRegistry()
        with pytest.raises(UnsupportedFormatError):
            registry.get(".txt")

    def test_convert_and_save_writes_markdown_to_output_path(self, sample_docx, tmp_path):
        registry = InputConverterRegistry()
        output_path = tmp_path / "resume.md"
        returned = registry.convert_and_save(sample_docx, output_path)
        assert isinstance(returned, str)
        assert returned.strip()
        assert output_path.exists()
        assert output_path.read_text(encoding="utf-8") == returned

    def test_convert_and_save_raises_file_not_found_for_missing_input(self, tmp_path):
        registry = InputConverterRegistry()
        with pytest.raises(ResumeFileNotFoundError):
            registry.convert_and_save(
                tmp_path / "missing.docx", tmp_path / "out.md"
            )


class TestAutoDetectResume:
    def test_prefers_docx_over_pdf_and_md(self, tmp_path):
        (tmp_path / "resume.docx").touch()
        (tmp_path / "resume.pdf").touch()
        (tmp_path / "resume.md").touch()
        assert auto_detect_resume(tmp_path) == tmp_path / "resume.docx"

    def test_falls_back_to_pdf_when_no_docx(self, tmp_path):
        (tmp_path / "resume.pdf").touch()
        (tmp_path / "resume.md").touch()
        assert auto_detect_resume(tmp_path) == tmp_path / "resume.pdf"

    def test_falls_back_to_md_when_only_option(self, tmp_path):
        (tmp_path / "resume.md").touch()
        assert auto_detect_resume(tmp_path) == tmp_path / "resume.md"

    def test_raises_no_resume_found_when_directory_is_empty(self, tmp_path):
        with pytest.raises(NoResumeFileFoundError):
            auto_detect_resume(tmp_path)
```

Also update the import block at the top of `tests/test_resume_converter.py` — replace the existing import block with:

```python
import pytest

from utils.resume_converter import (
    ConversionFailedError,
    DocxInputConverter,
    EmptyConversionResultError,
    InputConverterRegistry,
    NoResumeFileFoundError,
    OutputConversionFailedError,
    PdfInputConverter,
    ResumeConverterError,
    ResumeConverterProtocol,
    ResumeFileNotFoundError,
    UnsupportedFormatError,
    UnsupportedOutputFormatError,
    auto_detect_resume,
)
```

- [ ] **Step 3.2: Run tests to verify new tests fail**

```bash
uv run pytest tests/test_resume_converter.py -v
```

Expected: `ImportError` on `DocxInputConverter` (not yet defined).

- [ ] **Step 3.3: Append Protocol, converters, registry, and auto-detect to `utils/resume_converter.py`**

Add the following after the exceptions block:

```python
# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


class ResumeConverterProtocol(Protocol):
    def convert(self, input_path: Path) -> str:
        """Return markdown string from input file."""
        ...


# ---------------------------------------------------------------------------
# Concrete input converters
# ---------------------------------------------------------------------------


class DocxInputConverter:
    """Converts .docx → Markdown via markitdown."""

    def convert(self, input_path: Path) -> str:
        try:
            from markitdown import MarkItDown

            md = MarkItDown()
            result = md.convert(str(input_path))
            markdown = result.text_content
        except Exception as exc:
            raise ConversionFailedError(
                f"Failed to convert .docx: {exc}"
            ) from exc

        if not markdown.strip():
            raise EmptyConversionResultError(
                "Conversion produced empty content. Check your input file."
            )
        return markdown


class PdfInputConverter:
    """Converts .pdf → Markdown via markitdown."""

    def convert(self, input_path: Path) -> str:
        try:
            from markitdown import MarkItDown

            md = MarkItDown()
            result = md.convert(str(input_path))
            markdown = result.text_content
        except Exception as exc:
            raise ConversionFailedError(
                f"Failed to convert .pdf: {exc}"
            ) from exc

        if not markdown.strip():
            raise EmptyConversionResultError(
                "Conversion produced empty content. Check your input file."
            )
        return markdown


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class InputConverterRegistry:
    """Maps file extensions to their converter implementations."""

    _converters: dict[str, ResumeConverterProtocol] = {
        ".docx": DocxInputConverter(),
        ".pdf": PdfInputConverter(),
    }

    def get(self, ext: str) -> ResumeConverterProtocol:
        """Return converter for extension. Raises UnsupportedFormatError if unknown."""
        converter = self._converters.get(ext.lower())
        if converter is None:
            supported = ", ".join(self._converters)
            raise UnsupportedFormatError(
                f"Unsupported format '{ext}'. Supported: {supported}"
            )
        return converter

    def convert_and_save(self, input_path: Path, output_path: Path) -> str:
        """Convert input_path and write Markdown to output_path. Returns Markdown string."""
        if not input_path.exists():
            raise ResumeFileNotFoundError(
                f"Resume file not found at {input_path}"
            )
        converter = self.get(input_path.suffix)
        markdown = converter.convert(input_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(markdown, encoding="utf-8")
        return markdown


# ---------------------------------------------------------------------------
# Auto-detection
# ---------------------------------------------------------------------------


def auto_detect_resume(files_dir: Path) -> Path:
    """Return first resume file found in files_dir using priority order.

    Priority: resume.docx > resume.pdf > resume.md
    Raises NoResumeFileFoundError if none exist.
    """
    for name in ("resume.docx", "resume.pdf", "resume.md"):
        candidate = files_dir / name
        if candidate.exists():
            return candidate
    raise NoResumeFileFoundError(
        "No resume file found in files/. Add resume.docx, resume.pdf, or resume.md, "
        "or use --resume."
    )
```

- [ ] **Step 3.4: Run all input converter tests**

```bash
uv run pytest tests/test_resume_converter.py -v
```

Expected: all tests pass (exception tests + converter tests + registry tests + auto-detect tests).

- [ ] **Step 3.5: Commit**

```bash
git add utils/resume_converter.py tests/test_resume_converter.py
git commit -m "feat(converter): add input converters, registry, and auto-detection

- ResumeConverterProtocol, DocxInputConverter, PdfInputConverter
- InputConverterRegistry with get() and convert_and_save()
- auto_detect_resume() with docx > pdf > md priority

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Task 4: `build_resume_markdown` Helper

**Files:**
- Create: `utils/resume_output_converter.py` (`build_resume_markdown` only — converters added in Task 5)
- Create: `tests/test_resume_output_converter.py` (`build_resume_markdown` tests only)

- [ ] **Step 4.1: Write failing test for `build_resume_markdown`**

Create `tests/test_resume_output_converter.py`:

```python
import json

import pytest
from pathlib import Path

from models.workflow import ResumeTailorResult


SAMPLE_RESULT = ResumeTailorResult(
    company_name="Acme",
    tailored_resume=json.dumps({
        "full_name": "Jane Smith",
        "contact_info": "jane@example.com",
        "summary": "Experienced Python engineer.",
        "skills": ["Python", "Django"],
        "experience": [
            {
                "role": "Senior Engineer",
                "company": "Acme Corp",
                "dates": "2020-2024",
                "highlights": ["Built microservices", "Led team of 5"],
            }
        ],
        "education": ["BSc CS, State University, 2018"],
        "certifications": ["AWS Certified"],
        "publications": ["Python Patterns, 2023"],
        "projects": ["Open Source CLI tool"],
    }),
    audit_report={},
    passed=True,
)

SAMPLE_MARKDOWN = "# Jane Smith\n\n## Professional Summary\nExperienced engineer.\n"


class TestBuildResumeMarkdown:
    def test_returns_nonempty_string(self):
        from utils.resume_output_converter import build_resume_markdown

        result = build_resume_markdown(SAMPLE_RESULT)
        assert isinstance(result, str)
        assert result.strip()

    def test_contains_full_name(self):
        from utils.resume_output_converter import build_resume_markdown

        result = build_resume_markdown(SAMPLE_RESULT)
        assert "Jane Smith" in result

    def test_contains_contact_info(self):
        from utils.resume_output_converter import build_resume_markdown

        result = build_resume_markdown(SAMPLE_RESULT)
        assert "jane@example.com" in result

    def test_contains_summary(self):
        from utils.resume_output_converter import build_resume_markdown

        result = build_resume_markdown(SAMPLE_RESULT)
        assert "Experienced Python engineer." in result

    def test_contains_skills(self, subtests):
        from utils.resume_output_converter import build_resume_markdown

        result = build_resume_markdown(SAMPLE_RESULT)
        with subtests.test("Python"):
            assert "Python" in result
        with subtests.test("Django"):
            assert "Django" in result

    def test_contains_work_experience(self):
        from utils.resume_output_converter import build_resume_markdown

        result = build_resume_markdown(SAMPLE_RESULT)
        assert "Senior Engineer" in result
        assert "Acme Corp" in result

    def test_contains_education(self):
        from utils.resume_output_converter import build_resume_markdown

        result = build_resume_markdown(SAMPLE_RESULT)
        assert "BSc CS" in result

    def test_contains_certifications(self):
        from utils.resume_output_converter import build_resume_markdown

        result = build_resume_markdown(SAMPLE_RESULT)
        assert "AWS Certified" in result

    def test_contains_publications(self):
        from utils.resume_output_converter import build_resume_markdown

        result = build_resume_markdown(SAMPLE_RESULT)
        assert "Python Patterns" in result
```

- [ ] **Step 4.2: Run test to verify it fails**

```bash
uv run pytest tests/test_resume_output_converter.py -v
```

Expected: `ModuleNotFoundError: No module named 'utils.resume_output_converter'`

- [ ] **Step 4.3: Create `utils/resume_output_converter.py` with `build_resume_markdown` only**

```python
"""Output resume conversion: Markdown string → .md / .pdf / .docx files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

from models.workflow import ResumeTailorResult
from utils.resume_converter import OutputConversionFailedError, UnsupportedOutputFormatError


# ---------------------------------------------------------------------------
# Markdown builder
# ---------------------------------------------------------------------------


def build_resume_markdown(result: ResumeTailorResult) -> str:
    """Build a Markdown string from a tailored resume result.

    Args:
        result: ResumeTailorResult with tailored_resume as a JSON-encoded CV dict.

    Returns:
        Formatted Markdown string.
    """
    cv = json.loads(result.tailored_resume)
    parts: list[str] = [f"# {cv.get('full_name', 'N/A')}\n"]

    if cv.get("contact_info"):
        parts.append(f"{cv['contact_info']}\n")
    parts.append("\n")

    parts.append(f"## Professional Summary\n{cv.get('summary', '')}\n\n")

    parts.append("## Skills\n")
    for skill in cv.get("skills", []):
        parts.append(f"- {skill}\n")

    if cv.get("projects"):
        parts.append("\n## Projects\n")
        for project in cv.get("projects", []):
            parts.append(f"{project}\n\n")

    parts.append("\n## Work Experience\n")
    for exp in cv.get("experience", []):
        parts.append(
            f"### {exp.get('role', '')} at {exp.get('company', '')} "
            f"({exp.get('dates', '')})\n\n"
        )
        for highlight in exp.get("highlights", []):
            parts.append(f"- {highlight}\n")
        parts.append("\n")

    parts.append("## Education\n")
    for edu in cv.get("education", []):
        parts.append(f"- {edu}\n")

    if cv.get("certifications"):
        parts.append("\n## Certifications\n")
        for cert in cv.get("certifications", []):
            parts.append(f"- {cert}\n")

    if cv.get("publications"):
        parts.append("\n## Publications\n")
        for pub in cv.get("publications", []):
            parts.append(f"- {pub}\n")

    return "".join(parts)
```

- [ ] **Step 4.4: Run tests to verify they pass**

```bash
uv run pytest tests/test_resume_output_converter.py::TestBuildResumeMarkdown -v
```

Expected: all 9 tests pass.

- [ ] **Step 4.5: Commit**

```bash
git add utils/resume_output_converter.py tests/test_resume_output_converter.py
git commit -m "feat(converter): add build_resume_markdown output helper

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Task 5: Output Converters and Registry

**Files:**
- Modify: `utils/resume_output_converter.py` (add Protocol, converters, registry)
- Modify: `tests/test_resume_output_converter.py` (add converter + registry tests)

- [ ] **Step 5.1: Append output converter tests to `tests/test_resume_output_converter.py`**

Add the following classes at the end of the file:

```python
from utils.resume_converter import OutputConversionFailedError, UnsupportedOutputFormatError
from utils.resume_output_converter import (
    DocxOutputConverter,
    MarkdownOutputConverter,
    OutputConverterRegistry,
    PdfOutputConverter,
)


class TestMarkdownOutputConverter:
    def test_writes_content_to_file(self, tmp_path):
        converter = MarkdownOutputConverter()
        output_path = tmp_path / "tailored_resume.md"
        converter.convert(SAMPLE_MARKDOWN, output_path)
        assert output_path.exists()
        assert output_path.read_text(encoding="utf-8") == SAMPLE_MARKDOWN

    def test_creates_parent_directory_if_missing(self, tmp_path):
        converter = MarkdownOutputConverter()
        output_path = tmp_path / "subdir" / "tailored_resume.md"
        converter.convert(SAMPLE_MARKDOWN, output_path)
        assert output_path.exists()

    def test_raises_output_conversion_failed_on_write_error(self, tmp_path):
        converter = MarkdownOutputConverter()
        # Create a directory at the target path so write_text fails
        bad_path = tmp_path / "tailored_resume.md"
        bad_path.mkdir()
        with pytest.raises(OutputConversionFailedError):
            converter.convert(SAMPLE_MARKDOWN, bad_path)


class TestPdfOutputConverter:
    def test_writes_pdf_file(self, tmp_path):
        converter = PdfOutputConverter()
        output_path = tmp_path / "tailored_resume.pdf"
        converter.convert(SAMPLE_MARKDOWN, output_path)
        assert output_path.exists()
        assert output_path.stat().st_size > 0

    def test_pdf_file_starts_with_pdf_header(self, tmp_path):
        converter = PdfOutputConverter()
        output_path = tmp_path / "tailored_resume.pdf"
        converter.convert(SAMPLE_MARKDOWN, output_path)
        assert output_path.read_bytes()[:4] == b"%PDF"


class TestDocxOutputConverter:
    def test_writes_docx_file(self, tmp_path):
        converter = DocxOutputConverter()
        output_path = tmp_path / "tailored_resume.docx"
        converter.convert(SAMPLE_MARKDOWN, output_path)
        assert output_path.exists()
        assert output_path.stat().st_size > 0

    def test_docx_headings_are_preserved(self, tmp_path):
        from docx import Document

        converter = DocxOutputConverter()
        output_path = tmp_path / "tailored_resume.docx"
        content = "# Jane Smith\n\n## Skills\n\n- Python\n\nSome paragraph.\n"
        converter.convert(content, output_path)
        doc = Document(str(output_path))
        all_text = " ".join(p.text for p in doc.paragraphs)
        assert "Jane Smith" in all_text
        assert "Skills" in all_text
        assert "Python" in all_text


class TestOutputConverterRegistry:
    def test_get_md_returns_markdown_converter(self):
        registry = OutputConverterRegistry()
        assert isinstance(registry.get("md"), MarkdownOutputConverter)

    def test_get_pdf_returns_pdf_converter(self):
        registry = OutputConverterRegistry()
        assert isinstance(registry.get("pdf"), PdfOutputConverter)

    def test_get_docx_returns_docx_converter(self):
        registry = OutputConverterRegistry()
        assert isinstance(registry.get("docx"), DocxOutputConverter)

    def test_get_raises_unsupported_output_format_for_unknown(self):
        registry = OutputConverterRegistry()
        with pytest.raises(UnsupportedOutputFormatError):
            registry.get("html")

    def test_convert_all_writes_each_requested_format(self, tmp_path):
        registry = OutputConverterRegistry()
        written = registry.convert_all(SAMPLE_MARKDOWN, ["md", "docx"], tmp_path)
        assert (tmp_path / "tailored_resume.md").exists()
        assert (tmp_path / "tailored_resume.docx").exists()

    def test_convert_all_returns_correct_paths(self, tmp_path):
        registry = OutputConverterRegistry()
        written = registry.convert_all(SAMPLE_MARKDOWN, ["md"], tmp_path)
        assert written == [tmp_path / "tailored_resume.md"]

    def test_convert_all_with_all_formats(self, tmp_path):
        registry = OutputConverterRegistry()
        written = registry.convert_all(SAMPLE_MARKDOWN, ["md", "pdf", "docx"], tmp_path)
        assert len(written) == 3
        with subtests.test("md"):
            assert (tmp_path / "tailored_resume.md").exists()
        with subtests.test("pdf"):
            assert (tmp_path / "tailored_resume.pdf").exists()
        with subtests.test("docx"):
            assert (tmp_path / "tailored_resume.docx").exists()
```

Wait — `subtests` is a fixture. Fix `test_convert_all_with_all_formats` to use `subtests` parameter:

```python
    def test_convert_all_with_all_formats(self, tmp_path, subtests):
        registry = OutputConverterRegistry()
        written = registry.convert_all(SAMPLE_MARKDOWN, ["md", "pdf", "docx"], tmp_path)
        assert len(written) == 3
        with subtests.test("md"):
            assert (tmp_path / "tailored_resume.md").exists()
        with subtests.test("pdf"):
            assert (tmp_path / "tailored_resume.pdf").exists()
        with subtests.test("docx"):
            assert (tmp_path / "tailored_resume.docx").exists()
```

- [ ] **Step 5.2: Run tests to verify new tests fail**

```bash
uv run pytest tests/test_resume_output_converter.py -v
```

Expected: `ImportError` on `MarkdownOutputConverter` (not yet defined).

- [ ] **Step 5.3: Append Protocol, converters, and registry to `utils/resume_output_converter.py`**

Add after the `build_resume_markdown` function:

```python
# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


class OutputConverterProtocol(Protocol):
    def convert(self, content: str, output_path: Path) -> None:
        """Write resume content to output_path in the target format."""
        ...


# ---------------------------------------------------------------------------
# Concrete output converters
# ---------------------------------------------------------------------------


class MarkdownOutputConverter:
    """Writes tailored resume as .md."""

    def convert(self, content: str, output_path: Path) -> None:
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(content, encoding="utf-8")
        except Exception as exc:
            raise OutputConversionFailedError(
                f"Failed to write markdown: {exc}"
            ) from exc


class PdfOutputConverter:
    """Writes tailored resume as .pdf — delegates to utils/pdf_converter.py."""

    def convert(self, content: str, output_path: Path) -> None:
        try:
            from utils.pdf_converter import markdown_to_pdf

            output_path.parent.mkdir(parents=True, exist_ok=True)
            markdown_to_pdf(content, str(output_path))
        except Exception as exc:
            raise OutputConversionFailedError(
                f"Failed to write PDF: {exc}"
            ) from exc


class DocxOutputConverter:
    """Writes tailored resume as .docx using python-docx."""

    def convert(self, content: str, output_path: Path) -> None:
        try:
            from docx import Document

            doc = Document()
            for line in content.split("\n"):
                if line.startswith("# "):
                    doc.add_heading(line[2:].strip(), level=1)
                elif line.startswith("## "):
                    doc.add_heading(line[3:].strip(), level=2)
                elif line.startswith("### "):
                    doc.add_heading(line[4:].strip(), level=3)
                elif line.startswith("- "):
                    doc.add_paragraph(line[2:].strip(), style="List Bullet")
                elif line.strip():
                    doc.add_paragraph(line.strip())
            output_path.parent.mkdir(parents=True, exist_ok=True)
            doc.save(str(output_path))
        except Exception as exc:
            raise OutputConversionFailedError(
                f"Failed to write docx: {exc}"
            ) from exc


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class OutputConverterRegistry:
    """Maps format strings to output converter implementations."""

    _converters: dict[str, OutputConverterProtocol] = {
        "md": MarkdownOutputConverter(),
        "pdf": PdfOutputConverter(),
        "docx": DocxOutputConverter(),
    }

    def get(self, fmt: str) -> OutputConverterProtocol:
        """Return converter for format string. Raises UnsupportedOutputFormatError if unknown."""
        converter = self._converters.get(fmt.lower())
        if converter is None:
            supported = ", ".join(self._converters)
            raise UnsupportedOutputFormatError(
                f"Unsupported output format '{fmt}'. Supported: {supported}"
            )
        return converter

    def convert_all(
        self, content: str, formats: list[str], output_dir: Path
    ) -> list[Path]:
        """Write content in each requested format. Returns list of written paths."""
        written: list[Path] = []
        for fmt in formats:
            converter = self.get(fmt)
            output_path = output_dir / f"tailored_resume.{fmt}"
            converter.convert(content, output_path)
            written.append(output_path)
        return written
```

- [ ] **Step 5.4: Run all output converter tests**

```bash
uv run pytest tests/test_resume_output_converter.py -v
```

Expected: all tests pass.

- [ ] **Step 5.5: Run full test suite to make sure nothing is broken**

```bash
uv run pytest -v
```

Expected: all tests pass.

- [ ] **Step 5.6: Commit**

```bash
git add utils/resume_output_converter.py tests/test_resume_output_converter.py
git commit -m "feat(converter): add output converters and registry

- OutputConverterProtocol, MarkdownOutputConverter, PdfOutputConverter,
  DocxOutputConverter
- OutputConverterRegistry with get() and convert_all()
- DocxOutputConverter renders markdown headings, bullets, paragraphs
  via python-docx

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Task 6: Update `main.py`

**Files:**
- Modify: `main.py`

- [ ] **Step 6.1: Replace `main.py` with the updated version**

Replace the entire file content with:

```python
import argparse
import asyncio
import sys
from pathlib import Path

from utils.resume_converter import (
    EmptyConversionResultError,
    InputConverterRegistry,
    ResumeConverterError,
    auto_detect_resume,
)
from utils.resume_output_converter import OutputConverterRegistry, build_resume_markdown
from workflows import ResumeTailorWorkflow


def resolve_resume_path(resume_arg: str | None, files_dir: Path) -> Path:
    """Return resolved resume file path.

    If --resume is given, validate it exists. Otherwise auto-detect in files_dir.
    Raises ResumeConverterError subclasses on failure.
    """
    from utils.resume_converter import ResumeFileNotFoundError

    if resume_arg:
        path = Path(resume_arg)
        if not path.exists():
            raise ResumeFileNotFoundError(f"Resume file not found at {path}")
        return path
    return auto_detect_resume(files_dir)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Resume Tailorator")
    parser.add_argument(
        "--resume",
        help="Path to resume file (.md, .docx, or .pdf). "
        "Defaults to auto-detecting files/resume.{docx,pdf,md}.",
    )
    parser.add_argument(
        "--output",
        action="append",
        choices=["md", "pdf", "docx"],
        dest="outputs",
        metavar="FORMAT",
        help="Output format: md, pdf, or docx. Repeatable. Default: md.",
    )
    args = parser.parse_args()
    output_formats: list[str] = args.outputs or ["md"]

    files_dir = Path.cwd() / "files"
    md_path = files_dir / "resume.md"
    job_path = files_dir / "job_posting.md"

    try:
        resume_path = resolve_resume_path(args.resume, files_dir)

        if resume_path.suffix.lower() in (".docx", ".pdf"):
            print(f"🔄 Converting {resume_path.name} to Markdown...")
            original_cv_text = InputConverterRegistry().convert_and_save(
                resume_path, md_path
            )
            print("✅ Conversion complete.")
        else:
            original_cv_text = resume_path.read_text(encoding="utf-8")
            if not original_cv_text.strip():
                raise EmptyConversionResultError(
                    "Resume file is empty. Please add content."
                )

    except ResumeConverterError as exc:
        print(f"❌ {exc}")
        sys.exit(1)

    # Run the AI workflow
    workflow = ResumeTailorWorkflow()
    result = await workflow.run(
        original_cv_text, job_content_file_path=str(job_path)
    )

    if result.passed:
        print("\n✅ Audit Passed. Saving CV...")
        try:
            markdown_content = build_resume_markdown(result)
            written = OutputConverterRegistry().convert_all(
                markdown_content, output_formats, files_dir
            )
            for path in written:
                ext = path.suffix.upper().lstrip(".")
                print(f"   - {ext}: {path}")
        except ResumeConverterError as exc:
            print(f"❌ Output error: {exc}")
            sys.exit(1)
    else:
        print("\n❌ Audit Failed. Please review the feedback and try again.")
        print(f"Feedback: {result.audit_report.get('feedback_summary', '')}")


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 6.2: Run the full test suite**

```bash
uv run pytest -v
```

Expected: all tests pass.

- [ ] **Step 6.3: Verify the CLI help text works (smoke test — no API calls)**

```bash
uv run python main.py --help
```

Expected output:
```
usage: main.py [-h] [--resume RESUME] [--output FORMAT]

Resume Tailorator

options:
  -h, --help       show this help message and exit
  --resume RESUME  Path to resume file (.md, .docx, or .pdf). ...
  --output FORMAT  Output format: md, pdf, or docx. Repeatable. Default: md.
```

- [ ] **Step 6.4: Commit**

```bash
git add main.py
git commit -m "feat(main): add --resume and --output argparse flags with converter pipeline

- --resume accepts .md, .docx, .pdf with auto-detection fallback
- --output is repeatable: md, pdf, docx (default: md)
- Input conversion via InputConverterRegistry (docx/pdf → resume.md)
- Output via OutputConverterRegistry.convert_all()
- All ResumeConverterError subclasses caught at top level

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Self-Review Checklist

**Spec coverage:**

| Spec requirement | Covered by |
|---|---|
| `.docx` and `.pdf` input | Task 3 — `DocxInputConverter`, `PdfInputConverter` |
| Local conversion only | Task 3 — `markitdown` runs locally |
| Save to `files/resume.md` | Task 3 — `InputConverterRegistry.convert_and_save()` |
| `--resume` CLI flag + auto-detect | Task 3 + Task 6 |
| `--output` CLI flag (default `md`) | Task 6 — argparse with `append` action |
| `md`, `pdf`, `docx` output formats | Task 5 — `MarkdownOutputConverter`, `PdfOutputConverter`, `DocxOutputConverter` |
| All custom exceptions | Task 2 |
| Exceptions caught in `main.py`, never in converters | Task 6 — top-level `except ResumeConverterError` |
| `.md` input passthrough (no conversion) | Task 6 — `suffix.lower() not in (".docx", ".pdf")` branch |
| `files/resume.md` fallback in auto-detect | Task 3 — `auto_detect_resume()` checks `.md` last |
| `python-docx` for `.docx` output | Task 5 — `DocxOutputConverter` |
| `pdf_converter.py` wrapped (not deleted) | Task 5 — `PdfOutputConverter` imports `markdown_to_pdf` |
| `markdown_writer.py` not deleted | No task modifies or deletes it |
| Output files named `tailored_resume.{ext}` | Task 5 — `OutputConverterRegistry.convert_all()` |

All spec requirements are covered. No TBDs or placeholders.
