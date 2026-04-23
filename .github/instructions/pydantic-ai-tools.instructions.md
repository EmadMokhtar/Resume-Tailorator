---
applyTo: "**/*.py"
---

# Pydantic AI - Tools, Toolsets, and Output Validators

Reference: https://ai.pydantic.dev/tools/

Tools let agents call Python functions to retrieve information or perform actions.
Pydantic AI generates JSON schemas from type annotations and validates arguments automatically.

## `@agent.tool` - Tool with RunContext

Use when the tool needs access to dependencies (`ctx.deps`) or run metadata.

```python
from pydantic_ai import Agent, RunContext
from dataclasses import dataclass
import httpx

@dataclass
class Deps:
    http: httpx.AsyncClient
    api_key: str

agent = Agent("openai:gpt-4o", deps_type=Deps)

@agent.tool
async def search_knowledge_base(ctx: RunContext[Deps], query: str) -> str:
    """Search the internal knowledge base and return relevant content.

    Args:
        query: The search query string.
    """
    resp = await ctx.deps.http.get(
        "https://api.internal/search",
        params={"q": query},
        headers={"Authorization": f"Bearer {ctx.deps.api_key}"},
    )
    resp.raise_for_status()
    return resp.json()["content"]
```

## `@agent.tool_plain` - Plain Tool (no context)

Use for pure functions that don't need deps or run metadata.

```python
import random
from datetime import datetime, timezone

@agent.tool_plain
def get_current_utc_time() -> str:
    """Return the current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()

@agent.tool_plain
def roll_dice(sides: int = 6) -> int:
    """Roll a die and return the result.

    Args:
        sides: Number of sides on the die (default 6).
    """
    return random.randint(1, sides)
```

## Registering Tools at Agent Creation

Pass via the `tools` argument — useful for sharing tools between agents.

```python
from pydantic_ai import Agent, RunContext, Tool

def get_player_name(ctx: RunContext[str]) -> str:
    """Get the current player's name."""
    return ctx.deps

def roll_dice() -> str:
    """Roll a six-sided die."""
    return str(random.randint(1, 6))

# Pydantic AI infers takes_ctx from the signature
agent_a = Agent("openai:gpt-4o", deps_type=str, tools=[get_player_name, roll_dice])

# Explicit control with Tool()
agent_b = Agent(
    "openai:gpt-4o",
    deps_type=str,
    tools=[
        Tool(roll_dice, takes_ctx=False),
        Tool(get_player_name, takes_ctx=True, description="Override description"),
    ],
)
```

## Toolsets (MCP Servers and Tool Collections)

Use `toolsets=` to attach external tool providers (MCP servers, third-party tools).
All `tools` and `toolsets` are merged into a single combined toolset for the model.

```python
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStreamableHTTP

mcp_server = MCPServerStreamableHTTP("http://localhost:8000/mcp")

agent = Agent(
    "openai:gpt-4o",
    tools=[my_local_tool],         # local Python tools
    toolsets=[mcp_server],         # external tool providers
)
```

## Type Annotations and Docstrings Drive the Schema

The JSON schema sent to the model is built from type annotations and docstrings.
Pydantic AI extracts parameter descriptions from Google, NumPy, and Sphinx docstrings.

```python
from pydantic import BaseModel, Field

class SearchOptions(BaseModel):
    max_results: int = Field(default=5, ge=1, le=20, description="Max results to return")
    language: str = Field(default="en", description="ISO 639-1 language code")

@agent.tool_plain
def search_docs(query: str, options: SearchOptions) -> list[str]:
    """Search internal documentation.

    Args:
        query: The search query.
        options: Search configuration options.
    """
    ...
```

## Async vs Sync Tools

Both are fully supported. Sync tools run in a thread pool automatically.

```python
@agent.tool
async def fetch_from_db(ctx: RunContext[Deps], record_id: str) -> dict:
    """Fetch a record from the database by ID."""
    return await ctx.deps.db.get(record_id)

@agent.tool_plain
def compute_hash(text: str) -> str:
    """Compute a SHA-256 hash of the input text."""
    import hashlib
    return hashlib.sha256(text.encode()).hexdigest()
```

## Retrying with `ModelRetry`

Raise `ModelRetry` inside a tool to send a corrective message back to the model.

```python
from pydantic_ai import ModelRetry

@agent.tool
async def get_user(ctx: RunContext[Deps], user_id: str) -> dict:
    """Look up a user record by their ID."""
    user = await ctx.deps.db.find_user(user_id)
    if user is None:
        raise ModelRetry(f"No user found with id '{user_id}'. Verify the ID and try again.")
    return user.model_dump()
```

## Output Validator

Use `@agent.output_validator` to validate or transform the model's final output.
Raise `ModelRetry` to ask the model to produce a corrected output.

```python
from pydantic_ai import ModelRetry, RunContext

@agent.output_validator
async def validate_output(ctx: RunContext[Deps], output: MeetingSummary) -> MeetingSummary:
    """Validate the meeting summary has required fields."""
    if len(output.action_items) == 0:
        raise ModelRetry("Summary must include at least one action item. Please try again.")
    # Optionally transform the output
    output.title = output.title.strip().title()
    return output
```

## RunContext Fields

Inside `@agent.tool`, the `ctx` object provides:

| Field | Type | Description |
|---|---|---|
| `ctx.deps` | `DepsType` | Injected dependencies |
| `ctx.model` | `Model` | The model currently being used |
| `ctx.usage` | `RunUsage` | Token usage so far; pass as `usage=ctx.usage` to sub-agents |
| `ctx.messages` | `list[ModelMessage]` | Messages exchanged so far in this run |

## Tool Return Values

Tools can return anything Pydantic can serialise to JSON:
- Primitives: `str`, `int`, `float`, `bool`, `None`
- Collections: `list[str]`, `dict[str, Any]`
- Pydantic models (serialised as dicts)

## Best Practices

- One **focused responsibility** per tool.
- Always write a **docstring** — it becomes the tool description for the model.
- Use `Field(description=...)` on Pydantic model parameters.
- Raise `ModelRetry` for recoverable failures (not found, wrong args); let other exceptions propagate.
- Prefer `@agent.tool` when in doubt; switch to `@agent.tool_plain` only when deps are genuinely not needed.
