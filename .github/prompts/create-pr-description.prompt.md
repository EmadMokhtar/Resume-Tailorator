# Create PR Description Prompt

Use this prompt to generate concise PR descriptions that fit Azure DevOps constraints.

## Prompt

```
Create a PR description for [CHANGES/FEATURE] following these constraints:

**CRITICAL: Maximum 4000 characters (Azure DevOps limit)**

Structure:
```markdown
# [Concise Title - max 100 chars]

## Summary
[2-3 sentences max explaining the change and its impact]

## What's Changed
- [Key change 1]
- [Key change 2]
- [Key change 3]
[Use bullet points, max 10 items]

## Technical Details (if needed)
- [Important decision 1]
- [Breaking change (if any)]
- [Migration note (if any)]

## Testing
- [How validated]
- [Coverage metrics if relevant]

## Related
- [Issue/ticket references]
- [Documentation links]
```

Requirements:
1. **Character Limit:** Stay under 4000 characters (aim for 2000-3000)
2. **Be Concise:** Use bullets, not paragraphs
3. **Focus on Impact:** Explain why and what benefit, not how
4. **Scannable:** Easy to read in 30 seconds
5. **No Code Blocks:** Link to files instead of pasting code
6. **Group Changes:** Combine related items

What to Include:
- ✅ Summary of changes (2-3 sentences)
- ✅ Key changes as bullets
- ✅ Breaking changes (if any)
- ✅ Testing approach
- ✅ Issue references
- ✅ Benefits/impact

What to Avoid:
- ❌ Long prose paragraphs
- ❌ Detailed code examples (link instead)
- ❌ Excessive markdown formatting
- ❌ Copy-pasting entire files
- ❌ Redundant information
- ❌ Going over 4000 characters

Example Format:

```markdown
# Add User Authentication with JWT

## Summary
Implements JWT-based authentication for all API endpoints with token refresh mechanism and rate limiting. Supports both email/password and OAuth2 login flows.

## What's Changed
- JWT token generation and validation middleware
- Login endpoint with rate limiting (5 attempts/15 min)
- Token refresh endpoint with sliding window
- OAuth2 integration (Google, GitHub)
- Authentication required on all protected routes
- User session management with Redis

## Technical Details
- Token expiry: 15 minutes (access), 7 days (refresh)
- Rate limiting uses Redis with sliding window algorithm
- Passwords hashed with bcrypt (cost factor 12)
- OAuth2 state parameter for CSRF protection

## Breaking Changes
- All API endpoints now require `Authorization: Bearer <token>` header
- Previous API key authentication is deprecated (removed in v2.0.0)

## Testing
- Unit tests for token generation/validation (100% coverage)
- Integration tests for login flows
- Rate limiting verified with load tests
- OAuth2 flows tested with mock providers

## Related
- Fixes: #234
- Docs: See docs/authentication.md
- Migration guide: docs/migration/v1-to-v2.md
```

**Character count validation:**
After generating, count characters and ensure < 4000. If over, reduce by:
1. Removing less important bullets
2. Shortening descriptions
3. Linking to docs instead of explaining inline
4. Combining related points
```

## Example Usage

```
@technical-writer Create a PR description for the OpenTelemetry monitoring
feature we just added. Keep it under 4000 characters for Azure DevOps.

Changes:
- Added OpenTelemetry instrumentation
- Integrated Jaeger for tracing
- Added Prometheus metrics
- Health check endpoints
- docker-compose includes observability stack
```

## Character Count Tool

After generating description, validate with:
```bash
# Count characters (including spaces and newlines)
echo "PR_DESCRIPTION_HERE" | wc -m

# Or in Python
len("""PR_DESCRIPTION_HERE""")
```

**Target:** 2000-3000 characters (leaves buffer under 4000 limit)

## Tips for Staying Under 4000 Characters

1. **Use Short Bullet Points** - Not full sentences
2. **Link to Files** - "See docs/api.md" instead of explaining inline
3. **Combine Related Items** - "Updated API endpoints (3 files)" vs listing each
4. **Remove Fluff** - Every word should add value
5. **Use Numbers** - "5 new endpoints" vs listing each one
6. **Reference Commits** - Link to commits instead of explaining changes
7. **Use Abbreviations** - "auth" vs "authentication" (when clear)
8. **Skip Obvious Info** - Don't explain standard practices

## Template (Copy-Paste)

```markdown
# [Feature Name]

## Summary
[2-3 sentences max]

## What's Changed
- [Change 1]
- [Change 2]
- [Change 3]

## Technical Details
- [Detail 1]
- [Breaking change if any]

## Testing
- [How tested]
- [Coverage]

## Related
- Fixes: #123
- Docs: [link]
```

**Estimated length:** ~400-800 characters (safe buffer)

## Related
- Agent: @technical-writer
- Instructions: commit.instructions.md (PR description section)
