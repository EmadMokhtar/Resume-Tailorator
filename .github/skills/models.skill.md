# Skill: Models

> `src/meetingmind/models.py`

## Overview
Defines Pydantic models for structured agent outputs throughout the transcript analysis pipeline. These models enforce type safety, provide validation, and structure the data extracted by AI agents. Each model represents a specific aspect of meeting analysis, from summaries to action points to tone analysis.

## Capabilities
- Define structured output schemas for AI agents
- Validate extracted data against type constraints
- Provide clear field descriptions for AI agents
- Support nested data structures (lists of items)
- Enforce literal types for categorical fields (priority, sentiment)
- Aggregate all analysis results into a single comprehensive model
- Enable serialization to JSON for storage and transmission

## Key Symbols
| Symbol | Type | Description |
|--------|------|-------------|
| `MeetingMetadata` | class | Metadata extracted from transcript with title and meeting datetime |
| `Summary` | class | Meeting summary with content and key topics |
| `ActionPoint` | class | Single action item with owner, deadline, and priority |
| `ActionPoints` | class | Collection of action items |
| `TodoItem` | class | Single todo task with context |
| `TodoList` | class | Collection of todo items |
| `ImportantMention` | class | Important person/entity mention with context and significance |
| `ImportantMentions` | class | Collection of important mentions |
| `Recap` | class | Meeting recap with highlights, decisions, and next steps |
| `MeetingTone` | class | Analysis of meeting sentiment, energy, and collaboration quality |
| `KeyInsights` | class | Strategic insights, patterns, and recommendations |
| `TranscriptAnalysis` | class | Comprehensive analysis aggregating all worker agent outputs |

## Inputs & Outputs
| Symbol | Input | Output |
|--------|-------|--------|
| `MeetingMetadata.__init__` | `title: str` - meeting title (3-6 words), `meeting_datetime: datetime \| None` - meeting date/time | `MeetingMetadata` instance |
| `Summary.__init__` | `content: str` - summary text, `key_topics: list[str]` - main topics | `Summary` instance |
| `ActionPoint.__init__` | `description: str` - task description, `owner: str \| None` - person responsible, `deadline: str \| None` - due date, `priority: Literal` - high/medium/low | `ActionPoint` instance |
| `ActionPoints.__init__` | `items: list[ActionPoint]` - list of action items | `ActionPoints` instance |
| `TodoItem.__init__` | `task: str` - task description, `context: str \| None` - additional context | `TodoItem` instance |
| `TodoList.__init__` | `items: list[TodoItem]` - list of todo items | `TodoList` instance |
| `ImportantMention.__init__` | `person: str` - mentioned person/entity, `context: str` - mention context, `significance: str` - why important | `ImportantMention` instance |
| `ImportantMentions.__init__` | `items: list[ImportantMention]` - list of mentions | `ImportantMentions` instance |
| `Recap.__init__` | `highlights: list[str]` - key highlights, `decisions_made: list[str]` - decisions, `next_steps: list[str]` - next steps | `Recap` instance |
| `MeetingTone.__init__` | `overall_sentiment: Literal` - positive/neutral/negative/mixed, `energy_level: Literal` - high/medium/low, `collaboration_quality: Literal` - excellent/good/fair/poor, `notes: str \| None` - additional observations | `MeetingTone` instance |
| `KeyInsights.__init__` | `insights: list[str]` - important insights, `patterns: list[str]` - observed patterns, `recommendations: list[str]` - recommendations | `KeyInsights` instance |
| `TranscriptAnalysis.__init__` | `source_file: str` - original filename, `processed_at: datetime` - processing timestamp, `metadata: MeetingMetadata \| None` - meeting metadata, plus all worker outputs | `TranscriptAnalysis` instance |

## Usage Example
```python
from datetime import datetime
from meetingmind.models import (
    Summary, ActionPoint, ActionPoints, 
    TranscriptAnalysis
)

# Create individual models
summary = Summary(
    content="Discussed Q4 roadmap and resource allocation",
    key_topics=["Roadmap", "Resources", "Timeline"]
)

action1 = ActionPoint(
    description="Finalize Q4 roadmap",
    owner="John",
    deadline="2026-03-15",
    priority="high"
)

actions = ActionPoints(items=[action1])

# Create comprehensive analysis
analysis = TranscriptAnalysis(
    source_file="meeting_20260222.txt",
    processed_at=datetime.now(),
    summary=summary,
    action_points=actions,
    # ... other required fields
)

# Serialize to dict/JSON
analysis_dict = analysis.model_dump()
print(analysis_dict["summary"]["content"])
```

## Internal Dependencies
- None (standalone module with no internal dependencies)

## External Dependencies
- `pydantic` — Data validation, settings management, and serialization
- `datetime` — Timestamp handling for processed_at field
- `typing` — Type hints including Literal for categorical fields

## Notes
- **Field defaults:** Most list fields default to empty lists using `default_factory=list` to avoid mutable default issues
- **Optional fields:** Fields with `| None` type accept None values; use for optional data like deadline or owner
- **Literal types:** Priority, sentiment, energy_level, and collaboration_quality use Literal types to constrain values to specific options
- **Field descriptions:** All fields include descriptions that guide AI agents in extracting the correct information
- **Validation:** Pydantic automatically validates data types and constraints when creating instances
- **Serialization:** Use `.model_dump()` or `.model_dump_json()` for serialization; use `.model_validate()` for deserialization
- **Immutability:** Models are immutable by default; create new instances rather than modifying existing ones
- **Nested models:** TranscriptAnalysis contains instances of all other models, creating a complete analysis hierarchy

## Changelog
| Date | Change |
|------|--------|
| 2025-01-17 | Added MeetingMetadata model with title and meeting_datetime fields; added TranscriptAnalysis.metadata field for meeting metadata |
| 2026-02-22 | Initial skill created |
