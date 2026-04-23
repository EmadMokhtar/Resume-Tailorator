"""Tests for main.py CLI and integration with converter pipelines."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from models.workflow import ResumeTailorResult


@pytest.fixture
def sample_result():
    """Create a sample ResumeTailorResult for testing."""
    return ResumeTailorResult(
        company_name="TestCorp",
        tailored_resume=json.dumps(
            {
                "full_name": "John Doe",
                "contact_info": "john@example.com",
                "summary": "Software engineer.",
                "skills": ["Python", "JavaScript"],
                "experience": [
                    {
                        "role": "Developer",
                        "company": "TestCorp",
                        "dates": "2020-2024",
                        "highlights": ["Built features", "Fixed bugs"],
                    }
                ],
                "education": ["BS Computer Science"],
                "certifications": [],
                "publications": [],
                "projects": [],
            }
        ),
        audit_report={"feedback_summary": "Good match"},
        passed=True,
    )


class TestCliArgumentParsing:
    """Test CLI argument parsing for --resume and --output."""

    def test_parse_resume_argument_with_custom_path(self):
        """Test parsing --resume with custom path."""
        from main import create_parser

        parser = create_parser()
        args = parser.parse_args(["--resume", "/custom/path/resume.pdf"])
        assert args.resume == "/custom/path/resume.pdf"

    def test_parse_resume_argument_default(self):
        """Test --resume defaults to files/resume.md if not provided."""
        from main import create_parser

        parser = create_parser()
        args = parser.parse_args([])
        assert args.resume == "files/resume.md"

    def test_parse_output_single_format(self):
        """Test --output with single format."""
        from main import create_parser

        parser = create_parser()
        args = parser.parse_args(["--output", "pdf"])
        assert args.output == ["pdf"]

    def test_parse_output_multiple_formats(self):
        """Test --output with multiple formats (repeatable)."""
        from main import create_parser

        parser = create_parser()
        args = parser.parse_args(
            ["--output", "md", "--output", "pdf", "--output", "docx"]
        )
        assert args.output == ["md", "pdf", "docx"]

    def test_parse_output_default(self):
        """Test --output defaults to None if not provided, handled by main_impl."""
        from main import create_parser

        parser = create_parser()
        args = parser.parse_args([])
        # Default is None, main() will convert to ["md"]
        assert args.output is None

    def test_parse_output_case_insensitive(self):
        """Test that output formats are accepted in any case."""
        from main import create_parser

        parser = create_parser()
        args = parser.parse_args(["--output", "PDF", "--output", "MD"])
        assert args.output == ["PDF", "MD"]


class TestAutoDetectResume:
    """Test auto-detection and conversion of input resume."""

    @pytest.mark.anyio
    async def test_auto_detect_resume_with_docx(self):
        """Test input converter is called for docx files."""
        from main import main_impl

        mock_result = AsyncMock()
        mock_result.passed = False
        mock_result.audit_report = {}

        with patch("main.ResumeTailorWorkflow") as MockWorkflow:
            mock_workflow = AsyncMock()
            mock_workflow.run = AsyncMock(return_value=mock_result)
            MockWorkflow.return_value = mock_workflow

            with patch("main.InputConverterRegistry") as MockRegistry:
                mock_registry = MagicMock()
                mock_converter = MagicMock()
                mock_converter.convert.return_value = "# Test\n"
                mock_registry.get.return_value = mock_converter
                MockRegistry.return_value = mock_registry

                with patch("pathlib.Path.exists", return_value=True):
                    await main_impl(resume_path="resume.docx", output_formats=["md"])

                # Verify that converter was used for docx file
                mock_registry.get.assert_called_once()

    @pytest.mark.anyio
    async def test_unsupported_file_type_error_handling(self):
        """Test handling of UnsupportedFileTypeError."""
        from main import main_impl
        from utils.resume_converter import UnsupportedFormatError

        with patch("pathlib.Path.exists", return_value=True):
            with patch("main.InputConverterRegistry.get") as mock_get:
                mock_get.side_effect = UnsupportedFormatError("Unsupported format")

                with pytest.raises(SystemExit) as exc_info:
                    await main_impl(resume_path="resume.xyz", output_formats=["md"])

                assert exc_info.value.code == 1

    @pytest.mark.anyio
    async def test_input_conversion_failed_error_handling(self):
        """Test handling of InputConversionFailedError."""
        from main import main_impl
        from utils.resume_converter import ConversionFailedError

        with patch("pathlib.Path.exists", return_value=True):
            with patch("main.InputConverterRegistry.get") as mock_get:
                mock_converter = MagicMock()
                mock_converter.convert.side_effect = ConversionFailedError(
                    "Conversion failed"
                )
                mock_get.return_value = mock_converter

                with pytest.raises(SystemExit) as exc_info:
                    await main_impl(resume_path="broken.pdf", output_formats=["md"])

                assert exc_info.value.code == 1


class TestConverterPipeline:
    """Test the converter pipeline integration."""

    @pytest.mark.anyio
    async def test_build_resume_markdown_called(self, sample_result):
        """Test that build_resume_markdown is called with result."""
        from main import main_impl

        sample_result.passed = True

        with patch("main.ResumeTailorWorkflow") as MockWorkflow:
            mock_workflow = AsyncMock()
            mock_workflow.run = AsyncMock(return_value=sample_result)
            MockWorkflow.return_value = mock_workflow

            with patch("pathlib.Path.exists", return_value=True):
                with patch("builtins.open", create=True):
                    with patch("main.generate_resume"):
                        with patch("main.build_resume_markdown") as mock_build:
                            mock_build.return_value = "# Test\n"

                            with patch("main.OutputConverterRegistry") as MockRegistry:
                                mock_registry_instance = MagicMock()
                                mock_registry_instance.convert_all.return_value = [
                                    Path("files/tailored_resume.md")
                                ]
                                MockRegistry.return_value = mock_registry_instance

                                await main_impl(
                                    resume_path="files/resume.md",
                                    output_formats=["md", "pdf"],
                                )

                            mock_build.assert_called_once_with(sample_result)

    @pytest.mark.anyio
    async def test_convert_all_called_with_correct_params(self, sample_result):
        """Test that convert_all is called with correct markdown and formats."""
        from main import main_impl

        markdown_content = "# Test Resume\n"
        sample_result.passed = True

        with patch("main.ResumeTailorWorkflow") as MockWorkflow:
            mock_workflow = AsyncMock()
            mock_workflow.run = AsyncMock(return_value=sample_result)
            MockWorkflow.return_value = mock_workflow

            with patch("pathlib.Path.exists", return_value=True):
                with patch("builtins.open", create=True):
                    with patch("main.generate_resume"):
                        with patch(
                            "main.build_resume_markdown", return_value=markdown_content
                        ):
                            with patch("main.OutputConverterRegistry") as MockRegistry:
                                mock_registry_instance = MagicMock()
                                mock_registry_instance.convert_all.return_value = [
                                    Path("files/tailored_resume.md"),
                                    Path("files/tailored_resume.pdf"),
                                    Path("files/tailored_resume.docx"),
                                ]
                                MockRegistry.return_value = mock_registry_instance

                                await main_impl(
                                    resume_path="files/resume.md",
                                    output_formats=["md", "pdf", "docx"],
                                )

                            mock_registry_instance.convert_all.assert_called_once()
                            call_args = mock_registry_instance.convert_all.call_args
                            assert call_args[0][0] == markdown_content
                            assert set(call_args[0][1]) == {"md", "pdf", "docx"}

    @pytest.mark.anyio
    async def test_output_formats_normalized_to_lowercase(self, sample_result):
        """Test that output formats are normalized to lowercase."""
        from main import main_impl

        sample_result.passed = True

        with patch("main.ResumeTailorWorkflow") as MockWorkflow:
            mock_workflow = AsyncMock()
            mock_workflow.run = AsyncMock(return_value=sample_result)
            MockWorkflow.return_value = mock_workflow

            with patch("pathlib.Path.exists", return_value=True):
                with patch("builtins.open", create=True):
                    with patch("main.generate_resume"):
                        with patch(
                            "main.build_resume_markdown", return_value="# Test\n"
                        ):
                            with patch("main.OutputConverterRegistry") as MockRegistry:
                                mock_registry_instance = MagicMock()
                                mock_registry_instance.convert_all.return_value = []
                                MockRegistry.return_value = mock_registry_instance

                                await main_impl(
                                    resume_path="files/resume.md",
                                    output_formats=["PDF", "MD", "DOCX"],
                                )

                                call_args = mock_registry_instance.convert_all.call_args
                                assert all(fmt.islower() for fmt in call_args[0][1])


class TestErrorHandling:
    """Test error handling for input and output conversion failures."""

    @pytest.mark.anyio
    async def test_unsupported_format_error_exits_with_1(self):
        """Test UnsupportedFormatError causes exit(1)."""
        from main import main_impl
        from utils.resume_converter import UnsupportedFormatError

        with patch("pathlib.Path.exists", return_value=True):
            with patch("main.InputConverterRegistry.get") as mock_get:
                mock_get.side_effect = UnsupportedFormatError("Unsupported format .xyz")

                with pytest.raises(SystemExit) as exc_info:
                    await main_impl(resume_path="resume.xyz", output_formats=["md"])

                assert exc_info.value.code == 1

    @pytest.mark.anyio
    async def test_conversion_failed_error_exits_with_1(self):
        """Test ConversionFailedError causes exit(1)."""
        from main import main_impl
        from utils.resume_converter import ConversionFailedError

        with patch("pathlib.Path.exists", return_value=True):
            with patch("main.InputConverterRegistry.get") as mock_get:
                mock_converter = MagicMock()
                mock_converter.convert.side_effect = ConversionFailedError(
                    "PDF corrupt"
                )
                mock_get.return_value = mock_converter

                with pytest.raises(SystemExit) as exc_info:
                    await main_impl(resume_path="resume.pdf", output_formats=["md"])

                assert exc_info.value.code == 1

    @pytest.mark.anyio
    async def test_output_conversion_failed_error_exits_with_1(self, sample_result):
        """Test OutputConversionFailedError causes exit(1)."""
        from main import main_impl
        from utils.resume_converter import OutputConversionFailedError

        sample_result.passed = True

        with patch("main.ResumeTailorWorkflow") as MockWorkflow:
            mock_workflow = AsyncMock()
            mock_workflow.run = AsyncMock(return_value=sample_result)
            MockWorkflow.return_value = mock_workflow

            with patch("pathlib.Path.exists", return_value=True):
                with patch("builtins.open", create=True):
                    with patch("main.generate_resume"):
                        with patch(
                            "main.build_resume_markdown", return_value="# Test\n"
                        ):
                            with patch("main.OutputConverterRegistry") as MockRegistry:
                                mock_registry_instance = MagicMock()
                                mock_registry_instance.convert_all.side_effect = (
                                    OutputConversionFailedError("Failed to write PDF")
                                )
                                MockRegistry.return_value = mock_registry_instance

                                with pytest.raises(SystemExit) as exc_info:
                                    await main_impl(
                                        resume_path="files/resume.md",
                                        output_formats=["pdf"],
                                    )

                                assert exc_info.value.code == 1


class TestSuccessOutput:
    """Test success message formatting."""

    @pytest.mark.anyio
    async def test_success_message_includes_formats(self, sample_result, capsys):
        """Test success message includes output formats."""
        from main import main_impl

        sample_result.passed = True

        with patch("main.ResumeTailorWorkflow") as MockWorkflow:
            mock_workflow = AsyncMock()
            mock_workflow.run = AsyncMock(return_value=sample_result)
            MockWorkflow.return_value = mock_workflow

            with patch("pathlib.Path.exists", return_value=True):
                with patch("builtins.open", create=True):
                    with patch("main.generate_resume"):
                        with patch(
                            "main.build_resume_markdown", return_value="# Test\n"
                        ):
                            with patch("main.OutputConverterRegistry") as MockRegistry:
                                mock_registry_instance = MagicMock()
                                mock_registry_instance.convert_all.return_value = [
                                    Path("files/tailored_resume.md"),
                                    Path("files/tailored_resume.pdf"),
                                ]
                                MockRegistry.return_value = mock_registry_instance

                                await main_impl(
                                    resume_path="files/resume.md",
                                    output_formats=["md", "pdf"],
                                )

        captured = capsys.readouterr()
        assert "tailored_resume" in captured.out.lower()


class TestAuditFailure:
    """Test behavior when audit fails."""

    @pytest.mark.anyio
    async def test_audit_failure_prints_feedback(self, capsys):
        """Test that audit failure prints feedback (existing behavior preserved)."""
        from main import main_impl

        result = ResumeTailorResult(
            company_name="TestCorp",
            tailored_resume="{}",
            audit_report={"feedback_summary": "Missing experience"},
            passed=False,
        )

        with patch("main.ResumeTailorWorkflow") as MockWorkflow:
            mock_workflow = AsyncMock()
            mock_workflow.run = AsyncMock(return_value=result)
            MockWorkflow.return_value = mock_workflow

            with patch("pathlib.Path.exists", return_value=True):
                with patch("builtins.open", create=True):
                    await main_impl(
                        resume_path="files/resume.md", output_formats=["md"]
                    )

        captured = capsys.readouterr()
        assert "Missing experience" in captured.out or "Audit Failed" in captured.out
