---
name: pydantic-ai-testing
description: Guidance for testing Pydantic AI agents with deterministic model doubles, overrides, and run inspection. Use it when you need fast tests without real model calls.
---

# Skill: Pydantic AI Testing

> Topic scope: Pydantic AI testing with deterministic model doubles and run inspection
> Primary references: `../pydantic-ai/SKILL.md`, `https://pydantic.dev/docs/ai/guides/testing/`

## Overview
Documents the recommended testing stack for Pydantic AI applications: block real model calls, swap in deterministic test models, and assert the full request/response exchange. This skill is the quick reference for testing agent code without paying for or depending on live providers.

## Capabilities
- Prevent accidental real LLM traffic during tests
- Replace production models with `TestModel` or `FunctionModel`
- Override agents in-place without changing application call sites
- Capture full run messages for assertions and debugging
- Keep async agent tests deterministic and fast

## Key Symbols
| Symbol | Type | Description |
|--------|------|-------------|
| `models.ALLOW_MODEL_REQUESTS` | setting | Global guard that blocks real provider calls in tests |
| `TestModel` | class | Fast fake model that auto-runs tools and returns schema-valid output |
| `FunctionModel` | class | Custom fake model for fully controlled tool-call sequences |
| `Agent.override` | method | Context manager to temporarily replace model, deps, or toolsets |
| `capture_run_messages` | function | Captures the model request/response messages from a run |

## Inputs & Outputs
| Symbol | Input | Output |
|--------|-------|--------|
| `models.ALLOW_MODEL_REQUESTS` | `False` in tests | Raises if code tries to hit a real model |
| `TestModel(...)` | Optional custom output text or data | Deterministic stand-in model for broad path coverage |
| `FunctionModel(fn)` | `fn(messages, info)` fake-LLM callback | Model that returns exactly the messages you script |
| `Agent.override(...)` | Replacement `model`, `deps`, or `toolsets` | Temporary override that reverts on context exit |
| `capture_run_messages()` | No required input | Context manager exposing collected run messages |

## Usage Example
```python
import pytest
from pydantic_ai import capture_run_messages, models
from pydantic_ai.models.test import TestModel

from my_app import support_agent

pytestmark = pytest.mark.anyio
models.ALLOW_MODEL_REQUESTS = False


async def test_support_agent():
    with capture_run_messages() as messages:
        with support_agent.override(model=TestModel()):
            result = await support_agent.run("Reset my password")

    assert result.output is not None
    assert messages
```

## Internal Dependencies
- `../pydantic-ai/SKILL.md` — base agent setup patterns that test overrides wrap
- `../pydantic-ai-workflows/SKILL.md` — useful when testing multi-agent delegation and shared usage paths

## External Dependencies
- `pydantic-ai` — test models, overrides, and message capture utilities
- `pytest` — test runner and fixtures
- `pytest-anyio` — async test execution for agent runs

## Notes
- Set **`models.ALLOW_MODEL_REQUESTS = False`** in `conftest.py` or every agent test module.
- Use **`TestModel`** for smoke tests and integration-style tests where you mainly care that tools, validators, and control flow execute.
- `TestModel` generates valid-but-generic arguments; use **`custom_output_text`** or **`custom_output_data`** when assertions need specific outputs.
- Use **`FunctionModel`** when you need to script exact tool calls, retries, or message order.
- Use **`Agent.override`** instead of editing production code to thread test models through call sites.
- `capture_run_messages()` is best for asserting the exact agent↔model exchange, including tool calls and tool returns.
- Test tool functions directly when they are plain Python helpers; reserve model doubles for tool orchestration behavior.

## Changelog
| Date | Change |
|------|--------|
| 2026-04-22 | Converted the skill to Agent Skills spec layout with `SKILL.md`, YAML frontmatter, and updated relative links |
| 2026-04-21 | Initial skill created for `TestModel`, `FunctionModel`, overrides, and message capture |
| 2026-04-21 | Removed dead local instruction reference and normalized in-tree links |
