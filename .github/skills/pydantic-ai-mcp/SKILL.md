---
name: pydantic-ai-mcp
description: Guidance for integrating Pydantic AI with MCP servers and toolsets. Use it when choosing transports, attaching remote or local MCP tools, and managing connections efficiently.
---

# Skill: Pydantic AI MCP

> Topic scope: Pydantic AI Model Context Protocol toolset integration
> Primary references: `../pydantic-ai-tools/SKILL.md`, `https://pydantic.dev/docs/ai/mcp/overview/`

## Overview
Captures how Pydantic AI consumes MCP servers as toolsets. Use this skill when wiring agents to remote or local MCP tools, choosing between Streamable HTTP and stdio transports, and managing connections efficiently across one or more agents.

## Capabilities
- Attach MCP servers to agents through `toolsets`
- Choose the right transport for remote vs local tool servers
- Reuse MCP connections with agent or server context managers
- Mix MCP-backed tools with local Python tools
- Recognize when FastMCP-specific integration is a better fit

## Key Symbols
| Symbol | Type | Description |
|--------|------|-------------|
| `toolsets=` | agent argument | Registers external tool providers, including MCP servers |
| `MCPServerStreamableHTTP` | class | Preferred client for remote MCP servers over Streamable HTTP |
| `MCPServerStdio` | class | Starts a local MCP server as a subprocess over stdio |
| `FastMCPToolset` | class | Tighter client integration for FastMCP-based servers |
| `Agent.__aenter__` | method | Opens and reuses toolset connections for the agent scope |

## Inputs & Outputs
| Symbol | Input | Output |
|--------|-------|--------|
| `MCPServerStreamableHTTP(url)` | MCP endpoint URL | Toolset exposing server tools to the agent |
| `MCPServerStdio(command, args=...)` | Executable command and subprocess args | Toolset that launches and talks to a local MCP server |
| `Agent(toolsets=[...])` | One or more MCP servers or toolsets | Agent with external MCP tools available to the model |
| `async with agent:` | Agent configured with MCP toolsets | Open connections reused for all runs in the block |
| `async with server:` | Individual MCP server instance | Shared live connection across multiple agents |

## Usage Example
```python
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStreamableHTTP

docs_server = MCPServerStreamableHTTP("http://localhost:8000/mcp")
agent = Agent("openai:gpt-4o", toolsets=[docs_server])


async def ask_docs(question: str) -> str:
    async with agent:
        result = await agent.run(question)
        return result.output
```

## Internal Dependencies
- `../pydantic-ai/SKILL.md` — general agent configuration patterns that MCP extends
- `../pydantic-ai-workflows/SKILL.md` — orchestration guidance for agents that delegate through MCP tools

## External Dependencies
- `pydantic-ai` — agent runtime and MCP client support
- `pydantic-ai-slim[mcp]` — optional install extras for MCP transports
- `FastMCP` — relevant when the upstream server is implemented with FastMCP

## Notes
- Pass MCP servers through **`toolsets=[...]`**, not `tools=[...]`; MCP servers are tool providers, not plain Python functions.
- Prefer **`MCPServerStreamableHTTP`** for remote servers. It is the current recommended transport.
- Use **`MCPServerStdio`** when the server should run locally as a subprocess, such as sandboxed or workstation-only tools.
- Wrap calls in **`async with agent:`** for efficient connection reuse. If several agents share one server, use **`async with server:`** instead.
- Letting connections open per call works, but it is less efficient and adds avoidable setup overhead.
- You can mix MCP toolsets with local Python tools on the same agent.
- If the server is built with **FastMCP**, prefer **`FastMCPToolset`** for the most direct integration path.
- Older SSE transport exists for legacy setups, but new work should favor Streamable HTTP.

## Changelog
| Date | Change |
|------|--------|
| 2026-04-22 | Converted the skill to Agent Skills spec layout with `SKILL.md`, YAML frontmatter, and updated relative links |
| 2026-04-21 | Initial skill created for MCP toolsets, transports, and connection management |
| 2026-04-21 | Removed dead local instruction reference and normalized in-tree links |
