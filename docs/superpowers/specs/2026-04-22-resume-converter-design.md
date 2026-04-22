# Design: Resume Converter (Input: Word/PDF → Markdown; Output: Markdown/PDF/DOCX)

**Date:** 2026-04-22  
**Status:** Approved

---

## Problem

The Resume Tailorator has two conversion gaps:

1. **Input**: It accepts only `files/resume.md`. Users with resumes in Word (`.docx`) or PDF (`.pdf`) must manually convert before using the tool.
2. **Output**: It always produces all formats (`.md` and `.pdf`). Users have no control over which output formats are generated, and `.docx` is not supported at all.

This design adds local, offline conversion on both sides of the workflow.

---

## Goals

- Accept `.docx` and `.pdf` resume files as input
- Convert them locally to Markdown (no external API calls)
- Save the result to `files/resume.md` (overwrite — single source of truth)
- Support CLI `--resume` argument with fallback to auto-detection in `files/`
- Let users control output format(s) via repeatable `--output` CLI flag (default: `md`)
- Support output formats: `md`, `pdf`, `docx`
- Fail fast with clear, typed error messages on any conversion problem

---

## Out of Scope

- `.doc` (legacy Word), `.odt`, `.rtf` support
- Conversion of job postings
- Any cloud-based or API-backed conversion
- HTML output format

---

## Architecture & Data Flow

```
User runs:
  python main.py --resume path/to/cv.docx --output md --output pdf
  python main.py --resume path/to/cv.pdf
  python main.py                           ← auto-detects in files/, default output: md

       │
       ▼
  main.py  (argparse)
       │  resolves file path + output formats
       ▼
  utils/resume_converter.py              ← INPUT side
  ┌──────────────────────────────────────────────┐
  │  InputConverterRegistry                      │
  │  ├── ".docx"  →  DocxInputConverter          │
  │  └── ".pdf"   →  PdfInputConverter           │
  │                                              │
  │  Each implements ResumeConverterProtocol:    │
  │    convert(input_path: Path) -> str          │
  └──────────────────────────────────────────────┘
       │  markdown string
       │  saved to files/resume.md
       ▼
  validate_inputs.py  (unchanged — validates files/resume.md)
       │
       ▼
  ResumeTailorWorkflow.run(resume_text, ...)  (unchanged)
       │  tailored resume markdown string
       ▼
  utils/resume_output_converter.py       ← OUTPUT side
  ┌──────────────────────────────────────────────┐
  │  OutputConverterRegistry                     │
  │  ├── "md"   →  MarkdownOutputConverter       │
  │  ├── "pdf"  →  PdfOutputConverter            │
  │  └── "docx" →  DocxOutputConverter           │
  │                                              │
  │  Each implements OutputConverterProtocol:    │
  │    convert(content: str, output_path: Path)  │
  └──────────────────────────────────────────────┘
       │  one file written per requested format
       ▼
  files/tailored_resume.md / .pdf / .docx
```

**Auto-detection priority** (when `--resume` is not provided):

1. `files/resume.docx`
2. `files/resume.pdf`
3. `files/resume.md` (existing behaviour — no conversion)

If none found → `NoResumeFileFoundError`.

---

## Components

### `utils/resume_converter.py` — Input side

Contains the Protocol, concrete converters, registry, and all custom exceptions.

**Protocol:**
```python
class ResumeConverterProtocol(Protocol):
    def convert(self, input_path: Path) -> str:
        """Return markdown string from input file."""
        ...
```

**Converters:**
```python
class DocxInputConverter:
    """Converts .docx → markdown via markitdown."""
    def convert(self, input_path: Path) -> str: ...

class PdfInputConverter:
    """Converts .pdf → markdown via markitdown."""
    def convert(self, input_path: Path) -> str: ...
```

**Registry:**
```python
class InputConverterRegistry:
    _converters: dict[str, ResumeConverterProtocol] = {
        ".docx": DocxInputConverter(),
        ".pdf": PdfInputConverter(),
    }

    def get(self, ext: str) -> ResumeConverterProtocol:
        """Return converter for extension, raise UnsupportedFormatError if unknown."""
        ...

    def convert_and_save(self, input_path: Path, output_path: Path) -> str:
        """Convert input file and write markdown to output_path. Returns markdown string."""
        ...
```

Adding a new input format = one new class + one registry entry.

**Custom Exceptions:**
```python
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
```

---

### `utils/resume_output_converter.py` — Output side

Contains the Protocol, concrete output converters, registry, and output-specific exceptions.

**Protocol:**
```python
class OutputConverterProtocol(Protocol):
    def convert(self, content: str, output_path: Path) -> None:
        """Write the tailored resume content to output_path in the target format."""
        ...
```

**Converters:**
```python
class MarkdownOutputConverter:
    """Writes tailored resume as .md — wraps existing markdown_writer.py."""
    def convert(self, content: str, output_path: Path) -> None: ...

class PdfOutputConverter:
    """Writes tailored resume as .pdf — wraps existing pdf_converter.py."""
    def convert(self, content: str, output_path: Path) -> None: ...

class DocxOutputConverter:
    """Writes tailored resume as .docx via python-docx."""
    def convert(self, content: str, output_path: Path) -> None: ...
```

`MarkdownOutputConverter` and `PdfOutputConverter` delegate to the existing utility functions — they are **wrapped, not replaced**. The existing `markdown_writer.py` and `pdf_converter.py` files remain unchanged.

`DocxOutputConverter` uses `python-docx` to render the Markdown content into a Word document with basic heading/paragraph/bullet structure.

**Registry:**
```python
class OutputConverterRegistry:
    _converters: dict[str, OutputConverterProtocol] = {
        "md":   MarkdownOutputConverter(),
        "pdf":  PdfOutputConverter(),
        "docx": DocxOutputConverter(),
    }

    def get(self, fmt: str) -> OutputConverterProtocol:
        """Return converter for format string, raise UnsupportedOutputFormatError if unknown."""
        ...

    def convert_all(self, content: str, formats: list[str], output_dir: Path) -> list[Path]:
        """Write content in each requested format. Returns list of written paths."""
        ...
```

**Output-specific exceptions** (defined in `resume_converter.py` alongside the input exceptions — one place for all custom errors, importable by both converter modules):
```python
class OutputConversionFailedError(ResumeConverterError):
    """Raised when writing an output file fails."""

class UnsupportedOutputFormatError(ResumeConverterError):
    """Raised when the requested output format is not supported."""
```

---

### `main.py` — updated entry point

- Add `argparse` with:
  - Optional `--resume` argument (path to input file)
  - Repeatable `--output` argument, choices `["md", "pdf", "docx"]`, default `["md"]`
- **Input flow**:
  - If `--resume` ends in `.docx` or `.pdf`: call `InputConverterRegistry.convert_and_save()`, overwrite `files/resume.md`
  - If `--resume` ends in `.md`: read directly, no conversion, no overwrite
  - If `--resume` not provided: auto-detect in `files/` using priority order
- **Output flow**: after workflow completes, call `OutputConverterRegistry.convert_all()` for each requested format; output files named `tailored_resume.{ext}` in `files/`
- Catch all `ResumeConverterError` subclasses at top level, print `❌` message, exit
- Remove existing hard-coded calls to `markdown_writer.py` and `pdf_converter.py` (now handled by output registry)

---

### `pyproject.toml`

Add dependencies:
```toml
"markitdown[docx,pdf]>=0.1.0"
"python-docx>=1.1.0"
```

---

## Error Handling

| Exception | Trigger | User-facing message |
|---|---|---|
| `ResumeFileNotFoundError` | `--resume` path doesn't exist | `❌ Error: Resume file not found at <path>` |
| `UnsupportedFormatError` | Input extension not in registry | `❌ Error: Unsupported format '<ext>'. Supported: .docx, .pdf, .md` |
| `ConversionFailedError` | markitdown raises internally | `❌ Error: Failed to convert resume: <reason>` |
| `EmptyConversionResultError` | Conversion returns blank string | `❌ Error: Conversion produced empty content. Check your input file.` |
| `NoResumeFileFoundError` | Auto-detect finds nothing | `❌ Error: No resume file found in files/. Add resume.docx, resume.pdf, or resume.md, or use --resume.` |
| `UnsupportedOutputFormatError` | `--output` value not in registry | `❌ Error: Unsupported output format '<fmt>'. Supported: md, pdf, docx` |
| `OutputConversionFailedError` | Write to output file fails | `❌ Error: Failed to write <fmt> output: <reason>` |

All exceptions caught in `main.py`. Converter classes only raise — never print or exit.

---

## Testing

**Input converter tests (`utils/resume_converter.py`):**
- Unit tests for `DocxInputConverter.convert()` and `PdfInputConverter.convert()` using fixture files
- Unit tests for `InputConverterRegistry.get()` — correct converter per extension, `UnsupportedFormatError` on unknown
- Unit test for `InputConverterRegistry.convert_and_save()` — verifies markdown written to output path
- Unit tests for each custom input exception scenario (mock markitdown to simulate failures)
- Integration test — end-to-end: `.docx`/`.pdf` fixture → `files/resume.md` contains valid markdown

**Output converter tests (`utils/resume_output_converter.py`):**
- Unit tests for each `*OutputConverter.convert()` using a fixture markdown string
- Unit tests for `OutputConverterRegistry.get()` — correct converter per format, `UnsupportedOutputFormatError` on unknown
- Unit test for `OutputConverterRegistry.convert_all()` — verifies each format file written
- Unit tests for `OutputConversionFailedError` (mock write failures)

Existing workflow tests remain unaffected.

---

## Files Changed

| File | Change |
|---|---|
| `utils/resume_converter.py` | **New** — input Protocol, converters, registry, all custom exceptions |
| `utils/resume_output_converter.py` | **New** — output Protocol, converters, registry |
| `main.py` | **Updated** — argparse (`--resume`, `--output`), input conversion step, output registry call, error handling |
| `pyproject.toml` | **Updated** — add `markitdown[docx,pdf]` and `python-docx` |
| `utils/validate_inputs.py` | **No change** |
| `utils/markdown_writer.py` | **No change** — wrapped by `MarkdownOutputConverter` |
| `utils/pdf_converter.py` | **No change** — wrapped by `PdfOutputConverter` |
| `workflows/`, `models/`, `tools/` | **No change** |
