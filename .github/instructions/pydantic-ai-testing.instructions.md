---
applyTo: "**/*.py"
---

# Pydantic AI - Testing

Reference: https://ai.pydantic.dev/testing/

## Strategy

- Use **`make test`** to run all tests — ⛔ NEVER use `python`, `python -m pytest`, or bare `pytest` directly (see `pytest.instructions.md`).
- Use **pytest** as the test harness.
- Use **`TestModel`** or **`FunctionModel`** instead of real LLM calls — no API cost, no latency, no variability.
- Use **`Agent.override`** to inject test models into application code without modifying the call site.
- Set **`ALLOW_MODEL_REQUESTS = False`** globally to prevent accidental real LLM calls in tests.
- Use **`capture_run_messages`** to assert the full exchange between agent and model.
- Use **`anyio`** (via `pytest-anyio`) to run async tests.
- Use **`inline-snapshot`** and **`dirty-equals`** for readable assertions on large data structures.

## Install test dependencies

```
uv add --dev pytest pytest-anyio dirty-equals inline-snapshot
```

## Block Real LLM Calls

Add this at the top of every test file (or in `conftest.py`):

```python
from pydantic_ai import models

models.ALLOW_MODEL_REQUESTS = False  # raises if a real model is called
```

## `TestModel` — Fastest Option

`TestModel` calls **all registered tools** automatically, then returns a JSON summary of what
was called. No ML — it generates schema-valid but meaningless data for tool arguments.

```python
import pytest
from pydantic_ai import models
from pydantic_ai.models.test import TestModel
from my_app import my_agent, run_pipeline   # production code

pytestmark = pytest.mark.anyio
models.ALLOW_MODEL_REQUESTS = False

async def test_pipeline_calls_tools():
    with my_agent.override(model=TestModel()):
        result = await run_pipeline("Some user prompt")
    assert result is not None
```

### Customise TestModel output

```python
# Return a specific string as the model's text response
TestModel(custom_output_text="Sunny with a chance of rain")

# Return specific structured data matching output_type
TestModel(custom_output_data={"title": "Q3 Review", "action_items": ["Fix bug #42"]})
```

## `FunctionModel` — Full Control

Use `FunctionModel` when you need to control exactly which tools are called and with
which arguments. Your function acts as the "LLM".

```python
import re
from pydantic_ai import ModelMessage, ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

def fake_model(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    if len(messages) == 1:
        # First turn: parse the user prompt and call a tool
        user_text = messages[0].parts[-1].content
        m = re.search(r"\d{4}-\d{2}-\d{2}", user_text)
        date_str = m.group() if m else "2024-01-01"
        return ModelResponse(parts=[
            ToolCallPart("get_forecast", {"location": "London", "date": date_str})
        ])
    else:
        # Second turn: use the tool result to produce a final response
        tool_result = messages[-1].parts[0]
        assert tool_result.part_kind == "tool-return"
        return ModelResponse(parts=[TextPart(f"Forecast: {tool_result.content}")])

async def test_forecast_future_date():
    with my_agent.override(model=FunctionModel(fake_model)):
        result = await my_agent.run("What's the weather on 2032-06-15?")
    assert result.output.startswith("Forecast:")
```

## `Agent.override` — Inject into Application Code

`override` lets you replace a model, deps, or toolsets on an agent **without** changing the
call site. It's a context manager that reverts after the `with` block.

```python
# Override model only
with my_agent.override(model=TestModel()):
    result = await run_pipeline(prompts, conn)

# Override deps only (useful for injecting fakes)
fake_deps = FakeDeps(db=FakeDatabase(), http=FakeHttpClient())
with my_agent.override(deps=fake_deps):
    result = await my_agent.run("Hello")

# Override both
with my_agent.override(model=TestModel(), deps=fake_deps):
    ...
```

## `capture_run_messages` — Assert the Full Exchange

Use to inspect the full list of `ModelRequest` / `ModelResponse` messages from the most
recent agent run inside the context.

```python
from datetime import timezone
from pydantic_ai import capture_run_messages, RequestUsage
from pydantic_ai import ModelRequest, ModelResponse, UserPromptPart, TextPart, ToolCallPart, ToolReturnPart
from pydantic_ai.models.test import TestModel
from dirty_equals import IsNow, IsStr

async def test_full_exchange():
    with capture_run_messages() as messages:
        with my_agent.override(model=TestModel()):
            await run_pipeline([("London forecast for 2024-11-28", 1)], conn)

    assert messages == [
        ModelRequest(
            parts=[UserPromptPart(
                content="London forecast for 2024-11-28",
                timestamp=IsNow(tz=timezone.utc),   # dirty-equals: any recent timestamp
            )],
            instructions=IsStr(),
            timestamp=IsNow(tz=timezone.utc),
            run_id=IsStr(),
        ),
        ModelResponse(
            parts=[ToolCallPart(
                tool_name="get_forecast",
                args=IsStr() | dict,
                tool_call_id=IsStr(),
            )],
            model_name="test",
            timestamp=IsNow(tz=timezone.utc),
            run_id=IsStr(),
        ),
        ModelRequest(
            parts=[ToolReturnPart(
                tool_name="get_forecast",
                content=IsStr(),
                tool_call_id=IsStr(),
                timestamp=IsNow(tz=timezone.utc),
            )],
            timestamp=IsNow(tz=timezone.utc),
            run_id=IsStr(),
        ),
        ModelResponse(
            parts=[TextPart(content=IsStr())],
            model_name="test",
            timestamp=IsNow(tz=timezone.utc),
            run_id=IsStr(),
        ),
    ]
```

## Reusable Fixtures

Put shared overrides in `conftest.py`:

```python
# conftest.py
import pytest
from pydantic_ai import models
from pydantic_ai.models.test import TestModel
from my_app import my_agent

models.ALLOW_MODEL_REQUESTS = False   # global guard for all tests

@pytest.fixture
def test_model():
    with my_agent.override(model=TestModel()):
        yield

@pytest.fixture
def test_model_custom():
    with my_agent.override(model=TestModel(custom_output_text="Fixed response")):
        yield
```

```python
# test_my_agent.py
import pytest
pytestmark = pytest.mark.anyio

async def test_runs_tools(test_model):
    result = await my_agent.run("Hello")
    assert result.output is not None

async def test_custom_output(test_model_custom):
    result = await my_agent.run("Hello")
    assert result.output == "Fixed response"
```

## Testing Tools in Isolation

Test tool functions directly — they're plain Python functions.

```python
from dataclasses import dataclass
import pytest

@dataclass
class FakeDeps:
    db: FakeDatabase

# Tools are just functions; call them directly if they don't use RunContext
def test_roll_dice():
    from my_agent import roll_dice
    result = roll_dice()
    assert 1 <= int(result) <= 6

# For tools that use RunContext, test via FunctionModel
async def test_get_user_tool_not_found():
    def model_fn(messages, info):
        return ModelResponse(parts=[ToolCallPart("get_user", {"user_id": "missing-id"})])

    with my_agent.override(model=FunctionModel(model_fn)):
        # ModelRetry should cause the model to be called again
        with pytest.raises(Exception):
            await my_agent.run("Find user missing-id", deps=FakeDeps(db=FakeDatabase()))
```

## Testing Output Validators

Output validators run automatically during agent runs — test them via `override`:

```python
async def test_output_validator_rejects_empty_action_items():
    # TestModel returns empty action_items by default → validator raises ModelRetry
    # TestModel will retry once with corrected data
    with my_agent.override(model=TestModel()):
        result = await my_agent.run("Summarise this meeting.")
    # Validator should have forced at least one retry
    assert result.output is not None
```

## Quick Reference

| Tool | When to use |
|---|---|
| `TestModel` | Fast, runs all tools, good for smoke tests and integration paths |
| `TestModel(custom_output_text=...)` | When you need a specific text response |
| `TestModel(custom_output_data=...)` | When you need specific structured output |
| `FunctionModel` | Full control — test specific tool call sequences or date/content logic |
| `Agent.override(model=...)` | Inject test model into app code without changing call sites |
| `Agent.override(deps=...)` | Inject fake services/databases |
| `capture_run_messages` | Assert the full agent<->model message exchange |
| `ALLOW_MODEL_REQUESTS = False` | Safety guard — prevent accidental real LLM calls |
