#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""Orchestrator - Task and idea manager backed by SQLite, with claude-code integration."""

import argparse
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

DOTCLAUDE_HOME = Path(os.environ.get("DOTCLAUDE_HOME", Path.home() / ".orchestrator"))
DB_DIR = DOTCLAUDE_HOME
DB_PATH = DB_DIR / "orchestrator.db"

STATUSES = [
    "idea",
    "not-implemented",
    "in-progress",
    "needs-review",
    "done",
    "archived",
    "discarded",
]

STATUS_ICONS = {
    "idea": "💡",
    "not-implemented": "📋",
    "in-progress": "🔧",
    "needs-review": "👀",
    "done": "✅",
    "archived": "📦",
    "discarded": "🗑️",
}


def get_db():
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            directory TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY,
            project_id INTEGER NOT NULL REFERENCES projects(id),
            description TEXT NOT NULL,
            type TEXT NOT NULL DEFAULT 'task',
            status TEXT NOT NULL DEFAULT 'not-implemented',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );
    """)
    conn.commit()
    return conn


def resolve_project(conn, description=None, project_name=None):
    """Resolve project: explicit name > name found in description > current directory."""
    if project_name:
        row = conn.execute(
            "SELECT * FROM projects WHERE name = ?", (project_name,)
        ).fetchone()
        if row:
            return row
        conn.execute(
            "INSERT INTO projects (name, directory) VALUES (?, ?)",
            (project_name, os.getcwd()),
        )
        conn.commit()
        return conn.execute(
            "SELECT * FROM projects WHERE name = ?", (project_name,)
        ).fetchone()

    # Check if any known project name appears in description
    if description:
        projects = conn.execute(
            "SELECT * FROM projects ORDER BY length(name) DESC"
        ).fetchall()
        for p in projects:
            if p["name"].lower() in description.lower():
                return p

    # Auto-detect from current directory
    cwd = os.getcwd()
    row = conn.execute(
        "SELECT * FROM projects WHERE directory = ?", (cwd,)
    ).fetchone()
    if row:
        return row

    # Auto-register current directory
    name = os.path.basename(cwd)
    existing = conn.execute(
        "SELECT 1 FROM projects WHERE name = ?", (name,)
    ).fetchone()
    if existing:
        i = 2
        while conn.execute(
            "SELECT 1 FROM projects WHERE name = ?", (f"{name}-{i}",)
        ).fetchone():
            i += 1
        name = f"{name}-{i}"

    conn.execute(
        "INSERT INTO projects (name, directory) VALUES (?, ?)", (name, cwd)
    )
    conn.commit()
    return conn.execute(
        "SELECT * FROM projects WHERE directory = ?", (cwd,)
    ).fetchone()


def cmd_create(args):
    conn = get_db()
    project = resolve_project(conn, args.description, args.project)
    conn.execute(
        "INSERT INTO tasks (project_id, description, type, status) VALUES (?, ?, 'task', 'not-implemented')",
        (project["id"], args.description),
    )
    conn.commit()
    task_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    print(f"Task #{task_id} created in project '{project['name']}'")


def cmd_idea(args):
    conn = get_db()
    project = resolve_project(conn, args.description, args.project)
    conn.execute(
        "INSERT INTO tasks (project_id, description, type, status) VALUES (?, ?, 'idea', 'idea')",
        (project["id"], args.description),
    )
    conn.commit()
    task_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    print(f"Idea #{task_id} created in project '{project['name']}'")


def print_tasks(rows):
    if not rows:
        print("No tasks found.")
        return
    for r in rows:
        icon = STATUS_ICONS.get(r["status"], "?")
        print(
            f"  #{r['id']:<4} {icon} {r['status']:<16} ({r['type']:<4})  {r['description']}"
        )


def cmd_list(args):
    conn = get_db()

    if args.all:
        rows = conn.execute("""
            SELECT t.*, p.name as project_name FROM tasks t
            JOIN projects p ON t.project_id = p.id
            ORDER BY p.name, t.created_at DESC
        """).fetchall()
        if not rows:
            print("No tasks found.")
            return
        current_project = None
        for r in rows:
            if r["project_name"] != current_project:
                current_project = r["project_name"]
                print(f"\n  {current_project}:")
            icon = STATUS_ICONS.get(r["status"], "?")
            print(
                f"    #{r['id']:<4} {icon} {r['status']:<16} ({r['type']:<4})  {r['description']}"
            )
        print()
        return

    if args.project:
        project = conn.execute(
            "SELECT * FROM projects WHERE name = ?", (args.project,)
        ).fetchone()
        if not project:
            print(f"Project '{args.project}' not found.")
            sys.exit(1)
        project_id = project["id"]
    else:
        cwd = os.getcwd()
        project = conn.execute(
            "SELECT * FROM projects WHERE directory = ?", (cwd,)
        ).fetchone()
        if not project:
            print(
                "No project registered for current directory. Use --all to list everything."
            )
            return
        project_id = project["id"]

    query = """
        SELECT t.*, p.name as project_name FROM tasks t
        JOIN projects p ON t.project_id = p.id
        WHERE t.project_id = ?
    """
    params = [project_id]

    if args.status:
        query += " AND t.status = ?"
        params.append(args.status)

    query += " ORDER BY t.created_at DESC"
    rows = conn.execute(query, params).fetchall()
    print_tasks(rows)


def cmd_work(args):
    conn = get_db()
    task = conn.execute(
        """
        SELECT t.*, p.name as project_name, p.directory as project_dir FROM tasks t
        JOIN projects p ON t.project_id = p.id
        WHERE t.id = ?
    """,
        (args.task_id,),
    ).fetchone()

    if not task:
        print(f"Task #{args.task_id} not found.")
        sys.exit(1)

    project_dir = task["project_dir"]
    if not os.path.isdir(project_dir):
        print(f"Project directory does not exist: {project_dir}")
        sys.exit(1)

    conn.execute(
        "UPDATE tasks SET status = 'in-progress', updated_at = datetime('now') WHERE id = ?",
        (args.task_id,),
    )
    conn.commit()

    print(f"Working on #{args.task_id}: {task['description']}")
    print(f"Project: {task['project_name']} ({project_dir})")
    print()

    prompt = f"Work on this task: {task['description']}"
    result = subprocess.run(["claude", "-p", prompt], cwd=project_dir)

    if result.returncode == 0:
        conn.execute(
            "UPDATE tasks SET status = 'needs-review', updated_at = datetime('now') WHERE id = ?",
            (args.task_id,),
        )
        conn.commit()
        print(f"\nTask #{args.task_id} → needs-review")
    else:
        print(f"\nclaude exited with code {result.returncode}, task remains in-progress")


def cmd_status(args):
    conn = get_db()
    if args.new_status not in STATUSES:
        print(f"Invalid status. Choose from: {', '.join(STATUSES)}")
        sys.exit(1)

    task = conn.execute(
        "SELECT * FROM tasks WHERE id = ?", (args.task_id,)
    ).fetchone()
    if not task:
        print(f"Task #{args.task_id} not found.")
        sys.exit(1)

    conn.execute(
        "UPDATE tasks SET status = ?, updated_at = datetime('now') WHERE id = ?",
        (args.new_status, args.task_id),
    )
    conn.commit()
    icon = STATUS_ICONS.get(args.new_status, "?")
    print(f"Task #{args.task_id} → {icon} {args.new_status}")


def cmd_projects(args):
    conn = get_db()
    rows = conn.execute("""
        SELECT p.*, COUNT(t.id) as task_count
        FROM projects p
        LEFT JOIN tasks t ON t.project_id = p.id
        GROUP BY p.id
        ORDER BY p.name
    """).fetchall()
    if not rows:
        print("No projects registered.")
        return
    for r in rows:
        print(f"  {r['name']:<20} {r['task_count']:>3} tasks   {r['directory']}")


def main():
    parser = argparse.ArgumentParser(
        prog="orchestrator",
        description="Task and idea manager with claude-code integration",
    )
    sub = parser.add_subparsers(dest="command")

    p_create = sub.add_parser("create", help="Create a task")
    p_create.add_argument("description")
    p_create.add_argument("-p", "--project", help="Project name")

    p_idea = sub.add_parser("idea", help="Create an idea")
    p_idea.add_argument("description")
    p_idea.add_argument("-p", "--project", help="Project name")

    p_list = sub.add_parser("list", help="List tasks")
    p_list.add_argument("project", nargs="?", help="Project name (default: current dir)")
    p_list.add_argument("--all", action="store_true", help="List across all projects")
    p_list.add_argument(
        "-s", "--status", choices=STATUSES, help="Filter by status"
    )

    p_work = sub.add_parser("work", help="Work on a task using claude-code")
    p_work.add_argument("task_id", type=int)

    p_status = sub.add_parser("status", help="Update task status")
    p_status.add_argument("task_id", type=int)
    p_status.add_argument("new_status", choices=STATUSES)

    sub.add_parser("projects", help="List all projects")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    handlers = {
        "create": cmd_create,
        "idea": cmd_idea,
        "list": cmd_list,
        "work": cmd_work,
        "status": cmd_status,
        "projects": cmd_projects,
    }
    handlers[args.command](args)


if __name__ == "__main__":
    main()
