# Skill: Agents

> `src/meetingmind/agents.py`

## Overview
Implements a manager-worker orchestration system using Pydantic AI agents for transcript analysis. The manager agent coordinates eight specialized worker agents, each extracting specific insights (summary, action points, todos, mentions, recap, tone, key insights, and meeting metadata) from meeting transcripts. Uses lazy initialization to defer API key requirements until runtime.

## Capabilities
- Analyze meeting transcripts using AI-powered agents
- Extract summaries and key topics from discussions
- Identify action points with owners, deadlines, and priorities
- Generate todo lists with contextual information
- Detect important mentions of people, products, or clients
- Create meeting recaps with highlights and decisions
- Analyze meeting tone, sentiment, and collaboration quality
- Extract strategic insights and provide recommendations
- Orchestrate multiple worker agents through a manager agent
- Support multiple AI providers (OpenAI, Anthropic, test)

## Key Symbols
| Symbol | Type | Description |
|--------|------|-------------|
| `_LazyAgent` | class | Proxy that lazily initializes Pydantic AI agents on first access |
| `_OverrideContext` | class | Context manager for temporarily overriding agent configuration |
| `ManagerContext` | class | Context object for manager agent containing transcript and source file |
| `summary_agent` | _LazyAgent | Worker agent specialized in summarizing meeting transcripts |
| `action_points_agent` | _LazyAgent | Worker agent specialized in extracting action items |
| `todo_list_agent` | _LazyAgent | Worker agent specialized in extracting todo items |
| `important_mentions_agent` | _LazyAgent | Worker agent specialized in identifying important mentions |
| `recap_agent` | _LazyAgent | Worker agent specialized in creating meeting recaps |
| `meeting_tone_agent` | _LazyAgent | Worker agent specialized in analyzing meeting tone |
| `key_insights_agent` | _LazyAgent | Worker agent specialized in extracting strategic insights |
| `meeting_metadata_agent` | _LazyAgent | Worker agent specialized in extracting meeting metadata (title and datetime) |
| `manager_agent` | _LazyAgent | Manager agent that orchestrates all worker agents |
| `analyze_transcript` | function | Main entry point to analyze a transcript using manager-worker orchestration |
| `_get_model_string` | function | Gets the AI model string from settings and sets API keys |
| `_register_manager_tools` | function | Registers worker agent tools on the manager agent |
| `get_meeting_metadata` | tool | Tool registered on manager agent to extract meeting metadata from transcripts |

## Inputs & Outputs
| Symbol | Input | Output |
|--------|-------|--------|
| `analyze_transcript` | `transcript: str` - meeting transcript text, `source_file: str` - original filename | `TranscriptAnalysis` - comprehensive analysis from all workers |
| `_get_model_string` | None | `str` - formatted model string like "openai:gpt-4" |
| `_LazyAgent.__init__` | `model_factory: callable` - function returning model string, `result_type: BaseModel` - output type, `system_prompt: str` - agent prompt, `register_tools_callback: callable` - tool registration function | `_LazyAgent` instance |
| `_LazyAgent.override` | `model: Any` - override model, `**kwargs` - additional overrides | Context manager or override context |
| `ManagerContext.__init__` | `transcript: str` - transcript text, `source_file: str` - source filename | `ManagerContext` instance |

## Usage Example
```python
import asyncio
from meetingmind.agents import analyze_transcript

# Analyze a meeting transcript
transcript = """
Meeting: Q4 Planning
John: We need to finalize the roadmap by Friday.
Sarah: I'll prepare the design docs by Wednesday.
"""

async def main():
    # Analyze transcript (uses configured AI provider)
    analysis = await analyze_transcript(
        transcript=transcript,
        source_file="q4_planning.txt"
    )
    
    # Access different parts of the analysis
    print(f"Summary: {analysis.summary.content}")
    print(f"Action points: {len(analysis.action_points.items)}")
    print(f"Meeting tone: {analysis.meeting_tone.overall_sentiment}")

asyncio.run(main())
```

## Internal Dependencies
- `models` — Pydantic models for structured outputs (Summary, ActionPoints, TranscriptAnalysis, etc.)
- `config` — Settings for model provider, model name, and API key management

## External Dependencies
- `pydantic-ai` — Agent framework for building AI agents with structured outputs
- `pydantic` — Data validation and settings management
- `datetime` — Timestamp generation for processed_at field
- `os` — Environment variable management for API keys

## Notes
- **Lazy initialization:** Agents are not initialized until first use, deferring API key validation until runtime
- **Provider support:** Automatically sets appropriate environment variables (OPENAI_API_KEY or ANTHROPIC_API_KEY) based on configured provider
- **Override mechanism:** The `override()` method allows testing with mock models without initializing real agents
- **Parallel execution:** Manager agent can call worker tools in parallel for faster processing
- **Tool registration:** Worker agent tools are registered on the manager agent lazily to avoid circular dependencies
- **Error handling:** If a worker agent fails, the error propagates up to the caller; no automatic retry logic
- **Model string format:** Uses "provider:model_name" format (e.g., "openai:gpt-4", "anthropic:claude-3-opus")

## Changelog
| Date | Change |
|------|--------|
| 2025-01-17 | Added meeting_metadata_agent and get_meeting_metadata tool for extracting meeting title and datetime; manager now orchestrates 8 worker agents; TranscriptAnalysis includes metadata field |
| 2026-02-22 | Initial skill created |
