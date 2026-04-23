---
name: readme
description: Guide to all available custom agents and their specialized capabilities.
tools: [read]
---

# Custom Agents Guide

This repository includes specialized GitHub Copilot agents designed to assist with different aspects of software development. Each agent has specific expertise and tool access tailored to their role.

## 🎯 Subagent Orchestration (RECOMMENDED)

**The Orchestrator acts as a manager, automatically delegating tasks to specialized subagents.**

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    SUBAGENT ORCHESTRATION MODEL                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│                    ┌──────────────────────┐                             │
│                    │   ORCHESTRATOR       │                             │
│                    │   (Manager)          │                             │
│                    │                      │                             │
│                    │  • Creates Design    │                             │
│                    │  • Makes TODO List   │                             │
│                    │  • Delegates Tasks   │                             │
│                    └──────────┬───────────┘                             │
│                               │                                         │
│           ┌───────────────────┼───────────────────┬──────────┐          │
│           │         │         │         │         │          │          │
│           ▼         ▼         ▼         ▼         ▼          ▼          │
│     ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐│
│     │  🏗️     │ │  🔧     │ │  🔍     │ │  🧪     │ │  🔒     │ │  📚     ││
│     │ Lead    │ │ Impl.   │ │ Review  │ │  QA     │ │Security │ │  Docs   ││
│     └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘│
│                                                                         │
│     Complex      Standard    Code       Testing   Security   Documentation│
│     Features     Tasks       Review    Tasks      Review     Tasks        │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### How It Works

1. **Start with Orchestrator**: `@orchestrator Create a user management API`
2. **Orchestrator creates design**: Architecture, TODO list with agent assignments
3. **Orchestrator delegates automatically**: Calls specialized agents for each task type
4. **Agents work in sequence**: Implementation → Review (90%) → Security → QA → Docs
5. **Orchestrator manages iteration**: If issues found, coordinates fixes

### Task Type → Agent Mapping

| Task Type | Keywords | Agent |
|-----------|----------|-------|
| 🏗️ Complex Features | critical, complex, architecture, auth, security | `@lead-software-engineer` |
| 🔧 Implementation | create, implement, build, code, add | `@senior-software-engineer-implementation` |
| 🔍 Code Review | review, check, assess, score | `@senior-software-engineer-reviewer` |
| 🧪 Testing | test, validate, verify, coverage | `@senior-qa-engineer` |
| 🔒 Security | security, vulnerability, auth | `@senior-security-engineer` |
| 📚 Documentation | document, readme, api docs | `@technical-writer` |

### Quick Start

```
@orchestrator Create a user management API with CRUD operations

Requirements:
- User model with email, name, role
- CRUD endpoints with pagination
- Soft delete support
- Input validation
```

The Orchestrator will automatically:
1. Create technical design
2. Generate TODO list with agent assignments
3. Call `@lead-software-engineer` for complex/critical features
4. Call `@senior-software-engineer-implementation` for standard coding
5. Call `@senior-software-engineer-reviewer` for review (target: 90%)
6. Iterate if confidence < 90%
7. Call `@senior-security-engineer` for security review
8. Call `@senior-qa-engineer` for writing tests
9. Call `@technical-writer` for documentation

**All orchestrated automatically!**

---

## 🔄 Manual Workflow (Alternative)

For manual control, you can invoke each agent directly:

```
@senior-software-engineer-implementation Implement the User model
@senior-software-engineer-reviewer Review the User model implementation
@senior-qa-engineer Write tests for the User model
```
```

### Workflow Steps

| Step | Agent | Action | Output |
|------|-------|--------|--------|
| 1 | Lead Engineer | Design & create TODO list | Technical design + task breakdown |
| 2 | Implementation | Code the solution | Working implementation |
| 3 | Reviewer | Review & score (0-100%) | Confidence score + issues |
| 3a | Implementation | Fix issues (if < 90%) | Improved code |
| 4 | QA Engineer | Write tests & validate | Test suite + coverage |
| 4a | Implementation | Fix test failures | Bug fixes |
| 5 | Complete | All tests pass | Production-ready code |

### Using the Workflow in VS Code

**📖 For detailed instructions**: See [WORKFLOW.md](WORKFLOW.md)
**📋 For tracking progress**: Copy [WORKFLOW_TEMPLATE.md](WORKFLOW_TEMPLATE.md)

#### Quick Start:

1. **Start with Lead Engineer**: Ask to design a feature
2. **Click handoff button**: "🚀 Start Implementation"
3. **Implementation builds**: Code is created
4. **Click handoff button**: "🔍 Request Review"
5. **Reviewer scores**: Gives confidence % and issues
6. **If < 90%**: Click "🔧 Fix Issues" → back to Implementation
7. **If ≥ 90%**: Click "✅ Approved → QA"
8. **QA writes tests**: Creates comprehensive test suite
9. **If tests fail**: Click "🔧 Fix Test Issues" → back to Implementation
10. **If tests pass**: Click "✅ All Tests Pass" → Complete!

#### Example Command to Start:

```
@orchestrator I need to add [FEATURE NAME].

Requirements:
- [Requirement 1]
- [Requirement 2]

Please provide a technical design and TODO list.
```

## Available Agents

### 1. Orchestrator (@orchestrator)

**Role**: Team coordination and task delegation

**Expertise**:
- Solution design and architecture planning
- Breaking down complex problems into tasks
- Delegating to specialized agents
- Coordinating review loops and quality gates
- Managing workflow from design to completion
- Risk management and dependency tracking

**When to Use**:
- Orchestrating complex multi-agent workflows
- Coordinating feature development from start to finish
- Managing iterations and quality gates
- Breaking down large projects
- Ensuring all quality checks are completed

**Tools**: Agent invocation only (orchestration focus)

---

### 2. Lead Software Engineer (@lead-software-engineer)

**Role**: Hands-on technical leadership and complex implementation

**Expertise**:
- System architecture and design patterns
- Implementing complex, critical features
- Deep Python/WebAPI/hexagonal architecture knowledge
- Security-sensitive implementations
- Performance optimization
- Making final technical decisions
- Mentoring through code examples

**When to Use**:
- Implementing complex, critical features
- Architecture implementation (not just design)
- Security-sensitive code (auth, encryption)
- Performance-critical components
- Major refactoring efforts
- Technical guidance on hard problems

**Tools**: Full access (read, edit, search, execute, agent, web, todo)

---

### 3. Senior Software Engineer - Implementation (@senior-software-engineer-implementation)

**Role**: Feature implementation and clean code development

**Expertise**:
- Writing production-quality code
- Implementing features from specifications
- Applying design patterns and SOLID principles
- Writing comprehensive tests
- Debugging and problem-solving
- Code refactoring

**When to Use**:
- Implementing standard features (not complex/critical ones)
- Writing clean, maintainable code
- Adding test coverage
- Refactoring existing code
- Debugging issues
- Building reusable components

**Tools**: Full access (read, edit, search, execute, agent, web, todo)

---

### 4. Senior QA Engineer (@senior-qa-engineer)

**Role**: Test automation and quality assurance

**Expertise**:
- Test strategy and planning
- Test automation (unit, integration, e2e)
- Test framework development
- Quality assurance processes
- Bug identification and verification
- Performance and load testing

**When to Use**:
- Writing automated tests
- Designing test strategies
- Setting up test frameworks
- Improving test coverage
- Reviewing code for testability
- Creating test plans

**Tools**: Limited access (read, edit, search, execute) - No agent invocation or web access

---

### 5. Senior Security Engineer (@senior-security-engineer)

**Role**: Security review and vulnerability assessment

**Expertise**:
- Security vulnerability identification
- OWASP Top 10 assessment
- Secure coding practices
- Authentication and authorization review
- Threat modeling
- Security compliance

**When to Use**:
- Reviewing code for security issues
- Assessing authentication/authorization
- Checking for common vulnerabilities
- Security threat modeling
- Validating input handling
- Reviewing secrets management

**Tools**: Read-only access (read, search, execute) - Cannot modify code, safe for security reviews

---

### 6. Senior Software Engineer - Reviewer (@senior-software-engineer-reviewer)

**Role**: Code review and quality feedback

**Expertise**:
- Thorough code review
- Identifying bugs and logic errors
- Ensuring best practices
- Providing constructive feedback
- Knowledge sharing through reviews
- Maintaining code quality standards

**When to Use**:
- Reviewing pull requests
- Providing feedback on code quality
- Checking for best practices
- Identifying potential issues
- Mentoring through code review
- Ensuring standards compliance

**Tools**: Read-only access (read, search) - Perfect for non-invasive reviews

---

### 7. Senior DevOps Engineer (@senior-devops-engineer)

**Role**: Infrastructure, CI/CD, and operational excellence

**Expertise**:
- CI/CD pipeline design and implementation
- Infrastructure as Code (Terraform, CloudFormation)
- Docker and Kubernetes
- Cloud platforms (AWS, Azure, GCP)
- Monitoring and observability
- Security and secrets management

**When to Use**:
- Setting up CI/CD pipelines
- Writing infrastructure code
- Containerizing applications
- Deploying to cloud platforms
- Implementing monitoring
- Automating operational tasks

**Tools**: Full access (read, edit, search, execute, agent, web, todo)

---

### 8. Technical Writer (@technical-writer)

**Role**: Documentation and technical content creation

**Expertise**:
- Writing clear, comprehensive documentation
- Creating API documentation
- Writing tutorials and guides
- README and getting started docs
- Architecture documentation
- User guides

**When to Use**:
- Writing documentation
- Creating tutorials
- Documenting APIs
- Updating README files
- Writing how-to guides
- Creating architecture docs

**Tools**: Limited access (read, edit, search) - Focused on documentation tasks

---

## How to Use Agents

### In GitHub Copilot Chat

Mention an agent with `@agent-name` to invoke them:

```
@senior-qa-engineer Help me write tests for the user authentication module
```

```
@senior-security-engineer Review this code for security vulnerabilities
```

```
@technical-writer Create API documentation for these endpoints
```

### Best Practices

1. **Choose the right agent** - Each agent is specialized, pick the one that matches your task
2. **Be specific** - Provide clear context and requirements
3. **Use multiple agents** - Different agents can work on different aspects
4. **Sequential work** - Use one agent's output as input for another

### Example Workflows

**🔄 Iterative Feature Development (RECOMMENDED)**:
Use handoffs for automatic workflow progression:
1. `@lead-software-engineer` - "Design a user management API"
2. Click **"🚀 Start Implementation"** handoff
3. Implementation agent codes the solution
4. Click **"🔍 Request Review"** handoff
5. Reviewer gives confidence score (e.g., 75%)
6. Click **"🔧 Fix Issues"** → fix and re-request review
7. Reviewer approves (90%+) → Click **"✅ Approved → QA"**
8. QA writes tests → Click **"✅ All Tests Pass"**
9. Done! ✅

**Quick Feature Development**:
1. `@lead-software-engineer` - Design the solution architecture
2. `@senior-software-engineer-implementation` - Implement the feature
3. `@senior-software-engineer-reviewer` - Review the code (get 90%+ confidence)
4. `@senior-qa-engineer` - Add comprehensive tests
5. `@technical-writer` - Document the feature

**Security Review Flow**:
1. `@senior-security-engineer` - Identify security issues
2. `@senior-software-engineer-implementation` - Fix vulnerabilities
3. `@senior-security-engineer` - Verify fixes
4. `@technical-writer` - Document security considerations

**DevOps Setup Flow**:
1. `@senior-devops-engineer` - Design CI/CD pipeline
2. `@senior-devops-engineer` - Implement infrastructure code
3. `@senior-security-engineer` - Review security configuration
4. `@technical-writer` - Document deployment process

## Agent Comparison

| Agent | Implementation | Review | Testing | Security | Documentation | DevOps |
|-------|---------------|---------|---------|----------|---------------|--------|
| Orchestrator | ❌ No | ❌ No | ❌ No | ❌ No | ❌ No | ❌ No |
| Lead Software Engineer | ✅ Expert (Complex) | ✅ Advanced | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| Senior SWE - Implementation | ✅ Expert (Standard) | ⚠️ Basic | ✅ Yes | ⚠️ Basic | ⚠️ Basic | ⚠️ Basic |
| Senior QA Engineer | ⚠️ Basic | ⚠️ Tests Only | ✅ Expert | ⚠️ Basic | ⚠️ Basic | ❌ No |
| Senior Security Engineer | ❌ No | ✅ Security | ⚠️ Basic | ✅ Expert | ⚠️ Basic | ❌ No |
| Senior SWE - Reviewer | ❌ No | ✅ Expert | ⚠️ Review | ✅ Yes | ⚠️ Review | ❌ No |
| Senior DevOps Engineer | ⚠️ Basic | ⚠️ Basic | ⚠️ Basic | ✅ Yes | ⚠️ Basic | ✅ Expert |
| Technical Writer | ❌ No | ❌ No | ❌ No | ❌ No | ✅ Expert | ❌ No |

**Legend**: ✅ Expert, ⚠️ Basic/Limited, ❌ Not Available

**Note**: Orchestrator = Manager/Coordinator only (no hands-on work)

## Tool Access by Agent

| Tool | Orchestrator | Lead | Implementation | QA | Security | Reviewer | DevOps | Writer |
|------|--------------|------|----------------|-----|----------|----------|--------|--------|
| read | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| edit | ❌ | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ |
| search | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| execute | ❌ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ |
| agent | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ |
| web | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ |
| todo | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ |

**Note**: Orchestrator only has agent invocation tool (pure delegation)

## Quick Reference

### Want to orchestrate a full workflow?
→ `@orchestrator`

### Want hands-on implementation of complex features?
→ `@lead-software-engineer`

### Want to implement a standard feature?
→ `@senior-software-engineer-implementation`

### Want to review code?
→ `@senior-software-engineer-reviewer`

### Want to write tests?
→ `@senior-qa-engineer`

### Want to check security?
→ `@senior-security-engineer`

### Want to set up CI/CD or infrastructure?
→ `@senior-devops-engineer`

### Want to write documentation?
→ `@technical-writer`

## Tips

1. **Combine agents** - Use different agents for different aspects of the same task
2. **Be explicit** - Tell agents exactly what you need
3. **Provide context** - Share relevant files, requirements, or constraints
4. **Iterate** - Agents can refine their work based on your feedback
5. **Trust their expertise** - Each agent is trained for their specific domain

## Support

If you have questions or issues with the agents:
- **Workflow Guide**: [WORKFLOW.md](WORKFLOW.md) - Step-by-step instructions
- **Workflow Template**: [WORKFLOW_TEMPLATE.md](WORKFLOW_TEMPLATE.md) - Copy for your feature
- **Agent Details**: Review individual agent files in `.github/agents/`
- **Coding Standards**: Check `.github/instructions/` for best practices
- **GitHub Copilot**: [Official documentation](https://docs.github.com/copilot)

---

**Last Updated**: 2026-02-09
**Agent Version**: 1.0.0
