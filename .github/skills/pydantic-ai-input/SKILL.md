---
name: pydantic-ai-input
description: Guidance for multimodal and binary prompt inputs in Pydantic AI. Use it when prompts need images, documents, audio, video, or raw bytes and provider support matters.
---

# Skill: Pydantic AI Input

> Topic scope: Pydantic AI multimodal and binary prompt inputs
> Primary references: `../pydantic-ai/SKILL.md`, `https://pydantic.dev/docs/ai/advanced-features/input/`

## Overview
Explains how to pass text plus media into Pydantic AI agents. Use it when building prompts that include images, documents, audio, video, or raw bytes, and when checking provider-specific support before relying on a multimodal workflow.

## Capabilities
- Mix text and media objects in a single user prompt
- Send media by URL or raw bytes
- Choose the right wrapper type for each modality
- Force local download when providers cannot fetch URLs directly
- Account for provider and model support differences

## Key Symbols
| Symbol | Type | Description |
|--------|------|-------------|
| `ImageUrl` | class | References an image by URL for multimodal-capable models |
| `DocumentUrl` | class | References a document URL, commonly PDF or text |
| `AudioUrl` | class | References audio content by URL |
| `VideoUrl` | class | References video content by URL |
| `BinaryContent` | class | Sends local bytes plus a required MIME type |

## Inputs & Outputs
| Symbol | Input | Output |
|--------|-------|--------|
| `ImageUrl(url, force_download=...)` | Public or reachable image URL | Prompt part the model can inspect as an image |
| `DocumentUrl(url, force_download=...)` | Document URL, often PDF | Prompt part representing a remote document |
| `AudioUrl(url, force_download=...)` | Audio file URL | Prompt part representing remote audio |
| `VideoUrl(url, force_download=...)` | Video file URL | Prompt part representing remote video |
| `BinaryContent(data, media_type)` | Raw bytes and MIME type such as `image/png` | Prompt part for local or pre-fetched media |

## Usage Example
```python
from pathlib import Path

from pydantic_ai import Agent, BinaryContent, DocumentUrl, ImageUrl

agent = Agent("openai:gpt-4o")

result = agent.run_sync([
    "Compare the screenshot with the attached PDF.",
    ImageUrl(url="https://example.com/screenshot.png"),
    BinaryContent(
        data=Path("requirements.pdf").read_bytes(),
        media_type="application/pdf",
    ),
    DocumentUrl(url="https://example.com/reference.pdf", force_download=True),
])

print(result.output)
```

## Internal Dependencies
- `../pydantic-ai/SKILL.md` — core prompt and agent invocation patterns
- `../pydantic-ai-mcp/SKILL.md` — relevant when multimodal inputs are paired with external MCP tools

## External Dependencies
- `pydantic-ai` — multimodal input types and agent runtime
- `pathlib` — common way to read local files into `BinaryContent`
- `httpx` — useful when pre-downloading assets before wrapping them as bytes

## Notes
- Multimodal prompts are usually passed as a **list** that mixes text strings with media objects.
- Use **`BinaryContent`** for local files or when you need full control over the uploaded bytes.
- The `media_type` must match the actual payload, such as `image/png`, `application/pdf`, `audio/wav`, or `video/mp4`.
- Use **`force_download=True`** when the provider cannot fetch a URL itself or when the asset is only reachable from your app.
- **OpenAI** models commonly support images; document and audio flows may involve download-and-send behavior depending on model support.
- **Anthropic** models are strong for image and document input, but do not assume general audio or video support.
- **Google Gemini** has the broadest multimodal URL support of the common providers, including video-focused flows on supported models.
- Support is **model-specific**, not just provider-specific. Check the exact model docs before standardizing on a modality.

## Changelog
| Date | Change |
|------|--------|
| 2026-04-22 | Converted the skill to Agent Skills spec layout with `SKILL.md`, YAML frontmatter, and updated relative links |
| 2026-04-21 | Initial skill created for multimodal URL and binary input patterns |
| 2026-04-21 | Removed dead local instruction reference and normalized in-tree links |
