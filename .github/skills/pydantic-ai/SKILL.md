---
name: pydantic-ai
description: Entry-point skill for Pydantic AI in this repository. Use it to find the right companion skill for agents, tools, models, workflows, testing, MCP, multimodal input, and embeddings.
---

# Pydantic AI

> Topic scope: Pydantic AI authoring overview for this repository
> Primary references: companion skills in `.github/skills/`, `https://pydantic.dev/docs/ai/overview/`

## Overview
Entry point for using Pydantic AI in this repository. Use this skill to identify the right companion skill for agent design, tools, models, workflows, testing, MCP integration, multimodal input, or embeddings, then jump there for implementation details.

## Capabilities
- Define the scope of the repo's Pydantic AI guidance
- Route readers to the right companion skill quickly
- Summarize what belongs in skills vs deeper upstream or repo documentation
- Call out important exclusions to keep topic docs focused

## Key Symbols
| Symbol | Type | Description |
|--------|------|-------------|
| `Agent` | class | Core stateless interface for prompting models and returning typed results |
| `RunContext` | class | Per-run context passed into tools, instructions, and validators |
| `pydantic-ai-agents` | skill | Use for agent construction, runs, history, streaming, and outputs |
| `pydantic-ai-tools` | skill | Use for tool decorators, schemas, retries, validators, and toolsets |
| `pydantic-ai-models` | skill | Use for model strings, providers, settings, and fallbacks |
| `pydantic-ai-workflows` | skill | Use for delegation, handoff, shared usage, and multi-agent boundaries |
| `pydantic-ai-testing` | skill | Use for deterministic tests, overrides, and run inspection |
| `pydantic-ai-mcp` | skill | Use for MCP servers, transports, and external toolset integration |
| `pydantic-ai-input` | skill | Use for multimodal prompts, URLs, binary media, and provider support |
| `pydantic-ai-embeddings` | skill | Use for embeddings, retrieval, and RAG entry patterns |

## Inputs & Outputs
| Symbol | Input | Output |
|--------|-------|--------|
| `pydantic-ai` | "Where should I start?" or mixed Pydantic AI questions | Scope, exclusions, and the right companion skill |
| `pydantic-ai-agents` | Questions about `Agent`, `deps_type`, instructions, runs, history, or streaming | Practical agent patterns |
| `pydantic-ai-tools` | Questions about tools, validators, `ModelRetry`, or external tool providers | Tooling and validation patterns |
| `pydantic-ai-models` | Questions about providers, model IDs, settings, or fallback strategy | Model selection and configuration guidance |
| `pydantic-ai-workflows` | Questions about delegation, handoff, usage rollup, or multi-agent boundaries | Workflow selection and coordination patterns |
| `pydantic-ai-testing` | Questions about test doubles, overrides, or captured run messages | Testing guidance for agent code |
| `pydantic-ai-mcp` | Questions about MCP servers, transports, or external toolsets | MCP integration guidance |
| `pydantic-ai-input` | Questions about images, documents, audio, video, or raw bytes in prompts | Multimodal input guidance |
| `pydantic-ai-embeddings` | Questions about vectors, retrieval, or RAG setup | Embeddings and retrieval guidance |

## Usage Example
```python
from pydantic_ai import Agent

agent = Agent(
    "openai:gpt-4o-mini",
    instructions="Answer briefly and use tools when needed.",
)

result = agent.run_sync("Summarize why Pydantic AI is useful.")
print(result.output)
```

## Internal Dependencies
- `../pydantic-ai-agents/SKILL.md` — detailed agent lifecycle guidance
- `../pydantic-ai-tools/SKILL.md` — tool, validator, and toolset guidance
- `../pydantic-ai-models/SKILL.md` — model/provider selection guidance
- `../pydantic-ai-workflows/SKILL.md` — delegation and orchestration guidance
- `../pydantic-ai-testing/SKILL.md` — testing patterns and model doubles
- `../pydantic-ai-mcp/SKILL.md` — MCP toolset integration guidance
- `../pydantic-ai-input/SKILL.md` — multimodal prompt input guidance
- `../pydantic-ai-embeddings/SKILL.md` — embeddings and retrieval guidance

## External Dependencies
- `pydantic-ai` — agent framework, tool calling, streaming, and model abstraction
- `pydantic` — typed outputs, validation, and schema generation

## Notes
- **Scope:** Covers Pydantic AI concepts used by this repo, not every API surface in the upstream docs.
- **Exclusions:** Deep multi-agent workflow design, graphs, and app-specific orchestration belong in the workflow companion skill or broader repo docs rather than these foundation skills.
- **Use a skill when:** You want a short, navigable reference or a reminder of the recommended pattern.
- **Self-contained pack:** This skill pack does not depend on topic-specific local instruction files; use the companion skills and upstream docs together when you need more depth.
- **Companion links:** [Agents](../pydantic-ai-agents/SKILL.md), [Tools](../pydantic-ai-tools/SKILL.md), [Models](../pydantic-ai-models/SKILL.md), [Workflows](../pydantic-ai-workflows/SKILL.md), [Testing](../pydantic-ai-testing/SKILL.md), [MCP](../pydantic-ai-mcp/SKILL.md), [Input](../pydantic-ai-input/SKILL.md), [Embeddings](../pydantic-ai-embeddings/SKILL.md).
- **Companion skill guide:** Start with agents for most implementation work, tools when the model must call code, models when provider/config choices affect behavior, workflows for coordination, testing for validation, MCP for external tool servers, input for multimodal prompts, and embeddings for retrieval.

## Changelog
| Date | Change |
|------|--------|
| 2026-04-21 | Initial skill created |
| 2026-04-21 | Added full companion-skill routing and removed dead local instruction references |
| 2026-04-22 | Converted to Agent Skills spec directory structure with YAML frontmatter |
