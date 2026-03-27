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
    }[args.command](args)


if __name__ == "__main__":
    main()
