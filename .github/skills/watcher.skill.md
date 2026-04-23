# Skill: File Watcher

> `src/meetingmind/watcher.py`

## Overview
Implements a file watcher that monitors a folder for new transcript files and automatically processes them using the AI agent pipeline. Supports continuous watching mode, one-time batch processing, and direct file processing. Handles concurrent processing with configurable limits, file stability checks, graceful shutdown, and comprehensive error handling.

## Capabilities
- Watch a folder continuously for new transcript files
- Process files automatically when detected
- Check file stability before processing (prevent processing incomplete files)
- Process multiple files concurrently with bounded parallelism
- Track processed files using state store to prevent duplicates
- Generate formatted markdown output for each transcript
- Support graceful shutdown on SIGTERM/SIGINT signals
- Process all files once and exit (batch mode)
- Process a single file directly by path
- Create output folders automatically if missing
- Handle errors without stopping the watcher
- Report processing status and errors

## Key Symbols
| Symbol | Type | Description |
|--------|------|-------------|
| `TranscriptWatcher` | class | Main watcher class that monitors and processes transcript files |
| `TranscriptWatcher.__init__` | method | Initialize watcher with configuration and state store |
| `TranscriptWatcher.watch` | method | Start continuous watching for new files |
| `TranscriptWatcher.process_once` | method | Process all eligible files once and exit |
| `TranscriptWatcher.process_single_file` | method | Process a specific file by path |
| `TranscriptWatcher._get_eligible_files` | method | Find files that need processing |
| `TranscriptWatcher._is_file_stable` | method | Check if file is stable (not being written) |
| `TranscriptWatcher._process_file` | method | Process a single transcript file |
| `TranscriptWatcher._process_batch` | method | Process a batch of files with concurrency |
| `TranscriptWatcher._setup_signal_handlers` | method | Setup graceful shutdown handlers |
| `TranscriptWatcher._signal_handler` | method | Handle shutdown signals |

## Inputs & Outputs
| Symbol | Input | Output |
|--------|-------|--------|
| `TranscriptWatcher.__init__` | `config: WatcherConfig` - watcher configuration, `state_store: StateStore` - state persistence | `TranscriptWatcher` instance |
| `TranscriptWatcher.watch` | None | None (runs until stopped) |
| `TranscriptWatcher.process_once` | None | `int` - number of files successfully processed |
| `TranscriptWatcher.process_single_file` | `file_path: Path` - path to transcript file | None (raises exceptions on error) |
| `TranscriptWatcher._get_eligible_files` | None | `list[Path]` - files to process |
| `TranscriptWatcher._is_file_stable` | `file_path: Path` - file to check | `bool` - True if stable |
| `TranscriptWatcher._process_file` | `file_path: Path` - file to process | None (async, raises on error, extracts meeting_datetime from analysis.metadata) |
| `TranscriptWatcher._process_batch` | `files: list[Path]` - batch of files | None (async) |

## Usage Example
```python
import asyncio
from pathlib import Path
from meetingmind.config import WatcherConfig
from meetingmind.state import StateStore
from meetingmind.watcher import TranscriptWatcher

# Create configuration
config = WatcherConfig(
    input_folder=Path("./transcripts"),
    output_folder=Path("./outputs"),
    file_extensions=[".txt", ".md"],
    poll_interval_seconds=5.0,
    max_concurrent_files=3
)

# Create state store
state_store = StateStore(state_file=Path(".meetingmind_state.json"))

# Create watcher
watcher = TranscriptWatcher(config=config, state_store=state_store)

# Continuous watching mode
async def watch_continuously():
    await watcher.watch()

# Batch mode (process once and exit)
async def process_batch():
    count = await watcher.process_once()
    print(f"Processed {count} files")

# Process single file
async def process_one():
    await watcher.process_single_file(Path("transcripts/meeting.txt"))

# Run the watcher
asyncio.run(watch_continuously())
```

## Internal Dependencies
- `agents` — analyze_transcript function for AI-powered transcript analysis
- `structlog` — structured logging throughout the module
- `config` — WatcherConfig for watcher configuration
- `markdown` — generate_markdown and generate_output_filename for output generation
- `state` — StateStore for tracking processed files

## External Dependencies
- `asyncio` — Async/await support, concurrency control with Semaphore
- `signal` — Graceful shutdown handling for SIGTERM/SIGINT
- `pathlib` — Path handling for file operations
- `datetime` — Timestamp generation for output filenames

## Notes
- **File stability:** Waits `stability_check_seconds` and verifies file size hasn't changed before processing to avoid reading incomplete files
- **Concurrency:** Uses asyncio.Semaphore to limit concurrent processing to `max_concurrent_files`
- **Graceful shutdown:** Handles SIGTERM and SIGINT to stop gracefully, allowing current files to finish processing
- **Error handling:** Catches exceptions per file so one failure doesn't stop batch processing
- **State tracking:** Uses StateStore to remember processed files and skip them on subsequent runs
- **Folder creation:** Automatically creates input and output folders if they don't exist
- **Polling interval:** Uses `poll_interval_seconds` to control how often the input folder is checked
- **Async file I/O:** Uses `asyncio.to_thread` to avoid blocking the event loop during file reads/writes
- **Glob patterns:** Supports file extensions with or without leading dot (e.g., ".txt" or "txt")
- **Return values:** `process_once()` returns count of successfully processed files
- **Single file processing:** `process_single_file()` bypasses the state store and processes the file directly
- **Validation:** Single file processing validates file exists and has a supported extension
- **Structured logging:** All print statements replaced with structlog calls for consistent, structured output
- **Meeting datetime extraction:** Extracts `meeting_datetime` from `analysis.metadata` and passes to `generate_output_filename()`

## Changelog
| Date | Change |
|------|--------|
| 2025-01-17 | Integrated structlog for structured logging; _process_file extracts meeting_datetime from analysis.metadata and passes to generate_output_filename |
| 2026-02-22 | Initial skill created |
