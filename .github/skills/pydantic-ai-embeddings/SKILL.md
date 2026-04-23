---
name: pydantic-ai-embeddings
description: Guidance for Pydantic AI embeddings, retrieval, and RAG entry patterns. Use it when generating vectors, tuning dimensions, or feeding retrieved context into an agent.
---

# Skill: Pydantic AI Embeddings

> Topic scope: Pydantic AI embeddings, retrieval, and RAG entry patterns
> Primary references: `../pydantic-ai/SKILL.md`, `https://pydantic.dev/docs/ai/guides/embeddings/`

## Overview
Provides a compact reference for generating embeddings with Pydantic AI and using them in retrieval workflows. Focuses on the `Embedder` API, the difference between query and document embeddings, dimension tuning, common provider options, and the standard RAG retrieval pattern.

## Capabilities
- Generate semantic vectors for queries and documents
- Choose embedding models across hosted and local providers
- Tune embedding dimensions when the provider supports it
- Store vectors for similarity search or retrieval
- Feed retrieved context into an agent for RAG

## Key Symbols
| Symbol | Type | Description |
|--------|------|-------------|
| `Embedder` | class | Main entry point for embedding generation |
| `embed_query` | method | Produces a query embedding for search-time input |
| `embed_documents` | method | Produces embeddings for one or more indexable documents |
| `EmbeddingSettings` | class | Common settings, including optional dimension control |
| `GoogleEmbeddingSettings` | class | Google-specific settings such as task type and dimensions |

## Inputs & Outputs
| Symbol | Input | Output |
|--------|-------|--------|
| `Embedder(model)` | Model string or embedding model object | Reusable embedder instance |
| `embed_query(text)` | One search string | Embedding result containing one query vector |
| `embed_documents(texts)` | List of documents or chunks | Embedding result containing one vector per item |
| `EmbeddingSettings(dimensions=...)` | Reduced target dimension count | Smaller vectors when supported by the model |
| `result.embeddings` | Embedding result object | Raw `list[list[float]]` vectors for storage or similarity math |

## Usage Example
```python
from pydantic_ai import Embedder
from pydantic_ai.embeddings import EmbeddingSettings

embedder = Embedder(
    "openai:text-embedding-3-small",
    settings=EmbeddingSettings(dimensions=512),
)


async def retrieve_ready_vectors():
    docs = ["Pydantic AI supports structured outputs.", "Embeddings enable RAG."]
    doc_result = await embedder.embed_documents(docs)
    query_result = await embedder.embed_query("How do I build RAG?")
    return doc_result.embeddings, query_result.embeddings[0]
```

## Internal Dependencies
- `../pydantic-ai/SKILL.md` — core agent concepts used once retrieved context is handed to an agent
- `../pydantic-ai-workflows/SKILL.md` — helpful when embedding retrieval is one step in a larger pipeline

## External Dependencies
- `pydantic-ai` — embedder API and provider integrations
- `numpy` — common for cosine similarity or nearest-neighbor math in simple RAG demos
- `openai` — useful for Azure OpenAI client customization

## Notes
- Use **`embed_query()`** for search text and **`embed_documents()`** for content being indexed; some providers optimize them differently.
- Common provider options include **OpenAI**, **Google Gemini** (direct or Vertex), **Azure OpenAI** via the OpenAI provider, and **Ollama** for local embeddings.
- Dimension tuning can reduce memory and storage costs, but only when the model/provider supports it.
- Keep one vector size per index. Mixing dimensions in the same store breaks similarity search.
- A standard **RAG** flow is: chunk documents → `embed_documents()` once → store vectors → `embed_query()` at runtime → retrieve top matches → pass retrieved text into an agent.
- Embedding results expose vectors plus usage metadata; cost helpers may require optional pricing packages.

## Changelog
| Date | Change |
|------|--------|
| 2026-04-22 | Converted the skill to Agent Skills spec layout with `SKILL.md`, YAML frontmatter, and updated relative links |
| 2026-04-21 | Initial skill created for embedding APIs, providers, dimensions, and RAG patterns |
| 2026-04-21 | Removed dead local instruction reference and normalized in-tree links |
