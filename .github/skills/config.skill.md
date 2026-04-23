# Skill: Configuration

> `src/meetingmind/config.py`

## Overview
Provides configuration management for MeetingMind using Pydantic Settings. Loads configuration from environment variables and .env files, validates settings, and provides structured access to watcher configuration, model settings, and API credentials. Supports environment variable prefixing with `MEETINGMIND_` for all settings.

## Capabilities
- Load configuration from environment variables and .env files
- Validate configuration with type checking and constraints
- Manage AI model provider settings (OpenAI, Anthropic, test)
- Securely handle API keys using SecretStr
- Configure file watcher behavior (folders, extensions, intervals)
- Provide structured watcher configuration separate from general settings
- Support runtime configuration overrides
- Ensure sensitive data is not accidentally logged or exposed

## Key Symbols
| Symbol | Type | Description |
|--------|------|-------------|
| `ModelProvider` | enum | Enum for supported AI model providers (OPENAI, ANTHROPIC, AZURE, TEST) |
| `WatcherConfig` | class | Structured configuration for the file watcher component |
| `Settings` | class | Main application settings loaded from environment and .env file |
| `load_settings` | function | Factory function to load application settings |
| `settings` | variable | Module-level singleton for convenient access to settings |

## Inputs & Outputs
| Symbol | Input | Output |
|--------|-------|--------|
| `Settings.__init__` | None (loads from environment/env file) | `Settings` instance |
| `Settings.get_api_key` | None | `str \| None` - API key as plain string or None |
| `Settings.get_watcher_config` | None | `WatcherConfig` - structured watcher configuration |
| `WatcherConfig.__init__` | All fields optional with defaults | `WatcherConfig` instance |
| `load_settings` | None | `Settings` instance |

## Usage Example
```python
from meetingmind.config import Settings, load_settings

# Load settings (reads from environment and .env)
settings = load_settings()

# Access configuration
print(f"Input folder: {settings.input_folder}")
print(f"Model provider: {settings.model_provider}")
print(f"Model name: {settings.model_name}")

# Get API key safely (as plain string)
api_key = settings.get_api_key()
if api_key:
    # Use API key
    pass

# Get watcher-specific configuration
watcher_config = settings.get_watcher_config()
print(f"File extensions: {watcher_config.file_extensions}")
print(f"Max concurrent: {watcher_config.max_concurrent_files}")

# Access module-level singleton
from meetingmind.config import settings
print(settings.output_folder)
```

## Internal Dependencies
- None (standalone configuration module)

## External Dependencies
- `pydantic` — BaseModel for structured configuration and validation
- `pydantic-settings` — BaseSettings for environment variable loading
- `pathlib` — Path handling for folder configuration
- `typing` — Type hints including Literal for model_provider field

## Notes
- **Environment prefix:** All environment variables are prefixed with `MEETINGMIND_` (e.g., `MEETINGMIND_INPUT_FOLDER`)
- **Case insensitive:** Environment variable names are case-insensitive
- **.env file:** Automatically loads from `.env` file in the current directory if it exists
- **SecretStr:** API keys are stored as SecretStr to prevent accidental logging; use `get_api_key()` to access the plain value
- **File extensions:** The `file_extensions` setting is a comma-separated string (e.g., ".txt,.md") that gets parsed by `get_watcher_config()`
- **Path types:** Input/output folders and state file use Path objects for cross-platform compatibility
- **Validation:** Pydantic validates types and constraints (e.g., poll_interval_seconds must be >= 1.0)
- **Model providers:** Uses ModelProvider enum (OPENAI, ANTHROPIC, TEST) instead of string literals
- **Extra fields allowed:** SettingsConfigDict includes `extra="allow"` to permit unknown environment variables without raising validation errors
- **Defaults:** All settings have sensible defaults for quick local development
- **Singleton pattern:** The module-level `settings` variable provides convenient access but can cause issues in tests; use `load_settings()` for fresh instances

## Changelog
| Date | Change |
|------|--------|
| 2025-01-17 | Added ModelProvider enum to replace Literal type; added extra="allow" to SettingsConfigDict; changed default filename_template to "{meeting_timestamp}_{source_stem}.md" |
| 2026-02-22 | Initial skill created |
| 2026-02-23 | Added `ModelProvider.AZURE = "azure"` — Azure OpenAI is now a supported provider |
