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
    ResumeFileNotFoundError,
    UnsupportedFormatError,
    UnsupportedOutputFormatError,
    auto_detect_resume,
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

    def test_subclass_caught_by_base(self, subtests):
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
                with pytest.raises(ResumeConverterError):
                    raise exc_class("test")


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
        with pytest.raises((ConversionFailedError, EmptyConversionResultError)):
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
        with pytest.raises((ConversionFailedError, EmptyConversionResultError)):
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

    def test_convert_and_save_writes_markdown_to_output_path(
        self, sample_docx, tmp_path
    ):
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
            registry.convert_and_save(tmp_path / "missing.docx", tmp_path / "out.md")


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
