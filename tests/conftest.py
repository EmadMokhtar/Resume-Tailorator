"""Pytest configuration for Resume Tailorator."""

import os
from collections.abc import Generator

import pytest
from pydantic_ai import models

from models.agents.output import CV, WorkExperience

# Provide a dummy key so pydantic-ai agent constructors don't fail at import time.
# Real calls are blocked by the block_model_requests fixture below.
os.environ.setdefault("OPENAI_API_KEY", "test-dummy-key-for-pytest")


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
