"""Pytest configuration for Resume Tailorator."""

# Minimal bootstrap so tests can import local packages when running under make/test.
# This is intentionally small and only adjusts sys.path to include the worktree root.
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pytest
from pydantic_ai import models
from typing import Iterator

from models.agents.output import CV, WorkExperience


@pytest.fixture(autouse=True, scope="session")
def block_model_requests() -> Iterator[None]:
    models.ALLOW_MODEL_REQUESTS = False
    try:
        yield
    finally:
        models.ALLOW_MODEL_REQUESTS = True



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
