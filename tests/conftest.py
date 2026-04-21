"""Pytest configuration for Resume Tailorator."""

import pytest
import sys
from pathlib import Path

# Ensure the project root is on sys.path so tests can import local packages
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pydantic_ai import models

from models.agents.output import CV, WorkExperience


models.ALLOW_MODEL_REQUESTS = False


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
