#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""dotclaude - Bootstrap .claude/ configuration in any project."""

import argparse
import os
import sys
from pathlib import Path

DOTCLAUDE_HOME = Path(
    os.environ.get("DOTCLAUDE_HOME", Path.home() / "Development" / "dotclaude")
)

CATEGORIES = ["agents", "rules", "skills"]
VOLUMES_DIR = DOTCLAUDE_HOME / "volumes"

CLAUDE_MD_TEMPLATE = """\
# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

<!-- Describe what this project does -->

## Development

<!-- Commands to build, test, lint, etc. -->

## Git Workflow

- Conventional commits: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`
"""

PROFILE_TEMPLATE = r"""#!/bin/bash
# ------------------------------------------------------------------
#  volumes.sh  – define host:container mounts once, use everywhere
# ------------------------------------------------------------------
# List each mapping on its own line.
#   * Blank lines are ignored.
#   * Lines starting with # are comments.
#   * Add :ro / :rw at the end per Docker syntax if you need modes.

__VAR_DEFS__

VOLUME_LIST="$(cat <<'EOF'
__VOLUME_ENTRIES__
EOF
)"

[[ -z "${VOLUME_LIST}" ]] && { echo "Volume list is empty!"; exit 1; }

# Build an array of "-v" flags
VOL_ARGS=()
while IFS= read -r line; do
  [[ -z $line || $line == \#* ]] && continue   # skip blanks/comments
  # Expand variables ($PWD, $HOME) **after** we know the line is legit
  eval line_expanded=\"${line}\"
  VOL_ARGS+=(" -v" "${line_expanded}")
done <<< "${VOLUME_LIST}"

# Export for downstream scripts
export DOCKER_VOLUMES="${VOL_ARGS[*]}"
"""


def available_items(category):
    """List available items in a category from DOTCLAUDE_HOME."""
    src_dir = DOTCLAUDE_HOME / category
    if not src_dir.is_dir():
        return []
    if category == "skills":
        # Skills are directories containing SKILL.md
        return sorted(
            d for d in src_dir.iterdir()
            if d.is_dir() and (d / "SKILL.md").is_file()
        )
    return sorted(f for f in src_dir.iterdir() if f.suffix == ".md" and f.is_file())


def item_name(path):
    """Get display name from a path (directory name for skills, stem for files)."""
    if path.is_dir():
        return path.name
    return path.stem


def home_relative(path: Path) -> str:
    """Convert an absolute path to $HOME-relative string if possible."""
    home = str(Path.home())
    s = str(path)
    if s.startswith(home):
        return "$HOME" + s[len(home):]
    return s


def make_var_name(name: str) -> str:
    """Convert a directory name to a bash variable name (e.g. my-project -> MY_PROJECT_ROOT)."""
    return name.upper().replace("-", "_").replace(".", "_") + "_ROOT"


def available_profiles():
    """List available profile names in the volumes directory."""
    if not VOLUMES_DIR.is_dir():
        return []
    return sorted(
        f.name for f in VOLUMES_DIR.iterdir()
        if f.is_file() and not f.name.startswith(".")
    )


def detect_profile() -> str:
    """Detect the current profile via env var, directory basename, or default.

    Fallback chain:
      1. $DOTCLAUDE_PROFILE env var (set via .envrc / direnv / manual export)
      2. lowercase(basename(cwd)) if a matching profile file exists
      3. "default"
    """
    env_profile = os.environ.get("DOTCLAUDE_PROFILE")
    if env_profile and (VOLUMES_DIR / env_profile).is_file():
        return env_profile

    basename_profile = Path.cwd().name.lower()
    if (VOLUMES_DIR / basename_profile).is_file():
        return basename_profile

    return "default"


def ensure_claude_dir(target):
    """Create .claude/ and category subdirs as needed."""
    claude_dir = target / ".claude"
    claude_dir.mkdir(exist_ok=True)
    return claude_dir


def gitignore_entry(target, rel_path):
    """Add a path to .gitignore if not already present."""
    gitignore = target / ".gitignore"
    entry = f"/{rel_path}"

    if gitignore.exists():
        existing = gitignore.read_text()
        if entry in existing.splitlines():
            return
        # Append with newline safety
        if existing and not existing.endswith("\n"):
            existing += "\n"
        gitignore.write_text(existing + entry + "\n")
    else:
        gitignore.write_text(entry + "\n")

    print(f"  gitignore {entry}")


def link_item(src, dest, project_root, force=False):
    """Symlink a single file or directory. Returns True if linked."""
    if dest.exists() or dest.is_symlink():
        if not force:
            print(f"  skip {dest.name} (exists, use -f to overwrite)")
            return False
        dest.unlink()

    dest.symlink_to(src)
    print(f"  link {dest.name} -> {src}")

    # Add to .gitignore
    rel = dest.relative_to(project_root)
    gitignore_entry(project_root, rel)

    return True


def cmd_init(args):
    target = Path(args.directory).resolve()

    if not target.is_dir():
        print(f"Directory does not exist: {target}")
        sys.exit(1)

    if not DOTCLAUDE_HOME.is_dir():
        print(f"DOTCLAUDE_HOME not found: {DOTCLAUDE_HOME}")
        print("Set DOTCLAUDE_HOME to your dotclaude repo path.")
        sys.exit(1)

    claude_dir = ensure_claude_dir(target)
    print(f"Created {claude_dir}/")

    for cat in CATEGORIES:
        (claude_dir / cat).mkdir(exist_ok=True)

    claude_md = target / "CLAUDE.md"
    if claude_md.exists():
        print("  skip CLAUDE.md (already exists)")
    else:
        claude_md.write_text(CLAUDE_MD_TEMPLATE)
        print("  created CLAUDE.md")

    # Write .envrc if a matching profile exists
    profile_name = target.name.lower()
    if (VOLUMES_DIR / profile_name).is_file():
        envrc = target / ".envrc"
        envrc_line = f"export DOTCLAUDE_PROFILE={profile_name}"
        if envrc.exists():
            existing = envrc.read_text()
            if "DOTCLAUDE_PROFILE" not in existing:
                if not existing.endswith("\n"):
                    existing += "\n"
                envrc.write_text(existing + envrc_line + "\n")
                print(f"  appended DOTCLAUDE_PROFILE to .envrc")
            else:
                print(f"  skip .envrc (DOTCLAUDE_PROFILE already set)")
        else:
            envrc.write_text(envrc_line + "\n")
            print(f"  created .envrc (DOTCLAUDE_PROFILE={profile_name})")

    if args.what == "all":
        print()
        for cat in CATEGORIES:
            items = available_items(cat)
            if not items:
                continue
            dest_dir = claude_dir / cat
            print(f"{cat}/")
            for src in items:
                link_item(src, dest_dir / src.name, target, args.force)

    print("\nDone.")


def cmd_add(args):
    target = Path(args.directory).resolve()
    claude_dir = target / ".claude"

    if not claude_dir.is_dir():
        print("Not initialized. Run: dotclaude init")
        sys.exit(1)

    if not DOTCLAUDE_HOME.is_dir():
        print(f"DOTCLAUDE_HOME not found: {DOTCLAUDE_HOME}")
        sys.exit(1)

    category = args.category

    # Add all categories
    if category == "all":
        for cat in CATEGORIES:
            items = available_items(cat)
            if not items:
                continue
            dest_dir = claude_dir / cat
            dest_dir.mkdir(exist_ok=True)
            print(f"\n{cat}/")
            for src in items:
                link_item(src, dest_dir / src.name, target, args.force)
        return

    if category not in CATEGORIES:
        print(f"Unknown category: {category}")
        print(f"Choose from: {', '.join(CATEGORIES)}, all")
        sys.exit(1)

    items = available_items(category)
    if not items:
        print(f"No items available in {category}/")
        return

    dest_dir = claude_dir / category
    dest_dir.mkdir(exist_ok=True)

    names = args.names

    # Add everything in this category
    if not names or "all" in names:
        print(f"{category}/")
        for src in items:
            link_item(src, dest_dir / src.name, target, args.force)
        return

    # Cherry-pick specific items
    items_by_name = {item_name(f): f for f in items}
    print(f"{category}/")
    for name in names:
        if name in items_by_name:
            link_item(items_by_name[name], dest_dir / items_by_name[name].name, target, args.force)
        else:
            print(f"  not found: {name}")
            print(f"  available: {', '.join(items_by_name.keys())}")


def cmd_remove(args):
    target = Path(args.directory).resolve()
    claude_dir = target / ".claude"

    if not claude_dir.is_dir():
        print("Not initialized.")
        sys.exit(1)

    category = args.category
    if category not in CATEGORIES:
        print(f"Unknown category: {category}")
        sys.exit(1)

    dest_dir = claude_dir / category
    if not dest_dir.is_dir():
        print(f"No {category}/ directory.")
        return

    for name in args.names:
        # Try both file (agents: name.md) and directory (skills: name)
        candidates = [dest_dir / f"{name}.md", dest_dir / name]
        found = False
        for m in candidates:
            if m.exists() or m.is_symlink():
                found = True
                if m.is_symlink():
                    m.unlink()
                    print(f"  removed {m.name}")
                else:
                    print(f"  skip {m.name} (not a symlink, remove manually)")
                break
        if not found:
            print(f"  not found: {name}")


def cmd_list(args):
    if not DOTCLAUDE_HOME.is_dir():
        print(f"DOTCLAUDE_HOME not found: {DOTCLAUDE_HOME}")
        sys.exit(1)

    categories = [args.category] if args.category else CATEGORIES

    for cat in categories:
        items = available_items(cat)
        if not items:
            continue
        print(f"\n{cat}/")
        for f in items:
            print(f"  {item_name(f)}")
    print()


def cmd_status(args):
    target = Path(args.directory).resolve()
    claude_dir = target / ".claude"

    if not claude_dir.is_dir():
        print("Not initialized. Run: dotclaude init")
        return

    print(f"Project:        {target}")
    print(f"DOTCLAUDE_HOME: {DOTCLAUDE_HOME}")

    for cat in CATEGORIES:
        dest_dir = claude_dir / cat
        if not dest_dir.is_dir():
            continue

        # Collect both .md files and directories (skills)
        entries = sorted(
            [f for f in dest_dir.iterdir() if f.suffix == ".md" or f.is_dir()],
            key=lambda f: f.name,
        )
        if not entries:
            continue

        print(f"\n{cat}/")
        for f in entries:
            if f.is_symlink():
                link = f.readlink()
                ok = f.resolve().exists()
                status = f"-> {link}" if ok else f"BROKEN -> {link}"
            else:
                status = "local"
            print(f"  {item_name(f):<20} {status}")

    claude_md = target / "CLAUDE.md"
    print(f"\nCLAUDE.md: {'exists' if claude_md.exists() else 'missing'}")


def cmd_profile(args):
    action = getattr(args, "action", None)
    if action == "create":
        cmd_profile_create(args)
    elif action == "list":
        cmd_profile_list()
    else:
        # No subcommand: show current profile
        print(detect_profile())


def cmd_profile_list():
    profiles = available_profiles()
    if not profiles:
        print("No profiles found.")
        return
    current = detect_profile()
    for name in profiles:
        marker = " *" if name == current else ""
        print(f"  {name}{marker}")


def cmd_profiles(args):
    cmd_profile_list()


def cmd_profile_create(args):
    name = (args.name or Path.cwd().name).lower()
    profile_path = VOLUMES_DIR / name

    if profile_path.exists() and not args.force:
        print(f"Profile '{name}' already exists at {profile_path}")
        print("Use -f to overwrite.")
        sys.exit(1)

    VOLUMES_DIR.mkdir(parents=True, exist_ok=True)

    cwd = Path.cwd().resolve()
    var_name = make_var_name(name)
    dotclaude_display = home_relative(DOTCLAUDE_HOME)
    dir_display = home_relative(cwd)

    var_defs = f"DOTCLAUDE={dotclaude_display}\n{var_name}={dir_display}"
    vol_entry = "${" + var_name + "}:${" + var_name + "}:rw"
    volume_entries = "${DOTCLAUDE}:${DOTCLAUDE}:rw\n" + vol_entry + "\n/var/ccache:/ccache"

    content = PROFILE_TEMPLATE.replace("__VAR_DEFS__", var_defs).replace(
        "__VOLUME_ENTRIES__", volume_entries
    )
    profile_path.write_text(content)
    print(f"Created profile '{name}' at {profile_path}")


def cmd_volume(args):
    if args.action == "add":
        cmd_volume_add(args)
    else:
        print("Usage: dotclaude volume add [path] [--profile name]")
        sys.exit(1)


def cmd_volume_add(args):
    profile_name = (args.profile or Path.cwd().name).lower()
    vol_path = Path(args.path or ".").resolve()
    profile_path = VOLUMES_DIR / profile_name

    if not vol_path.is_dir():
        print(f"Error: '{vol_path}' is not a valid directory")
        sys.exit(1)

    if not profile_path.exists():
        print(f"Profile '{profile_name}' does not exist.")
        print(f"Create it with: dotclaude profile create {profile_name}")
        sys.exit(1)

    content = profile_path.read_text()
    dir_display = home_relative(vol_path)

    # Check if path is already mounted (exact variable assignment match)
    if f"={dir_display}\n" in content or f"={str(vol_path)}\n" in content:
        print(f"'{dir_display}' is already mounted in profile '{profile_name}'")
        return

    var_name = make_var_name(vol_path.name)

    # Handle variable name collision
    if f"\n{var_name}=" in content or content.startswith(f"{var_name}="):
        i = 2
        while f"{var_name}_{i}=" in content:
            i += 1
        var_name = f"{var_name}_{i}"

    vol_entry = "${" + var_name + "}:${" + var_name + "}:rw"

    # Insert variable definition before VOLUME_LIST and volume entry before EOF
    lines = content.split("\n")
    result = []
    for line in lines:
        if line.startswith("VOLUME_LIST="):
            result.append(f"{var_name}={dir_display}")
            result.append("")
        if line == "EOF":
            result.append(vol_entry)
        result.append(line)

    profile_path.write_text("\n".join(result))
    print(f"Added '{dir_display}' to profile '{profile_name}'")


def main():
    parser = argparse.ArgumentParser(
        prog="dotclaude",
        description="Bootstrap .claude/ configuration in any project",
    )
    sub = parser.add_subparsers(dest="command")

    # init
    p_init = sub.add_parser("init", help="Initialize .claude/ skeleton")
    p_init.add_argument("what", nargs="?", default=None, help="'all' to also install everything")
    p_init.add_argument("-C", "--directory", default=".", help="Project directory")
    p_init.add_argument("-f", "--force", action="store_true", help="Overwrite existing symlinks")

    # add
    p_add = sub.add_parser("add", help="Add agents/commands/rules/skills")
    p_add.add_argument("category", help="Category: agents, commands, rules, skills, or all")
    p_add.add_argument("names", nargs="*", help="Item names (omit or 'all' for everything)")
    p_add.add_argument("-f", "--force", action="store_true", help="Overwrite existing symlinks")
    p_add.add_argument("-C", "--directory", default=".", help="Project directory")

    # remove
    p_rm = sub.add_parser("remove", help="Remove installed items")
    p_rm.add_argument("category", help="Category: agents, commands, rules, skills")
    p_rm.add_argument("names", nargs="+", help="Item names to remove")
    p_rm.add_argument("-C", "--directory", default=".", help="Project directory")

    # list
    p_list = sub.add_parser("list", help="List available items in DOTCLAUDE_HOME")
    p_list.add_argument("category", nargs="?", help="Filter by category")

    # status
    p_status = sub.add_parser("status", help="Show what's installed in current project")
    p_status.add_argument("directory", nargs="?", default=".", help="Project directory (default: .)")

    # profile
    p_profile = sub.add_parser("profile", help="Manage volume profiles")
    p_profile_sub = p_profile.add_subparsers(dest="action")
    p_profile_create = p_profile_sub.add_parser("create", help="Create a new volume profile")
    p_profile_create.add_argument("name", nargs="?", help="Profile name (default: current dir name)")
    p_profile_create.add_argument("-f", "--force", action="store_true", help="Overwrite existing profile")
    p_profile_sub.add_parser("list", help="List available profiles")

    # profiles (alias for profile list)
    sub.add_parser("profiles", help="List available volume profiles")

    # volume
    p_volume = sub.add_parser("volume", help="Manage volume mappings")
    p_volume_sub = p_volume.add_subparsers(dest="action")
    p_volume_add = p_volume_sub.add_parser("add", help="Add a volume mapping to a profile")
    p_volume_add.add_argument("path", nargs="?", help="Path to mount (default: current dir)")
    p_volume_add.add_argument("-p", "--profile", help="Profile name (default: current dir name)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    {
        "init": cmd_init,
        "add": cmd_add,
        "remove": cmd_remove,
        "list": cmd_list,
        "status": cmd_status,
        "profile": cmd_profile,
        "profiles": cmd_profiles,
        "volume": cmd_volume,
    }[args.command](args)


if __name__ == "__main__":
    main()
