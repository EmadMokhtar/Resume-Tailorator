"""Tests for deterministic resume parsing via pre-parsed CV cache."""
import inspect
import pytest

from resume_tailorator.models.agents.output import CV, WorkExperience
from resume_tailorator.workflows import ResumeTailorWorkflow


@pytest.fixture
def sample_pre_parsed_cv():
    return CV(
        full_name="Jane Doe",
        contact_info="jane@example.com",
        summary="Senior engineer with 10 years experience",
        skills=["Python", "TypeScript", "React", "AWS", "Docker", "Kubernetes"],
        projects=["Built CI/CD pipeline"],
        experience=[
            WorkExperience(
                company="Acme Corp",
                role="Staff Engineer",
                dates="2020-2024",
                highlights=["Led team of 5", "Designed distributed system"],
            )
        ],
        education=["BSc Computer Science"],
        certifications=["AWS Solutions Architect"],
        publications=[],
    )


def test_workflow_run_signature_accepts_pre_parsed_cv():
    """run() has pre_parsed_cv and debug parameters with correct defaults."""
    sig = inspect.signature(ResumeTailorWorkflow.run)
    assert "pre_parsed_cv" in sig.parameters
    assert sig.parameters["pre_parsed_cv"].default is None
    assert "debug" in sig.parameters
    assert sig.parameters["debug"].default is False


def test_pre_parsed_cv_preserves_skills(sample_pre_parsed_cv):
    """A pre-parsed CV should faithfully carry its data."""
    assert len(sample_pre_parsed_cv.skills) == 6
    assert sample_pre_parsed_cv.full_name == "Jane Doe"
    assert len(sample_pre_parsed_cv.experience) == 1


@pytest.mark.asyncio
async def test_tailor_impl_accepts_debug_param():
    """_tailor_impl signature includes debug param."""
    from resume_tailorator.main import _tailor_impl
    sig = inspect.signature(_tailor_impl)
    assert "debug" in sig.parameters
    assert sig.parameters["debug"].default is False


@pytest.mark.asyncio
async def test_re_tailor_impl_accepts_debug_param():
    """_re_tailor_impl signature includes debug param."""
    from resume_tailorator.main import _re_tailor_impl
    sig = inspect.signature(_re_tailor_impl)
    assert "debug" in sig.parameters
    assert sig.parameters["debug"].default is False


@pytest.mark.asyncio
async def test_run_workflow_signature_includes_new_params():
    """_run_workflow passes pre_parsed_cv and debug through."""
    from resume_tailorator.main import _run_workflow
    sig = inspect.signature(_run_workflow)
    assert "pre_parsed_cv" in sig.parameters
    assert "debug" in sig.parameters
