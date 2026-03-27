---
name: worktree-merge
description: Merge a worktree's feature branch into the base branch, resolve conflicts, and verify build/tests pass
---

# Merge Worktree Branch and Resolve Conflicts

Merge a feature branch developed in a worktree back into its base branch, handling conflicts carefully and verifying correctness.

## 1. Identify the Branches

- Run `git worktree list` to show active worktrees and their branches
- If not specified, ask the user which feature branch to merge and into which base branch (default: `main`)
- Confirm the merge direction with the user: `<feature-branch>` -> `<base-branch>`

## 2. Pre-Merge Checks

From the **main worktree** (not the feature worktree):

- Run `git fetch origin` to get latest remote state
- Check that the base branch is up to date: `git log --oneline origin/<base>...<base>`
- If behind, pull the base branch first
- Check that the feature branch has no uncommitted changes by inspecting its worktree with `git -C <worktree-path> status`
- Ensure all commits on the feature branch are pushed: `git -C <worktree-path> log --oneline @{u}..HEAD`

## 3. Pre-Merge Build & Test Verification

Before merging, verify the feature branch is in a good state:

- Run the project's build command in the feature worktree (e.g., `make build`, `npm run build`, `cargo build`, `go build ./...`)
- Run the project's test suite in the feature worktree (e.g., `make test`, `npm test`, `pytest`, `go test ./...`)
- If either fails, **stop and report the failures**. The feature branch must be green before merging.
- Detect the build/test commands by checking for Makefile, package.json scripts, Cargo.toml, pyproject.toml, go.mod, or similar project files

## 4. Attempt the Merge

From the base branch in the main worktree:

```
git checkout <base-branch>
git merge <feature-branch>
```

- If the merge completes cleanly, skip to step 6

## 5. Resolve Conflicts (if any)

When conflicts occur:

### 5a. Assess the Conflicts

- Run `git diff --name-only --diff-filter=U` to list all conflicted files
- For each conflicted file, run `git diff` to understand both sides of the conflict
- Categorize conflicts:
  - **Trivial**: whitespace, import ordering, non-overlapping additions
  - **Semantic**: both sides changed the same logic differently
  - **Structural**: file was moved/renamed/deleted on one side

### 5b. Resolve Each Conflict

- Read each conflicted file to understand the full context around conflict markers
- For each conflict:
  - Understand what the base branch changed and why (check `git log --oneline <base>` for relevant commits)
  - Understand what the feature branch changed and why (check `git log --oneline <feature>` for relevant commits)
  - Choose the resolution that preserves the intent of both changes
  - If the correct resolution is ambiguous, present both versions to the user and ask which to keep
- Edit the file to remove conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`) and write the resolved content
- Stage each resolved file with `git add <file>`

### 5c. Verify Resolution

- Run `git diff --cached` to review all resolved changes
- Present a summary of how each conflict was resolved

## 6. Post-Merge Build & Test Verification (Mandatory)

This step is **required** and must not be skipped regardless of whether the merge was clean or had conflicts.

- Run the full build to verify compilation succeeds
- Run the complete test suite to catch any regressions introduced by the merge
- Run the linter/type checker if the project has one configured
- If **any** of these fail:
  - Report the exact failures to the user
  - Diagnose and fix the issues (broken imports, type mismatches, test expectations invalidated by merged changes, etc.)
  - Re-run build and tests after each fix until everything passes
  - Stage and amend the merge commit with the fixes, or create a follow-up commit depending on user preference
- Do NOT proceed to the final step until build and tests are fully green

## 7. Complete and Report

- If the merge commit has not been created yet (conflict resolution flow), run `git commit`
- Run `git log --oneline -5` to show the merge result
- Report:
  - Merge status (clean or conflicts resolved)
  - Build result (pass/fail and what was run)
  - Test result (pass/fail, number of tests, coverage if available)
  - Any fixes that were needed post-merge
- Remind the user they can now:
  - Push the base branch: `git push origin <base-branch>`
  - Clean up the worktree with `/worktree-remove`
  - Delete the feature branch if no longer needed

## Notes

- Never force-resolve conflicts without understanding both sides
- If a conflict involves code you don't fully understand, ask the user rather than guessing
- Prefer `git merge` over `git rebase` for worktree branches to preserve the full history
- If the merge is complex and risky, suggest doing it on a temporary branch first so the base branch stays clean
- Never use `--no-verify` when committing the merge
- Build and test verification is non-negotiable — a green merge is the only acceptable outcome
