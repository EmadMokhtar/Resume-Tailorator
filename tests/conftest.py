"""Pytest configuration for Resume Tailorator."""

import pytest
from pydantic_ai import models
from collections.abc import Generator

from models.agents.output import CV, WorkExperience


@pytest.fixture(autouse=True, scope="session")
def block_model_requests() -> Generator[None, None, None]:
    with models.override_allow_model_requests(False):
        yield

@pytest.fixture
def sample_cv() -> CV:
    return CV(
        full_name="Jane Doe",
        contact_info="jane@example.com",
        summary="Platform engineer with Python experience.",
        skills=["Python", "SQL", "Communication"],
        projects=["Built internal tooling"],
        experience=[
            WorkExperience(
                company="Acme",
                role="Software Engineer",
                dates="2022-2026",
                highlights=["Built Python services", "Improved reliability"],
            )
        ],
        education=["BSc Computer Science"],
        certifications=[],
        publications=[],
    )
