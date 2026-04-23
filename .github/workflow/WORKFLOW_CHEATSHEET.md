# Workflow Cheat Sheet

Quick reference for the iterative development workflow.

## 🎯 The Flow

```
START
  ↓
┌─────────────────────────┐
│ 1. ORCHESTRATOR         │ Design + TODO + Assignments
│ @orchestrator           │
└────────────┬────────────┘
             ↓
┌────────────────────────────────┐
│ 2. IMPLEMENTATION              │ Write the code
│ @lead-software-engineer OR     │ (Complex vs Standard)
│ @senior-software-engineer-     │
│    implementation              │
└────────────┬───────────────────┘
             ↓
┌────────────────────────────────┐
│ 3. REVIEWER                    │ Score: X%
│ @senior-software-engineer-     │ Issues: [list]
│    reviewer                    │
└────────────┬───────────────────┘
             ↓
        < 90%? ───────┐
             │        │
         NO  │   YES  │
             │        ↓
             │   ┌────────────────────────┐
             │   │ Fix Issues             │
             │   │ @lead-software-        │
             │   │    engineer OR         │
             │   │ @senior-software-      │
             │   │    engineer-           │
             │   │    implementation      │
             │   └────────┬───────────────┘
             │            │
             │            └──→ Back to REVIEWER (Step 3)
             ↓
┌────────────────────────────────┐
│ 4. QA ENGINEER                 │ Write tests
│ @senior-qa-engineer            │ Run tests
└────────────┬───────────────────┘
             ↓
    Tests fail? ───────┐
             │         │
         NO  │    YES  │
             │         ↓
             │   ┌────────────────────────┐
             │   │ Fix Test Issues        │
             │   │ @lead-software-        │
             │   │    engineer OR         │
             │   │ @senior-software-      │
             │   │    engineer-           │
             │   │    implementation      │
             │   └────────┬───────────────┘
             │            │
             │            └──→ Back to QA (Step 4)
             ↓
┌────────────────────────────────┐
│ ✅ COMPLETE                    │ Production ready!
└────────────────────────────────┘
```

## 📝 Command Templates

### Step 1: Design
```
@orchestrator I need to [FEATURE].
Requirements: [LIST]
Please provide technical design and TODO list with agent assignments.
```

### Step 2a: Implementation (Complex)
```
@lead-software-engineer
Based on the design above, implement [COMPLEX FEATURE]:
- [Critical requirement 1]
- [Critical requirement 2]
Follow security and project standards.
```

### Step 2b: Implementation (Standard)
```
@senior-software-engineer-implementation
Based on the design above, implement:
[TODO LIST]
Follow conventions from .github/instructions/
```

### Step 3: Review
```
@senior-software-engineer-reviewer
Review the implementation.
Provide confidence score (need 90%+) and issues.
```

### Step 4a: Fix Issues (if score < 90%)
```
@senior-software-engineer-implementation
Fix these issues (Current score: X%):
1. [Issue 1]
2. [Issue 2]
```

Or for complex features:
```
@lead-software-engineer
Fix these architectural issues (Current score: X%):
1. [Issue 1]
2. [Issue 2]
```

### Step 5: QA Testing
```
@senior-qa-engineer
Implementation approved (90%+).
Write comprehensive tests:
- Unit tests
- Integration tests
- Edge cases
Target: 90%+ coverage
```

### Step 6a: Fix Test Issues
```
@senior-software-engineer-implementation
Fix test failures:
1. [Test 1] - [Error]
2. [Test 2] - [Error]
```

Or for complex features:
```
@lead-software-engineer
Fix these critical test failures:
1. [Test 1] - [Error]
2. [Test 2] - [Error]
```

## 🎨 Decision Points

| Checkpoint | Decision | Action |
|------------|----------|--------|
| After Review | Score < 90% | → Fix Issues → Review Again |
| After Review | Score ≥ 90% | → Proceed to QA |
| After QA | Tests Fail | → Fix Bugs → Test Again |
| After QA | Tests Pass | → Complete ✅ |

## 📊 Success Criteria

- ✅ **Design**: Clear architecture + TODO with agent assignments
- ✅ **Implementation**: Working code following conventions (Lead for complex, Implementation for standard)
- ✅ **Review**: 90%+ confidence score
- ✅ **QA**: 90%+ test coverage, all tests passing
- ✅ **Complete**: Production ready

## 🚀 Quick Start

1. Copy [WORKFLOW_TEMPLATE.md](WORKFLOW_TEMPLATE.md)
2. Fill in feature name
3. Follow steps 1-7
4. Track progress with checkboxes

## 💡 Pro Tips

- **Always** provide context and requirements
- **Reference** instruction files in prompts
- **Track** confidence scores in each iteration
- **Don't skip** the review loop - quality matters!
- **Test early** to catch issues sooner

## ⚡ One-Liner Start

```
@orchestrator Design [FEATURE]: [Requirements]. Include design doc, TODO list, and agent assignments.
```

Then follow the handoff buttons in VS Code! 🎯
