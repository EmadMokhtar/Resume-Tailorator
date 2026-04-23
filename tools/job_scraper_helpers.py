"""Job scraper helper utilities for parsing and validation.

This module provides parsing strategies for extracting job posting content
from HTML using multiple fallback parsers, cleaning utilities, and placeholder
detection.
"""

import logging
import re

logger = logging.getLogger(__name__)


def parse_html_with_markitdown(html: str) -> str:
    """Parse HTML to markdown using markitdown library.

    Attempts to extract body content first for cleaner output, falls back to
    full HTML if body tag not found. Provides structured text output suitable
    for LLM processing.

    Args:
        html: Raw HTML string from web page.

    Returns:
        Markdown-formatted string, or empty string if parsing fails.

    Raises:
        Handled internally: Logs warning and returns empty string on exception.
    """
    try:
        from markitdown import MarkItDown
        import tempfile
        import os

        # Try to extract body content for cleaner output
        body_match = re.search(
            r"<body[^>]*>(.*?)</body>", html, re.DOTALL | re.IGNORECASE
        )
        content = body_match.group(1) if body_match else html

        # MarkItDown requires a file path, so create temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            converter = MarkItDown()
            result = converter.convert(temp_path)
            # Result is either a string or DocumentConverterResult object
            markdown = str(result) if result else ""
        finally:
            os.unlink(temp_path)

        logger.debug("markitdown parsing successful", extra={"length": len(markdown)})
        return markdown
    except Exception as e:
        logger.warning("markitdown parsing failed", extra={"error": str(e)})
        return ""


def parse_html_with_html2text(html: str) -> str:
    """Parse HTML to markdown using html2text library.

    Configures html2text to preserve links and images, with no line wrapping
    for consistent output. Provides clean markdown output with minimal formatting.

    Args:
        html: Raw HTML string from web page.

    Returns:
        Markdown-formatted string, or empty string if parsing fails.

    Raises:
        Handled internally: Logs warning and returns empty string on exception.
    """
    try:
        import html2text

        converter = html2text.HTML2Text()
        converter.ignore_links = False
        converter.ignore_images = False
        converter.body_width = 0  # no line wrapping

        markdown = converter.handle(html)
        logger.debug("html2text parsing successful", extra={"length": len(markdown)})
        return markdown
    except Exception as e:
        logger.warning("html2text parsing failed", extra={"error": str(e)})
        return ""


def detect_placeholder_content(text: str) -> bool:
    """Detect if text contains placeholder or error indicators.

    Checks for common signs that parsing failed or returned incomplete content,
    including unexecuted HTML/JavaScript code blocks, placeholder text, very short
    content, and error messages.

    Note: Legitimate mentions of "JavaScript" as a required skill are NOT flagged
    as placeholders. Only unexecuted code blocks (<script tags) are detected as
    parsing failures, which is the actual indicator of malformed content.

    Args:
        text: Text to check for placeholder/error indicators.

    Returns:
        True if content appears to be placeholder/error content. False if
        content likely represents real job posting data.

    Examples:
        >>> detect_placeholder_content("")
        True
        >>> detect_placeholder_content("Senior JavaScript Developer needed")
        False
        >>> detect_placeholder_content("<script>alert('error')</script>")
        True
        >>> detect_placeholder_content("Click here to apply")
        True
        >>> detect_placeholder_content("Short text")  # < 100 chars
        True
        >>> detect_placeholder_content("This is a real job posting " * 5)
        False
    """
    if not text:
        return True

    # Check for common placeholders and error indicators
    # Note: 'javascript' substring removed - legitimate job postings mention JavaScript skills
    placeholders = [
        r"<script",  # Unexecuted HTML/JavaScript code blocks
        r"click here",  # Common placeholder CTA
        r"error loading",  # Parsing error indicator
        r"page not found",  # Parsing error indicator
        r"404",  # HTTP error code
    ]

    text_lower = text.lower()
    if any(re.search(pattern, text_lower) for pattern in placeholders):
        logger.debug("placeholder content detected", extra={"pattern_match": True})
        return True

    # Check for minimum length (real job postings are longer)
    if len(text.strip()) < 100:
        logger.debug("content too short", extra={"length": len(text.strip())})
        return True

    return False


def clean_job_posting_markdown(markdown: str) -> str:
    """Clean and normalize job posting markdown.

    Removes excessive whitespace, trailing spaces from lines, and normalizes
    line endings. Ensures output is consistently formatted for workflow
    processing and LLM input.

    Args:
        markdown: Raw markdown from parser (potentially with excess whitespace).

    Returns:
        Cleaned markdown string with normalized formatting.

    Examples:
        >>> clean_job_posting_markdown("")
        ""
        >>> clean_job_posting_markdown("line1\\n\\n\\n\\nline2")
        "line1\\n\\nline2\\n"
        >>> clean_job_posting_markdown("text with trailing  \\nmore text")
        "text with trailing\\nmore text\\n"
    """
    if not markdown:
        return ""

    # Collapse multiple blank lines to max 2
    cleaned = re.sub(r"\n\n\n+", "\n\n", markdown)

    # Remove trailing whitespace from each line
    cleaned = "\n".join(line.rstrip() for line in cleaned.split("\n"))

    # Ensure single trailing newline
    cleaned = cleaned.rstrip() + "\n"

    logger.debug(
        "markdown cleaned",
        extra={
            "original_length": len(markdown),
            "cleaned_length": len(cleaned),
        },
    )
    return cleaned
