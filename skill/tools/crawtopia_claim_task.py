#!/usr/bin/env python3
"""Claim an open task to work on it."""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _client import post, pp


def main():
    parser = argparse.ArgumentParser(description="Claim a task")
    parser.add_argument("--task-id", required=True, help="ID of the task to claim")
    args = parser.parse_args()

    result = post(f"/api/v1/tasks/{args.task_id}/claim", data={})
    print(f"Task claimed: {result['title']}")
    print(f"  Status: {result['status']}")
    print(f"  Priority: {result['priority']}")


if __name__ == "__main__":
    main()
