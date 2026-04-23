---
name: pydantic-ai-workflows
description: Guidance for Pydantic AI multi-agent workflows, delegation, and handoff. Use it when deciding between a single agent, tool-based delegation, and application-level orchestration.
---

# Skill: Pydantic AI Workflows

> Topic scope: Pydantic AI multi-agent coordination, delegation, and handoff patterns
> Primary references: `../pydantic-ai-agents/SKILL.md`, `https://pydantic.dev/docs/ai/guides/multi-agent-applications/`

## Overview
Summarizes the practical Pydantic AI workflow patterns to prefer before reaching for heavier orchestration. Use it to choose between a single agent, tool-based delegation, and programmatic handoff; preserve shared dependencies and cumulative usage; and avoid graph or deep-agent complexity unless the problem truly needs it.

## Capabilities
- Choose between delegation and application-level handoff patterns
- Roll token and request usage up across related agent runs
- Share dependency objects safely across cooperating agents
- Keep multi-agent designs shallow, observable, and debuggable
- Recognize when graph-based or deep-agent systems are overkill

## Key Symbols
| Symbol | Type | Description |
|--------|------|-------------|
| `Agent` | class | Defines a specialist or coordinator agent |
| `RunContext` | class | Gives tools access to shared `deps` and current `usage` |
| `RunUsage` | class | Accumulates usage across separate programmatic runs |
| `UsageLimits` | class | Constrains request count or token consumption |
| `Agent.run` | method | Executes an agent asynchronously for delegation or handoff |
| `result.all_messages()` | method | Returns full conversation history for replay or observability |

## Inputs & Outputs
| Symbol | Input | Output |
|--------|-------|--------|
| `Agent.run` | `prompt: str | list`, optional `deps`, `usage`, `message_history` | `AgentRunResult` with `output`, usage, and messages |
| `RunContext.deps` | Shared dependency object from parent run | Reusable services for sub-agents or tools |
| `RunContext.usage` | Parent run usage tracker | Aggregated usage across delegated calls |
| `RunUsage` | No required input | Mutable accumulator for multi-step application handoffs |
| `UsageLimits` | Request or token caps | Guardrails for expensive workflows |

## Usage Example
```python
from dataclasses import dataclass

import httpx
from pydantic_ai import Agent, RunContext
from pydantic_ai.usage import RunUsage


@dataclass
class Deps:
    http: httpx.AsyncClient


writer = Agent("openai:gpt-4o-mini", output_type=str)
reviewer = Agent("openai:gpt-4o", instructions="Use `draft_copy`, then improve it.")


@reviewer.tool
async def draft_copy(ctx: RunContext[Deps], topic: str) -> str:
    result = await writer.run(topic, deps=ctx.deps, usage=ctx.usage)
    return result.output


async def handoff(topic: str, deps: Deps) -> str:
    total_usage = RunUsage()
    result = await reviewer.run(topic, deps=deps, usage=total_usage)
    return result.output
```

## Internal Dependencies
- `../pydantic-ai/SKILL.md` — baseline Pydantic AI boundaries and companion-skill routing
- `../pydantic-ai-agents/SKILL.md` — agent lifecycle patterns reused by delegation and handoff flows

## External Dependencies
- `pydantic-ai` — agents, usage tracking, and run context primitives
- `pydantic` — structured outputs for routers and handoff contracts
- `dataclasses` — lightweight shared dependency containers
- `httpx` — async client used in the shared-dependency example

## Notes
- Prefer a **single agent** first. Add more agents only when specialization clearly improves prompts, cost, or maintainability.
- In a delegation tool, pass **`usage=ctx.usage`** so sub-agent cost rolls into the parent run.
- Pass **`deps=ctx.deps`** when the sub-agent should reuse the same clients, stores, or caches.
- Keep agents as stateless globals; do **not** put agent instances inside `deps_type`.
- Use **programmatic handoff** when your app must inspect intermediate output, involve a human, or branch explicitly.
- Save **`result.all_messages()`** when you need auditability, replay, or debugging.
- Reach for **`pydantic-graph`** only when you truly need a state machine with explicit transitions.
- Avoid **deep agents** for normal business workflows; they add planning, tool autonomy, and debugging overhead that most CRUD, routing, and extraction flows do not need.

## Changelog
| Date | Change |
|------|--------|
| 2026-04-22 | Converted the skill to Agent Skills spec layout with `SKILL.md`, YAML frontmatter, and updated relative links |
| 2026-04-21 | Initial skill created for delegation, handoff, usage rollup, and complexity selection guidance |
| 2026-04-21 | Removed dead local instruction reference to keep the skill self-contained |
