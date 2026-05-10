# Release Automation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automate version bumping, changelog generation, and GitHub Releases via commitizen on merges to main.

**Architecture:** Two GitHub Actions workflows. `ci.yml` runs tests/lint on PRs to main. `release.yml` runs commitizen on push to main (merge) to bump version, update CHANGELOG.md, create git tag, and publish a GitHub Release.

**Tech Stack:** commitizen (cz_conventional_commits), GitHub Actions, uv, Python 3.13

---

### Task 1: Add commitizen config and dev dependency

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Add `[tool.commitizen]` section to pyproject.toml**

Append the commitizen configuration to `pyproject.toml`:

```toml
[tool.commitizen]
name = "cz_conventional_commits"
tag_format = "v$version"
bump_message = "chore(release): bump version $current_version -> $new_version"
version_files = ["pyproject.toml:version"]
update_changelog_on_bump = true
```

- [ ] **Step 2: Add commitizen as a dev dependency**

Run: `uv add --dev commitizen`

- [ ] **Step 3: Verify config is recognized**

Run: `uv run cz info`

Expected: Output shows `name: cz_conventional_commits`, `version: 0.1.0`, etc.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "chore: add commitizen config and dev dependency"
```

---

### Task 2: Create CI workflow

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Create the CI workflow file**

Create `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  pull_request:
    branches: [main]
    types: [opened, synchronize, reopened]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v5
        with:
          python-version: "3.13"
          enable-cache: true

      - name: Install dependencies
        run: uv sync --dev

      - name: Lint with Ruff
        run: uv run ruff check .

      - name: Check formatting with Ruff
        run: uv run ruff format --check .

      - name: Run tests
        run: uv run pytest
```

- [ ] **Step 2: Verify workflow syntax (if `act` is available)**

Run: `act pull_request -W .github/workflows/ci.yml --dryrun 2>&1 | head -5` or skip if `act` is not installed.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add PR testing workflow with ruff and pytest"
```

---

### Task 3: Create release workflow

**Files:**
- Create: `.github/workflows/release.yml`

- [ ] **Step 1: Create the release workflow file**

Create `.github/workflows/release.yml`:

```yaml
name: Release

on:
  push:
    branches: [main]

permissions:
  contents: write

jobs:
  release:
    runs-on: ubuntu-latest
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Install uv
        uses: astral-sh/setup-uv@v5
        with:
          python-version: "3.13"

      - name: Install dependencies
        run: uv sync --dev

      - name: Bump version and update changelog
        uses: commitizen-tools/commitizen-action@v4.4.0
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          push: true
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/release.yml
git commit -m "ci: add release workflow with commitizen bump and changelog"
```

---

### Task 4: Initialize changelog from existing commit history

**Files:**
- Create: `CHANGELOG.md`

- [ ] **Step 1: Verify commitizen is installed and configured**

Run: `uv run cz info`

Expected: commitizen reports version info and conventional commits scheme.

- [ ] **Step 2: Generate initial CHANGELOG.md**

Run: `uv run cz changelog`

This reads all past commits and generates a `CHANGELOG.md` with entries grouped by version (feat, fix, etc.).

- [ ] **Step 3: Review the generated changelog**

Read `CHANGELOG.md` and verify it correctly categorizes past commits. Edit if needed.

- [ ] **Step 4: Commit**

```bash
git add CHANGELOG.md
git commit -m "docs: add initial CHANGELOG.md from commit history"
```
