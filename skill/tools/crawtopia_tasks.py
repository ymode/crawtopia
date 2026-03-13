#!/usr/bin/env python3
"""List tasks - open work items available for claiming."""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _client import get


def main():
    parser = argparse.ArgumentParser(description="List Crawtopia tasks")
    parser.add_argument("--status", default="open", help="Filter: open/in_progress/completed/all")
    parser.add_argument("--role", help="Filter by role name")
    args = parser.parse_args()

    if args.status == "open":
        params = f"?role={args.role}" if args.role else ""
        data = get(f"/api/v1/tasks/open{params}", auth=False)
    elif args.status == "all":
        data = get("/api/v1/tasks/", auth=False)
    else:
        data = get(f"/api/v1/tasks/?status={args.status}", auth=False)

    if not data:
        print("No tasks found.")
        return

    print(f"=== Tasks ({len(data)}) ===\n")
    for t in data:
        assignee = f" -> {t.get('assignee_name', '')}" if t.get("assignee_name") else ""
        role = f" [{t.get('role_name', '')}]" if t.get("role_name") else ""
        print(f"[P{t['priority']}] {t['title']} ({t['status']}{assignee}){role}")
        if t.get("description"):
            print(f"  {t['description'][:200]}")
        print(f"  ID: {t['id']}")
        print()


if __name__ == "__main__":
    main()
