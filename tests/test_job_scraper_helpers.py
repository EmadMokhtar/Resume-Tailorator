"""Tests for job_scraper_helpers module.

Tests for placeholder detection, HTML parsing, and content cleaning utilities.
"""

import pytest
from tools.job_scraper_helpers import (
    detect_placeholder_content,
    clean_job_posting_markdown,
)


class TestDetectPlaceholderContent:
    """Tests for detect_placeholder_content function."""

    def test_empty_string_is_placeholder(self):
        """Empty text should be detected as placeholder."""
        assert detect_placeholder_content("") is True

    def test_none_is_placeholder(self):
        """None string should be detected as placeholder."""
        assert detect_placeholder_content(None) is True

    @pytest.mark.parametrize(
        "text",
        [
            "Senior JavaScript Developer needed at TechCorp. 5+ yrs exp required. React, Node, AWS. Apply at careers@techcorp.com or submit your resume.",
            "We are hiring for a role requiring: JavaScript, TypeScript, React. Salary 120-150K. Apply today with your resume and cover letter.",
            "Position: Full Stack Engineer. Skills needed: JavaScript/TypeScript, Python, AWS. 6+ years exp. Contact: jobs@example.com with questions.",
        ],
    )
    def test_legitimate_javascript_skill_not_flagged(self, text):
        """Legitimate job postings mentioning JavaScript as a skill should NOT be flagged.

        This is the fix for the bug: r'javascript' pattern was too broad and caught
        legitimate skill mentions. Only HTML <script> tags indicate parsing failure.
        """
        assert detect_placeholder_content(text) is False

    @pytest.mark.parametrize(
        "text",
        [
            "<script>alert('error')</script>",
            "Some job description <script>var x = 1;</script> more text" + " x" * 50,
            "Job posting <script type='text/javascript'>console.log('fail');</script>"
            + " x" * 50,
        ],
    )
    def test_script_tags_are_placeholder(self, text):
        """Unexecuted HTML script tags should be detected as placeholder."""
        assert detect_placeholder_content(text) is True

    @pytest.mark.parametrize(
        "text",
        [
            "To view the full job posting, click here" + " x" * 50,
            "Error loading page. Please try again." + " x" * 50,
            "Page not found. The job posting has been removed." + " x" * 50,
            "404: The requested job posting could not be found." + " x" * 50,
        ],
    )
    def test_common_placeholder_indicators(self, text):
        """Test detection of common placeholder/error indicators."""
        assert detect_placeholder_content(text) is True

    def test_text_at_99_chars_is_placeholder(self):
        """Text at 99 chars should be detected as placeholder."""
        text = "x" * 99
        assert detect_placeholder_content(text) is True

    def test_text_at_100_chars_not_placeholder(self):
        """Text at exactly 100 chars should NOT be placeholder."""
        text = "x" * 100
        assert detect_placeholder_content(text) is False

    def test_text_above_100_chars_not_placeholder(self):
        """Text above 100 chars should NOT be placeholder."""
        text = "x" * 150
        assert detect_placeholder_content(text) is False

    def test_realistic_job_posting_1_not_flagged(self):
        """Real job posting 1 should not be flagged as placeholder."""
        text = """
        Senior Software Engineer
        Location: San Francisco, CA
        
        We're looking for an experienced Software Engineer to join our team.
        Requirements:
        - 5+ years of software development experience
        - Proficiency in Python, Go, or Rust
        - Experience with distributed systems
        - Strong problem-solving skills
        
        We offer competitive salary, health benefits, and remote work options.
        Apply now at careers@techcorp.com
        """
        assert detect_placeholder_content(text) is False

    def test_realistic_job_posting_2_not_flagged(self):
        """Real job posting 2 should not be flagged as placeholder."""
        text = """
        Frontend Engineer - React/TypeScript
        About the role: We're seeking a talented frontend engineer to build
        amazing user experiences using modern web technologies. You'll work
        with a talented team on challenging problems and have the opportunity
        to grow your skills.
        
        Requirements: 3+ years frontend development, React/Vue experience,
        understanding of CSS and responsive design.
        
        Compensation: $130K-$160K + benefits
        """
        assert detect_placeholder_content(text) is False

    def test_uppercase_click_here_is_placeholder(self):
        """Uppercase 'CLICK HERE' should be detected as placeholder."""
        text = "To continue, CLICK HERE" + " x" * 50
        assert detect_placeholder_content(text) is True

    def test_mixed_case_click_here_is_placeholder(self):
        """Mixed case 'Click Here' should be detected as placeholder."""
        text = "To continue, Click Here" + " x" * 50
        assert detect_placeholder_content(text) is True

    def test_uppercase_error_loading_is_placeholder(self):
        """Uppercase 'ERROR LOADING' should be detected as placeholder."""
        text = "ERROR LOADING the page. Please refresh." + " x" * 50
        assert detect_placeholder_content(text) is True

    def test_short_text_with_leading_trailing_whitespace(self):
        """Short text with leading/trailing whitespace should be placeholder."""
        text = "    short    "
        assert detect_placeholder_content(text) is True

    def test_short_text_with_newlines(self):
        """Short text with newlines should be placeholder."""
        text = "Short\ntext\nhere"
        assert detect_placeholder_content(text) is True

    def test_long_text_with_newlines(self):
        """Long text with newlines should not be placeholder."""
        text = "This is a long job posting\n" * 10
        assert detect_placeholder_content(text) is False


class TestCleanJobPostingMarkdown:
    """Tests for clean_job_posting_markdown function."""

    def test_empty_string_returns_empty(self):
        """Empty string should return empty string."""
        assert clean_job_posting_markdown("") == ""

    def test_none_returns_empty(self):
        """None input should return empty string."""
        assert clean_job_posting_markdown(None) == ""

    def test_three_newlines_collapse_to_two(self):
        """Three newlines should collapse to two."""
        text = "line1\n\n\n\nline2"
        result = clean_job_posting_markdown(text)
        assert result == "line1\n\nline2\n"

    def test_multiple_groups_of_blank_lines(self):
        """Multiple groups of blank lines should each collapse to two."""
        text = "line1\n\n\n\nline2\n\n\n\n\n\nline3"
        result = clean_job_posting_markdown(text)
        assert result == "line1\n\nline2\n\nline3\n"

    def test_single_line_trailing_spaces_removed(self):
        """Trailing spaces should be removed from single line."""
        text = "text with trailing  "
        result = clean_job_posting_markdown(text)
        assert result == "text with trailing\n"

    def test_multiple_lines_trailing_spaces_removed(self):
        """Trailing spaces should be removed from all lines."""
        text = "line1  \nline2   \nline3 "
        result = clean_job_posting_markdown(text)
        assert result == "line1\nline2\nline3\n"

    def test_text_without_trailing_newline_gets_one(self):
        """Text without trailing newline should get one."""
        text = "some text"
        result = clean_job_posting_markdown(text)
        assert result.endswith("\n")
        assert not result.endswith("\n\n")

    def test_text_with_trailing_newline_preserved(self):
        """Text with trailing newline should be preserved (not doubled)."""
        text = "some text\n"
        result = clean_job_posting_markdown(text)
        assert result.endswith("\n")
        assert not result.endswith("\n\n")

    def test_text_with_multiple_trailing_newlines_normalized(self):
        """Multiple trailing newlines should be normalized to one."""
        text = "some text\n\n\n"
        result = clean_job_posting_markdown(text)
        assert result.endswith("\n")
        assert not result.endswith("\n\n")

    def test_comprehensive_cleanup_no_trailing_spaces(self):
        """Comprehensive cleanup should remove all trailing spaces."""
        text = "line1  \n\n\n\n\nline2   \n\n\n\nline3  \n\n\n"
        result = clean_job_posting_markdown(text)

        for line in result.split("\n")[:-1]:  # exclude empty last line
            assert line == line.rstrip()

    def test_comprehensive_cleanup_no_triple_newlines(self):
        """Comprehensive cleanup should prevent triple newlines."""
        text = "line1  \n\n\n\n\nline2   \n\n\n\nline3  \n\n\n"
        result = clean_job_posting_markdown(text)

        assert "\n\n\n" not in result

    def test_comprehensive_cleanup_single_trailing_newline(self):
        """Comprehensive cleanup should end with exactly one newline."""
        text = "line1  \n\n\n\n\nline2   \n\n\n\nline3  \n\n\n"
        result = clean_job_posting_markdown(text)

        assert result.endswith("\n")
        assert not result.endswith("\n\n")
