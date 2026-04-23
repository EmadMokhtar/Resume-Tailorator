# Refactor Code Prompt

Use this prompt to improve code quality while maintaining functionality.

## Prompt

```
Refactor [FILE/MODULE/FUNCTION] to improve code quality:

Refactoring Goals:
- [ ] Improve readability
- [ ] Reduce complexity
- [ ] Eliminate duplication (DRY)
- [ ] Apply SOLID principles
- [ ] Improve testability
- [ ] Enhance maintainability
- [ ] Optimize performance (if applicable)

Code Quality Checks:
1. **Single Responsibility Principle**
   - Each function/class has one clear purpose
   - Functions are small and focused (<20 lines)
   - Clear separation of concerns

2. **DRY (Don't Repeat Yourself)**
   - Extract common patterns to functions
   - Use inheritance/composition for shared behavior
   - Centralize configuration

3. **Naming**
   - Variables: snake_case, descriptive
   - Functions: verb_noun pattern
   - Classes: PascalCase, noun pattern
   - Constants: UPPER_SNAKE_CASE
   - Private: _leading_underscore

4. **Type Safety**
   - Add type hints to all signatures
   - Use Pydantic models for complex types
   - Avoid `Any` type (use specific types)
   - Run: uv run mypy

5. **Error Handling**
   - Use specific exception types
   - Handle errors at appropriate level
   - Add context with structlog
   - Don't catch-all exceptions

6. **Documentation**
   - Google-style docstrings for all public functions
   - Inline comments for complex logic only
   - Update module docstrings

Refactoring Patterns:
```python
# Before: Long function with multiple responsibilities
def process_user_data(user_id):
    # Fetch data
    user = db.get_user(user_id)
    # Validate
    if not user.email:
        raise ValueError("No email")
    # Transform
    formatted = user.name.upper()
    # Save
    db.update_user(user_id, formatted)
    # Send email
    send_email(user.email, "Updated")

# After: Split into focused functions
def fetch_user(user_id: str) -> User:
    """Fetch user from database."""
    return db.get_user(user_id)

def validate_user_email(user: User) -> None:
    """Validate user has email."""
    if not user.email:
        raise ValueError(f"User {user.id} has no email")

def format_user_name(name: str) -> str:
    """Format user name to uppercase."""
    return name.upper()

def update_user_name(user_id: str, formatted_name: str) -> None:
    """Update user name in database."""
    db.update_user(user_id, formatted_name)

def notify_user(email: str, message: str) -> None:
    """Send email notification to user."""
    send_email(email, message)

def process_user_data(user_id: str) -> None:
    """Process user data: fetch, validate, format, update, notify."""
    user = fetch_user(user_id)
    validate_user_email(user)
    formatted_name = format_user_name(user.name)
    update_user_name(user_id, formatted_name)
    notify_user(user.email, "Name updated")
```

Testing After Refactoring:
- [ ] All existing tests still pass
- [ ] Coverage maintained or improved
- [ ] Add tests for new extracted functions
- [ ] Run: make tests

Commit Format:
```
refactor([scope]): [brief description]

[What was refactored and why]
[Benefits of the refactoring]

No functional changes.
```

Checklist:
- [ ] Functionality unchanged (tests prove it)
- [ ] Code is more readable
- [ ] Complexity reduced
- [ ] Type hints complete
- [ ] Docstrings updated
- [ ] No performance regression
- [ ] Ruff checks pass
- [ ] Mypy checks pass
```

## Example Usage

```
Refactor src/sidiap_azure_devops_agent/services/workflows_service.py to improve code quality:
[... rest of prompt ...]
```

## Related
- Agent: @lead-software-engineer, @senior-software-engineer-implementation
- Instructions: python.instructions.md
