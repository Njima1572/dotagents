---
name: worktree-create
description: Create a git worktree for a new feature branch - sets up an isolated working directory for parallel development
---

# Create Worktree for New Feature

Set up an isolated git worktree so a new feature can be developed without disturbing the current working directory.

## 1. Gather Context

- Ask the user for the feature name or branch name if not provided as an argument
- Ask which base branch to branch from (default: `main`)
- Determine the worktree path (default: `../<repo-name>-<branch-name>`)

## 2. Pre-flight Checks

- Run `git status` to confirm the current repo is clean or has no conflicting state
- Run `git fetch origin` to ensure we have the latest remote refs
- Verify the base branch is up to date with `git log --oneline -1 origin/<base>` vs `git log --oneline -1 <base>`
- Check that the target worktree path does not already exist
- Check that the branch name does not already exist with `git branch --list <branch>`

## 3. Create the Worktree

Run the following command to create a new worktree with a new branch:

```
git worktree add -b <branch-name> <worktree-path> <base-branch>
```

- Branch naming convention: use conventional prefixes like `feat/`, `fix/`, `refactor/`, `docs/` based on the type of work
- If the user provides a branch name without a prefix, suggest one but respect their choice

## 4. Post-Setup

- Verify the worktree was created with `git worktree list`
- If the project has dependency files (package.json, Gemfile, requirements.txt, go.mod, etc.), remind the user to install dependencies in the new worktree
- Print the full path to the new worktree so the user can navigate to it or open it in their editor

## 5. Report

Summarize what was created:
- Branch name
- Base branch
- Worktree path
- Any next steps (install deps, open in editor, etc.)

## Notes

- Never force-create a branch that already exists
- If the worktree path already exists, ask the user how to proceed rather than overwriting
- If the base branch is behind remote, warn the user and offer to pull first
