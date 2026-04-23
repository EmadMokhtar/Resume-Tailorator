# Skill: State Management

> `src/meetingmind/state.py`

## Overview
Provides persistent JSON-based state tracking for processed transcript files. Maintains a record of which files have been processed, when they were processed, and where the output was written. Prevents duplicate processing across application restarts and supports querying processing history. Uses atomic file writes to ensure data integrity.

## Capabilities
- Persist processing state to disk as JSON
- Track processed files with timestamps and output paths
- Check if a file has already been processed
- Mark files as processed after successful analysis
- Query all processed files
- Retrieve individual processing records
- Clear all state (useful for testing)
- Atomic writes to prevent corruption during crashes
- Graceful handling of corrupted state files

## Key Symbols
| Symbol | Type | Description |
|--------|------|-------------|
| `ProcessedFileRecord` | class | Record of a single processed file with metadata |
| `ProcessedFilesState` | class | Container for all processed file records |
| `StateStore` | class | Persistent store for managing processed files state |
| `StateStore.load` | method | Load state from disk (or initialize if missing) |
| `StateStore.save` | method | Save state to disk atomically |
| `StateStore.is_processed` | method | Check if a file has been processed |
| `StateStore.mark_processed` | method | Mark a file as processed and save |
| `StateStore.get_record` | method | Get the record for a specific file |
| `StateStore.get_all_processed` | method | Get all processed file records |
| `StateStore.clear` | method | Clear all state |

## Inputs & Outputs
| Symbol | Input | Output |
|--------|-------|--------|
| `StateStore.__init__` | `state_file: Path` - path to state JSON file | `StateStore` instance |
| `StateStore.load` | None | `ProcessedFilesState` - loaded or fresh state |
| `StateStore.save` | None | None (writes to disk) |
| `StateStore.is_processed` | `file_path: Path` - file to check | `bool` - True if processed |
| `StateStore.mark_processed` | `file_path: Path` - file to mark, `output_path: Path \| None` - optional output path | `ProcessedFileRecord` - created record |
| `StateStore.get_record` | `file_path: Path` - file to query | `ProcessedFileRecord \| None` - record or None |
| `StateStore.get_all_processed` | None | `list[ProcessedFileRecord]` - all records |
| `StateStore.clear` | None | None (clears state and deletes file) |
| `ProcessedFileRecord.__init__` | `path: str` - file path, `processed_at: datetime` - timestamp, `output_path: str \| None` - output path | `ProcessedFileRecord` instance |
| `ProcessedFilesState.__init__` | `version: int` - format version, `files: dict` - file records | `ProcessedFilesState` instance |

## Usage Example
```python
from pathlib import Path
from meetingmind.state import StateStore

# Initialize state store
state_store = StateStore(state_file=Path(".meetingmind_state.json"))

# Check if a file has been processed
transcript_file = Path("transcripts/meeting_20260222.txt")
if state_store.is_processed(transcript_file):
    print("Already processed, skipping...")
else:
    # Process the file...
    output_file = Path("outputs/meeting_20260222_analysis.md")
    
    # Mark as processed
    record = state_store.mark_processed(
        file_path=transcript_file,
        output_path=output_file
    )
    print(f"Processed at: {record.processed_at}")

# Query processing history
all_records = state_store.get_all_processed()
print(f"Total processed: {len(all_records)}")

# Get specific record
record = state_store.get_record(transcript_file)
if record:
    print(f"Output: {record.output_path}")
```

## Internal Dependencies
- `structlog` — structured logging throughout the module

## External Dependencies
- `pydantic` — Data validation and serialization for state models
- `json` — JSON serialization for persistent storage
- `pathlib` — Path handling for file operations
- `datetime` — Timestamp management for processed_at field

## Notes
- **Atomic writes:** Uses temp file + rename pattern to ensure state file is never corrupted during writes
- **Absolute paths:** All file paths are stored as absolute paths (using `Path.resolve()`) to avoid issues with relative paths
- **Lazy loading:** State is only loaded from disk on first access to minimize I/O
- **Corruption handling:** If the state file is corrupted, starts with fresh state and logs a warning
- **Version field:** State includes a version field for future migration support
- **Parent directory creation:** Automatically creates parent directories when saving if they don't exist
- **Cache behavior:** State is cached in memory after first load; call `load()` doesn't re-read from disk
- **Concurrency:** Not thread-safe or process-safe; designed for single-process usage
- **Testing:** Use `clear()` method to reset state between tests
- **Structured logging:** All print/warning statements replaced with structlog calls
- **UTC timestamps:** `mark_processed()` uses `datetime.now(timezone.utc)` instead of `datetime.now()` for consistency

## Changelog
| Date | Change |
|------|--------|
| 2025-01-17 | Integrated structlog for structured logging; mark_processed now uses datetime.now(timezone.utc) for UTC timestamps |
| 2026-02-22 | Initial skill created |
