---
name: worktree-remove
description: Clean up a git worktree after a feature is complete - removes the worktree directory and optionally deletes the branch
---

# Remove Worktree After Task Completion

Safely tear down a git worktree when development on a feature branch is done.

## 1. Identify the Worktree

- Run `git worktree list` to show all active worktrees
- If the user did not specify which worktree to remove, present the list and ask them to pick one
- Never remove the main/bare worktree (the original repo checkout)

## 2. Pre-Removal Checks

- `cd` into the worktree path (or read its status remotely) and run `git status` to check for:
  - Uncommitted changes (staged or unstaged)
  - Untracked files that might be important
  - Unpushed commits (`git log --oneline @{u}..HEAD` or `git log --oneline origin/<branch>..HEAD`)
- If there are uncommitted changes or unpushed commits, **stop and warn the user**. Ask whether to:
  - Commit and push first
  - Stash the changes
  - Discard and proceed (only if the user explicitly confirms)

## 3. Check Merge Status

- Check if the feature branch has been merged into the base branch:
  - `git branch --merged <base-branch>` from the main worktree
  - Or check if a PR was merged via `gh pr list --head <branch> --state merged` if gh is available
- If the branch has NOT been merged, warn the user clearly. Do not delete the branch unless they explicitly confirm.

## 4. Remove the Worktree

```
git worktree remove <worktree-path>
```

- If removal fails due to unclean state and the user has confirmed they want to discard, use `git worktree remove --force <worktree-path>`
- Run `git worktree prune` to clean up stale worktree references

## 5. Optionally Delete the Branch

- If the branch was merged, offer to delete it:
  - Local: `git branch -d <branch-name>`
  - Remote: `git push origin --delete <branch-name>`
- If the branch was NOT merged, only delete with `git branch -D` if the user explicitly requests it

## 6. Verify Cleanup

- Run `git worktree list` to confirm the worktree is gone
- Run `git branch` to confirm branch state
- Report what was removed

## Notes

- Safety is the priority: never silently discard uncommitted work
- Always show the user what will be lost before any destructive action
- If the worktree directory was already manually deleted, `git worktree prune` handles the cleanup
