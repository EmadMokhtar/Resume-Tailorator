"""Tests for per-agent quality gate validators."""
import pytest
from pydantic_ai import models
from pydantic_ai.exceptions import UnexpectedModelBehavior
from pydantic_ai.models.test import TestModel

models.ALLOW_MODEL_REQUESTS = False

# ---------------------------------------------------------------------------
# Shared test data
# ---------------------------------------------------------------------------

SAMPLE_CV = {
    "full_name": "Jane Smith",
    "contact_info": "jane@example.com",
    "summary": "Software engineer with 5 years experience.",
    "skills": ["Python", "FastAPI"],
    "projects": [],
    "experience": [
        {
            "company": "Acme Corp",
            "role": "Engineer",
            "dates": "2020-2023",
            "highlights": ["Built REST APIs"],
        }
    ],
    "education": ["BSc Computer Science"],
    "certifications": [],
    "publications": [],
}

QC_PASS = {"score": 9, "reasoning": "Good output.", "improvements": []}
QC_FAIL = {"score": 5, "reasoning": "Needs improvement.", "improvements": ["Fix tone"]}


@pytest.fixture(autouse=True)
def reset_quality_states():
    """Reset all _QualityState singletons before and after each test."""
    from workflows.agents import (
        _analyst_qs,
        _auditor_qs,
        _cover_qs,
        _parser_qs,
        _writer_qs,
    )

    for qs in (_parser_qs, _analyst_qs, _writer_qs, _auditor_qs, _cover_qs):
        qs.last_output = None
    yield
    for qs in (_parser_qs, _analyst_qs, _writer_qs, _auditor_qs, _cover_qs):
        qs.last_output = None


# ---------------------------------------------------------------------------
# Resume Parser
# ---------------------------------------------------------------------------


def test_resume_parser_validator_passes_when_score_9():
    from workflows.agents import quality_gate_agent, resume_parser_agent

    with quality_gate_agent.override(model=TestModel(custom_output_args=QC_PASS)):
        with resume_parser_agent.override(model=TestModel(custom_output_args=SAMPLE_CV)):
            result = resume_parser_agent.run_sync("Parse this resume.")

    assert result.output.full_name == "Jane Smith"


def test_resume_parser_validator_saves_last_output_when_score_low():
    from workflows.agents import _parser_qs, quality_gate_agent, resume_parser_agent

    with quality_gate_agent.override(model=TestModel(custom_output_args=QC_FAIL)):
        with resume_parser_agent.override(model=TestModel(custom_output_args=SAMPLE_CV)):
            with pytest.raises(UnexpectedModelBehavior):
                resume_parser_agent.run_sync("Parse this resume.")

    assert _parser_qs.last_output is not None
    assert _parser_qs.last_output.full_name == "Jane Smith"


# ---------------------------------------------------------------------------
# Auditor
# ---------------------------------------------------------------------------

SAMPLE_AUDIT = {
    "passed": True,
    "hallucination_score": 0,
    "ai_cliche_score": 0,
    "issues": [],
    "feedback_summary": "Sound professional and add metrics.",
}


def test_auditor_validator_passes_when_score_9():
    from workflows.agents import auditor_agent, quality_gate_agent

    with quality_gate_agent.override(model=TestModel(custom_output_args=QC_PASS)):
        with auditor_agent.override(model=TestModel(custom_output_args=SAMPLE_AUDIT)):
            result = auditor_agent.run_sync("Audit this resume.")

    assert result.output.hallucination_score == 0


def test_auditor_validator_saves_last_output_when_score_low():
    from workflows.agents import _auditor_qs, auditor_agent, quality_gate_agent

    with quality_gate_agent.override(model=TestModel(custom_output_args=QC_FAIL)):
        with auditor_agent.override(model=TestModel(custom_output_args=SAMPLE_AUDIT)):
            with pytest.raises(UnexpectedModelBehavior):
                auditor_agent.run_sync("Audit this resume.")

    assert _auditor_qs.last_output is not None
    assert _auditor_qs.last_output.hallucination_score == 0


# ---------------------------------------------------------------------------
# Cover Letter Writer
# ---------------------------------------------------------------------------

SAMPLE_COVER_LETTER = "Dear Hiring Manager,\n\nI am excited to apply for the Backend Engineer position at TechCorp.\n\nSincerely,\nJane Smith"


def test_cover_letter_validator_passes_when_score_9():
    from workflows.agents import cover_letter_writer_agent, quality_gate_agent

    with quality_gate_agent.override(model=TestModel(custom_output_args=QC_PASS)):
        with cover_letter_writer_agent.override(model=TestModel(custom_output_text=SAMPLE_COVER_LETTER)):
            result = cover_letter_writer_agent.run_sync("Write a cover letter.")

    assert "Dear Hiring Manager" in result.output


def test_cover_letter_validator_saves_last_output_when_score_low():
    from workflows.agents import _cover_qs, cover_letter_writer_agent, quality_gate_agent

    with quality_gate_agent.override(model=TestModel(custom_output_args=QC_FAIL)):
        with cover_letter_writer_agent.override(model=TestModel(custom_output_text=SAMPLE_COVER_LETTER)):
            with pytest.raises(UnexpectedModelBehavior):
                cover_letter_writer_agent.run_sync("Write a cover letter.")

    assert _cover_qs.last_output is not None
    assert "Dear Hiring Manager" in _cover_qs.last_output


# ---------------------------------------------------------------------------
# Job Analyst
# ---------------------------------------------------------------------------

SAMPLE_JOB = {
    "job_title": "Backend Engineer",
    "company_name": "TechCorp",
    "summary": "Build scalable backend systems.",
    "hard_skills": ["Python", "FastAPI"],
    "soft_skills": ["Communication"],
    "key_responsibilities": ["Build APIs", "Write tests"],
    "keywords_to_target": ["Python", "FastAPI", "REST"],
}


def test_analyst_validator_passes_when_score_9():
    from workflows.agents import analyst_agent, quality_gate_agent

    with quality_gate_agent.override(model=TestModel(custom_output_args=QC_PASS)):
        with analyst_agent.override(model=TestModel(custom_output_args=SAMPLE_JOB)):
            result = analyst_agent.run_sync("Analyse this job posting.")

    assert result.output.job_title == "Backend Engineer"


def test_analyst_validator_saves_last_output_when_score_low():
    from workflows.agents import _analyst_qs, analyst_agent, quality_gate_agent

    with quality_gate_agent.override(model=TestModel(custom_output_args=QC_FAIL)):
        with analyst_agent.override(model=TestModel(custom_output_args=SAMPLE_JOB)):
            with pytest.raises(UnexpectedModelBehavior):
                analyst_agent.run_sync("Analyse this job posting.")

    assert _analyst_qs.last_output is not None
    assert _analyst_qs.last_output.job_title == "Backend Engineer"


# ---------------------------------------------------------------------------
# CV Writer
# ---------------------------------------------------------------------------


def test_writer_validator_passes_when_score_9():
    from workflows.agents import writer_agent, quality_gate_agent

    with quality_gate_agent.override(model=TestModel(custom_output_args=QC_PASS)):
        with writer_agent.override(model=TestModel(custom_output_args=SAMPLE_CV)):
            result = writer_agent.run_sync("Tailor this resume.")

    assert result.output.full_name == "Jane Smith"


def test_writer_validator_saves_last_output_when_score_low():
    from workflows.agents import _writer_qs, writer_agent, quality_gate_agent

    with quality_gate_agent.override(model=TestModel(custom_output_args=QC_FAIL)):
        with writer_agent.override(model=TestModel(custom_output_args=SAMPLE_CV)):
            with pytest.raises(UnexpectedModelBehavior):
                writer_agent.run_sync("Tailor this resume.")

    assert _writer_qs.last_output is not None
    assert _writer_qs.last_output.full_name == "Jane Smith"



# ---------------------------------------------------------------------------
# Workflow Fallback Handling
# ---------------------------------------------------------------------------


def test_quality_state_objects_are_importable_from_agents():
    """Verify _QualityState singletons are importable from workflows.agents."""
    from workflows.agents import _analyst_qs, _auditor_qs, _parser_qs, _writer_qs

    for qs in (_parser_qs, _analyst_qs, _writer_qs, _auditor_qs):
        assert hasattr(qs, "last_output")
        assert qs.last_output is None


def test_quality_state_accepts_cv_assignment():
    """Verify _QualityState can store and retrieve CV objects."""
    from workflows.agents import _parser_qs

    from models.agents.output import CV, WorkExperience

    cv = CV(
        full_name="Test User",
        contact_info="test@example.com",
        summary="Summary text.",
        skills=["Python"],
        experience=[
            WorkExperience(company="X Corp", role="Engineer", dates="2020", highlights=[])
        ],
        education=["BSc Computer Science"],
    )
    _parser_qs.last_output = cv
    assert _parser_qs.last_output.full_name == "Test User"
