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
