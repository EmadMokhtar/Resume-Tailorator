# Reusable Prompt Library

This directory contains reusable prompts for common development tasks. These prompts are designed to work with GitHub Copilot and are based on the project's instruction files and custom agents.

## Available Prompts

### Development Prompts

| Prompt | Purpose | Related Agent | Use When |
|--------|---------|---------------|----------|
| **feature-implementation.prompt.md** | Implement new features following project standards | @senior-software-engineer-implementation | Starting a new feature |
| **fix-bug.prompt.md** | Debug and fix issues systematically | @senior-software-engineer-implementation | Troubleshooting bugs |
| **refactor-code.prompt.md** | Improve code quality while maintaining functionality | @lead-software-engineer | Cleaning up technical debt |
| **create-api-endpoint.prompt.md** | Create WebAPI endpoints with full stack | @senior-software-engineer-implementation | Adding new API routes |

### Quality Assurance Prompts

| Prompt | Purpose | Related Agent | Use When |
|--------|---------|---------------|----------|
| **code-review.prompt.md** | Perform comprehensive code reviews | @senior-software-engineer-reviewer | Reviewing pull requests |
| **write-tests.prompt.md** | Generate comprehensive test suites | @senior-qa-engineer | Writing tests for code |
| **security-audit.prompt.md** | Security review and vulnerability assessment | @senior-security-engineer | Security hardening |

### DevOps & Documentation Prompts

| Prompt | Purpose | Related Agent | Use When |
|--------|---------|---------------|----------|
| **docker-setup.prompt.md** | Create/modify Docker configurations | @senior-devops-engineer | Setting up containers |
| **add-monitoring.prompt.md** | Add observability and monitoring | @senior-devops-engineer | Adding tracing/metrics |
| **write-documentation.prompt.md** | Create comprehensive documentation | @technical-writer | Documenting features |
| **create-pr-description.prompt.md** | Generate concise PR descriptions (≤4000 chars) | @technical-writer | Creating pull requests |

## How to Use Prompts

### Method 1: Copy and Customize
1. Open the relevant `.prompt.md` file
2. Copy the content in the "Prompt" section
3. Replace placeholders (e.g., `[FEATURE_NAME]`, `[FILE/MODULE]`) with your specifics
4. Paste into GitHub Copilot Chat

### Method 2: Reference in Chat
```
@workspace Use the feature-implementation.prompt.md to implement user authentication
```

### Method 3: Use with Custom Agents
```
@senior-software-engineer-implementation Use feature-implementation.prompt.md to implement workflow submission endpoint
```

## Prompt Structure

Each prompt file follows this structure:

```markdown
# [Prompt Name]

Use this prompt when [scenario description].

## Prompt

```
[The actual prompt content with instructions and templates]
```

## Example Usage

```
[Concrete example of using the prompt]
```

## Related
- Agent: [Which custom agent to use]
- Instructions: [Which instruction files are relevant]
```

## Example Workflows

### Creating a New Feature

1. **Plan** (with Lead SWE):
   ```
   @lead-software-engineer Review the architecture for adding payment processing feature
   ```

2. **Implement** (with feature-implementation.prompt.md):
   ```
   @senior-software-engineer-implementation Use feature-implementation.prompt.md to implement payment processing

   Requirements:
   - Stripe integration
   - Payment webhook handling
   - Receipt generation
   - Audit logging
   ```

3. **Write Tests** (with write-tests.prompt.md):
   ```
   @senior-qa-engineer Use write-tests.prompt.md to test payment processing service
   ```

4. **Security Review** (with security-audit.prompt.md):
   ```
   @senior-security-engineer Use security-audit.prompt.md to review payment processing implementation
   ```

5. **Document** (with write-documentation.prompt.md):
   ```
   @technical-writer Use write-documentation.prompt.md to document payment API endpoints
   ```

### Fixing a Bug

1. **Debug** (with fix-bug.prompt.md):
   ```
   @senior-software-engineer-implementation Use fix-bug.prompt.md

   Bug: API returns 500 when workflow_id contains special characters
   Expected: Return 400 with validation error
   ```

2. **Write Regression Test**:
   ```
   @senior-qa-engineer Write a test that verifies workflow_id validation handles special characters
   ```

3. **Review Fix**:
   ```
   @senior-software-engineer-reviewer Use code-review.prompt.md to review the bug fix in workflows_service.py
   ```

### Code Refactoring

1. **Review Current State**:
   ```
   @lead-software-engineer Analyze workflows_service.py and identify refactoring opportunities
   ```

2. **Refactor** (with refactor-code.prompt.md):
   ```
   @senior-software-engineer-implementation Use refactor-code.prompt.md to refactor workflows_service.py

   Goals:
   - Reduce function complexity
   - Extract duplicate code
   - Improve type safety
   ```

3. **Verify Tests**:
   ```
   @senior-qa-engineer Verify all tests still pass after refactoring
   ```

## Best Practices

### When Using Prompts

1. **Be Specific**: Replace all placeholders with actual values
2. **Provide Context**: Include relevant file paths and requirements
3. **Use Agents**: Invoke appropriate custom agents for better results
4. **Iterate**: Refine the prompt if results aren't what you expect
5. **Combine Prompts**: Use multiple prompts for complex tasks

### Customizing Prompts

1. **Add Your Requirements**: Include project-specific needs
2. **Adjust Scope**: Remove sections not relevant to your task
3. **Add Examples**: Include concrete examples from your codebase
4. **Reference Files**: Point to specific files/modules to analyze

### Creating New Prompts

If you need a new reusable prompt:

1. **Follow the naming convention**: `[purpose].prompt.md`
2. **Use the standard structure**: See "Prompt Structure" above
3. **Base on instructions**: Align with existing instruction files
4. **Map to agents**: Identify which custom agent(s) to use
5. **Include examples**: Show how to use the prompt
6. **Add to README**: Update this file with the new prompt

## Prompt Categories

### By Development Phase

| Phase | Prompts |
|-------|---------|
| **Planning** | (Use Lead SWE agent directly) |
| **Implementation** | feature-implementation, create-api-endpoint |
| **Testing** | write-tests |
| **Review** | code-review, security-audit |
| **Deployment** | docker-setup, add-monitoring |
| **Documentation** | write-documentation |
| **Maintenance** | fix-bug, refactor-code |

### By Role

| Role | Relevant Prompts |
|------|------------------|
| **Software Engineer** | feature-implementation, fix-bug, refactor-code, create-api-endpoint |
| **QA Engineer** | write-tests, code-review |
| **Security Engineer** | security-audit, code-review |
| **DevOps Engineer** | docker-setup, add-monitoring |
| **Technical Writer** | write-documentation |
| **Tech Lead** | code-review, refactor-code |

## Tips for Better Results

1. **Start with the Right Agent**: Choose the agent that matches the task
2. **Provide Full Context**: Include file paths, requirements, and constraints
3. **Use Checklists**: Ensure all items in prompt checklists are addressed
4. **Follow Up**: Ask clarifying questions if output is unclear
5. **Validate Output**: Always review and test generated code
6. **Learn Patterns**: Study the prompts to understand project standards

## Related Resources

- **Custom Agents**: `.github/agents/*.agent.md`
- **Instruction Files**: `.github/instructions/*.instructions.md`
- **Project Documentation**: `README.md`, `docs/`
- **Makefile**: Available commands and workflows

## Contributing

To add a new prompt:

1. Create `[name].prompt.md` in this directory
2. Follow the standard structure
3. Update this README with the new prompt
4. Test the prompt with relevant agents
5. Submit a PR with conventional commit message

## Questions?

- Check the custom agents README: `.github/agents/README.agent.md`
- Review instruction files: `.github/instructions/`
- Ask in team chat or create an issue
