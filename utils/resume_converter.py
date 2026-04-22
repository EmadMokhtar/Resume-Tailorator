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
