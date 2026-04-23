# Skills Documentation System

**Applies to:** `**/*.py`

This instruction file defines the skills documentation system for MeetingMind. Skills are specialized documentation files that describe individual Python modules, their purpose, capabilities, and how to use them.

---

## What is a Skill File?

A **skill file** is a structured markdown document that provides comprehensive documentation for a specific Python module. It serves as:

- **Quick reference** for developers understanding module capabilities
- **Onboarding guide** for new team members
- **Living documentation** that evolves with the codebase
- **AI agent context** for code generation and assistance

### When to Use Skill Files

Create a skill file when:
- ✅ A new Python module is added to the codebase
- ✅ A module has public classes, functions, or constants
- ✅ The module provides reusable functionality
- ✅ The module is part of the core system architecture

Do **not** create skill files for:
- ❌ Test files (`test_*.py`, `*_test.py`)
- ❌ Private/internal modules with no public API
- ❌ Simple script files with no reusable logic
- ❌ Migration or one-off utility scripts

---

## Location & Naming Convention

All skill files are stored in the `.github/skills/` directory at the repository root.

### Naming Pattern

```
.github/skills/<module-name>.skill.md
```

### Examples

| Module Path | Skill File Path |
|-------------|-----------------|
| `src/meetingmind/agents.py` | `.github/skills/agents.skill.md` |
| `src/meetingmind/config.py` | `.github/skills/config.skill.md` |
| `src/meetingmind/markdown.py` | `.github/skills/markdown.skill.md` |

**Rules:**
- Use the module's base name (without `.py` extension)
- Use lowercase, with hyphens for multi-word names if needed
- Always use `.skill.md` suffix
- One skill file per module

---

## Ownership & Responsibilities

### Technical Writer
**Owns the skill documentation system.** Responsible for:

- ✍️ Creating new skill files when modules are added
- 📝 Updating skill files when module APIs change
- 🎨 Maintaining consistent formatting and structure
- ✅ Ensuring accuracy and completeness
- 🔄 Periodic review and maintenance

### Engineers
**Flag changes that require documentation updates.** Responsible for:

- 🚩 Commenting in PRs when public APIs change
- 📢 Notifying Technical Writer of new modules
- 👀 Reviewing skill files for technical accuracy
- 💡 Suggesting improvements and corrections

**Process:**
1. Engineer adds/modifies a Python module
2. Engineer flags the change in PR description or comment
3. Technical Writer reviews the change
4. Technical Writer creates/updates the corresponding skill file
5. Engineer reviews skill file for accuracy

---

## Standard Template

Every skill file **must** follow this exact template structure:

```markdown
# Skill: <Module Name>

> `src/meetingmind/<module>.py`

## Overview
[One paragraph describing the module's purpose and its role in the system. Answer: What does this module do? Why does it exist?]

## Capabilities
- [Key capability 1]
- [Key capability 2]
- [Key capability 3]

## Key Symbols
| Symbol | Type | Description |
|--------|------|-------------|
| `ClassName` | class | Brief description of the class |
| `function_name` | function | Brief description of the function |
| `CONSTANT_NAME` | constant | Brief description of the constant |

## Inputs & Outputs
| Symbol | Input | Output |
|--------|-------|--------|
| `function_name` | `param: Type` - description | `ReturnType` - description |
| `ClassName.__init__` | `config: Config` - configuration object | `ClassName` instance |

## Usage Example
```python
# Minimal working example demonstrating primary use case
from meetingmind.module import ClassName, function_name

# Example usage
result = function_name(input_data)
print(result)
```

## Internal Dependencies
- `module_name` — why this dependency is used (e.g., "models for data structures")
- `another_module` — why this dependency is used

## External Dependencies
- `pydantic` — why this dependency is used (e.g., "data validation and settings")
- `asyncio` — why this dependency is used

## Notes
[Gotchas, important architectural decisions, design rationale, performance considerations, or anything else developers should know]

## Changelog
| Date | Change |
|------|--------|
| YYYY-MM-DD | Initial skill created |
| YYYY-MM-DD | Added XYZ feature documentation |
```

---

## Rules for Creation, Updating, and Maintenance

### Creation Rules

**When creating a new skill file:**

1. **Read the source code first** — understand the module thoroughly
2. **Follow the template exactly** — do not skip sections
3. **Be accurate** — all information must match the actual code
4. **Test examples** — ensure usage examples work
5. **Use consistent terminology** — match variable/function names exactly
6. **Add creation date** — log when the skill was first created
7. **Review for completeness** — ensure all public symbols are documented

**Quality Checklist:**
- [ ] Template structure is followed exactly
- [ ] All public classes, functions, constants are documented
- [ ] Usage example is valid and demonstrates common use case
- [ ] Input/output types match actual function signatures
- [ ] Dependencies are complete and explained
- [ ] Changelog has initial creation date
- [ ] Markdown formatting is correct (no syntax errors)
- [ ] No typos or grammatical errors

### Update Rules

**When to update:**
- ✅ Public API changes (new functions, modified signatures)
- ✅ Module capabilities change or expand
- ✅ Dependencies are added or removed
- ✅ Important notes or gotchas are discovered
- ✅ Usage patterns change

**Update process:**
1. **Review the code changes** — understand what changed
2. **Update affected sections** — modify only what changed
3. **Test examples** — ensure they still work
4. **Add changelog entry** — document what was updated
5. **Verify accuracy** — cross-check with actual code

**Update Checklist:**
- [ ] Updated sections reflect actual code changes
- [ ] Usage example still works (or updated if needed)
- [ ] Changelog entry added with date and description
- [ ] No outdated information remains
- [ ] Cross-referenced with source code for accuracy

### Maintenance Rules

**Periodic review:**
- **Quarterly** — check for outdated information
- **After major releases** — ensure all changes are documented
- **When refactoring occurs** — update affected skills

**Deprecation:**
If a module is deprecated or removed:
1. Add **"DEPRECATED"** to the module name
2. Add deprecation notice in the Overview
3. Add changelog entry with deprecation date
4. Archive the skill file to `.github/skills/archived/`

---

## Related Documentation

- Contributing Guide — How to contribute to MeetingMind (see repository root if available)
- [Technical Reference](../../docs/technical-reference.md) — System components and design details

---

*These instructions ensure consistent, maintainable skill documentation across the MeetingMind project.*
