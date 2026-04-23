import json

import pytest

from models.workflow import ResumeTailorResult
from utils.resume_converter import (
    OutputConversionFailedError,
    UnsupportedOutputFormatError,
)
from utils.resume_output_converter import (
    DocxOutputConverter,
    MarkdownOutputConverter,
    OutputConverterRegistry,
    PdfOutputConverter,
)


SAMPLE_RESULT = ResumeTailorResult(
    company_name="Acme",
    tailored_resume=json.dumps(
        {
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
        }
    ),
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
        registry.convert_all(SAMPLE_MARKDOWN, ["md", "docx"], tmp_path)
        assert (tmp_path / "tailored_resume.md").exists()
        assert (tmp_path / "tailored_resume.docx").exists()

    def test_convert_all_returns_correct_paths(self, tmp_path):
        registry = OutputConverterRegistry()
        written = registry.convert_all(SAMPLE_MARKDOWN, ["md"], tmp_path)
        assert written == [tmp_path / "tailored_resume.md"]

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
