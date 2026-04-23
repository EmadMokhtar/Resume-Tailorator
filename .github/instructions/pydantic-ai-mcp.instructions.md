---
applyTo: "**/*.py"
---

# Pydantic AI - MCP (Model Context Protocol)

Reference: https://ai.pydantic.dev/mcp/overview/

MCP is a standardised protocol that lets agents connect to external tools and services.
Pydantic AI can act as an **MCP client** (consuming tool servers) and agents can be
**exposed as MCP servers**.

## Install

```
pip install "pydantic-ai-slim[mcp]"
# or
uv add "pydantic-ai-slim[mcp]"
```

## Attaching MCP Servers to an Agent

MCP servers are passed via `toolsets=` — each server is a toolset providing tools to the model.

### Streamable HTTP (recommended)

Use when you have a running MCP server reachable over HTTP.

```python
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStreamableHTTP

server = MCPServerStreamableHTTP("http://localhost:8000/mcp")

agent = Agent("openai:gpt-4o", toolsets=[server])

async def main():
    # Wrap in the agent context manager for efficient connection reuse
    async with agent:
        result = await agent.run("What is 7 plus 5?")
        print(result.output)
```

### stdio (subprocess)

Use when the MCP server should be launched as a subprocess (local tools, sandboxed execution).

```python
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStdio

server = MCPServerStdio(
    "python",
    args=["mcp_server.py"],
    timeout=10,
)

agent = Agent("openai:gpt-4o", toolsets=[server])

async def main():
    async with agent:      # starts the subprocess
        result = await agent.run("What is the weather in Paris?")
        print(result.output)
```

### SSE (deprecated)

Use only for legacy MCP servers that don't support Streamable HTTP.

```python
from pydantic_ai.mcp import MCPServerSSE

server = MCPServerSSE("http://localhost:3001/sse")
agent = Agent("openai:gpt-4o", toolsets=[server])
```

## Connection Management

```python
# Option A: agent context manager (opens/closes ALL toolset connections)
async with agent:
    result = await agent.run("Task", deps=deps)

# Option B: individual server context manager (share across multiple agents)
async with server:
    result_a = await agent_a.run("Task A")
    result_b = await agent_b.run("Task B")

# Option C: no context manager (connection opened automatically per-call — less efficient)
result = await agent.run("Task")
```

## Combining Local Tools and MCP Servers

```python
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStreamableHTTP

mcp = MCPServerStreamableHTTP("http://localhost:8000/mcp")

@agent.tool_plain
def local_tool() -> str:
    """A local Python tool."""
    return "local result"

agent = Agent(
    "openai:gpt-4o",
    tools=[local_tool],      # local Python tools
    toolsets=[mcp],          # MCP server tools
    instructions="Use available tools to answer questions.",
)
```

## Notable Public MCP Servers

| Server | What it provides |
|---|---|
| `github.com/pydantic/mcp-run-python` | Run Python in a sandbox |
| `github.com/pydantic/logfire-mcp` | Query Logfire traces/metrics |
| `github.com/modelcontextprotocol/servers` | Full list of community servers |

## FastMCP Integration

If the server is built with FastMCP, use `FastMCPToolset` for tighter integration.

```python
from pydantic_ai.toolsets.fastmcp import FastMCPToolset

toolset = FastMCPToolset("http://localhost:8000/mcp")
agent = Agent("openai:gpt-4o", toolsets=[toolset])
```

## Using an Agent as an MCP Server

An agent can itself be exposed as an MCP server for other agents or tools to call.
See: https://ai.pydantic.dev/mcp/server/

## Best Practices

- Always use `async with agent:` (or `async with server:`) to manage connections efficiently.
- Prefer `MCPServerStreamableHTTP` over `MCPServerSSE` (SSE is deprecated).
- Use `MCPServerStdio` for local tools that should run in a sandboxed subprocess.
- Pass `usage=ctx.usage` when calling agents with MCP tools for accurate cost rollup.
