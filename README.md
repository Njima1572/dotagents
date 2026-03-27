# dotclaude

A dotfiles-style configuration repo for [Claude Code](https://claude.ai/code). Stores reusable agents, skills, and scripts that can be installed into any project's `.claude/` directory via symlinks.

## Setup

Add `bin/` to your PATH:

```bash
export PATH="$HOME/Development/dotclaude/bin:$PATH"
```

Requires [uv](https://docs.astral.sh/uv/) for running Python scripts.

## What's Included

### Skills

Skills are slash commands available in Claude Code (e.g., `/plan`, `/tdd`).

| Skill | Description |
|---|---|
| `build-fix` | Diagnose and fix build failures, test failures, and compilation errors |
| `code-review` | Review code changes for quality, standards compliance, and potential issues |
| `plan` | Create implementation plan before coding |
| `tdd` | Test-driven development workflow |

### Agents

Agents are specialized subagents that Claude can spawn for specific tasks.

| Agent | Description |
|---|---|
| `code-roaster` | Brutally honest code review with actionable fixes |
| `tdd-guide` | Guides test-driven development from test to implementation |

### CLI Tools

| Tool | Description |
|---|---|
| `dotclaude` | Bootstrap `.claude/` in any project |
| `orchestrator` | Task and idea manager backed by SQLite |

## dotclaude CLI

Initialize `.claude/` in a project and cherry-pick what to install.

```bash
# Scaffold .claude/ directory and CLAUDE.md
dotclaude init

# Scaffold and install everything
dotclaude init all

# See what's available
dotclaude list

# Cherry-pick specific items
dotclaude add skills plan tdd
dotclaude add agents code-roaster

# Install everything in a category
dotclaude add skills
dotclaude add all

# Remove an item
dotclaude remove skills plan

# Check what's installed
dotclaude status
```

Symlinked items are automatically added to the project's `.gitignore`.

### Configuration

By default, `dotclaude` looks for the repo at `~/Development/dotclaude`. Override with:

```bash
export DOTCLAUDE_HOME=/path/to/your/dotclaude
```

## orchestrator CLI

A task and idea manager backed by SQLite, with `claude -p` integration for working on tasks.

```bash
# Create tasks and ideas (auto-registers current directory as a project)
orchestrator create "fix the login bug"
orchestrator idea "maybe add dark mode"

# List tasks
orchestrator list                    # current project
orchestrator list myproject          # specific project
orchestrator list --all              # all projects
orchestrator list -s in-progress     # filter by status

# Work on a task (runs claude -p in the project directory)
orchestrator work 3

# Update status manually
orchestrator status 3 done

# List all registered projects
orchestrator projects
```

### Task States

```
idea -> not-implemented -> in-progress -> needs-review -> done -> archived
                                    \                        \-> discarded
                                     \-> discarded
```

| Status | Description |
|---|---|
| `idea` | Initial idea, not yet fleshed out |
| `not-implemented` | Mature idea, ready to be worked on |
| `in-progress` | Currently being worked on |
| `needs-review` | Work complete, awaiting review |
| `done` | Reviewed and complete |
| `archived` | Completed and archived |
| `discarded` | Dropped |

### Configuration

Database is stored at `~/.orchestrator/orchestrator.db` by default. Override with:

```bash
export DOTCLAUDE_HOME=/path/to/data
```

## Project Structure

```
dotclaude/
  agents/               # Subagent definitions (.md)
  skills/               # Slash commands (dir/SKILL.md)
    build-fix/
    code-review/
    plan/
    tdd/
  rules/                # Rules (.md)
  bin/                  # CLI entrypoints (shell wrappers)
    dotclaude
    orchestrator
  scripts/              # Python scripts and shell utilities
    dotclaude.py
    orchestrator.py
    setup.sh
    notify-discord.sh
```

## Discord Notifications

Run `scripts/setup.sh` to install a notification hook that posts to Discord when Claude Code needs attention (idle, permission prompt, etc.).

```bash
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/... ./scripts/setup.sh
```
