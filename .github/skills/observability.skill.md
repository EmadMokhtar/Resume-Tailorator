# Skill: Observability

> `src/meetingmind/observability.py`

## Overview
Provides observability configuration for MeetingMind using structured logging with structlog. Configures logging with ISO timestamps, console rendering, and context variable merging. Should be initialized once at application startup to enable structured logging throughout the application lifecycle.

## Capabilities
- Configure structured logging with structlog
- Set up ISO timestamp formatting for log entries
- Enable console rendering for readable log output
- Merge context variables into log records
- Set default log level filtering (INFO level)
- Configure logging processors pipeline

## Key Symbols
| Symbol | Type | Description |
|--------|------|-------------|
| `configure_logging` | function | Configures structlog for the application; call once at startup |

## Inputs & Outputs
| Symbol | Input | Output |
|--------|-------|--------|
| `configure_logging` | None | `None` - side effect: configures global structlog state |

## Usage Example
```python
from meetingmind.observability import configure_logging
import structlog

# Configure logging at application startup (before any logging occurs)
configure_logging()

# Now use structlog throughout your application
logger = structlog.get_logger()
logger.info("application_started", version="1.0.0")
logger.warning("configuration_missing", setting="api_key")
```

## Internal Dependencies
- None (standalone observability module)

## External Dependencies
- `structlog` — Structured logging library for consistent log formatting
- `logging` — Python standard library for log level constants

## Notes
- **Call once at startup:** `configure_logging()` should be called exactly once at application startup, before any logging occurs
- **Global configuration:** This function configures structlog globally; all subsequent calls to `structlog.get_logger()` will use this configuration
- **Console renderer:** Uses `ConsoleRenderer()` for human-readable console output; consider switching to `JSONRenderer()` for production environments
- **Default log level:** Filters logs at INFO level and above; lower-level logs (DEBUG) will be suppressed
- **Context variables:** The `merge_contextvars` processor allows adding contextual information to logs using `structlog.contextvars.bind_contextvars()`
- **Entry point:** Imported and called in `main.py` at CLI startup to ensure logging is configured before any other operations

## Changelog
| Date | Change |
|------|--------|
| 2026-02-23 | Initial skill created |
