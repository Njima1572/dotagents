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
| `worktree-create` | Create a git worktree for parallel development |
| `worktree-merge` | Merge a worktree's feature branch into the base branch |
| `worktree-remove` | Clean up a git worktree after a feature is complete |

### Agents

Agents are specialized subagents that Claude can spawn for specific tasks.

| Agent | Description |
|---|---|
| `code-roaster` | Brutally honest code review with actionable fixes |
| `tdd-guide` | Guides test-driven development from test to implementation |

### CLI Tools

| Tool | Description |
|---|---|
| `dotclaude` | Bootstrap `.claude/` in any project, manage volume profiles |
| `claude-code` | Run Claude Code in a Docker container with the correct volume profile |
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

### Volume Profiles

Volume profiles define which host directories are mounted into the Docker container. Each profile is a file in `volumes/` (e.g., `volumes/proect1`, `volumes/project2`). The `default` profile is used as a fallback.

```bash
# Show the current profile (detected automatically)
dotclaude profile

# List all available profiles (* marks active)
dotclaude profiles
dotclaude profile list

# Create a new profile for the current directory
dotclaude profile create
dotclaude profile create myproject

# Add a volume to an existing profile
dotclaude volume add                          # current dir -> current profile
dotclaude volume add /path/to/dir             # specific dir -> current profile
dotclaude volume add --profile myproject      # current dir -> specific profile
```

#### Profile Detection

The active profile is resolved via a 3-step fallback:

1. **`$DOTCLAUDE_PROFILE`** env var — set via `.envrc` / [direnv](https://direnv.net/) / manual export
2. **Directory basename** — `lowercase(basename(cwd))` matched against profile files
3. **`default`** — the fallback profile

Using [direnv](https://direnv.net/) is recommended. `dotclaude init` automatically writes a `.envrc` when a matching profile exists:

```bash
# .envrc (auto-created by dotclaude init)
export DOTCLAUDE_PROFILE=myproject
```

### Configuration

By default, `dotclaude` looks for the repo at `~/Development/dotclaude`. Override with:

```bash
export DOTCLAUDE_HOME=/path/to/your/dotclaude
```

## claude-code (Docker)

The `claude-code` wrapper runs Claude Code inside a Docker container, automatically selecting the right volume profile for the current directory.

```bash
# From any project directory
claude-code
```

If the current directory is not mounted in the selected profile, it warns and prompts before proceeding:

```
WARNING: /path/to/dir is not mounted in the container.
To fix this, run:
  dotclaude volume add /path/to/dir
Continue anyway? [y/N]
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
    worktree-create/
    worktree-merge/
    worktree-remove/
  rules/                # Rules (.md)
  volumes/              # Docker volume profiles (bash scripts)
    default             # Fallback profile
    project1            # Project-specific profiles
    ...
  bin/                  # CLI entrypoints (shell wrappers)
    claude-code
    dotclaude
    orchestrator
  scripts/              # Python scripts and shell utilities
    dotclaude.py
    orchestrator.py
    setup.sh
    notify-discord.sh
  Dockerfile.claude     # Docker image for containerized Claude Code
  docker-compose.yml
```

## Discord Notifications

Run `scripts/setup.sh` to install a notification hook that posts to Discord when Claude Code needs attention (idle, permission prompt, etc.).

```bash
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/... ./scripts/setup.sh
```
