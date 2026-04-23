import json

from models.workflow import ResumeTailorResult


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
