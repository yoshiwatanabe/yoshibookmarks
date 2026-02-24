---
description: |
  This workflow runs daily on weekdays to keep repository documentation up to date.
  It identifies documentation files that are out of sync with recent code changes
  and opens a pull request with the necessary updates.

on:
  schedule: daily on weekdays

permissions:
  contents: read
  issues: read
  pull-requests: read

network: defaults

tools:
  github:
    toolsets: [default]

safe-outputs:
  create-pull-request:
    max: 1
    allowed-labels: [documentation]
---

# Documentation Sync

Review repository documentation and keep it up to date with recent code changes.

## Documentation Files to Review

Check the following documentation files for accuracy relative to the current codebase:

- `README.md` - Main project overview, installation, and usage instructions
- `DESIGN.md` - Architecture and design documentation
- `spec.md` - Feature specifications and acceptance criteria
- `CLAUDE.md` - Development guidelines and project conventions

## Process

The source code for this repository lives in `src/`, `extension/`, `setup.py`, `pyproject.toml`, and `requirements.txt`.

1. **Examine recent code changes**: Use git to identify commits from the past 7 days that touched source code files.

   ```bash
   git log --oneline --since="7 days ago" -- src/ extension/ setup.py pyproject.toml requirements.txt
   ```

2. **Read changed source files**: For each recent commit, list the specific files that changed and review their contents.

   ```bash
   git log --since="7 days ago" --name-only --format="" -- src/ extension/ setup.py pyproject.toml requirements.txt | sort -u
   ```

3. **Review each documentation file**: Read each doc file and compare its content against the current state of the code.

4. **Identify outdated sections**: Find sections that describe features, APIs, file structures, or behaviors that no longer match the code.

5. **Update documentation**: Make minimal, accurate edits to bring docs in sync with the code. Only change what is actually outdated.

6. **Create a pull request**: If any documentation was updated, create a pull request with the changes.

## Guidelines

- Make **minimal, targeted changes** — only update what is actually outdated
- Preserve the existing writing style and tone of each document
- Focus on **factual accuracy**: do not invent features or capabilities that don't exist in the code
- Do not rewrite entire sections; prefer surgical edits to specific outdated statements
- If no documentation is out of sync, do not create a pull request

## Pull Request Format

When creating a pull request:
- **Title**: `docs: sync documentation with recent code changes`
- **Body**: List each file changed and summarize what was updated and why, referencing the specific commits that triggered each change
