---
name: pydantic-ai-agents
description: Guidance for building and running Pydantic AI agents in this repository, including dependencies, instructions, outputs, streaming, and message history.
---

# Pydantic AI Agents

> Topic scope: Pydantic AI agent construction, execution, and message history
> Primary references: `../pydantic-ai/SKILL.md`, `https://pydantic.dev/docs/ai/core-concepts/agent/`

## Overview
Summarizes the core agent patterns this repo should prefer with Pydantic AI: global stateless `Agent` instances, typed dependencies via `deps_type`, dynamic instructions through `RunContext`, structured outputs, streaming, and message history for multi-turn conversations.

## Capabilities
- Create agents with string or structured outputs
- Inject runtime services with `deps_type` and `RunContext`
- Add static or dynamic instructions
- Run agents synchronously, asynchronously, or with streaming
- Continue conversations with message history

## Key Symbols
| Symbol | Type | Description |
|--------|------|-------------|
| `Agent` | class | Stateless reusable LLM interface with typed deps and output |
| `RunContext` | class | Access to runtime deps, model, usage, and messages |
| `instructions=` | argument | Preferred way to define a static instruction prompt |
| `@agent.instructions` | decorator | Adds dynamic instructions computed per run |
| `output_type` | argument | Declares plain-text, model, or union output types |
| `agent.run` | method | Async execution entry point |
| `agent.run_stream` | method | Streaming execution for partial text or events |
| `result.new_messages` | method | Returns only messages produced in the current run |
| `UsageLimits` | class | Caps requests or token consumption for a run |

## Inputs & Outputs
| Symbol | Input | Output |
|--------|-------|--------|
| `Agent(...)` | `model`, optional `deps_type`, `instructions`, `output_type` | Configured reusable agent |
| `agent.run(...)` | User prompt plus optional `deps`, `message_history`, `model`, `model_settings` | `AgentRunResult` with typed `output` and usage data |
| `RunContext[Deps]` | Runtime dependency instance and run metadata | Values for instructions, tools, or validators |
| `agent.run_stream(...)` | Prompt and optional runtime args | Stream object for text deltas or events |
| `result.new_messages()` | Prior run result | Continuation-safe message history |
| `result.all_messages()` | Prior run result | Full run history for logging, persistence, or replay |
| `usage=` / `usage_limits=` | Shared `RunUsage` object or `UsageLimits` values | Cross-run accounting or per-run limits |

## Usage Example
```python
from dataclasses import dataclass

from pydantic import BaseModel
from pydantic_ai import Agent, RunContext


@dataclass
class Deps:
    user_name: str


class Greeting(BaseModel):
    message: str


agent = Agent(
    "openai:gpt-4o-mini",
    deps_type=Deps,
    output_type=Greeting,
    instructions="Be concise and friendly.",
)


@agent.instructions
def personalize(ctx: RunContext[Deps]) -> str:
    return f"The user's name is {ctx.deps.user_name}."


result = agent.run_sync("Say hello.", deps=Deps(user_name="Emad"))
print(result.output.message)
```

## Internal Dependencies
- `../pydantic-ai/SKILL.md` — entry point and topic boundaries
- `../pydantic-ai-tools/SKILL.md` — add tools and output validators to agents
- `../pydantic-ai-models/SKILL.md` — choose models and provider settings for agents

## External Dependencies
- `pydantic-ai` — `Agent`, `RunContext`, run results, streaming, and history support
- `pydantic` — typed output models and validation
- `dataclasses` — lightweight dependency containers for `deps_type`

## Notes
- **Instantiate once:** Agents are designed to be module-level globals, not rebuilt per request.
- **`deps_type` rule:** Pass the dependency **type** at construction and the dependency **instance** via `deps=` at run time.
- **Instructions:** Prefer `instructions=` over `system_prompt=` for new code. Multiple dynamic instruction decorators concatenate.
- **Outputs:** Omit `output_type` for plain `str`; use a Pydantic model for structured output; use unions when more than one valid shape is expected.
- **Runs:** Prefer `await agent.run(...)` in app code. Reserve `run_sync()` for scripts, tests, and simple CLIs.
- **Streaming:** Use `run_stream()` for partial text and `run_stream_events()` when you also need tool-call or graph events.
- **History:** `new_messages()` is the normal way to continue a conversation without regenerating prior instructions; `all_messages()` is better for persistence and observability.
- **Usage:** Pass a shared `RunUsage` object when multiple runs should roll up into one total, and use `UsageLimits` to cap requests or tokens.

## Changelog
| Date | Change |
|------|--------|
| 2026-04-21 | Initial skill created |
| 2026-04-21 | Removed dead local instruction reference to keep the skill self-contained |
| 2026-04-22 | Converted to Agent Skills spec directory structure with YAML frontmatter |
