---
applyTo: "**/*.py"
---

# Pydantic AI - Agents

Reference: https://ai.pydantic.dev/agent

An `Agent` is the primary interface to an LLM. It is **stateless and designed to be global** —
instantiate once at module level and reuse across all requests (like a FastAPI app).

## Creating an Agent

```python
from pydantic_ai import Agent
from pydantic import BaseModel, Field

class MeetingSummary(BaseModel):
    title: str = Field(description="Short title of the meeting")
    action_items: list[str] = Field(description="Concrete next steps")
    attendees: list[str]

agent = Agent(
    "openai:gpt-4o",
    output_type=MeetingSummary,          # omit for plain str output
    instructions="You are a helpful assistant.",
    deps_type=MyDeps,                    # omit if no dependencies needed
)
```

The agent's generic type is `Agent[DepsType, OutputType]`.

## Dependencies (`deps_type`)

Inject services, clients, and config via a dataclass. This is how Pydantic AI avoids global state.

```python
from dataclasses import dataclass
import httpx
from pydantic_ai import Agent, RunContext

@dataclass
class Deps:
    user_id: str
    db: DatabaseClient
    http: httpx.AsyncClient

agent = Agent("openai:gpt-4o", deps_type=Deps)
```

- Pass the **type** (not instance) to `deps_type` at construction time.
- Pass an **instance** to `deps=` at run time.

## Instructions (System Prompt)

### Static string
Both `instructions=` and `system_prompt=` are valid kwargs; prefer `instructions=`.

```python
agent = Agent("openai:gpt-4o", instructions="You are a concise assistant.")
```

### Dynamic (decorator)
Both `@agent.system_prompt` and `@agent.instructions` are valid decorators.

```python
@agent.system_prompt
async def build_instructions(ctx: RunContext[Deps]) -> str:
    user = await ctx.deps.db.get_user(ctx.deps.user_id)
    return f"You are helping {user.name}. Their subscription: {user.plan}."
```

- Multiple decorators are allowed; return values are concatenated.
- Use `async def` when fetching data; sync is fine for pure logic.

## Output Types

### Plain text (default)
```python
agent = Agent("openai:gpt-4o")
result = agent.run_sync("Hello")
print(result.output)  # str
```

### Structured Pydantic model
```python
agent = Agent("openai:gpt-4o", output_type=MeetingSummary)
result = await agent.run("Summarise the meeting transcript.")
summary = result.output           # typed as MeetingSummary
print(summary.title)
print(summary.action_items)       # list[str]
```

### Multiple types (union)
```python
agent = Agent("openai:gpt-4o", output_type=[MeetingSummary, str])
# Returns MeetingSummary when extractable, str otherwise
```

## Running an Agent

```python
# Async (preferred)
result = await agent.run("Your prompt", deps=Deps(...))
print(result.output)

# Sync (scripts and tests only)
result = agent.run_sync("Your prompt", deps=Deps(...))

# With model override per run
result = await agent.run("Your prompt", model="anthropic:claude-3-5-haiku-latest")
```

## Streaming

### Stream text
```python
async with agent.run_stream("Explain async Python") as stream:
    async for chunk in stream.stream_text():
        print(chunk, end="", flush=True)
```

### Stream all events (tools + output)
```python
from pydantic_ai import AgentRunResultEvent, AgentStreamEvent

async for event in agent.run_stream_events("What's the weather in Tokyo?"):
    if isinstance(event, AgentRunResultEvent):
        print(event.result.output)
    else:
        print(event)   # FunctionToolCallEvent, PartStartEvent, etc.
```

### Low-level graph iteration
```python
async with agent.iter("Long-running task") as agent_run:
    async for node in agent_run:
        print(node)    # inspect each graph node
result = agent_run.result
```

## Message History (Multi-Turn Conversation)

```python
result1 = agent.run_sync("What is the capital of France?")

# Pass new_messages() to continue — does NOT re-generate instructions
result2 = agent.run_sync(
    "What is its population?",
    message_history=result1.new_messages(),
)
```

- `result.new_messages()` — messages from this run only (use for continuation)
- `result.all_messages()` — all messages including prior runs (use for logging/evals)

### Persist conversation to JSON
```python
from pydantic_ai import ModelMessagesTypeAdapter
from pydantic_core import to_jsonable_python

serialised = to_jsonable_python(result1.all_messages())
history    = ModelMessagesTypeAdapter.validate_python(serialised)
result3    = agent.run_sync("Another question", message_history=history)
```

## Usage Tracking and Limits

```python
from pydantic_ai import UsageLimits

result = await agent.run(
    "Analyse this document",
    usage_limits=UsageLimits(request_limit=10, total_tokens_limit=5000),
)
print(result.usage())
# RunUsage(input_tokens=..., output_tokens=..., requests=1, tool_calls=0)
```

Accumulate usage across multiple separate runs:
```python
from pydantic_ai.usage import RunUsage

total_usage = RunUsage()
result1 = await agent.run("Step 1", usage=total_usage)
result2 = await agent.run("Step 2", usage=total_usage)
print(total_usage)  # combined totals
```

## Output Validator

Use `@agent.output_validator` to post-process or validate the model's output.

```python
from pydantic_ai import ModelRetry

@agent.output_validator
async def validate_summary(ctx: RunContext[Deps], output: MeetingSummary) -> MeetingSummary:
    if not output.action_items:
        raise ModelRetry("The summary must include at least one action item. Try again.")
    return output
```

## Local Web UI (development only)

```python
# pip install "pydantic-ai-slim[web]"
app = agent.to_web()   # returns an ASGI app
# Run: uvicorn my_module:app --host 127.0.0.1 --port 7932
```

## Testing with TestModel

```python
from pydantic_ai.models.test import TestModel

def test_agent():
    with agent.override(model=TestModel()):
        result = agent.run_sync("Hello")
        assert result.output is not None
```

## Error Handling

```python
from pydantic_ai.exceptions import UnexpectedModelBehavior
from pydantic_ai import ModelRetry

# In tools or output validators, raise ModelRetry to let the model fix its mistake:
raise ModelRetry("No record found for that ID. Please try a different one.")

# Catch unexpected model failures:
try:
    result = await agent.run("...", deps=deps)
except UnexpectedModelBehavior as e:
    print(f"Model error: {e}")
```
