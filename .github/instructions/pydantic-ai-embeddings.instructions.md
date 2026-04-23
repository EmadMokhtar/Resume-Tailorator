---
applyTo: "**/*.py"
---

# Pydantic AI - Embeddings and RAG

Reference: https://ai.pydantic.dev/embeddings/

Embeddings are vector representations of text that capture semantic meaning.
Use them for: semantic search, RAG, similarity detection, and document classification.

## Quick Start

```python
from pydantic_ai import Embedder

embedder = Embedder("openai:text-embedding-3-small")

async def main():
    # Single query
    result = await embedder.embed_query("What is machine learning?")
    vector = result.embeddings[0]     # list[float]
    print(f"Dimensions: {len(vector)}")  # 1536

    # Multiple documents at once
    docs = [
        "Machine learning is a subset of AI.",
        "Deep learning uses neural networks.",
        "Python is a programming language.",
    ]
    result = await embedder.embed_documents(docs)
    print(f"Embedded {len(result.embeddings)} documents")
```

> **Queries vs Documents**: use `embed_query()` for search terms and `embed_documents()`
> for content being indexed. Some models optimise differently for each use case.

## Accessing Results

```python
result = await embedder.embed_query("Hello world")

# Three equivalent ways to access a single embedding
vec = result.embeddings[0]     # by index via .embeddings
vec = result[0]                # by index via __getitem__
vec = result["Hello world"]    # by original input text

# Usage metadata
print(result.usage.input_tokens)

# Cost (requires genai-prices package)
cost = result.cost()
print(f"Cost: ${cost.total_price:.6f}")
```

## Providers

### OpenAI
```python
from pydantic_ai import Embedder

embedder = Embedder("openai:text-embedding-3-small")   # 1536 dims
embedder = Embedder("openai:text-embedding-3-large")   # 3072 dims
embedder = Embedder("openai:text-embedding-ada-002")   # legacy
```

### Google (Gemini API)
```python
embedder = Embedder("google-gla:gemini-embedding-001")   # 3072 dims
embedder = Embedder("google-vertex:gemini-embedding-001") # via Vertex AI
```

### Azure OpenAI
```python
from openai import AsyncAzureOpenAI
from pydantic_ai import Embedder
from pydantic_ai.embeddings.openai import OpenAIEmbeddingModel
from pydantic_ai.providers.openai import OpenAIProvider

azure_client = AsyncAzureOpenAI(
    azure_endpoint="https://your-resource.openai.azure.com",
    api_version="2024-02-01",
    api_key="your-azure-key",
)
model = OpenAIEmbeddingModel(
    "text-embedding-3-small",
    provider=OpenAIProvider(openai_client=azure_client),
)
embedder = Embedder(model)
```

### Ollama (local)
```python
embedder = Embedder("ollama:nomic-embed-text")
```

## Dimension Control

Reduce embedding dimensions to save memory and improve speed:

```python
from pydantic_ai import Embedder
from pydantic_ai.embeddings import EmbeddingSettings

embedder = Embedder(
    "openai:text-embedding-3-small",
    settings=EmbeddingSettings(dimensions=256),   # reduced from 1536
)
```

Google-specific settings:
```python
from pydantic_ai.embeddings.google import GoogleEmbeddingSettings

embedder = Embedder(
    "google-gla:gemini-embedding-001",
    settings=GoogleEmbeddingSettings(
        dimensions=768,
        google_task_type="SEMANTIC_SIMILARITY",  # optimise for similarity
    ),
)
```

## RAG Pattern (Retrieval-Augmented Generation)

Combine embeddings with an agent for context-aware answers.

```python
import numpy as np
from pydantic_ai import Agent, Embedder, RunContext
from dataclasses import dataclass

embedder = Embedder("openai:text-embedding-3-small")

# Pre-index your documents
DOCS = [
    "Pydantic AI is a Python agent framework.",
    "Use output_type to get structured responses.",
    "RunContext provides access to deps in tools.",
]

@dataclass
class Deps:
    doc_embeddings: list[list[float]]
    docs: list[str]

agent = Agent("openai:gpt-4o", deps_type=Deps,
              instructions="Answer questions using the retrieved context.")

@agent.tool
async def retrieve_context(ctx: RunContext[Deps], query: str) -> str:
    """Find the most relevant document for the query."""
    query_result = await embedder.embed_query(query)
    query_vec = np.array(query_result[0])
    doc_vecs  = np.array(ctx.deps.doc_embeddings)

    # Cosine similarity
    scores = doc_vecs @ query_vec / (
        np.linalg.norm(doc_vecs, axis=1) * np.linalg.norm(query_vec)
    )
    best_idx = int(np.argmax(scores))
    return ctx.deps.docs[best_idx]

async def main():
    # Build index once
    index_result = await embedder.embed_documents(DOCS)
    deps = Deps(
        doc_embeddings=[index_result[i] for i in range(len(DOCS))],
        docs=DOCS,
    )

    result = await agent.run("How do I get structured output?", deps=deps)
    print(result.output)
```

## When to Use Embeddings

| Use case | Approach |
|---|---|
| Semantic search over documents | `embed_documents()` + cosine similarity |
| RAG (inject context into agent) | Embed query at tool call time, retrieve top-k |
| Deduplication / near-duplicate detection | `embed_documents()` + pairwise similarity threshold |
| Text classification | Embeddings as features for a downstream classifier |

## Available Embedding Models

| Provider | Model | Dimensions |
|---|---|---|
| OpenAI | `text-embedding-3-small` | 1536 |
| OpenAI | `text-embedding-3-large` | 3072 |
| Google | `gemini-embedding-001` | 3072 |
| Ollama | `nomic-embed-text` | 768 |
