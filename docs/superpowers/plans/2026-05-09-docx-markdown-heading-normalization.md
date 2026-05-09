# DOCX to Markdown Heading Normalization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Post-process markitdown output to convert all-caps section headers (e.g., `SKILLS`, `PROFESSIONAL SUMMARY`) into proper markdown `##` headings so the AI parser agent can better recognize resume structure.

**Architecture:** Add a `_normalize_markdown_headings()` function in `resume_converter.py` that scans the converted markdown line-by-line, detects standalone all-caps lines with no markdown formatting, and prepends `## `. Applied as a post-processing step in both `DocxInputConverter.convert()` and `PdfInputConverter.convert()` after the markitdown call.

**Tech Stack:** Python, regex (stdlib `re`)

---

## File Structure

| File | Responsibility |
|------|---------------|
| `resume_tailorator/utils/resume_converter.py` | Add `_normalize_markdown_headings()` helper; call it in both converters |
| `tests/test_resume_converter.py` | Add tests for heading normalization |

---

### Task 1: Add heading normalization helper and wire into converters

**Files:**
- Modify: `resume_tailorator/utils/resume_converter.py`

- [ ] **Step 1: Add the `_is_section_header` and `_normalize_markdown_headings` functions**

At the top of the file, `re` is not yet imported. Add `import re` to the imports. Then add these two functions between the exceptions block and the Protocol class (around line 44):

```python
import re


def _is_section_header(line: str) -> bool:
    """True if *line* looks like a section header (all caps, no markdown formatting)."""
    if not line:
        return False
    # Must not contain markdown formatting characters
    if any(c in line for c in "**#[]()"):
        return False
    # Strip common non-alpha characters that could appear in headers, then
    # check the remaining characters are all uppercase letters.
    cleaned = re.sub(r"[\s/&]", "", line)
    return len(cleaned) >= 2 and cleaned.isupper()


def _normalize_markdown_headings(markdown: str) -> str:
    """Convert all-caps section header lines to markdown H2 headings.

    A line is promoted to a heading when:
    * It consists entirely of uppercase text (with optional spaces, /, &)
    * It contains no existing markdown formatting (**, #, [, ], (, ))
    * It is at least 2 characters long
    * It is not already a heading (doesn't start with #)
    * It stands alone (preceded by a blank line; this naturally filters out
      inline bold labels like **Programming Languages:** that sit within a
      paragraph block).
    """
    lines = markdown.split("\n")
    result: list[str] = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        prev_blank = i == 0 or not lines[i - 1].strip()
        if (
            prev_blank
            and _is_section_header(stripped)
            and not stripped.startswith("#")
        ):
            result.append(f"## {stripped}")
        else:
            result.append(line)
    return "\n".join(result)
```

- [ ] **Step 2: Call `_normalize_markdown_headings` in `DocxInputConverter.convert()`**

After `markdown = result.text_content` (line 79), add:

```python
            markdown = _normalize_markdown_headings(markdown)
```

- [ ] **Step 3: Call `_normalize_markdown_headings` in `PdfInputConverter.convert()`**

After `markdown = result.text_content` (line 109), add:

```python
            markdown = _normalize_markdown_headings(markdown)
```

- [ ] **Step 4: Verify syntax**

```bash
cd /Users/emadmokhtar/Projects/resume_tailorator/.claude/worktrees/fix-resume-parsing-determinism && python -c "from resume_tailorator.utils.resume_converter import DocxInputConverter, PdfInputConverter, _normalize_markdown_headings; print('OK')"
```

- [ ] **Step 5: Commit**

```bash
git add resume_tailorator/utils/resume_converter.py
git commit -m "feat: normalize all-caps section headers to markdown H2 after DOCX/PDF conversion"
```

---

### Task 2: Add tests for heading normalization

**Files:**
- Modify: `tests/test_resume_converter.py`

- [ ] **Step 1: Add test cases**

Append to the end of `tests/test_resume_converter.py`:

```python
# ---------------------------------------------------------------------------
# Heading normalization
# ---------------------------------------------------------------------------

from resume_tailorator.utils.resume_converter import (
    _is_section_header,
    _normalize_markdown_headings,
)


class TestIsSectionHeader:
    def test_all_caps_is_header(self):
        assert _is_section_header("SKILLS") is True

    def test_multi_word_all_caps_is_header(self):
        assert _is_section_header("PROFESSIONAL SUMMARY") is True
        assert _is_section_header("WORK EXPERIENCE") is True

    def test_with_slash_is_header(self):
        assert _is_section_header("CERTIFICATIONS/LICENSES") is True

    def test_with_ampersand_is_header(self):
        assert _is_section_header("AI & LLM") is True

    def test_bold_text_not_header(self):
        assert _is_section_header("**Emad Mokhtar**") is False
        assert _is_section_header("**Programming Languages:** Go, Python") is False

    def test_hashtag_not_header(self):
        assert _is_section_header("## Already a heading") is False

    def test_mixed_case_not_header(self):
        assert _is_section_header("Senior Engineer at Acme") is False

    def test_empty_not_header(self):
        assert _is_section_header("") is False
        assert _is_section_header("   ") is False

    def test_numbers_not_header(self):
        assert _is_section_header("2020-2024") is False

    def test_contact_line_not_header(self):
        assert _is_section_header("+31 (6) 45955236 | me@emadmokhtar.com | Rotterdam") is False

    def test_single_char_not_header(self):
        assert _is_section_header("A") is False


class TestNormalizeMarkdownHeadings:
    def test_converts_standalone_all_caps_line(self):
        input_md = "Some text\n\nSKILLS\n\nMore text"
        output = _normalize_markdown_headings(input_md)
        assert "## SKILLS" in output
        assert "SKILLS\n" not in output.replace("## SKILLS\n", "")

    def test_does_not_convert_already_heading(self):
        input_md = "Some text\n\n## SKILLS\n\nMore text"
        output = _normalize_markdown_headings(input_md)
        assert output.count("## SKILLS") == 1

    def test_does_not_convert_inline_bold_label(self):
        input_md = "**Programming Languages:** Go, Python"
        output = _normalize_markdown_headings(input_md)
        assert "## **Programming Languages:**" not in output
        assert output.rstrip() == input_md

    def test_multiple_headers(self):
        input_md = "intro\n\nSKILLS\n\ncontent\n\nPROJECTS\n\nmore"
        output = _normalize_markdown_headings(input_md)
        assert "## SKILLS" in output
        assert "## PROJECTS" in output

    def test_header_at_document_start(self):
        input_md = "SKILLS\n\ncontent"
        output = _normalize_markdown_headings(input_md)
        assert output.startswith("## SKILLS")

    def test_header_at_document_end(self):
        input_md = "content\n\nSKILLS"
        output = _normalize_markdown_headings(input_md)
        assert output.endswith("## SKILLS")

    def test_preserves_blank_lines(self):
        input_md = "a\n\nSKILLS\n\nb"
        output = _normalize_markdown_headings(input_md)
        lines = output.split("\n")
        assert lines[1] == ""  # blank line preserved
        assert lines[3] == ""  # blank line preserved
```

- [ ] **Step 2: Run the new tests**

```bash
cd /Users/emadmokhtar/Projects/resume_tailorator/.claude/worktrees/fix-resume-parsing-determinism && python -m pytest tests/test_resume_converter.py::TestIsSectionHeader tests/test_resume_converter.py::TestNormalizeMarkdownHeadings -v
```

Expected: all tests pass

- [ ] **Step 3: Run the existing converter tests to check for regressions**

```bash
cd /Users/emadmokhtar/Projects/resume_tailorator/.claude/worktrees/fix-resume-parsing-determinism && python -m pytest tests/test_resume_converter.py -v
```

Expected: all pre-existing tests still pass

- [ ] **Step 4: Commit**

```bash
git add tests/test_resume_converter.py
git commit -m "test: add heading normalization tests for DOCX/PDF markdown conversion"
```

---

### Task 3: Final verification

- [ ] **Step 1: Run full test suite**

```bash
cd /Users/emadmokhtar/Projects/resume_tailorator/.claude/worktrees/fix-resume-parsing-determinism && python -m pytest tests/ -v
```

- [ ] **Step 2: Spot-check with actual conversion**

```bash
cd /Users/emadmokhtar/Projects/resume_tailorator/.claude/worktrees/fix-resume-parsing-determinism && python -c "
from resume_tailorator.utils.resume_converter import InputConverterRegistry
reg = InputConverterRegistry()
md = reg.get('.docx').convert('/Volumes/External/OneDrive/Documents/Resume/Staff Software Engineer.docx')
print(md[:1000])
"
```

Expected: `## PROFESSIONAL SUMMARY`, `## SKILLS`, `## PROJECTS`, `## WORK EXPERIENCE` visible in output

- [ ] **Step 3: Commit any remaining changes**

```bash
git status
```
