#!/usr/bin/env python3
"""Mark an in-progress task as complete."""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _client import post, pp


def main():
    parser = argparse.ArgumentParser(description="Complete a task")
    parser.add_argument("--task-id", required=True, help="ID of the task to complete")
    parser.add_argument("--result", help="Summary of work done")
    args = parser.parse_args()

    data = {}
    if args.result:
        data["result"] = args.result

    result = post(f"/api/v1/tasks/{args.task_id}/complete", data=data)
    print(f"Task completed: {result['title']}")


if __name__ == "__main__":
    main()
