# Skill: CLI Entry Point

> `src/meetingmind/main.py`

## Overview
Provides the command-line interface (CLI) for MeetingMind using Click. Offers four commands: watch (continuous monitoring), process (batch processing), status (view history), and reset (clear state). Each command supports configuration overrides via CLI options, integrating all components (watcher, state, config) into a cohesive user experience.

## Capabilities
- Provide a user-friendly CLI with multiple commands
- Watch folders continuously for new transcript files
- Process all unprocessed files once and exit
- Display processing status and history
- Reset processing state for fresh starts
- Override configuration with command-line options
- Show version information
- Handle keyboard interrupts gracefully
- Exit with appropriate status codes

## Key Symbols
| Symbol | Type | Description |
|--------|------|-------------|
| `cli` | function | Main CLI group (entry point for all commands) |
| `_configure_logging` | function | Configure structlog with ISO timestamps and console renderer |
| `watch` | function | Watch command for continuous monitoring |
| `process` | function | Process command for one-time batch processing |
| `status` | function | Status command to view processing history |
| `reset` | function | Reset command to clear all processing state |

## Inputs & Outputs
| Symbol | Input | Output |
|--------|-------|--------|
| `cli` | None | None (entry point group) |
| `watch` | `--input-folder: Path`, `--output-folder: Path`, `--poll-interval: float`, `--max-concurrent: int` | None (runs until stopped) |
| `process` | `--input-folder: Path`, `--output-folder: Path`, `--max-concurrent: int` | None (prints count) |
| `status` | None | None (prints status) |
| `reset` | None (requires confirmation) | None (prints confirmation) |

## Usage Example
```bash
# Watch for new transcript files continuously
meetingmind watch

# Watch with custom folders
meetingmind watch --input-folder ./my-transcripts --output-folder ./my-outputs

# Process all unprocessed files once
meetingmind process

# Check processing status and history
meetingmind status

# Reset processing state (requires confirmation)
meetingmind reset

# Show version
meetingmind --version

# Get help
meetingmind --help
meetingmind watch --help
```

## Internal Dependencies
- `config` — load_settings for configuration management
- `structlog` — structured logging throughout the module
- `state` — StateStore for processing history and state management
- `watcher` — TranscriptWatcher for file monitoring and processing

## External Dependencies
- `click` — CLI framework for building command-line interfaces
- `asyncio` — Async/await support for running async watcher methods
- `sys` — Exit code management
- `pathlib` — Path handling for folder options

## Notes
- **Command structure:** Uses Click's group/command pattern with `@cli.command()` decorators
- **Option precedence:** CLI options override environment variables and .env file settings
- **Asyncio integration:** Uses `asyncio.run()` to execute async watcher methods from sync CLI commands
- **Graceful interruption:** Catches KeyboardInterrupt and exits cleanly with appropriate message
- **Exit codes:** Uses exit code 0 for success, 1 for errors
- **Confirmation prompts:** Reset command requires user confirmation before clearing state
- **Status display:** Shows up to 10 most recent processed files with timestamps and output paths
- **Path types:** Uses `click.Path(path_type=Path)` for type-safe path handling
- **Help text:** All commands and options include help text accessible via `--help`
- **Version option:** `@click.version_option()` adds automatic version display
- **Settings isolation:** Each command loads settings independently for clean separation
- **Error handling:** Errors during processing are reported but don't crash the CLI
- **Structured logging:** All print statements replaced with structlog calls for consistent output
- **Logging configuration:** `_configure_logging()` sets up structlog with ISO timestamps and console renderer, called at CLI startup

## Changelog
| Date | Change |
|------|--------|
| 2025-01-17 | Added _configure_logging function for structlog setup; integrated structlog throughout for structured logging |
| 2026-02-22 | Initial skill created |
