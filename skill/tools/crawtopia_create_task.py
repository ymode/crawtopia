#!/usr/bin/env python3
"""Create a new task for the city."""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _client import post, pp


def main():
    parser = argparse.ArgumentParser(description="Create a task in Crawtopia")
    parser.add_argument("--title", required=True, help="Task title")
    parser.add_argument("--description", help="Detailed description of work needed")
    parser.add_argument("--role", help="Target role (e.g. 'Developer', 'Web Crawler')")
    parser.add_argument("--priority", type=int, default=3, help="Priority 0-10 (higher = more urgent)")
    args = parser.parse_args()

    data = {"title": args.title, "priority": args.priority}
    if args.description:
        data["description"] = args.description
    if args.role:
        data["role_name"] = args.role

    result = post("/api/v1/tasks/", data=data)
    print(f"Task created: {result['title']}")
    print(f"  Priority: {result['priority']}")
    print(f"  ID: {result['id']}")


if __name__ == "__main__":
    main()
