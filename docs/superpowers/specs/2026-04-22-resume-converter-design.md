# Design: Resume File Converter (Word & PDF → Markdown)

**Date:** 2026-04-22  
**Status:** Approved

---

## Problem

The Resume Tailorator currently accepts only a Markdown file (`files/resume.md`) as input. Users who have their resume in Word (`.docx`) or PDF (`.pdf`) format must manually convert it before using the tool. This feature adds local, offline conversion as a first-class step before the AI agent workflow begins.

---

## Goals

- Accept `.docx` and `.pdf` resume files as input
- Convert them locally to Markdown (no external API calls)
- Save the result to `files/resume.md` (overwrite — single source of truth)
- Support CLI `--resume` argument with fallback to auto-detection in `files/`
- Fail fast with clear, typed error messages on any conversion problem

---

## Out of Scope

- `.doc` (legacy Word), `.odt`, `.rtf` support
- Conversion of job postings
- Any cloud-based or API-backed conversion

---

## Architecture & Data Flow

```
User runs:
  python main.py --resume path/to/cv.docx
  python main.py --resume path/to/cv.pdf
  python main.py                           ← auto-detects in files/

       │
       ▼
  main.py  (argparse)
       │  resolves file path
       ▼
  utils/resume_converter.py
  ┌──────────────────────────────────────────────┐
  │  ConverterRegistry                           │
  │  ├── ".docx"  →  DocxConverter               │
  │  └── ".pdf"   →  PdfConverter                │
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
```

**Auto-detection priority** (when `--resume` is not provided):

1. `files/resume.docx`
2. `files/resume.pdf`
3. `files/resume.md` (existing behaviour — no conversion)

If none found → `NoResumeFileFoundError`.

---

## Components

### `utils/resume_converter.py`

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
class DocxConverter:
    """Converts .docx → markdown via markitdown."""
    def convert(self, input_path: Path) -> str: ...

class PdfConverter:
    """Converts .pdf → markdown via markitdown."""
    def convert(self, input_path: Path) -> str: ...
```

**Registry:**
```python
class ConverterRegistry:
    _converters: dict[str, ResumeConverterProtocol] = {
        ".docx": DocxConverter(),
        ".pdf": PdfConverter(),
    }

    def get(self, ext: str) -> ResumeConverterProtocol:
        """Return converter for extension, raise UnsupportedFormatError if unknown."""
        ...

    def convert_and_save(self, input_path: Path, output_path: Path) -> str:
        """Convert input file and write markdown to output_path. Returns markdown string."""
        ...
```

Adding a new format in the future = one new class + one registry entry.

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

### `main.py` — updated entry point

- Add `argparse` with optional `--resume` argument
- If `--resume` provided with `.docx` or `.pdf`: call `ConverterRegistry.convert_and_save()`, which converts and overwrites `files/resume.md`
- If `--resume` provided with `.md`: read directly, no conversion, no overwrite needed — use as-is
- If not provided: auto-detect in `files/` using priority order above
- Catch all `ResumeConverterError` subclasses at top level, print `❌` message, exit
- No changes to workflow invocation

---

### `pyproject.toml`

Add dependency:
```toml
"markitdown[docx,pdf]>=0.1.0"
```

---

### `utils/validate_inputs.py`

No structural changes needed. Conversion runs before validation, so `files/resume.md` is always present by the time validation runs.

---

## Error Handling

| Exception | Trigger | User-facing message |
|---|---|---|
| `ResumeFileNotFoundError` | `--resume` path doesn't exist | `❌ Error: Resume file not found at <path>` |
| `UnsupportedFormatError` | Extension not in registry | `❌ Error: Unsupported format '<ext>'. Supported: .docx, .pdf, .md` |
| `ConversionFailedError` | markitdown raises internally | `❌ Error: Failed to convert resume: <reason>` |
| `EmptyConversionResultError` | Conversion returns blank string | `❌ Error: Conversion produced empty content. Check your input file.` |
| `NoResumeFileFoundError` | Auto-detect finds nothing | `❌ Error: No resume file found in files/. Add resume.docx, resume.pdf, or resume.md, or use --resume.` |

All exceptions caught in `main.py`. Converter classes only raise — never print or exit.

---

## Testing

- **Unit tests** for `DocxConverter.convert()` and `PdfConverter.convert()` using fixture files
- **Unit tests** for `ConverterRegistry.get()` — correct converter per extension, `UnsupportedFormatError` on unknown
- **Unit test** for `ConverterRegistry.convert_and_save()` — verifies markdown written to output path
- **Unit tests** for each custom exception scenario (mock markitdown to simulate failures)
- **Integration test** — end-to-end: `.docx`/`.pdf` fixture → `files/resume.md` contains valid markdown
- Existing workflow tests remain unaffected

---

## Files Changed

| File | Change |
|---|---|
| `utils/resume_converter.py` | **New** — Protocol, converters, registry, exceptions |
| `main.py` | **Updated** — argparse, conversion step, error handling |
| `pyproject.toml` | **Updated** — add `markitdown[docx,pdf]` |
| `utils/validate_inputs.py` | **No change** |
| `workflows/`, `models/`, `tools/` | **No change** |
