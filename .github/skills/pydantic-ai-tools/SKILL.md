---
name: pydantic-ai-tools
description: Guidance for exposing Python functions to Pydantic AI models, including tool registration, schemas, retries, output validation, and external toolsets.
---

# Pydantic AI Tools

> Topic scope: Pydantic AI tools, tool registration, retries, validators, and toolsets
> Primary references: `../pydantic-ai-agents/SKILL.md`, `https://pydantic.dev/docs/ai/tools-toolsets/tools/`

## Overview
Covers how Pydantic AI exposes Python functions to models. Use this skill for tool decorators, schema generation from type hints and docstrings, shared registration patterns, recoverable retries with `ModelRetry`, final output validation, and attaching external toolsets such as MCP servers.

## Capabilities
- Register tools with or without `RunContext`
- Reuse tools through `tools=` and `Tool(...)`
- Shape tool schemas with type hints, models, and docstrings
- Ask the model to recover from bad calls with `ModelRetry`
- Validate or normalize final output before returning it
- Combine local tools with external toolsets

## Key Symbols
| Symbol | Type | Description |
|--------|------|-------------|
| `@agent.tool` | decorator | Registers a tool that receives `RunContext` |
| `@agent.tool_plain` | decorator | Registers a pure tool with no context parameter |
| `Tool` | class | Wraps a function for explicit reusable registration metadata |
| `ModelRetry` | exception | Sends corrective feedback so the model can try again |
| `@agent.output_validator` | decorator | Validates or transforms the final agent output |
| `toolsets=` | argument | Attaches external tool providers alongside local tools |

## Inputs & Outputs
| Symbol | Input | Output |
|--------|-------|--------|
| `@agent.tool` | Function with `ctx: RunContext[...]` plus typed args | Callable tool exposed to the model |
| `@agent.tool_plain` | Typed sync or async function with no context arg | Simpler tool exposed to the model |
| `Tool(function, ...)` | Existing function plus optional metadata overrides | Reusable tool registration object |
| `ModelRetry(...)` | Recoverable validation or lookup failure | Retry message sent back to the model |
| `@agent.output_validator` | Function receiving final parsed output | Validated/transformed output or retry |
| `toolsets=[...]` | MCP server or other external tool providers | Combined tool inventory available to the model |

## Usage Example
```python
from dataclasses import dataclass

from pydantic_ai import Agent, ModelRetry, RunContext


@dataclass
class Deps:
    users: dict[str, str]


agent = Agent("openai:gpt-4o-mini", deps_type=Deps)


@agent.tool
def get_user_name(ctx: RunContext[Deps], user_id: str) -> str:
    """Return a user's display name."""
    try:
        return ctx.deps.users[user_id]
    except KeyError as exc:
        raise ModelRetry(f"Unknown user_id: {user_id}") from exc


@agent.tool_plain
def make_slug(text: str) -> str:
    """Convert text into a simple slug."""
    return text.lower().replace(" ", "-")
```

## Internal Dependencies
- `../pydantic-ai/SKILL.md` — topic boundaries and navigation
- `../pydantic-ai-agents/SKILL.md` — how tools plug into agent runs and `RunContext`
- `../pydantic-ai-workflows/SKILL.md` — deeper orchestration patterns for sub-agent handoff

## External Dependencies
- `pydantic-ai` — tool registration, retries, output validators, and external toolset support
- `pydantic` — parameter models and JSON schema metadata
- `mcp` / provider SDKs — optional external tool providers when using `toolsets=`

## Notes
- **Decorator choice:** Use `@agent.tool` when the function needs deps, usage, model info, or current messages. Use `@agent.tool_plain` for pure helpers.
- **Schema source:** Tool JSON schema comes from Python type hints plus docstrings; add `Field(description=...)` on Pydantic models to make arguments clearer to the model.
- **Registration patterns:** Decorators are best for agent-local tools. Use `tools=[callable, Tool(...)]` when sharing tools across agents or when you need explicit metadata control.
- **Sync vs async:** Both work. Sync tools are run in a thread pool automatically.
- **`ModelRetry`:** Raise it only for recoverable issues such as missing records or invalid user-supplied arguments. Let real infrastructure exceptions bubble up.
- **Output validators:** They run after the model produces final output, not after each tool call. Use them to enforce business rules or normalize the returned value.
- **Toolsets and handoff:** `tools` and `toolsets` are merged. For sub-agent handoff inside a tool, pass `usage=ctx.usage` and usually `deps=ctx.deps` so usage and shared resources stay aligned.

## Changelog
| Date | Change |
|------|--------|
| 2026-04-21 | Initial skill created |
| 2026-04-21 | Replaced dead instruction-file links with in-tree skill references |
| 2026-04-22 | Converted to Agent Skills spec directory structure with YAML frontmatter |
