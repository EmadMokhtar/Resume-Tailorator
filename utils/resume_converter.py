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
    """Raised when a file cannot be converted to the target format."""


class EmptyConversionResultError(ResumeConverterError):
    """Raised when conversion produces empty/whitespace output."""


class NoResumeFileFoundError(ResumeConverterError):
    """Raised when auto-detection finds no supported resume file."""


class OutputConversionFailedError(ResumeConverterError):
    """Raised when writing an output file fails."""


class UnsupportedOutputFormatError(ResumeConverterError):
    """Raised when the requested output format is not supported."""


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
            import zipfile

            # Validate that the file is a ZIP archive (docx is a ZIP)
            if not zipfile.is_zipfile(input_path):
                raise ConversionFailedError(
                    f"File is not a valid .docx (ZIP) archive: {input_path}"
                )

            from markitdown import MarkItDown

            md = MarkItDown()
            result = md.convert(str(input_path))
            markdown = result.text_content
        except ConversionFailedError:
            raise
        except Exception as exc:
            raise ConversionFailedError(f"Failed to convert .docx: {exc}") from exc

        if not markdown.strip():
            raise EmptyConversionResultError(
                "Conversion produced empty content. Check your input file."
            )
        return markdown


class PdfInputConverter:
    """Converts .pdf → Markdown via markitdown."""

    def convert(self, input_path: Path) -> str:
        try:
            # Validate PDF magic bytes
            with open(input_path, "rb") as f:
                header = f.read(5)
            if header != b"%PDF-":
                raise ConversionFailedError(
                    f"File is not a valid PDF (missing %PDF- header): {input_path}"
                )

            from markitdown import MarkItDown

            md = MarkItDown()
            result = md.convert(str(input_path))
            markdown = result.text_content
        except ConversionFailedError:
            raise
        except Exception as exc:
            raise ConversionFailedError(f"Failed to convert .pdf: {exc}") from exc

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

    def __init__(self) -> None:
        self._converters: dict[str, ResumeConverterProtocol] = {
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
            raise ResumeFileNotFoundError(f"Resume file not found at {input_path}")
        converter = self.get(input_path.suffix)
        markdown = converter.convert(input_path)
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(markdown, encoding="utf-8")
        except OSError as exc:
            raise OutputConversionFailedError(
                f"Failed to write output file {output_path}: {exc}"
            ) from exc
        return markdown


# ---------------------------------------------------------------------------
# Auto-detection
# ---------------------------------------------------------------------------


def auto_detect_resume(files_dir: Path) -> Path:
    """Return first resume file found in files_dir using priority order.

    Priority: resume.docx > resume.pdf > resume.md
    Raises NoResumeFileFoundError if none exist.
    """
    if not files_dir.is_dir():
        raise NoResumeFileFoundError(f"Resume directory does not exist: {files_dir}")
    for name in ("resume.docx", "resume.pdf", "resume.md"):
        candidate = files_dir / name
        if candidate.exists():
            return candidate
    raise NoResumeFileFoundError(
        "No resume file found in files/. Add resume.docx, resume.pdf, or resume.md, "
        "or use --resume."
    )
