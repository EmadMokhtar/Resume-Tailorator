# Release Automation Design

## Summary

Automate version bumping, changelog generation, and GitHub Releases
using Commitizen and the Conventional Commits already in use by the repo.
Two GitHub Actions workflows (CI + Release) plus a one-time init PR to
backfill the changelog from existing history.

## commitizen Configuration

Add to `pyproject.toml`:

```toml
[tool.commitizen]
name = "cz_conventional_commits"
tag_format = "v$version"
bump_message = "chore(release): bump version $current_version -> $new_version"
version_files = ["pyproject.toml:version"]
update_changelog_on_bump = true
```

Add `commitizen` as a dev dependency.

Commitizen auto-detects bump level from commits since the last tag:
`feat:` -> MINOR, `fix:` -> PATCH, `feat!:` or `BREAKING CHANGE:` -> MAJOR.

## CI Workflow (`.github/workflows/ci.yml`)

**Trigger:** `pull_request` targeting `main` (opened, synchronize, reopened).

**Jobs:**
1. Checkout
2. Install uv + Python 3.13
3. Install deps with `uv sync --dev`
4. Ruff lint + format check
5. Pytest

No version or changelog concerns in this workflow.

## Release Workflow (`.github/workflows/release.yml`)

**Trigger:** `push` to `main`. Protected branch means all pushes are merges.

**Permissions:** `contents: write` (push commits, tags, create releases).

**Jobs:**
1. Checkout with `fetch-depth: 0` (full history for commitizen analysis)
2. Setup uv + Python 3.13
3. Run `commitizen-tools/commitizen-action@v4.4.0` with:
   - `github_token: ${{ secrets.GITHUB_TOKEN }}`
   - `push: true` (pushes bumped pyproject.toml + updated CHANGELOG.md)
4. Action auto-creates git tag and GitHub Release from changelog entry

## Initialization PR (One-Time)

1. Add commitizen dev dependency: `uv add --dev commitizen`
2. Run `cz changelog` to generate CHANGELOG.md from all past commits
3. Verify starting version (currently 0.1.0 in pyproject.toml)
4. Review and commit:
   - Updated `pyproject.toml` (commitizen config + dev dep)
   - New `CHANGELOG.md`
5. Merge PR — release workflow is live from that point forward

## Files Changed

| File | Action |
|------|--------|
| `pyproject.toml` | Add `[tool.commitizen]` section, add commitizen dev dep |
| `CHANGELOG.md` | New — backfilled from git history |
| `.github/workflows/ci.yml` | New — PR testing workflow |
| `.github/workflows/release.yml` | New — merge-to-main release workflow |

## Error Handling

- Release workflow only runs if CI passes on the PR (branch protection enforces this)
- If commitizen finds no bump-worthy commits (e.g. only `docs:` or `chore:`), it won't bump — the workflow exits cleanly with no tag/release created
- GITHUB_TOKEN scoped to repo — no external secrets needed
