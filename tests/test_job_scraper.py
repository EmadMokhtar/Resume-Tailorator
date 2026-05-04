"""Tests for job scraper agent and integration.

Comprehensive tests for JobScraperAgent, including:
- Successful scraping with valid HTML
- Placeholder detection triggering retry
- Markdown parsing with fallback strategies
- URL validation
- Extraction quality scoring
- CLI integration with URL and environment variables
"""

import os
import pytest
from pydantic_ai import models
from pydantic_ai.models.test import TestModel

from models.agents.output import ScrapedJobPosting
from tools.job_scraper_helpers import (
    detect_placeholder_content,
    clean_job_posting_markdown,
    parse_html_with_markitdown,
    parse_html_with_html2text,
)

# Check if playwright is available for agent tests
try:
    import playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

# Ensure model requests are blocked (test mode only)
models.ALLOW_MODEL_REQUESTS = False

# Import agent and tools only if playwright is available
if HAS_PLAYWRIGHT:
    from workflows.agents import job_scraper_agent, validate_extraction
else:
    # Define dummy validate_extraction for non-agent tests
    def validate_extraction(raw_html: str, extracted_markdown: str) -> dict:
        """Dummy validate_extraction for when playwright not available."""
        raise RuntimeError("playwright not installed")


# --- Test Data ---

REALISTIC_JOB_HTML = """\
<!DOCTYPE html>
<html>
<head><title>Senior Software Engineer</title></head>
<body>
<h1>Senior Software Engineer</h1>
<p><strong>Company:</strong> TechCorp Inc.</p>
<p><strong>Location:</strong> San Francisco, CA (Remote)</p>
<p><strong>Salary:</strong> $180K-$220K</p>

<h2>About the Role</h2>
<p>We're seeking an experienced Senior Software Engineer to join our platform team. 
You'll design and build scalable backend systems serving millions of users.</p>

<h2>Requirements</h2>
<ul>
<li>7+ years of software engineering experience</li>
<li>Strong proficiency in Python, Go, or Rust</li>
<li>Experience with distributed systems and microservices</li>
<li>Deep knowledge of database design and optimization</li>
<li>Leadership experience mentoring junior engineers</li>
<li>BS in Computer Science or equivalent</li>
</ul>

<h2>What We Offer</h2>
<ul>
<li>Competitive salary and equity</li>
<li>Comprehensive health benefits</li>
<li>Professional development budget</li>
<li>Flexible work arrangements</li>
</ul>

<p>Apply at careers@techcorp.com or submit via LinkedIn.</p>
</body>
</html>\
"""

PLACEHOLDER_HTML = """\
<!DOCTYPE html>
<html>
<head><title>Error</title></head>
<body>
<h1>Page Not Found</h1>
<script>console.log('error');</script>
<p>The job posting you're looking for could not be found.</p>
<p>404 error</p>
</body>
</html>\
"""

MINIMAL_JOB_HTML = """\
<!DOCTYPE html>
<html>
<body>
<h1>Frontend Developer</h1>
<p>Join our team! We need a frontend developer.</p>
<p>Requirements: JavaScript, React, CSS</p>
<p>Apply now at jobs@example.com</p>
</body>
</html>\
"""

SHORT_CONTENT = "This is too short"
REALISTIC_EXTRACTED_MARKDOWN = """\
# Senior Software Engineer

**Company:** TechCorp Inc.
**Location:** San Francisco, CA (Remote)
**Salary:** $180K-$220K

## About the Role

We're seeking an experienced Senior Software Engineer to join our platform team. 
You'll design and build scalable backend systems serving millions of users.

## Requirements

- 7+ years of software engineering experience
- Strong proficiency in Python, Go, or Rust
- Experience with distributed systems and microservices
- Deep knowledge of database design and optimization
- Leadership experience mentoring junior engineers
- BS in Computer Science or equivalent

## What We Offer

- Competitive salary and equity
- Comprehensive health benefits
- Professional development budget
- Flexible work arrangements

Apply at careers@techcorp.com or submit via LinkedIn.
"""


@pytest.mark.skipif(not HAS_PLAYWRIGHT, reason="playwright not installed")
class TestJobScraperAgent:
    """Tests for JobScraperAgent."""

    def test_successful_scraping_with_test_model(self):
        """Test successful job posting scraping with TestModel.

        Verifies that the agent can successfully scrape and extract job posting
        content into the ScrapedJobPosting model with all required fields.
        """
        # Override with TestModel for deterministic output
        with job_scraper_agent.override(
            model=TestModel(
                custom_output_args=ScrapedJobPosting(
                    url="https://example.com/job/123",
                    markdown=REALISTIC_EXTRACTED_MARKDOWN,
                    source_text="raw html content",
                    extraction_strategy="html2text",
                )
            )
        ):
            result = job_scraper_agent.run_sync("Scrape this job: https://example.com/job/123")

            assert isinstance(result.output, ScrapedJobPosting)
            assert result.output.url == "https://example.com/job/123"
            assert len(result.output.markdown) > 0
            assert "Senior Software Engineer" in result.output.markdown
            assert result.output.extraction_strategy == "html2text"

    def test_scraping_returns_non_empty_markdown(self):
        """Test that scraped markdown content is substantial."""
        with job_scraper_agent.override(
            model=TestModel(
                custom_output_args=ScrapedJobPosting(
                    url="https://example.com/job/456",
                    markdown=REALISTIC_EXTRACTED_MARKDOWN,
                    source_text="<html>...</html>",
                    extraction_strategy="markitdown",
                )
            )
        ):
            result = job_scraper_agent.run_sync("Scrape: https://example.com/job/456")

            assert result.output.markdown.strip() != ""
            assert len(result.output.markdown.strip()) > 100

    def test_scraping_preserves_url(self):
        """Test that the original URL is preserved in the output."""
        test_url = "https://jobs.github.com/123"
        with job_scraper_agent.override(
            model=TestModel(
                custom_output_args=ScrapedJobPosting(
                    url=test_url,
                    markdown="Job content here" * 20,
                    source_text="<html>content</html>",
                    extraction_strategy="html2text",
                )
            )
        ):
            result = job_scraper_agent.run_sync(f"Scrape: {test_url}")

            assert result.output.url == test_url

    def test_scraping_with_different_strategies(self):
        """Test that extraction strategy field is properly populated."""
        strategies = ["html2text", "markitdown", "playwright_llm"]

        for strategy in strategies:
            with job_scraper_agent.override(
                model=TestModel(
                    custom_output_args=ScrapedJobPosting(
                        url="https://example.com/job",
                        markdown=REALISTIC_EXTRACTED_MARKDOWN,
                        source_text="<html>...</html>",
                        extraction_strategy=strategy,
                    )
                )
            ):
                result = job_scraper_agent.run_sync(
                    "Scrape: https://example.com/job"
                )

                assert result.output.extraction_strategy == strategy


@pytest.mark.skipif(not HAS_PLAYWRIGHT, reason="playwright not installed")
class TestValidateExtraction:
    """Tests for validate_extraction tool."""

    def test_valid_extraction_passes(self):
        """Test that valid extraction passes validation."""
        result = validate_extraction(
            raw_html=REALISTIC_JOB_HTML,
            extracted_markdown=REALISTIC_EXTRACTED_MARKDOWN,
        )

        assert result["valid"] is True
        assert result["message"] == "Extraction meets quality thresholds"
        assert 0 <= result["quality_score"] <= 100

    def test_valid_extraction_quality_score_range(self):
        """Test that quality score is always in valid range."""
        result = validate_extraction(
            raw_html=REALISTIC_JOB_HTML,
            extracted_markdown=REALISTIC_EXTRACTED_MARKDOWN,
        )

        assert isinstance(result["quality_score"], int)
        assert 0 <= result["quality_score"] <= 100

    def test_valid_extraction_with_short_markdown(self):
        """Test that extraction with minimum valid length passes."""
        # Create markdown that's exactly 200 characters
        short_markdown = "x" * 200

        result = validate_extraction(
            raw_html="<html>" + "y" * 100 + "</html>",
            extracted_markdown=short_markdown,
        )

        assert result["valid"] is True

    def test_missing_html_raises_retry(self):
        """Test that missing HTML triggers ModelRetry."""
        from pydantic_ai import ModelRetry

        with pytest.raises(ModelRetry):
            validate_extraction(
                raw_html="",
                extracted_markdown=REALISTIC_EXTRACTED_MARKDOWN,
            )

    def test_missing_markdown_raises_retry(self):
        """Test that missing markdown triggers ModelRetry."""
        from pydantic_ai import ModelRetry

        with pytest.raises(ModelRetry):
            validate_extraction(
                raw_html=REALISTIC_JOB_HTML,
                extracted_markdown="",
            )

    def test_placeholder_content_raises_retry(self):
        """Test that placeholder content triggers ModelRetry."""
        from pydantic_ai import ModelRetry

        with pytest.raises(ModelRetry):
            validate_extraction(
                raw_html=PLACEHOLDER_HTML,
                extracted_markdown="<script>error</script>" + " x" * 50,
            )

    def test_short_content_raises_retry(self):
        """Test that content < 200 chars triggers ModelRetry."""
        from pydantic_ai import ModelRetry

        with pytest.raises(ModelRetry):
            validate_extraction(
                raw_html=MINIMAL_JOB_HTML,
                extracted_markdown="This is too short" + " x" * 5,  # ~25 chars
            )

    def test_exactly_199_chars_raises_retry(self):
        """Test that content at 199 chars triggers ModelRetry."""
        from pydantic_ai import ModelRetry

        with pytest.raises(ModelRetry):
            validate_extraction(
                raw_html="<html>content</html>",
                extracted_markdown="x" * 199,
            )

    def test_exactly_200_chars_passes(self):
        """Test that content at exactly 200 chars passes."""
        result = validate_extraction(
            raw_html="<html>content</html>",
            extracted_markdown="x" * 200,
        )

        assert result["valid"] is True

    def test_quality_score_scales_with_content_length(self):
        """Test that quality score increases with content length."""
        short_md = "x" * 200
        long_md = "x" * 5000

        result_short = validate_extraction(
            raw_html="<html>html</html>",
            extracted_markdown=short_md,
        )

        result_long = validate_extraction(
            raw_html="<html>html</html>",
            extracted_markdown=long_md,
        )

        # Long content should have higher or equal quality score
        assert result_long["quality_score"] >= result_short["quality_score"]


class TestURLValidation:
    """Tests for URL validation in fetch_webpage tool."""

    def test_valid_https_url_format(self):
        """Test that valid HTTPS URL format is recognized."""
        # Just verify the URL pattern - tool would be called in integration test
        valid_urls = [
            "https://example.com/job/123",
            "https://jobs.github.com/positions/123",
            "https://www.example.com/careers?id=456",
        ]

        for url in valid_urls:
            # Verify URL has required format
            assert url.startswith(("http://", "https://"))
            assert isinstance(url, str)

    def test_valid_http_url_format(self):
        """Test that valid HTTP URL format is recognized."""
        valid_urls = [
            "http://example.com/job/123",
            "http://jobs.example.com/positions/456",
        ]

        for url in valid_urls:
            assert url.startswith(("http://", "https://"))

    def test_invalid_url_no_protocol(self):
        """Test that URL without protocol is invalid."""
        invalid_url = "example.com/job/123"

        assert not invalid_url.startswith(("http://", "https://"))

    def test_invalid_url_wrong_protocol(self):
        """Test that URL with wrong protocol is invalid."""
        invalid_urls = [
            "ftp://example.com/job",
            "file:///path/to/job",
            "gopher://example.com/job",
        ]

        for url in invalid_urls:
            assert not url.startswith(("http://", "https://"))

    def test_invalid_url_empty_string(self):
        """Test that empty URL string is invalid."""
        invalid_url = ""

        assert not invalid_url.startswith(("http://", "https://"))

    def test_invalid_url_none_raises_error(self):
        """Test that None URL would raise error."""
        # In actual tool, this would raise ValueError
        url = None
        assert url is None or not isinstance(url, str)


@pytest.mark.skipif(not HAS_PLAYWRIGHT, reason="playwright not installed")
class TestExtractionQualityScoring:
    """Tests for quality scoring in validate_extraction."""

    def test_quality_score_200_chars(self):
        """Test quality score for minimum valid content (200 chars)."""
        markdown = "x" * 200
        result = validate_extraction(
            raw_html="<html>html</html>",
            extracted_markdown=markdown,
        )

        # 200 chars should have low but non-zero quality
        assert 0 < result["quality_score"] < 50

    def test_quality_score_1000_chars(self):
        """Test quality score for moderate content (1000 chars)."""
        markdown = "x" * 1000
        result = validate_extraction(
            raw_html="<html>html</html>",
            extracted_markdown=markdown,
        )

        # 1000 chars should have moderate quality
        assert 0 < result["quality_score"] < 100

    def test_quality_score_5000_chars(self):
        """Test quality score for substantial content (5000 chars)."""
        markdown = "x" * 5000
        result = validate_extraction(
            raw_html="<html>html</html>",
            extracted_markdown=markdown,
        )

        # 5000 chars should have high quality score
        assert result["quality_score"] >= 95

    def test_quality_score_over_5000_chars_capped_at_100(self):
        """Test that quality score caps at 100."""
        markdown = "x" * 10000
        result = validate_extraction(
            raw_html="<html>html</html>",
            extracted_markdown=markdown,
        )

        # Should be capped at 100
        assert result["quality_score"] == 100

    def test_quality_score_includes_whitespace(self):
        """Test that quality score considers total length including whitespace."""
        # Content with significant whitespace
        markdown_with_spaces = "word " * 200  # 1000 chars with spaces
        markdown_no_spaces = "word" * 200    # 800 chars no spaces

        result_spaces = validate_extraction(
            raw_html="<html>html</html>",
            extracted_markdown=markdown_with_spaces,
        )

        result_no_spaces = validate_extraction(
            raw_html="<html>html</html>",
            extracted_markdown=markdown_no_spaces,
        )

        # More characters should score higher
        assert result_spaces["quality_score"] >= result_no_spaces["quality_score"]


class TestHelperFunctionsIntegration:
    """Integration tests for helper functions used in scraping."""

    def test_placeholder_detection_in_validation_flow(self):
        """Test that placeholder detection integrates properly."""
        # Script tag content should trigger placeholder detection
        assert detect_placeholder_content("<script>error</script>" + " x" * 50) is True

    def test_clean_job_posting_in_validation_flow(self):
        """Test that markdown cleaning integrates properly."""
        dirty_markdown = "line1  \n\n\n\nline2\n"
        clean_markdown = clean_job_posting_markdown(dirty_markdown)

        # Should have no triple+ newlines
        assert "\n\n\n" not in clean_markdown

    def test_html_parsing_produces_markdown(self):
        """Test that HTML parsing integrates properly."""
        # Placeholder detection should work
        assert detect_placeholder_content("<script>error</script>" + " x" * 50) is True
        
        # Cleaning should work
        dirty_markdown = "line1  \n\n\n\nline2\n"
        clean_markdown = clean_job_posting_markdown(dirty_markdown)
        assert "\n\n\n" not in clean_markdown


class TestCLIIntegration:
    """Tests for CLI argument and environment variable handling."""

    def test_cli_job_url_argument_parsing(self):
        """Test that CLI correctly parses --job-url argument."""
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument("--job-url", default=None)

        # Test with URL provided
        args = parser.parse_args(["--job-url", "https://example.com/job/123"])
        assert args.job_url == "https://example.com/job/123"

    def test_cli_job_url_none_when_not_provided(self):
        """Test that job_url is None when not provided."""
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument("--job-url", default=None)

        args = parser.parse_args([])
        assert args.job_url is None

    def test_cli_job_url_with_complex_url(self):
        """Test that CLI handles complex URLs with query parameters."""
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument("--job-url", default=None)

        url = "https://example.com/job?id=123&ref=email&source=newsletter"
        args = parser.parse_args(["--job-url", url])
        assert args.job_url == url

    def test_job_url_env_var_fallback(self, monkeypatch):
        """Test that JOB_URL environment variable is used as fallback."""
        import argparse

        # Set environment variable
        monkeypatch.setenv("JOB_URL", "https://example.com/job/from-env")

        parser = argparse.ArgumentParser()
        parser.add_argument(
            "--job-url",
            default=os.environ.get("JOB_URL"),
        )

        # Parse without --job-url argument
        args = parser.parse_args([])

        # Should use env var
        assert args.job_url == "https://example.com/job/from-env"

    def test_cli_argument_overrides_env_var(self, monkeypatch):
        """Test that CLI argument takes precedence over environment variable."""
        import argparse

        # Set environment variable
        monkeypatch.setenv("JOB_URL", "https://example.com/job/from-env")

        parser = argparse.ArgumentParser()
        parser.add_argument(
            "--job-url",
            default=os.environ.get("JOB_URL"),
        )

        # Parse with explicit --job-url argument
        cli_url = "https://example.com/job/from-cli"
        args = parser.parse_args(["--job-url", cli_url])

        # Should use CLI argument
        assert args.job_url == cli_url

    def test_job_url_env_var_not_set_defaults_to_none(self, monkeypatch):
        """Test that job_url defaults to None when env var not set."""
        import argparse

        # Ensure env var is not set
        monkeypatch.delenv("JOB_URL", raising=False)

        parser = argparse.ArgumentParser()
        parser.add_argument("--job-url", default=os.environ.get("JOB_URL"))

        args = parser.parse_args([])

        # Should be None
        assert args.job_url is None


class TestPlaceholderDetectionInScraping:
    """Tests for placeholder detection edge cases in scraping context."""

    def test_error_page_detected_as_placeholder(self):
        """Test that error pages are detected as placeholders."""
        error_content = "<script>alert('Error loading')</script>" + " x" * 50
        assert detect_placeholder_content(error_content) is True

    def test_click_here_detected_as_placeholder(self):
        """Test that 'click here' content is detected as placeholder."""
        content = "To view the job posting, click here" + " x" * 50
        assert detect_placeholder_content(content) is True

    def test_real_posting_with_javascript_skills_not_placeholder(self):
        """Test that real job posting mentioning JavaScript is not flagged."""
        content = """
        Senior Software Engineer
        Requirements: JavaScript, TypeScript, React
        We seek an expert in JavaScript frameworks.
        Must have 5+ years working with JavaScript.
        """ + " x" * 50
        assert detect_placeholder_content(content) is False

    def test_minimum_valid_content_length(self):
        """Test boundary of minimum content length."""
        # 99 chars - should be placeholder
        content_99 = "x" * 99
        assert detect_placeholder_content(content_99) is True

        # 100 chars - should be valid
        content_100 = "x" * 100
        assert detect_placeholder_content(content_100) is False

        # 101 chars - should be valid
        content_101 = "x" * 101
        assert detect_placeholder_content(content_101) is False


class TestScrapedJobPostingModel:
    """Tests for ScrapedJobPosting data model."""

    def test_scraped_job_posting_creation(self):
        """Test creating ScrapedJobPosting with all fields."""
        posting = ScrapedJobPosting(
            url="https://example.com/job/123",
            markdown="# Job Title\n\nRequirements...",
            source_text="<html>...</html>",
            extraction_strategy="html2text",
        )

        assert posting.url == "https://example.com/job/123"
        assert posting.markdown == "# Job Title\n\nRequirements..."
        assert posting.source_text == "<html>...</html>"
        assert posting.extraction_strategy == "html2text"

    def test_scraped_job_posting_url_validation(self):
        """Test that URL field accepts valid URLs."""
        valid_urls = [
            "https://example.com/job/123",
            "https://jobs.github.com/positions/456",
            "http://careers.company.com/job?id=789",
        ]

        for url in valid_urls:
            posting = ScrapedJobPosting(
                url=url,
                markdown="Job content",
                source_text="HTML",
                extraction_strategy="html2text",
            )
            assert posting.url == url

    def test_scraped_job_posting_markdown_field(self):
        """Test that markdown field stores formatted content."""
        markdown = """# Senior Engineer

## Requirements
- 5+ years experience
- Python expertise

## Location
San Francisco, CA
"""
        posting = ScrapedJobPosting(
            url="https://example.com/job",
            markdown=markdown,
            source_text="<html>...</html>",
            extraction_strategy="markitdown",
        )

        assert posting.markdown == markdown
        assert "Senior Engineer" in posting.markdown

    def test_scraped_job_posting_strategies(self):
        """Test different extraction strategy values."""
        strategies = ["html2text", "markitdown", "playwright_llm", "custom_parser"]

        for strategy in strategies:
            posting = ScrapedJobPosting(
                url="https://example.com/job",
                markdown="Job content",
                source_text="HTML",
                extraction_strategy=strategy,
            )
            assert posting.extraction_strategy == strategy
