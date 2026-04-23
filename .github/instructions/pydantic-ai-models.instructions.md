---
applyTo: "**/*.py"
---

# Pydantic AI - Model Providers and Configuration

Reference: https://ai.pydantic.dev/models/overview/

## Model String Shorthand

The simplest way to specify a model. Pydantic AI selects the right model class automatically.

```python
from pydantic_ai import Agent

# OpenAI
agent = Agent("openai:gpt-4o")
agent = Agent("openai:gpt-4o-mini")
agent = Agent("openai:gpt-4.1")

# Anthropic
agent = Agent("anthropic:claude-sonnet-4-5")
agent = Agent("anthropic:claude-3-5-haiku-latest")
agent = Agent("anthropic:claude-3-opus-latest")

# Google Gemini (via Generative Language API)
agent = Agent("google-gla:gemini-3-flash-preview")
agent = Agent("google-gla:gemini-3-pro-preview")

# Groq
agent = Agent("groq:llama-3.3-70b-versatile")

# Mistral
agent = Agent("mistral:mistral-large-latest")
```

## Explicit Model Classes (recommended for non-default config)

```python
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.providers.openai import OpenAIProvider

# Custom base URL (Azure AI Foundry, LiteLLM proxy, etc.)
model = OpenAIChatModel(
    "gpt-4o",
    provider=OpenAIProvider(
        base_url="https://my-resource.openai.azure.com/",
        api_key="my-azure-key",
    ),
)
agent = Agent(model)
```

## Ollama (Local Models)

Ollama is OpenAI-compatible; use `OpenAIChatModel` with a custom provider.

```python
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

model = OpenAIChatModel(
    "llama3.2",   # model name as shown in `ollama list`
    provider=OpenAIProvider(base_url="http://localhost:11434/v1"),
)
agent = Agent(model, instructions="You are a local assistant.")
```

## OpenAI-Compatible Providers

Any OpenAI-compatible endpoint works via `OpenAIProvider`:

```python
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
import os

# LiteLLM proxy
model = OpenAIChatModel(
    "gpt-4o",
    provider=OpenAIProvider(
        base_url="http://localhost:4000",
        api_key=os.environ["LITELLM_API_KEY"],
    ),
)
```

Supported via `OpenAIChatModel`: Ollama, LiteLLM, Azure AI Foundry, DeepSeek, Fireworks AI,
GitHub Models, Perplexity, Together AI, Vercel AI Gateway, Nebius, SambaNova, and more.

## Model Settings

Override temperature, max tokens, and other parameters per-agent or per-run.

```python
from pydantic_ai.settings import ModelSettings

# Agent-wide defaults
agent = Agent(
    "openai:gpt-4o",
    model_settings=ModelSettings(temperature=0.2, max_tokens=2048),
)

# Per-run override (takes precedence)
result = await agent.run(
    "Write a creative story.",
    model_settings=ModelSettings(temperature=0.9),
)
```

## Fallback Model

Try models in sequence; switch automatically on 4xx/5xx errors.

```python
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.fallback import FallbackModel

fallback = FallbackModel(
    OpenAIChatModel("gpt-4o"),
    AnthropicModel("claude-sonnet-4-5"),  # used if OpenAI fails
)
agent = Agent(fallback)
```

> **Tip**: Disable provider SDK retries (e.g. `max_retries=0`) so fallback activates immediately
> instead of waiting for the primary provider's retry delay.

## Concurrency Limiting

Wrap any model to limit concurrent HTTP requests (useful for rate limits).

```python
from pydantic_ai import Agent, ConcurrencyLimitedModel

model = ConcurrencyLimitedModel("openai:gpt-4o", limiter=5)
agent = Agent(model)
```

Share a limiter across multiple models:
```python
from pydantic_ai import ConcurrencyLimiter, ConcurrencyLimitedModel

limiter = ConcurrencyLimiter(max_running=10, name="openai-pool")
model1  = ConcurrencyLimitedModel("openai:gpt-4o",      limiter=limiter)
model2  = ConcurrencyLimitedModel("openai:gpt-4o-mini", limiter=limiter)
```

## Test Model (unit tests, no API calls)

```python
from pydantic_ai.models.test import TestModel

def test_agent_logic():
    with agent.override(model=TestModel()):
        result = agent.run_sync("Hello")
        assert result.output is not None
```

## Model Selection Guidelines

| Use Case | Recommended Model |
|---|---|
| Routing / classification | `openai:gpt-4o-mini`, `anthropic:claude-3-5-haiku-latest` |
| Extraction / summarisation | `openai:gpt-4o-mini`, `google-gla:gemini-3-flash-preview` |
| Complex reasoning / orchestration | `openai:gpt-4o`, `anthropic:claude-sonnet-4-5` |
| Long context (>100k tokens) | `google-gla:gemini-3-pro-preview`, `anthropic:claude-sonnet-4-5` |
| Local / private | Ollama (`llama3.2`, `qwen2.5`) via `OpenAIChatModel` |
| Cost-sensitive production | `openai:gpt-4o-mini`, `groq:llama-3.3-70b-versatile` |

## Environment Variables

Pydantic AI reads standard environment variables automatically:

```
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=...
GROQ_API_KEY=gsk_...
MISTRAL_API_KEY=...
```

Load before creating any agent:
```python
from dotenv import load_dotenv
load_dotenv()
```
