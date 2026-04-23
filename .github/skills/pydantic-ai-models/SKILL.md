---
name: pydantic-ai-models
description: Guidance for selecting and configuring Pydantic AI models in this repository, including providers, settings, explicit model classes, and fallbacks.
---

# Pydantic AI Models

> Topic scope: Pydantic AI model selection, provider configuration, and runtime settings
> Primary references: `../pydantic-ai/SKILL.md`, `https://pydantic.dev/docs/ai/models/overview/`

## Overview
Explains how this repo should choose and configure Pydantic AI models. Covers shorthand model strings, explicit model/provider classes when custom endpoints are needed, per-agent and per-run settings, fallback models for resilience, and practical guidance for selecting providers by workload.

## Capabilities
- Pick models with shorthand provider strings
- Configure explicit providers for custom or OpenAI-compatible endpoints
- Apply generation settings at agent or run scope
- Add fallback models for provider outages
- Choose providers based on cost, latency, privacy, and task complexity

## Key Symbols
| Symbol | Type | Description |
|--------|------|-------------|
| `"provider:model"` | shorthand | Fastest way to select a model through Pydantic AI |
| `OpenAIChatModel` | class | Explicit chat model class for OpenAI-compatible endpoints |
| `OpenAIProvider` | class | Provider configuration for API key and base URL overrides |
| `ModelSettings` | class | Temperature, token, and other generation settings |
| `FallbackModel` | class | Sequentially tries multiple models when one fails |
| `ConcurrencyLimitedModel` | class | Wraps a model with shared concurrency limits |

## Inputs & Outputs
| Symbol | Input | Output |
|--------|-------|--------|
| `"provider:model"` | Provider prefix and model name | Resolved model used by `Agent(...)` |
| `OpenAIChatModel(...)` | Model name plus provider config | Explicit model instance for custom endpoints |
| `ModelSettings(...)` | Temperature, max tokens, and related options | Agent defaults or per-run overrides |
| `FallbackModel(...)` | Primary and backup model instances | Resilient model chain |
| `ConcurrencyLimitedModel(...)` | Base model plus limiter | Model wrapper that caps simultaneous requests |

## Usage Example
```python
from pydantic_ai import Agent
from pydantic_ai.models.fallback import FallbackModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.settings import ModelSettings

primary = OpenAIChatModel("gpt-4o-mini")
backup = OpenAIChatModel(
    "llama3.2",
    provider=OpenAIProvider(base_url="http://localhost:11434/v1"),
)

agent = Agent(
    FallbackModel(primary, backup),
    model_settings=ModelSettings(temperature=0.2, max_tokens=800),
)
```

## Internal Dependencies
- `../pydantic-ai/SKILL.md` — entry point and skill routing
- `../pydantic-ai-agents/SKILL.md` — where model choices are applied in agent definitions

## External Dependencies
- `pydantic-ai` — model abstractions, provider classes, settings, fallbacks, and concurrency wrappers
- Provider SDKs / environment variables — credentials and endpoint access for OpenAI, Anthropic, Gemini, Groq, Mistral, and compatible services

## Notes
- **Start simple:** Use model strings such as `openai:gpt-4o-mini` or `anthropic:claude-sonnet-4-5` unless you need a custom base URL or provider object.
- **Use explicit classes when:** You need Azure/OpenAI-compatible gateways, Ollama, LiteLLM, or any non-default endpoint configuration.
- **Settings precedence:** Agent-level `model_settings` establish defaults; per-run settings override them.
- **Fallbacks:** `FallbackModel` is useful for transient 4xx/5xx provider failures. Disable or reduce SDK-level retries if you want fallback to happen quickly.
- **Provider selection:** Prefer smaller/cheaper models for routing, extraction, and summarization; use stronger models for complex reasoning or orchestration; prefer local/OpenAI-compatible endpoints when privacy or offline access matters.
- **Environment:** Load provider API keys before creating agents. Common examples include `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `GROQ_API_KEY`, and `MISTRAL_API_KEY`.

## Changelog
| Date | Change |
|------|--------|
| 2026-04-21 | Initial skill created |
| 2026-04-21 | Removed dead local instruction reference to keep the skill self-contained |
| 2026-04-22 | Converted to Agent Skills spec directory structure with YAML frontmatter |
