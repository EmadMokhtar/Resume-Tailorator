---
applyTo: "**/*.py"
---

# Pydantic AI - Multimodal Input

Reference: https://ai.pydantic.dev/input/

Some models support image, audio, video, and document inputs in addition to text.
Pass a **list** mixing text and media objects as the user prompt.

## Image Input

```python
from pydantic_ai import Agent, ImageUrl, BinaryContent
import httpx

agent = Agent(model="openai:gpt-4o")

# From a URL (model downloads it)
result = agent.run_sync([
    "What company is this logo from?",
    ImageUrl(url="https://example.com/logo.png"),
])
print(result.output)

# From local bytes
image_bytes = httpx.get("https://example.com/logo.png").content
result = agent.run_sync([
    "Describe this image.",
    BinaryContent(data=image_bytes, media_type="image/png"),
])

# From a local file
from pathlib import Path
result = agent.run_sync([
    "Describe this image.",
    BinaryContent(data=Path("screenshot.png").read_bytes(), media_type="image/png"),
])
```

## Document Input (PDF, Text)

```python
from pydantic_ai import Agent, DocumentUrl, BinaryContent
from pathlib import Path

agent = Agent(model="anthropic:claude-sonnet-4-5")

# From URL
result = agent.run_sync([
    "Summarise the main findings in this paper.",
    DocumentUrl(url="https://arxiv.org/pdf/2303.08774"),
])

# From local PDF bytes
result = agent.run_sync([
    "Extract all action items from this document.",
    BinaryContent(
        data=Path("meeting_notes.pdf").read_bytes(),
        media_type="application/pdf",
    ),
])
```

## Audio Input

```python
from pydantic_ai import Agent, AudioUrl, BinaryContent

agent = Agent(model="openai:gpt-4o-audio-preview")

# From URL
result = agent.run_sync([
    "Transcribe this audio clip.",
    AudioUrl(url="https://example.com/recording.mp3"),
])

# From local bytes
result = agent.run_sync([
    "What language is spoken in this audio?",
    BinaryContent(data=Path("clip.wav").read_bytes(), media_type="audio/wav"),
])
```

## Video Input

```python
from pydantic_ai import Agent, VideoUrl

agent = Agent(model="google-gla:gemini-3-pro-preview")

result = agent.run_sync([
    "Describe what happens in this video.",
    VideoUrl(url="https://example.com/demo.mp4"),
])
```

## Force Local Download

If the model cannot access a URL directly, force Pydantic AI to download it first:

```python
from pydantic_ai import ImageUrl, DocumentUrl

result = agent.run_sync([
    "Analyse this image.",
    ImageUrl(url="https://private.internal/image.png", force_download=True),
])
```

## Combining Multiple Media in One Prompt

```python
result = agent.run_sync([
    "Compare the content of these two documents and summarise differences:",
    DocumentUrl(url="https://example.com/v1.pdf"),
    DocumentUrl(url="https://example.com/v2.pdf"),
])
```

## Provider Support Matrix

| Media Type | OpenAI (`gpt-4o`) | Anthropic (`claude-*`) | Google (`gemini-*`) |
|---|---|---|---|
| `ImageUrl` | Direct URL | Direct URL | All URL types |
| `ImageUrl` bytes | `BinaryContent` | `BinaryContent` | `BinaryContent` |
| `DocumentUrl` (PDF) | Download + send | Direct URL | All URL types |
| `AudioUrl` | Download + send | Not supported | All URL types |
| `VideoUrl` | Not supported | Not supported | All URL types |

> Check model documentation before using multimodal inputs — not all models support all types.

## Media Types Reference

| Class | Use for | `media_type` values |
|---|---|---|
| `ImageUrl` / `BinaryContent` | Images | `image/png`, `image/jpeg`, `image/gif`, `image/webp` |
| `DocumentUrl` / `BinaryContent` | Documents | `application/pdf`, `text/plain` |
| `AudioUrl` / `BinaryContent` | Audio | `audio/wav`, `audio/mp3`, `audio/mpeg` |
| `VideoUrl` / `BinaryContent` | Video | `video/mp4`, `video/mpeg` |
