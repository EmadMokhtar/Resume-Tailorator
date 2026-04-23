---
applyTo: "**/*.py"
---

# Pydantic AI - Agentic Workflows and Multi-Agent Applications

Reference: https://ai.pydantic.dev/multi-agent-applications/

## Complexity Levels

1. **Single agent** - one agent handles everything
2. **Agent delegation** - agent delegates to a sub-agent via a tool, then resumes
3. **Programmatic hand-off** - app code calls agents in sequence (human-in-the-loop)
4. **Graph-based** - `pydantic-graph` for complex state machines
5. **Deep agents** - autonomous agents with planning, file ops, and sandboxed code execution

## 1. Agent Delegation (Sub-Agent via Tool)

A parent agent calls a specialist sub-agent from inside a tool.

Key rules:
- Always pass `usage=ctx.usage` so token counts roll up to the parent's total.
- Pass `deps=ctx.deps` when sub-agent needs the same dependencies.
- Agents are **stateless globals** — do NOT include them in `deps_type`.

```python
from pydantic_ai import Agent, RunContext, UsageLimits

joke_generation_agent = Agent(
    "google-gla:gemini-3-flash-preview",
    output_type=list[str],
)

joke_selection_agent = Agent(
    "openai:gpt-4o",
    instructions="Use `joke_factory` to generate jokes, then pick the best one.",
)

@joke_selection_agent.tool
async def joke_factory(ctx: RunContext[None], count: int) -> list[str]:
    """Generate a list of jokes to choose from."""
    result = await joke_generation_agent.run(
        f"Generate {count} jokes.",
        usage=ctx.usage,        # roll up token usage to parent
    )
    return result.output

result = joke_selection_agent.run_sync(
    "Tell me a joke.",
    usage_limits=UsageLimits(request_limit=5, total_tokens_limit=1000),
)
print(result.output)
print(result.usage())  # includes usage from both agents
```

### With shared dependencies
```python
from dataclasses import dataclass
import httpx

@dataclass
class Deps:
    http: httpx.AsyncClient
    api_key: str

@parent_agent.tool
async def delegate_task(ctx: RunContext[Deps], task: str) -> str:
    result = await sub_agent.run(
        task,
        deps=ctx.deps,       # share the same dependency instance
        usage=ctx.usage,     # roll up usage
    )
    return result.output
```

## 2. Programmatic Hand-Off (Sequential Pipeline)

Chain agents in application code where each step's output feeds the next.
Use `RunUsage` to accumulate usage across all separate runs.

```python
from pydantic_ai import Agent
from pydantic_ai.usage import RunUsage
from pydantic import BaseModel

class TranscriptSummary(BaseModel):
    key_points: list[str]
    action_items: list[str]

class ActionPlan(BaseModel):
    tasks: list[str]
    owner_suggestions: dict[str, str]

summariser = Agent("openai:gpt-4o-mini", output_type=TranscriptSummary,
                   instructions="Extract key points and action items.")
planner    = Agent("openai:gpt-4o",      output_type=ActionPlan,
                   instructions="Create a concrete action plan.")

async def run_pipeline(transcript: str) -> ActionPlan:
    total_usage = RunUsage()
    summary = await summariser.run(f"Summarise:\n{transcript}", usage=total_usage)
    plan    = await planner.run(
        f"Create an action plan from:\n{summary.output.model_dump_json(indent=2)}",
        usage=total_usage,
    )
    print(f"Total pipeline usage: {total_usage}")
    return plan.output
```

## 3. Human-in-the-Loop (Programmatic Hand-Off with User Input)

Loop until the model produces the desired output, prompting the user between turns.

```python
from pydantic_ai import Agent, UsageLimits
from pydantic_ai.usage import RunUsage
from pydantic_ai.messages import ModelMessage
from typing import Literal
from pydantic import BaseModel

class BookingResult(BaseModel):
    flight_number: str

class Failed(BaseModel):
    """Unable to complete the booking."""

search_agent = Agent(
    "openai:gpt-4o-mini",
    output_type=BookingResult | Failed,  # type: ignore
    instructions='Use `search_flights` to find a flight.',
)

usage_limits = UsageLimits(request_limit=15)

async def book_flight() -> BookingResult | None:
    total_usage = RunUsage()
    message_history: list[ModelMessage] | None = None

    for _ in range(3):      # max 3 user attempts
        user_input = input("Where would you like to fly? ")
        result = await search_agent.run(
            user_input,
            message_history=message_history,
            usage=total_usage,
            usage_limits=usage_limits,
        )
        if isinstance(result.output, BookingResult):
            return result.output
        # Let the model know to try again, keeping full history
        message_history = result.all_messages(
            output_tool_return_content="Please try again."
        )
    return None
```

## 4. Router / Handoff Pattern

A lightweight router picks the right specialist agent.

```python
from pydantic_ai import Agent
from pydantic import BaseModel
from typing import Literal

class Route(BaseModel):
    department: Literal["billing", "support", "sales"]

router = Agent("openai:gpt-4o-mini", output_type=Route,
               instructions="Route the user message to the correct department.")

AGENTS: dict[str, Agent] = {
    "billing": Agent("openai:gpt-4o-mini", instructions="You handle billing."),
    "support": Agent("openai:gpt-4o-mini", instructions="You handle tech support."),
    "sales":   Agent("openai:gpt-4o-mini", instructions="You handle sales."),
}

async def handle(message: str) -> str:
    route  = await router.run(message)
    result = await AGENTS[route.output.department].run(message)
    return result.output
```

## 5. Stateful Multi-Turn Session

```python
from pydantic_ai.messages import ModelMessage

class Session:
    def __init__(self, agent: Agent):
        self.agent = agent
        self.history: list[ModelMessage] = []

    async def chat(self, user_message: str) -> str:
        result = await self.agent.run(
            user_message,
            message_history=self.history,
        )
        self.history = result.all_messages()
        return result.output
```

## Sharing Dependencies Across Agents

Initialise expensive resources once and reuse via `deps`.

```python
import httpx

async def main():
    async with httpx.AsyncClient() as http:
        deps = Deps(http=http, db=DatabaseClient())
        result_a = await agent_a.run("Task A", deps=deps)
        result_b = await agent_b.run(result_a.output, deps=deps)
```

## Workflow Best Practices

- **Specialise agents** — narrow, well-defined instructions per agent.
- **Use smaller models for subtasks** — `gpt-4o-mini` / `gemini-flash` for routing and extraction; larger models for reasoning.
- **Prefer structured `output_type`** — so orchestrators reliably parse sub-agent results.
- **Always pass `usage=ctx.usage`** in delegation tools for accurate cost tracking.
- **Use `RunUsage`** to accumulate usage across programmatic hand-offs.
- **Avoid deep nesting** — more than 3 levels of agent delegation is hard to debug; flatten.
- **Store `result.all_messages()`** for observability, evals, and conversation replay.
